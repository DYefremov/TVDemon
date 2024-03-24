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
import os
import shutil
import sys
from enum import StrEnum, IntEnum

import requests

from .madia import Player
from .common import *
from .settings import Settings


class Page(StrEnum):
    """ Displayed page. """
    START = "start-page"
    CATEGORIES = "categories-page"
    CHANNELS = "channels-page"
    SEARCH = "search-page"
    TV = "tv-page"
    MOVIES = "movies-page"
    SERIES = "series-page"
    PROVIDERS = "providers-page"
    PROVIDER = "provider-properties-page"
    PREFERENCES = "preferences-page"


class PLaybackPage(StrEnum):
    STATUS = "status"
    LOAD = "load"
    PLAYBACK = "playback"


class ProviderType(IntEnum):
    URL = 0
    LOCAL = 1
    XTREAM = 2

    @classmethod
    def from_str(cls, name: str):
        name = name.upper()
        for p_type in ProviderType:
            if p_type.name == name:
                return p_type
        return cls.URL


@Gtk.Template(filename=f"{UI_PATH}provider_widget.ui")
class ProviderWidget(Adw.ActionRow):
    """ A custom widget for displaying and holding provider data. """
    __gtype_name__ = "ProviderWidget"

    def __init__(self, app_window, provider, **kwargs):
        super().__init__(**kwargs)
        self.app_window = app_window
        self.provider = provider

    @Gtk.Template.Callback()
    def on_edit(self, button):
        self.app_window.emit("provider-edit", self)

    @Gtk.Template.Callback()
    def on_remove(self, button):
        self.app_window.emit("provider-remove", self)


@Gtk.Template(filename=f"{UI_PATH}provider_properties_widget.ui")
class ProviderProperties(Adw.NavigationPage):
    __gtype_name__ = "ProviderProperties"

    save_button = Gtk.Template.Child()
    action_switch_action = Gtk.Template.Child()
    name_entry_row = Gtk.Template.Child()
    type_combo_row = Gtk.Template.Child()
    path_action_row = Gtk.Template.Child()
    url_entry_row = Gtk.Template.Child()
    user_group = Gtk.Template.Child()
    user_entry_row = Gtk.Template.Child()
    password_entry_row = Gtk.Template.Child()
    epg_source_entry = Gtk.Template.Child()
    epg_sources_list = Gtk.Template.Child()
    epg_sources_drop_down = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def on_type_activated(self, row: Adw.ComboRow, param: GObject):
        p_type = ProviderType(row.get_selected())
        self.user_group.set_visible(p_type is ProviderType.XTREAM)
        self.path_action_row.set_visible(p_type is ProviderType.LOCAL)
        self.url_entry_row.set_visible(p_type is not ProviderType.LOCAL)

    @Gtk.Template.Callback()
    def on_provider_path_activated(self, row: Adw.ActionRow):
        select_path(row.set_subtitle)


@Gtk.Template(filename=f"{UI_PATH}channel_widget.ui")
class ChannelWidget(Gtk.ListBoxRow):
    """ A custom widget for displaying and holding channel data. """
    __gtype_name__ = "ChannelWidget"

    TARGET = "GTK_LIST_BOX_ROW"

    label = Gtk.Template.Child()
    logo = Gtk.Template.Child()

    def __init__(self, channel, logo_pixbuf=None, **kwargs):
        super().__init__(**kwargs)
        self.channel = channel

        self.label.set_text(channel.name)
        self.set_tooltip_text(channel.name)
        self.logo.set_from_pixbuf(logo_pixbuf) if logo_pixbuf else None


@Gtk.Template(filename=f"{UI_PATH}group_widget.ui")
class GroupWidget(Gtk.FlowBoxChild):
    """ A custom widget for displaying and holding group data. """
    __gtype_name__ = "GroupWidget"

    box = Gtk.Template.Child()
    label = Gtk.Template.Child()
    logo = Gtk.Template.Child()

    def __init__(self, data, name, logo_pixbuf=None, orientation=Gtk.Orientation.HORIZONTAL, **kwargs):
        super().__init__(**kwargs)
        self._data = data
        self.name = name
        self.label.set_text(name)
        self.box.set_orientation(orientation)
        self.logo.set_from_pixbuf(logo_pixbuf) if logo_pixbuf else None

    @property
    def data(self):
        return self._data


@Gtk.Template(filename=f"{UI_PATH}preferences.ui")
class PreferencesPage(Adw.PreferencesPage):
    __gtype_name__ = "PreferencesPage"

    media_lib_row = Gtk.Template.Child()
    recordings_path_row = Gtk.Template.Child()
    useragent_entry = Gtk.Template.Child()
    referer_entry = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @Gtk.Template.Callback("on_recordings_path_activated")
    def on_recordings_path_select(self, row: Adw.ActionRow):
        select_path(row.set_subtitle)


@Gtk.Template(filename=f"{UI_PATH}question_dialog.ui")
class QuestionDialog(Adw.MessageDialog):
    __gtype_name__ = "QuestionDialog"

    def __init__(self, parent, clb=None, **kwargs):
        super().__init__(**kwargs)
        self.set_transient_for(parent)
        self.clb = clb

    @Gtk.Template.Callback()
    def on_response(self, dialog, resp):
        if self.clb:
            self.clb(dialog.get_default_response() == resp)


@Gtk.Template(filename=f"{UI_PATH}shortcuts.ui")
class ShortcutsWindow(Gtk.ShortcutsWindow):
    __gtype_name__ = "ShortcutsWindow"


@Gtk.Template(filename=f"{UI_PATH}app.ui")
class AppWindow(Adw.ApplicationWindow):
    __gtype_name__ = "AppWindow"

    navigation_view = Gtk.Template.Child()
    # Start page.
    start_page = Gtk.Template.Child()
    tv_logo = Gtk.Template.Child()
    tv_label = Gtk.Template.Child()
    tv_button = Gtk.Template.Child()
    movies_logo = Gtk.Template.Child()
    movies_label = Gtk.Template.Child()
    movies_button = Gtk.Template.Child()
    series_logo = Gtk.Template.Child()
    series_label = Gtk.Template.Child()
    series_button = Gtk.Template.Child()
    # Categories page.
    categories_flowbox = Gtk.Template.Child()
    # Channels page.
    channels_header = Gtk.Template.Child()
    channels_paned = Gtk.Template.Child()
    channels_box = Gtk.Template.Child()
    channels_list_box = Gtk.Template.Child()
    playback_stack = Gtk.Template.Child()
    playback_status_page = Gtk.Template.Child()
    playback_widget = Gtk.Template.Child()
    channel_info = Gtk.Template.Child()
    # Movies page.
    movies_flowbox = Gtk.Template.Child()
    # Series page.
    series_list = Gtk.Template.Child()
    # Providers page.
    providers_list = Gtk.Template.Child()
    provider_properties = Gtk.Template.Child()
    # Status bar.
    status_bar = Gtk.Template.Child()
    status_label = Gtk.Template.Child()
    playback_bar = Gtk.Template.Child()
    playback_label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Signals.
        GObject.signal_new("provider-edit", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))
        GObject.signal_new("provider-remove", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))

        self.settings = Settings()
        self.manager = Manager(self.settings)
        self.providers = []
        self.active_provider = None
        self.active_group = None
        self.active_serie = None
        self.marked_provider = None
        self.content_type = TV_GROUP  # content being browsed
        self.active_channel = None
        self.is_full_screen = False
        self.player = None
        self.xtream = None
        self.current_page = Page.START

        self._is_tv_mode = True
        # Delay before hiding the mouse cursor.
        self._mouse_hide_interval = 5
        self._is_mouse_cursor_hidden = True
        # TODO add to preferences!
        # Used for redownloading timer
        self.reload_timeout_sec = 60 * 5
        self._timer_id = -1
        # Start page.
        self.tv_logo.set_from_file(f"{UI_PATH}pictures/tv.svg")
        self.movies_logo.set_from_file(f"{UI_PATH}pictures/movies.svg")
        self.series_logo.set_from_file(f"{UI_PATH}pictures/series.svg")
        self.tv_button.connect("clicked", self.show_groups, TV_GROUP)
        self.movies_button.connect("clicked", self.show_groups, MOVIES_GROUP)
        self.series_button.connect("clicked", self.show_groups, SERIES_GROUP)
        # Categories.
        self.categories_flowbox.connect("child-activated", self.on_group_activate)
        # Channels.
        self.channels_list_box.connect("row-activated", self.play_channel)
        self.bind_property("is_tv_mode", self.channels_box, "visible")
        # Movies.
        self.movies_flowbox.connect("child-activated", self.on_movie_activate)
        # Providers.
        self.connect("provider-edit", self.on_provider_edit)
        self.connect("provider-remove", self.on_provider_remove)
        self.provider_properties.save_button.connect("clicked", self.on_provider_save)
        # Shortcuts.
        self.set_help_overlay(ShortcutsWindow())
        # Main
        self.navigation_view.connect("pushed", self.on_navigation_view_pushed)
        self.navigation_view.connect("popped", self.on_navigation_view_popped)
        self.connect("realize", self.on_realized)
        # Activating mouse events for playback widget.
        controller = Gtk.EventControllerMotion()
        controller.connect("motion", self.on_playback_mouse_motion)
        self.playback_widget.add_controller(controller)
        controller = Gtk.EventControllerScroll()
        controller.connect("scroll", self.on_playback_mouse_scroll)
        self.playback_widget.add_controller(controller)
        controller = Gtk.GestureClick()
        controller.connect("pressed", self.on_playback_mouse_press)
        self.playback_widget.add_controller(controller)
        self.bind_property("is-mouse-cursor-hidden", self.channel_info, "visible", 4)

    @GObject.Property(type=bool, default=True)
    def is_tv_mode(self):
        return self._is_tv_mode

    @is_tv_mode.setter
    def is_tv_mode(self, value):
        self._is_tv_mode = value

    @GObject.Property(type=bool, default=True)
    def is_mouse_cursor_hidden(self):
        return self._is_mouse_cursor_hidden

    @is_mouse_cursor_hidden.setter
    def is_mouse_cursor_hidden(self, value):
        self._is_mouse_cursor_hidden = value

    def on_realized(self, window: Adw.ApplicationWindow):
        log("Starting...")
        size = self.settings.get_value("main-window-size")
        if size:
            self.set_default_size(*size)

        self.reload(Page.START)
        self.init_playback()
        # Redownload playlists by default
        # This is going to get readjusted
        self._timer_id = GLib.timeout_add_seconds(self.reload_timeout_sec, self.force_reload)

    def init_playback(self):
        self.player = Player.get_instance("gst", self.playback_widget)
        self.player.connect("played", self.on_played)
        self.player.connect("error", self.on_playback_error)

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
                    from .xtream import XTream
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

    def force_reload(self):
        self.reload(page=None, refresh=True)
        return False

    @idle_function
    def status(self, msg, provider=None):
        if msg is None:
            self.status_label.set_text("")
            self.status_label.hide()
            return
        self.status_label.show()
        if provider:
            status = f"{provider.name}: {msg}"
            self.status_label.set_text(status)
            log(status)
        else:
            self.status_label.set_text(msg)
            log(msg)

    def navigate_to(self, page: Page):
        if page is Page.START:
            self.navigation_view.pop()
        else:
            self.navigation_view.push_by_tag(page)

        provider = self.active_provider
        if page is Page.START:
            if provider is None:
                self.tv_label.set_text(translate("TV Channels (0)"))
                self.movies_label.set_text(translate("Movies (0)"))
                self.series_label.set_text(translate("Series (0)"))
                self.preferences_button.set_sensitive(False)
                self.tv_button.set_sensitive(False)
                self.movies_button.set_sensitive(False)
                self.series_button.set_sensitive(False)
            else:
                self.tv_label.set_text(translate(f"TV Channels ({len(provider.channels)})"))
                self.movies_label.set_text(translate(f"Movies ({len(provider.movies)})"))
                self.series_label.set_text(translate(f"Series ({len(provider.series)})"))
                self.tv_button.set_sensitive(len(provider.channels) > 0)
                self.movies_button.set_sensitive(len(provider.movies) > 0)
                self.series_button.set_sensitive(len(provider.series) > 0)

    def get_badge_pixbuf(self, name) -> GdkPixbuf.Pixbuf:
        """ Returns group badge. """
        added_words = set()
        extensions = ("svg", "png")

        for word in name.split():
            word = BADGES.get(word, word)

            if word not in added_words:
                for extension in extensions:
                    badge = f"{UI_PATH}pictures/badges/{word}.{extension}"
                    if os.path.exists(badge):
                        pixbuf = get_pixbuf_from_file(badge, 32)
                        if pixbuf:
                            added_words.add(word)
                            return pixbuf

    def show_groups(self, widget, content_type):
        self.content_type = content_type
        self.active_group = None
        found_groups = False

        self.categories_flowbox.remove_all()

        for group in self.active_provider.groups:
            if group.group_type != self.content_type:
                continue
            found_groups = True

            if self.content_type == TV_GROUP:
                label = f"{group.name} ({len(group.channels)})"
            elif self.content_type == MOVIES_GROUP:
                label = f"{self.remove_word('VOD', group.name)} ({len(group.channels)})"
            else:
                label = f"{self.remove_word('SERIES', group.name)} ({len(group.series)})"

            name = group.name.lower().replace("(", " ").replace(")", " ")
            self.categories_flowbox.append(GroupWidget(group, label, self.get_badge_pixbuf(name)))

        self.navigate_to(Page.CATEGORIES)

        if not found_groups:
            self.on_group_activate()

    def on_group_activate(self, box=None, group_widget=None):
        group = group_widget.data if group_widget else None
        self.active_group = group
        if self.content_type == TV_GROUP:
            self.show_channels(group.channels) if group else self.show_channels(self.active_provider.channels)
        elif self.content_type == MOVIES_GROUP:
            self.show_movies(group.channels) if group else self.show_movies(self.active_provider.movies)
        elif self.content_type == SERIES_GROUP:
            self.show_movies(group.series) if group else self.show_movies(self.active_provider.series)

    # ******************** Providers ******************** #

    @idle_function
    def refresh_providers_page(self):
        self.providers_list.remove_all()

        for provider in self.providers:
            p_row = ProviderWidget(self, provider)
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

    @Gtk.Template.Callback()
    def on_provider_activated(self, list_box: Gtk.ListBox, widget: ProviderWidget):
        provider = widget.provider
        self.active_provider = provider
        self.settings.set_string("active-provider", provider.name)
        self.navigate_to(Page.START)

    @Gtk.Template.Callback()
    def on_provider_add(self, button):
        provider = Provider("", Provider.SEP * 5)
        self.init_provider_properties(provider)
        self.provider_properties.action_switch_action.set_active(True)
        self.navigate_to(Page.PROVIDER)

    @Gtk.Template.Callback()
    def on_providers_reset(self, button):
        def cls(confirm=False):
            if confirm:
                self.settings.reset("providers")
                self.reload()

        QuestionDialog(self, cls).present()

    def on_provider_edit(self, win, widget: ProviderWidget):
        self.provider_properties.action_switch_action.set_active(False)
        self.marked_provider = widget.provider
        self.init_provider_properties(self.marked_provider)
        self.navigate_to(Page.PROVIDER)

    def on_provider_remove(self, win, widget: ProviderWidget):
        self.providers.remove(widget.provider)
        self.providers_list.remove(widget)

    def on_provider_save(self, button):
        def cls(confirm=False):
            self.provider_save() if confirm else self.navigation_view.pop()

        QuestionDialog(self, cls).present()

    def provider_save(self):
        self.navigation_view.pop()
        add_action = self.provider_properties.action_switch_action.get_active()
        name = self.provider_properties.name_entry_row.get_text()
        type_id = ProviderType(self.provider_properties.type_combo_row.get_selected()).name.lower()
        url = self.provider_properties.url_entry_row.get_text()
        path = self.provider_properties.path_action_row.get_subtitle()
        user = self.provider_properties.user_entry_row.get_text()
        password = self.provider_properties.password_entry_row.get_text()
        epg = self.provider_properties.epg_source_entry.get_text()
        info = Provider.SEP.join((name, type_id, url, user, password, epg))
        if add_action:
            provider = Provider(name, info)
            self.providers.append(provider)
        else:
            self.marked_provider.set_info(info)

        self.settings.set_strv("providers", [provider.get_info() for provider in self.providers])
        self.reload(refresh=True)

    def init_provider_properties(self, provider: Provider):
        self.provider_properties.name_entry_row.set_text(provider.name)
        self.provider_properties.path_action_row.set_subtitle(provider.path)
        self.provider_properties.url_entry_row.set_text(provider.url)
        self.provider_properties.user_entry_row.set_text(provider.username)
        self.provider_properties.password_entry_row.set_text(provider.password)
        self.provider_properties.type_combo_row.set_selected(ProviderType.from_str(provider.type_id))

    # ******************** Channels ******************** #

    def show_channels(self, channels: [Channel]):
        self.navigate_to(Page.CHANNELS)
        if self.content_type == TV_GROUP:
            self.update_channels_data(channels, self.channels_list_box)

    def update_channels_data(self, channels: list, ch_box: Gtk.ListBox, clear: bool = True):
        if clear:
            ch_box.remove_all()

        logos_to_refresh = []
        list(map(ch_box.append, (self.get_ch_widget(ch, logos_to_refresh) for ch in channels)))

        if len(logos_to_refresh) > 0:
            self.download_channel_logos(logos_to_refresh)

    def get_ch_widget(self, channel: Channel, logos_to_refresh: list):
        path = channel.logo_path
        pixbuf = get_pixbuf_from_file(path) if path else None
        widget = ChannelWidget(channel, pixbuf)
        if not pixbuf:
            logos_to_refresh.append((channel, widget.logo))

        return widget

    def play_channel(self, box: Gtk.ListBox, row: ChannelWidget):
        self.active_channel = row.channel
        self.play(row.channel)

    # ******************** Movies ******************** #

    def show_movies(self, items):
        logos_to_refresh = []
        self.navigate_to(Page.MOVIES)
        self.movies_flowbox.remove_all()

        for item in items:
            logo_path = item.logo_path
            pixbuf = get_pixbuf_from_file(item.logo_path, 128) if logo_path else None
            widget = GroupWidget(item, item.name, pixbuf, orientation=Gtk.Orientation.VERTICAL)
            widget.logo.set_pixel_size(56)
            if logo_path and not pixbuf:
                logos_to_refresh.append((item, widget.logo))

            self.movies_flowbox.append(widget)

        if len(logos_to_refresh) > 0:
            self.download_channel_logos(logos_to_refresh)

    def on_movie_activate(self, box: Gtk.FlowBox, widget: GroupWidget):
        if self.content_type == MOVIES_GROUP:
            self.active_channel = widget.data
            self.show_channels(None)
            self.play(widget.data)
        else:
            self.show_episodes(widget.data)

    # ******************** Series ******************** #

    def show_series(self, serie: Serie):
        logos_to_refresh = []
        self.active_serie = serie
        # If we are using xtream provider
        # Load every Episodes of every Season for this Series
        if self.active_provider.type_id == "xtream":
            self.xtream.get_series_info_by_id(self.active_serie)

        self.series_list.remove_all()
        self.navigate_to(Page.SERIES)

        for season_name in serie.seasons.keys():
            season = serie.seasons[season_name]
            serie_box = Gtk.Box()
            serie_box.set_orientation(Gtk.Orientation.VERTICAL)
            serie_box.set_spacing(6)
            label = Gtk.Label()
            label.set_use_markup(True)
            label.set_markup(translate(f"<b>Season {season_name}</b>"))
            serie_box.append(label)
            flow_box = Gtk.FlowBox()
            serie_box.append(flow_box)
            self.series_list.append(serie_box)
            flow_box.connect("child-activated", self.on_serie_activate)

            for episode_name in season.episodes.keys():
                episode = season.episodes[episode_name]
                logo_path = episode.logo_path
                pixbuf = get_pixbuf_from_file(logo_path) if logo_path else None
                widget = GroupWidget(episode, translate(f"Episode {episode_name}"), pixbuf,
                                     orientation=Gtk.Orientation.VERTICAL)
                if logo_path and not pixbuf:
                    logos_to_refresh.append((episode, widget.logo))

                flow_box.append(widget)

    def on_serie_activate(self, box: Gtk.FlowBox, widget: GroupWidget):
        self.active_channel = widget.data
        self.show_channels(None)
        self.play(self.active_channel)

    # ******************** Playback ******************** #

    @idle_function
    def play(self, channel: Channel):
        if self.player:
            self.playback_stack.set_visible_child_name(PLaybackPage.LOAD)
            self.channel_info.set_title(channel.name)
            self.channel_info.set_subtitle(channel.url)
            self.playback_label.set_text(channel.name)
            GLib.timeout_add(200, self.player.play, channel.url)

    @Gtk.Template.Callback()
    def on_playback_stop(self, button):
        self.playback_bar.hide()
        self.player.stop()

    @Gtk.Template.Callback()
    def on_playback_pause(self, button):
        self.player.pause()

    @Gtk.Template.Callback()
    def on_playback_show(self, button):
        self.navigate_to(Page.CHANNELS)

    def on_played(self, player: Player, status: int):
        self.playback_stack.set_visible_child_name(PLaybackPage.PLAYBACK)

    def on_playback_error(self, player: Player, status: int):
        self.playback_status_page.set_title(translate("Can't Playback!"))
        self.playback_stack.set_visible_child_name(PLaybackPage.STATUS)
        log(f"Playback error: {status}")

    def on_playback_mouse_press(self, gest: Gtk.GestureClick, num: int, x: float, y: float):
        if num == 2:
            self.toggle_fullscreen()

    def on_playback_mouse_scroll(self, *args):
        pass

    def on_playback_mouse_motion(self, controller: Gtk.EventControllerMotion, x: float, y: float):
        if self.is_mouse_cursor_hidden:
            self.playback_widget.set_cursor(Gdk.Cursor.new_from_name("default"))
            self.is_mouse_cursor_hidden = False

            GLib.timeout_add_seconds(self._mouse_hide_interval, self.hide_mouse_cursor)

    def hide_mouse_cursor(self):
        self.playback_widget.set_cursor(Gdk.Cursor.new_from_name("none"))
        self.is_mouse_cursor_hidden = True

    def toggle_fullscreen(self):
        self.is_full_screen = not self.is_full_screen
        if self.is_full_screen:
            self.channels_header.hide()
            self.channels_paned.set_margin_start(0)
            self.channels_paned.set_margin_end(0)
            self.status_bar.hide()
            if self._is_tv_mode:
                self.channels_box.hide()
            self.fullscreen()
        else:
            self.channels_header.show()
            self.channels_paned.set_margin_start(12)
            self.channels_paned.set_margin_end(12)
            self.status_bar.show()
            if self._is_tv_mode:
                self.channels_box.show()
            self.unfullscreen()

    # ******************** Additional ******************** #

    def on_navigation_view_pushed(self, view: Adw.NavigationView):
        page = Page(view.get_visible_page().get_tag())
        self.is_tv_mode = self.current_page not in (Page.MOVIES, Page.SERIES)
        self.current_page = page
        self.playback_bar.set_visible(self.current_page is not Page.CHANNELS and self.player.is_playing())

    def on_navigation_view_popped(self, view: Adw.NavigationView, prev_page: Adw.NavigationPage):
        self.current_page = Page(view.get_visible_page().get_tag())
        self.playback_bar.set_visible(self.current_page is not Page.CHANNELS and self.player.is_playing())

    @async_function
    def download_channel_logos(self, logos_to_refresh: list):
        headers = {'User-Agent': self.settings.get_string("user-agent"),
                   'Referer': self.settings.get_string("http-referer")}

        for channel, image in logos_to_refresh:
            if channel.logo_path is None:
                continue
            if os.path.isfile(channel.logo_path):
                continue
            try:
                response = requests.get(channel.logo, headers=headers, timeout=10, stream=True)
                if response.status_code == 200:
                    response.raw.decode_content = True
                    with open(channel.logo_path, 'wb') as f:
                        shutil.copyfileobj(response.raw, f)
                        self.refresh_channel_logo(channel, image)
            except Exception as e:
                log(e)

    @idle_function
    def refresh_channel_logo(self, channel: Channel, image: Gtk.Image):
        pixbuf = get_pixbuf_from_file(channel.logo_path, 32)
        image.set_from_pixbuf(pixbuf) if pixbuf else None

    def remove_word(self, word, string):
        if " " not in string:
            return
        return " ".join(w for w in string.split() if w != word)

    @Gtk.Template.Callback()
    def on_close_window(self, window):
        self.settings.set_value("main-window-size", self.get_default_size())
        return False


class Application(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                         **kwargs)
        self.add_main_option("log", ord("l"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "", None)
        self.add_main_option("debug", ord("d"), GLib.OptionFlags.NONE, GLib.OptionArg.STRING, "", None)
        # App style.
        # TODO add option.
        self.style_manager = Adw.StyleManager().get_default()
        self.style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

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
        settings = self.window.settings
        settings.save()

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
        self.window.navigate_to(Page.PREFERENCES)

    def on_about_app(self, action, value):
        pass

    def on_close_app(self, action, value):
        self.window.emit("close-request")
        self.quit()


def run_app():
    app = Application()
    app.run(sys.argv)


if __name__ == "__main__":
    pass
