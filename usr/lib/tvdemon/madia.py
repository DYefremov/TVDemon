# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 Dmitriy Yefremov <https://github.com/DYefremov>
#
#
# This file is part of TVDemon.
#
# TVDemon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# TVDemon is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with TVDemon  If not, see <http://www.gnu.org/licenses/>.
#

""" Basic playback module. """
from gi.repository import GLib, GObject

from common import _, idle_function

AUDIO_SAMPLE_FORMATS = {"u16": "unsigned 16 bits",
                        "s16": "signed 16 bits",
                        "s16p": "signed 16 bits, planar",
                        "flt": "float",
                        "float": "float",
                        "fltp": "float, planar",
                        "floatp": "float, planar",
                        "dbl": "double",
                        "dblp": "double, planar"}


class Player(GObject.GObject):
    """ Wrapper class for the media library. """

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self._app = app
        self._player = None

        GObject.signal_new("volume-changed", self, GObject.SIGNAL_RUN_LAST,
                           GObject.TYPE_PYOBJECT, (GObject.TYPE_PYOBJECT,))

        self._video_properties = {}
        self._audio_properties = {}
        self._video_bitrates = []
        self._audio_bitrates = []

        self._lib = app.settings.get_string("playback-library")

    @property
    def current_lib(self):
        return self._lib

    @property
    def video_properties(self):
        return self._video_properties

    @property
    def audio_properties(self):
        return self._audio_properties

    @property
    def video_bitrates(self):
        return self._video_properties

    @property
    def audio_bitrates(self):
        return self._audio_bitrates

    def play(self, url):
        pass

    def pause(self):
        pass

    def stop(self):
        pass

    def set_volume(self, value):
        pass

    def volume_up(self):
        pass

    def volume_down(self):
        pass

    def get_xid(self):
        return self._app.drawing_area.get_window().get_xid()

    @staticmethod
    def get_instance(app):
        lib = app.settings.get_string("playback-library")
        if lib == "MPV":
            return MpvPlayer(app)
        raise NameError(f"There is no such [{lib}] implementation.")


class MpvPlayer(Player):
    """ Wrapper class for the MPV library. """

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self._player = self.get_mpv()
        self._volume_value = 100.0

    def get_mpv(self):
        options = {}
        try:
            mpv_options = self._app.settings.get_string("mpv-options")
            if "=" in mpv_options:
                pairs = mpv_options.split()
                for pair in pairs:
                    key, value = pair.split("=")
                    options[key] = value
        except Exception as e:
            print("Could not parse MPV options!")
            print(e)

        options["user_agent"] = self._app.settings.get_string("user-agent")
        options["referrer"] = self._app.settings.get_string("http-referer")

        try:
            import mpv
        except ImportError as e:
            print(e)
            GLib.idle_add(self._app.emit, "error", f"MPV initialization error: {e}.")
        else:
            player = mpv.MPV(**options,
                             input_cursor=False,
                             cursor_autohide="no",
                             input_default_bindings=False,
                             ytdl=True,
                             wid=str(self.get_xid()))

            @player.event_callback(mpv.MpvEventID.END_FILE)
            def on_end(event):
                event = event.as_dict(mpv.strict_decoder)
                if event.get("reason", None) == "error":
                    error = event.get("file_error", _("Can't Playback!")).capitalize()
                    GLib.idle_add(self._app.emit, "error", f"{error}.")

            player.observe_property("video-params", self.on_video_params)
            player.observe_property("video-format", self.on_video_format)
            player.observe_property("audio-params", self.on_audio_params)
            player.observe_property("audio-codec", self.on_audio_codec)
            player.observe_property("video-bitrate", self.on_bitrate)
            player.observe_property("audio-bitrate", self.on_bitrate)
            player.observe_property("volume", self.on_volume)

            return player

    def play(self, url):
        self.before_play()
        self._player.play(url)
        self._player.wait_until_playing()

    def pause(self):
        self._player.pause = not self._player.pause

    def stop(self):
        self._player.stop()

    def set_volume(self, value):
        self._volume_value = value
        self._player._set_property("volume", self._volume_value)

    def volume_up(self):
        self._volume_value += 5.0
        self._volume_value = self._volume_value if self._volume_value <= 100 else 100
        self._player._set_property("volume", self._volume_value)
        self.emit("volume-changed", self._volume_value)

    def volume_down(self):
        self._volume_value -= 5.0
        self._volume_value = self._volume_value if self._volume_value > 0 else 0
        self._player._set_property("volume", self._volume_value)
        self.emit("volume-changed", self._volume_value)

    @idle_function
    def before_play(self):
        self._video_properties.clear()
        self._video_properties[_("General")] = {}
        self._video_properties[_("Color")] = {}

        self._audio_properties.clear()
        self._audio_properties[_("General")] = {}
        self._audio_properties[_("Layout")] = {}

        self._video_bitrates.clear()
        self._audio_bitrates.clear()

    @idle_function
    def on_bitrate(self, prop, bitrate):
        if not bitrate or prop not in ["video-bitrate", "audio-bitrate"]:
            return

        # Only update the bitrates when the info window is open unless we don't have any data yet.
        if _("Average Bitrate") in self._video_properties:
            if _("Average Bitrate") in self._audio_properties:
                if not self._app.info_window.props.visible:
                    return

        rates = {"video": self._video_bitrates, "audio": self._audio_bitrates}
        rate = "video"
        if prop == "audio-bitrate":
            rate = "audio"

        rates[rate].append(int(bitrate) / 1000.0)
        rates[rate] = rates[rate][-30:]
        br = sum(rates[rate]) / float(len(rates[rate]))

        if rate == "video":
            self._video_properties[_("General")][_("Average Bitrate")] = f"{br:.0f} Kbps"
        else:
            self._audio_properties[_("General")][_("Average Bitrate")] = f"{br:.0f} Kbps"

    @idle_function
    def on_video_params(self, prop, params):
        if not params or not type(params) == dict:
            return
        if "w" in params and "h" in params:
            self._video_properties[_("General")][_("Dimensions")] = f"{params['w']}x{params['h']}"
        if "aspect" in params:
            aspect = round(float(params["aspect"]), 2)
            self._video_properties[_("General")][_("Aspect")] = f"{aspect}"
        if "pixelformat" in params:
            self._video_properties[_("Color")][_("Pixel Format")] = params["pixelformat"]
        if "gamma" in params:
            self._video_properties[_("Color")][_("Gamma")] = params["gamma"]
        if "average-bpp" in params:
            self._video_properties[_("Color")][_("Bits Per Pixel")] = params["average-bpp"]

    @idle_function
    def on_video_format(self, prop, vformat):
        if not vformat:
            return
        self._video_properties[_("General")][_("Codec")] = vformat

    @idle_function
    def on_audio_params(self, prop, params):
        if not params or not type(params) == dict:
            return
        if "channels" in params:
            chans = params["channels"]
            if "5.1" in chans or "7.1" in chans:
                chans += " " + _("surround sound")
            self._audio_properties[_("Layout")][_("Channels")] = chans
        if "samplerate" in params:
            sr = float(params["samplerate"]) / 1000.0
            self._audio_properties[_("General")][_("Sample Rate")] = f"{sr:.1f}.1f KHz"
        if "format" in params:
            fmt = params["format"]
            if fmt in AUDIO_SAMPLE_FORMATS:
                fmt = AUDIO_SAMPLE_FORMATS[fmt]
            self._audio_properties[_("General")][_("Format")] = fmt
        if "channel-count" in params:
            self._audio_properties[_("Layout")][_("Channel Count")] = params["channel-count"]

    @idle_function
    def on_audio_codec(self, prop, codec):
        if not codec:
            return

        self._audio_properties[_("General")][_("Codec")] = codec.split()[0]

    def on_volume(self, prp, value):
        self._volume_value = value


if __name__ == "__main__":
    pass
