# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2024 Dmitriy Yefremov <https://github.com/DYefremov>
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


@Gtk.Template(filename=f'{UI_PATH}preferences.ui')
class PreferencesPage(Adw.PreferencesPage):
    __gtype_name__ = "PreferencesPage"

    media_lib = Gtk.Template.Child("media_lib_prop")
    recordings_path_row = Gtk.Template.Child()
    useragent_entry = Gtk.Template.Child()
    referer_entry = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @Gtk.Template.Callback("on_recordings_path_activated")
    def on_recordings_path_select(self, row: Adw.ActionRow):
        Gtk.FileDialog().select_folder(callback=self.on_recordings_path_selected)

    def on_recordings_path_selected(self, dialog: Gtk.FileDialog, task: Gio.Task):
        try:
            file = dialog.select_folder_finish(task)
        except GLib.GError:
            pass  # NOP
        else:
            self.recordings_path_row.set_subtitle(file.get_path())


@Gtk.Template(filename=f'{UI_PATH}shortcuts.ui')
class ShortcutsWindow(Gtk.ShortcutsWindow):
    __gtype_name__ = "ShortcutsWindow"


@Gtk.Template(filename=f'{UI_PATH}app.ui')
class AppWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'AppWindow'

    navigation_view = Gtk.Template.Child("navigation_view")
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
        # Shortcuts.
        self.set_help_overlay(ShortcutsWindow())


class Application(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                         **kwargs)
        self.add_main_option("log", ord("l"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "", None)
        self.add_main_option("debug", ord("d"), GLib.OptionFlags.NONE, GLib.OptionArg.STRING, "", None)

        self.app_window = None
        self.connect("activate", self.on_activate)

        self.init_actions()

    def on_activate(self, app: Adw.Application):
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

    def init_actions(self):
        self.set_action("preferences", self.on_preferences)
        self.set_action("about", self.on_about_app)
        self.set_action("quit", self.on_close_app)

    def set_action(self, name, fun, enabled=True):
        ac = Gio.SimpleAction.new(name, None)
        ac.connect("activate", fun)
        ac.set_enabled(enabled)
        self.add_action(ac)

        return ac

    def on_preferences(self, action, value):
        self.app_window.navigation_view.push_by_tag("preferences-page")

    def on_about_app(self, action, value):
        pass

    def on_close_app(self, action, value):
        self.quit()


def run_app():
    app = Application()
    app.run(sys.argv)


if __name__ == "__main__":
    pass
