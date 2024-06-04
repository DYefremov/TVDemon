# -*- coding: utf-8 -*-
#
# Copyright © 2023 Dmitriy Yefremov <https://github.com/DYefremov>
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
import sys

from .common import GObject, Gtk, Gdk, log


class Player(GObject.GObject):
    """ Wrapper class for the media library. """

    def __init__(self, widget: Gdk.Paintable, **kwargs):
        super().__init__(**kwargs)
        self.widget = widget
        self._player = None

        GObject.signal_new("error", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))
        GObject.signal_new("played", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))

        self._video_properties = {}
        self._audio_properties = {}

    @property
    def current_lib(self):
        return self._lib

    @property
    def video_properties(self):
        return self._video_properties

    @property
    def audio_properties(self):
        return self._audio_properties

    def play(self, url):
        pass

    def pause(self):
        pass

    def stop(self):
        pass

    def set_volume(self, value):
        pass

    def get_volume(self):
        pass

    def volume_up(self):
        pass

    def volume_down(self):
        pass

    def is_playing(self):
        pass

    @staticmethod
    def get_instance(lib: str, widget: Gdk.Paintable):
        if lib == "gst":
            return GstPlayer.get_instance(widget)
        raise NameError(f"There is no such [{lib}] implementation.")


class GstPlayer(Player):
    """ Simple wrapper for GStreamer playbin. """

    __INSTANCE = None

    def __init__(self, widget):
        super().__init__(widget)
        try:
            import gi

            gi.require_version("Gst", "1.0")
            gi.require_version("GstVideo", "1.0")
            gi.require_version("GstPlayer", "1.0")
            from gi.repository import Gst, GstVideo, GstPlayer
            # Initialization of GStreamer.
            # For Arch linux -> gst-plugin-gtk4
            Gst.init(sys.argv)
        except (OSError, ValueError) as e:
            log(f"{__class__.__name__}: Load library error: {e}")
            raise ImportError("No GStreamer is found. Check that it is installed!")
        else:
            self.STATE = Gst.State
            self.STAT_RETURN = Gst.StateChangeReturn
            # -> gst-plugin-gtk4
            gtk_sink = Gst.ElementFactory.make("gtk4paintablesink")
            if gtk_sink:
                self._player = Gst.ElementFactory.make("playbin", "player")
                self._player.set_property("video-sink", gtk_sink)
                self.widget.set_paintable(gtk_sink.props.paintable)
            else:
                msg = f"Error: The Gtk4 plugin for GStreamer is not initialized. Check that it is installed!"
                log(msg)
                raise ImportError(msg)

            bus = self._player.get_bus()
            bus.add_signal_watch()
            bus.connect("message::error", self.on_error)
            bus.connect("message::state-changed", self.on_state_changed)
            bus.connect("message::eos", self.on_eos)

    @classmethod
    def get_instance(cls, widget):
        if not cls.__INSTANCE:
            cls.__INSTANCE = GstPlayer(widget)
        return cls.__INSTANCE

    def get_play_mode(self):
        return self._mode

    def play(self, mrl=None):
        self._player.set_state(self.STATE.READY)
        if not mrl:
            return

        self._player.set_property("uri", mrl)

        log(f"Setting the URL for playback: {mrl}")
        ret = self._player.set_state(self.STATE.PLAYING)

        if ret == self.STAT_RETURN.FAILURE:
            msg = f"ERROR: Unable to set the 'PLAYING' state for '{mrl}'."
            log(msg)
            self.emit("error", msg)

    def stop(self):
        log("Stop playback...")
        self._player.set_state(self.STATE.READY)

    def pause(self):
        state = self._player.get_state(self.STATE.NULL).state
        if state == self.STATE.PLAYING:
            self._player.set_state(self.STATE.PAUSED)
        elif state == self.STATE.PAUSED:
            self._player.set_state(self.STATE.PLAYING)

    def set_volume(self, value: float):
        self._player.set_property("volume", value)

    def get_volume(self):
        return self._player.get_property("volume")

    def volume_up(self):
        volume = self._player.get_property("volume") + 0.1
        self.set_volume(1.0 if volume >= 1 else volume)

    def volume_down(self):
        volume = self._player.get_property("volume") - 0.1
        self.set_volume(0.0 if volume <= 0 else volume)

    def is_playing(self):
        return self._player.get_state(self.STATE.NULL).state is self.STATE.PLAYING

    def release(self):
        if self._player:
            self._player.set_state(self.STATE.NULL)
            self.__INSTANCE = None

    def on_error(self, bus, msg):
        err, dbg = msg.parse_error()
        log(err)
        self.emit("error", "Can't Playback!")

    def on_state_changed(self, bus, msg):
        if not msg.src == self._player:
            # Not from the player.
            return

        old_state, new_state, pending = msg.parse_state_changed()
        if new_state is self.STATE.PLAYING:
            log("Starting playback...")
            self.emit("played", 0)
            self.get_stream_info()

    def on_eos(self, bus, msg):
        """ Called when an end-of-stream message appears. """
        self._player.set_state(self.STATE.READY)

    def get_stream_info(self):
        log("Getting stream info...")
        nr_video = self._player.get_property("n-video")
        for i in range(nr_video):
            # Retrieve the stream's video tags.
            tags = self._player.emit("get-video-tags", i)
            if tags:
                _, cod = tags.get_string("video-codec")
                log(f"Video codec: {cod or 'unknown'}")

        nr_audio = self._player.get_property("n-audio")
        for i in range(nr_audio):
            # Retrieve the stream's video tags.
            tags = self._player.emit("get-audio-tags", i)
            if tags:
                _, cod = tags.get_string("audio-codec")
                log(f"Audio codec: {cod or 'unknown'}")


if __name__ == "__main__":
    pass
