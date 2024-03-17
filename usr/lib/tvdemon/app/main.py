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


import gettext
import sys

from .common import *
from .settings import Settings


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

    navigation_view = Gtk.Template.Child()
    # Start page.
    tv_logo = Gtk.Template.Child()
    tv_label = Gtk.Template.Child()
    movies_logo = Gtk.Template.Child()
    movies_label = Gtk.Template.Child()
    series_logo = Gtk.Template.Child()
    series_label = Gtk.Template.Child()
    # Providers page.
    providers_list = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # TODO add to preferences!
        # Used for redownloading timer
        self.reload_timeout_sec = 60 * 5
        self._timer_id = -1

        self.settings = Settings()
        self.manager = Manager(self.settings)
        self.providers = []
        self.active_provider = None
        self.active_group = None
        self.active_serie = None
        self.marked_provider = None
        self.content_type = TV_GROUP  # content being browsed
        self.back_page = None  # page to go back to if the back button is pressed
        self.active_channel = None
        self.fullscreen = False
        self.latest_search_bar_text = None
        self.visible_search_results = 0
        self.player = None
        self.xtream = None

        # Start page.
        self.tv_logo.set_from_file(f"{UI_PATH}pictures/tv.svg")
        self.movies_logo.set_from_file(f"{UI_PATH}pictures/movies.svg")
        self.series_logo.set_from_file(f"{UI_PATH}pictures/series.svg")
        # Shortcuts.
        self.set_help_overlay(ShortcutsWindow())

        self.connect("realize", self.on_realized)

    def on_realized(self, window: Adw.ApplicationWindow):
        log("Starting...")
        self.reload()
        # Redownload playlists by default
        # This is going to get readjusted
        self._timer_id = GLib.timeout_add_seconds(self.reload_timeout_sec, self.force_reload)

    @async_function
    def reload(self, page=None, refresh=False):
        self.status(translate("Loading providers..."))
        self.providers = []
        for provider_info in self.settings.get_strv("providers"):
            try:
                provider = Provider(name=None, provider_info=provider_info)
                # Add provider to list. This must be done so that it shows up in the
                # list of providers for editing.
                self.providers.append(provider)

                if provider.type_id != "xtream":
                    # Download M3U
                    if refresh:
                        self.status(translate("Downloading playlist..."), provider)
                    else:
                        self.status(translate("Getting playlist..."), provider)
                    ret = self.manager.get_playlist(provider, refresh=refresh)
                    p_name = provider.name
                    if ret:
                        self.status(translate("Checking playlist..."), provider)
                        if self.manager.check_playlist(provider):
                            self.status(translate("Loading channels..."), provider)
                            self.manager.load_channels(provider)
                            if p_name == self.settings.get_string("active-provider"):
                                self.active_provider = provider
                            self.status(None)
                            lc, lg, ls = len(provider.channels), len(provider.groups), len(provider.series)
                            log(f"{p_name}: {lc} channels, {lg} groups, {ls} series, {len(provider.movies)} movies")
                    else:
                        self.status(translate(f"Failed to Download playlist from {p_name}"), provider)
                else:
                    # Load xtream class
                    from xtream import XTream
                    # Download via Xtream
                    self.xtream = XTream(provider.name, provider.username, provider.password, provider.url,
                                         hide_adult_content=False, cache_path=PROVIDERS_PATH)
                    if self.xtream.auth_data != {}:
                        log(f"XTREAM `{provider.name}` Loading Channels")
                        # Save default cursor
                        current_cursor = self.window.get_window().get_cursor()
                        # Set waiting cursor
                        self.window.get_window().set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), 'wait'))
                        # Load data
                        self.xtream.load_iptv()
                        # Restore default cursor
                        self.window.get_window().set_cursor(current_cursor)
                        # Inform Provider of data
                        provider.channels = self.xtream.channels
                        provider.movies = self.xtream.movies
                        provider.series = self.xtream.series
                        provider.groups = self.xtream.groups
                        # Change redownload timeout
                        self.reload_timeout_sec = 60 * 60 * 2  # 2 hours
                        if self._timer_id:
                            GLib.source_remove(self._timer_id)
                        self._timer_id = GLib.timeout_add_seconds(self.reload_timeout_sec, self.force_reload)
                        # If no errors, approve provider
                        if provider.name == self.settings.get_string("active-provider"):
                            self.active_provider = provider
                        self.status(None)
                    else:
                        log("XTREAM Authentication Failed")

            except Exception as e:
                log(e)
                log("Couldn't parse provider info: ", provider_info)

        # If there are more than 1 providers and no Active Provider, set to the first one
        if len(self.providers) > 0 and self.active_provider is None:
            self.active_provider = self.providers[0]

        self.refresh_providers_page()

        if page:
            self.navigate_to(page)
        self.status(None)
        self.latest_search_bar_text = None

    def force_reload(self):
        self.reload(page=None, refresh=True)
        return False

    @idle_function
    def status(self, string, provider=None):
        if string is None:
            # self.status_label.set_text("")
            # self.status_label.hide()
            return
        # self.status_label.show()
        if provider:
            status = f"{provider.name}: {string}"
            # self.status_label.set_text(status)
            log(status)
        else:
            # self.status_label.set_text(string)
            log(string)

    @idle_function
    def refresh_providers_page(self):
        [self.providers_list.remove(c) for c in [r for r in self.providers_list]]

        for provider in self.providers:
            p_row = Adw.ActionRow()
            p_row.set_use_markup(True)
            p_row.set_title(f"<b>{provider.name}</b>")
            p_row.set_icon_name("tv-symbolic")
            labels = []
            num = len(provider.channels)
            if num > 0:
                labels.append(gettext.ngettext("%d TV channel", "%d TV channels", num) % num)

            num = len(provider.movies)
            if num > 0:
                labels.append(gettext.ngettext("%d movie", "%d movies", num) % num)
            num = len(provider.series)
            if num > 0:
                labels.append(gettext.ngettext("%d series", "%d series", num) % num)

            if provider == self.active_provider:
                labels.append("%s %d (active)" % (provider.name, len(provider.channels)))
            else:
                labels.append(provider.name)

            p_row.set_subtitle(f"<i>{' '.join(labels)}</i>")

            self.providers_list.append(p_row)


class Application(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                         **kwargs)
        self.add_main_option("log", ord("l"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "", None)
        self.add_main_option("debug", ord("d"), GLib.OptionFlags.NONE, GLib.OptionArg.STRING, "", None)

        self.window = None
        self.init_actions()

    def do_activate(self):
        if not self.window:
            self.window = AppWindow(application=self)

        self.window.present()

    def do_command_line(self, command_line):
        """ Processing command line parameters. """
        options = command_line.get_options_dict()
        options = options.end().unpack()

        if "log" in options:
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
        self.window.navigation_view.push_by_tag("preferences-page")

    def on_about_app(self, action, value):
        pass

    def on_close_app(self, action, value):
        self.quit()


def run_app():
    app = Application()
    app.run(sys.argv)


if __name__ == "__main__":
    pass
