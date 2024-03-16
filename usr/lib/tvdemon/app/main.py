# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2024 Dmitriy Yefremov <https://github.com/DYefremov>
#               2020-2022 Linux Mint <root@linuxmint.com>
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


import sys

from .common import *

PROVIDER_OBJ, PROVIDER_NAME = range(2)
PROVIDER_TYPE_ID, PROVIDER_TYPE_NAME = range(2)

GROUP_OBJ, GROUP_NAME = range(2)
CHANNEL_OBJ, CHANNEL_NAME, CHANNEL_LOGO = range(3)

COL_PROVIDER_NAME, COL_PROVIDER = range(2)

PROVIDER_TYPE_URL = "url"
PROVIDER_TYPE_LOCAL = "local"
PROVIDER_TYPE_XTREAM = "xtream"

UPDATE_BR_INTERVAL = 5


class ChannelWidget(Gtk.ListBoxRow):
    """ A custom widget for displaying and holding channel data. """

    TARGET = "GTK_LIST_BOX_ROW"

    def __init__(self, channel, logo, **kwargs):
        super().__init__(**kwargs)
        self._channel = channel
        self.set_tooltip_text(channel.name)
        self.label = Gtk.Label(channel.name, max_width_chars=30, ellipsize=Pango.EllipsizeMode.END)
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.pack_start(logo, False, False, 6)
        self.box.pack_start(self.label, False, False, 6)
        frame = Gtk.Frame()
        frame.add(self.box)
        self.add(frame)

        self.show_all()

    @property
    def channel(self):
        return self._channel

    @channel.setter
    def channel(self, value):
        self._channel = value


class GroupWidget(Gtk.FlowBoxChild):
    """ A custom widget for displaying and holding group data. """

    def __init__(self, data, name, logo, orientation=Gtk.Orientation.HORIZONTAL, **kwargs):
        super().__init__(**kwargs)
        self._data = data

        self.name = name
        self.logo = logo

        self.box = Gtk.Box(border_width=6, orientation=orientation)
        self.box.pack_start(logo, False, False, 0) if logo else None
        self.label = Gtk.Label(name, max_width_chars=30, ellipsize=Pango.EllipsizeMode.END)
        self.box.pack_start(self.label, False, False, 0)
        self.box.set_spacing(6)
        frame = Gtk.Frame()
        frame.add(self.box)
        self.add(frame)

        self.tooltip_logo = None
        self.set_has_tooltip(logo)
        self.connect("query-tooltip", self.on_query_tooltip)

        self.show_all()

    @property
    def data(self):
        return self._data

    def on_query_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        if not widget.tooltip_logo:
            path = widget.data.logo_path
            try:
                self.tooltip_logo = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, -1, 96, 1) if path else None
            except GLib.Error:
                pass  # NOP

        tooltip.set_icon(self.tooltip_logo)
        tooltip.set_text(widget.name)
        return True


class FavGroupWidget(GroupWidget):
    def __init__(self, data, name, logo, **kwargs):
        super().__init__(data, name, logo, **kwargs)

        self.entry = Gtk.Entry(text=name, has_frame=False)
        self.box.pack_start(self.entry, False, False, 0)
        self.entry.bind_property("visible", self.label, "visible", 4)
        self.entry.connect("activate", self.on_activate)

    def on_activate(self, entry):
        text = entry.get_text()
        self.label.set_text(text)
        self.data.name = text
        entry.set_visible(False)


@Gtk.Template(filename=f'{UI_PATH}app.ui')
class AppWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'AppWindow'

    # Start page.
    tv_logo = Gtk.Template.Child("tv_logo")
    movies_logo = Gtk.Template.Child("movies_logo")
    series_logo = Gtk.Template.Child("series_logo")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Start page.
        self.tv_logo.set_from_file(f"{UI_PATH}pictures/tv.svg")
        self.movies_logo.set_from_file(f"{UI_PATH}pictures/movies.svg")
        self.series_logo.set_from_file(f"{UI_PATH}pictures/series.svg")


class Application(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                         **kwargs)
        self.add_main_option("log", ord("l"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "", None)
        self.add_main_option("debug", ord("d"), GLib.OptionFlags.NONE, GLib.OptionArg.STRING, "", None)

        self.app_window = None
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        if not self.app_window:
            self.app_window = AppWindow(application=app)

        self.app_window.present()

    def do_command_line(self, command_line):
        """ Processing command line parameters. """
        options = command_line.get_options_dict()
        options = options.end().unpack()

        if "log" in options:
            from .common import init_logger
            init_logger()

        if "debug" in options:
            log(f"Debug mode not implemented yet!")

        self.activate()
        return 0

    def do_shutdown(self):
        """  Performs shutdown tasks. """
        log("Exiting...")
        Gtk.Application.do_shutdown(self)


def run_app():
    app = Application()
    app.run(sys.argv)


if __name__ == "__main__":
    pass
