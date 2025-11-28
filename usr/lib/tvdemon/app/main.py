# -*- coding: utf-8 -*-
#
# Copyright © 2022-2025 Dmitriy Yefremov <https://github.com/DYefremov>
#             2020-2022 Linux Mint <root@linuxmint.com>
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

__version__ = "2.0.0 Alpha2"
__author__ = "Dmitriy Yefremov"

import gettext
import os
import shutil
import sys
from datetime import datetime
from itertools import chain

import requests

from .common import *
from .epg import EpgCache
from .madia import Player
from .settings import Settings, Language
from .ui import *


@Gtk.Template(filename=f"{UI_PATH}app.ui")
class AppWindow(Adw.ApplicationWindow):
    __gtype_name__ = "AppWindow"

    navigation_view = Gtk.Template.Child()
    # Start page.
    start_page = Gtk.Template.Child()
    tv_logo = Gtk.Template.Child()
    tv_label = Gtk.Template.Child()
    tv_button = Gtk.Template.Child()
    search_button = Gtk.Template.Child()
    providers_button = Gtk.Template.Child()
    movies_logo = Gtk.Template.Child()
    movies_label = Gtk.Template.Child()
    movies_button = Gtk.Template.Child()
    series_logo = Gtk.Template.Child()
    series_label = Gtk.Template.Child()
    series_button = Gtk.Template.Child()
    active_provider_info = Gtk.Template.Child()
    # Categories page.
    categories_flowbox = Gtk.Template.Child()
    # Channels page.
    channels_page = Gtk.Template.Child()
    channels_header = Gtk.Template.Child()
    channels_paned = Gtk.Template.Child()
    channels_box = Gtk.Template.Child()
    channels_list_box = Gtk.Template.Child()
    playback_stack = Gtk.Template.Child()
    playback_status_page = Gtk.Template.Child()
    playback_widget = Gtk.Template.Child()
    media_bar = Gtk.Template.Child()
    # Channels overview page.
    overview_flowbox = Gtk.Template.Child()
    overview_button = Gtk.Template.Child()
    # Movies page.
    movies_page = Gtk.Template.Child()
    movies_flowbox = Gtk.Template.Child()
    # Series page.
    series_page = Gtk.Template.Child()
    series_list = Gtk.Template.Child()
    # Providers page.
    providers_page = Gtk.Template.Child()
    add_provider_button = Gtk.Template.Child()
    reset_providers_button = Gtk.Template.Child()
    providers_list = Gtk.Template.Child()
    provider_properties = Gtk.Template.Child()
    # Status bar.
    status_bar = Gtk.Template.Child()
    status_label = Gtk.Template.Child()
    playback_bar = Gtk.Template.Child()
    playback_label = Gtk.Template.Child()
    # Overlay.
    messages_overlay = Gtk.Template.Child()
    # Favorites.
    fav_button_content = Gtk.Template.Child()
    add_fav_button = Gtk.Template.Child()
    favorites = Gtk.Template.Child("favorites_page")
    # History.
    history = Gtk.Template.Child("history_widget")
    # Search.
    search_entry = Gtk.Template.Child()
    search_stack = Gtk.Template.Child()
    search_status = Gtk.Template.Child()
    search_channels_box = Gtk.Template.Child()
    # Preferences.
    preferences_button = Gtk.Template.Child()
    preferences_page = Gtk.Template.Child()
    # EPG
    epg_page = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Signals.
        GObject.signal_new("language-changed", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))
        GObject.signal_new("provider-edit", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))
        GObject.signal_new("provider-remove", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))
        GObject.signal_new("show-channel-epg", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))

        self.settings = Settings.get_instance()
        self.manager = Manager(self.settings)
        self.providers = []
        self.active_provider = None
        self.active_group = None
        self.active_serie = None
        self.marked_provider = None
        self.content_type = TV_GROUP  # content being browsed
        self.active_channel = None
        self.is_full_screen = False
        self.is_fav_mode = False
        self.player = None
        self.xtream = None
        self.search_running = False
        self.current_page = Page.START
        self.ia = None  # IMDb

        self._is_tv_mode = True
        self.TV_PAGES = {Page.MOVIES, Page.SERIES, Page.SEARCH, Page.OVERVIEW}
        # Delay before hiding the mouse cursor.
        self._mouse_hide_interval = 5
        self._is_mouse_cursor_hidden = True
        # Mouse cursor position. Used for small 'hack'
        # on macOS and some Linux distro to prevent 'phantom' cursor wake up.
        # Perhaps this will be fixed in future Gtk4 updates.
        self._mouse_pos = (0, 0)
        # Used for redownloading timer
        self.reload_timeout_sec = self.settings.get_value("reload-interval")
        # History.
        self.history.is_active = self.settings.get_value("enable-history")
        # Start page.
        self.tv_logo.set_from_file(f"{UI_PATH}pictures/tv.svg")
        self.movies_logo.set_from_file(f"{UI_PATH}pictures/movies.svg")
        self.series_logo.set_from_file(f"{UI_PATH}pictures/series.svg")
        self.tv_button.connect("clicked", self.show_groups, TV_GROUP)
        self.movies_button.connect("clicked", self.show_groups, MOVIES_GROUP)
        self.series_button.connect("clicked", self.show_groups, SERIES_GROUP)
        self.start_page.connect("showing", self.on_start_page_showing)
        # Channels.
        self.bind_property("is_tv_mode", self.channels_box, "visible")
        # Channels DnD.
        dnd = Gtk.DropTarget.new(ChannelWidget, Gdk.DragAction.MOVE)
        dnd.connect("drop", self.on_channel_dnd_drop)
        self.channels_list_box.add_controller(dnd)
        dnd = Gtk.DragSource.new()
        dnd.set_actions(Gdk.DragAction.MOVE)
        dnd.connect("prepare", self.on_channel_dnd_prepare)
        self.channels_list_box.add_controller(dnd)
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
        self.default_cursor = Gdk.Cursor.new_from_name("default")
        self.blank_cursor = Gdk.Cursor.new_from_name("none")
        controller = Gtk.EventControllerScroll()
        controller.set_flags(Gtk.EventControllerScrollFlags.VERTICAL)
        controller.connect("scroll", self.on_playback_mouse_scroll)
        self.playback_widget.add_controller(controller)
        controller = Gtk.GestureClick()
        controller.connect("pressed", self.on_playback_mouse_press)
        self.playback_widget.add_controller(controller)
        self.bind_property("is-mouse-cursor-hidden", self.media_bar, "visible", 4)
        # Favorites.
        self.favorites.connect("favorite-list-updated", self.on_favorite_list_updated)
        self.favorites.connect("favorite-groups-updated", self.on_favorite_groups_updated)
        self.favorites.connect("favorite-group-activated", self.on_favorite_group_activated)
        self.favorites.connect("favorites-error", self.on_favorites_error)
        # Media bar.
        self.media_bar.stop_button.connect("clicked", self.on_playback_stop)
        self.media_bar.pause_button.connect("clicked", self.on_playback_pause)
        self.media_bar.backward_button.connect("clicked", self.on_playback_backward)
        self.media_bar.forward_button.connect("clicked", self.on_playback_forward)
        self.media_bar.volume_button.connect("value-changed", self.on_volume_changed)
        self.media_bar.fullscreen_button.connect("clicked", self.toggle_fullscreen)
        self.media_bar.record_button.connect("clicked", self.on_record)
        self.media_bar.stream_info_button.connect("clicked", self.on_stream_info)
        self.media_bar.epg_button.connect("clicked", lambda b: self.on_show_channel_epg(self, self.active_channel))
        self.bind_property("is_tv_mode", self.media_bar.epg_button, "visible")
        # Shortcuts.
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(controller)
        # EPG.
        self._epg_timer_id = -1
        self._epg_cache = None
        self.connect("show-channel-epg", self.on_show_channel_epg)
        # Translation.
        if not IS_LINUX:
            self.connect("language-changed", self.on_language_changed)
        # Observing fullscreen mode (for macOS only).
        if IS_DARWIN:
            self.connect("notify::fullscreened", self.on_fullscreened)

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

        self.active_provider_info.set_title(tr("Loading..."))
        GLib.idle_add(self.init, priority=GLib.PRIORITY_LOW)

    def init(self):
        # Set waiting cursor
        self.set_cursor(Gdk.Cursor.new_from_name("wait"))
        self.reload(Page.START)
        self.init_playback()
        self.init_imdb()
        if not IS_LINUX:
            self.retranslate()
        # Redownload playlists by default.
        GLib.timeout_add_seconds(self.reload_timeout_sec, self.force_reload)

    def init_playback(self):
        try:
            self.player = Player.get_instance("gst", self.playback_widget)
        except (ImportError, NameError) as e:
            self.playback_status_page.set_description(str(e))
            GLib.idle_add(self.on_playback_error, self.player, "Not initialized!")
        else:
            self.player.connect("played", self.on_played)
            self.player.connect("recorded", self.on_recorded)
            self.player.connect("error", self.on_playback_error)

    def init_imdb(self):
        try:
            from imdb import Cinemagoer
        except ImportError as e:
            log(f"IMDb init error: {e}")
        else:
            self.ia = Cinemagoer()

    @async_function
    def reload(self, page=None, refresh=False, provider=None):
        self.providers_button.set_sensitive(refresh)

        if self._epg_timer_id >= 0:
            GLib.source_remove(self._epg_timer_id)

        self.providers = []
        for provider_info in self.settings.get_strv("providers"):
            try:
                provider = Provider(name=None, provider_info=provider_info)
                # Add provider to list.
                # This must be done so that it shows up in the list of providers for editing.
                self.providers.append(provider)
            except Exception as e:
                log(e)
                log("Couldn't parse provider info: ", provider_info)

        if not refresh and page is Page.START:
            self.status(tr("Loading favorites..."))
            self.favorites.set_groups(self.manager.load_favorites())
            self.status(tr("Loading history..."))
            if self.history.is_active:
                self.history.set_channels(self.manager.load_history())
                self.history.update_channels()
            # Preload channel logos for providers.
            [self.update_provider_logo_cache(p) for p in self.providers]
            # Restore default cursor.
            GLib.idle_add(self.set_cursor)

        self.load_providers(refresh)
        if page:
            GLib.idle_add(self.navigate_to, page)

    def force_reload(self):
        self.reload(page=None, refresh=True)
        return False

    @async_function
    def load_providers(self, refresh=False):
        self.status(tr("Loading providers..."))
        [self.load_provider(p, refresh) for p in self.providers]

        # If there are more than 1 providers and no Active Provider, set to the first one
        if len(self.providers) > 0 and self.active_provider is None:
            self.active_provider = self.providers[0]

        if self.active_provider.epg:
            GLib.timeout_add_seconds(2, self.init_epg)

        self.refresh_providers_page()

    def load_provider(self, provider, refresh=False):
        if provider.type_id != "xtream":
            # Download M3U
            self.status(tr("Downloading playlist..." if refresh else "Getting playlist..."), provider)
            p_name = provider.name
            if p_name == self.settings.get_string("active-provider"):
                self.active_provider = provider
            ret = self.manager.get_playlist(provider, refresh=refresh)

            if ret:
                self.status(tr("Checking playlist..."), provider)
                if self.manager.check_playlist(provider):
                    self.status(tr("Loading channels..."), provider)
                    self.manager.load_channels(provider)
                    self.status(None)
                    lc, lg, ls = len(provider.channels), len(provider.groups), len(provider.series)
                    log(f"{p_name}: {lc} channels, {lg} groups, {ls} series, {len(provider.movies)} movies")
            else:
                self.status(tr(f"Failed to Download playlist from {p_name}"), provider)
        else:
            # Load xtream class
            from .xtream import XTream
            # Download via Xtream
            self.xtream = XTream(provider.name, provider.username, provider.password, provider.url,
                                 hide_adult_content=False, cache_path=PROVIDERS_PATH)
            if self.xtream.auth_data != {}:
                log(f"XTREAM `{provider.name}` Loading Channels")
                # Load data
                self.xtream.load_iptv()
                # Inform Provider of data
                provider.channels = self.xtream.channels
                provider.movies = self.xtream.movies
                provider.series = self.xtream.series
                provider.groups = self.xtream.groups
                # If no errors, approve provider
                if provider.name == self.settings.get_string("active-provider"):
                    self.active_provider = provider
                self.status(None)
            else:
                log("XTREAM Authentication Failed")

    @async_function
    def reload_provider(self, provider, provider_type):
        self.load_provider(provider, refresh=provider_type is not ProviderType.LOCAL)
        self.refresh_providers_page()

    @async_function
    def update_provider_logo_cache(self, p: Provider):
        list(map(lambda c: get_pixbuf_from_file(c.logo_path), filter(lambda ch: ch.logo_path, p.channels)))

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

        if page is Page.START:
            provider = self.active_provider
            if provider is None:
                self.tv_label.set_text(tr("TV Channels (0)"))
                self.movies_label.set_text(tr("Movies (0)"))
                self.series_label.set_text(tr("Series (0)"))
                self.tv_button.set_sensitive(False)
                self.movies_button.set_sensitive(False)
                self.series_button.set_sensitive(False)
                self.active_provider_info.set_title(tr("No provider selected"))
            else:
                self.tv_label.set_text(tr(f"TV Channels ({len(provider.channels)})"))
                self.movies_label.set_text(tr(f"Movies ({len(provider.movies)})"))
                self.series_label.set_text(tr(f"Series ({len(provider.series)})"))
                self.tv_button.set_sensitive(len(provider.channels) > 0)
                self.movies_button.set_sensitive(len(provider.movies) > 0)
                self.series_button.set_sensitive(len(provider.series) > 0)
                self.active_provider_info.set_title(provider.name)

    def on_start_page_showing(self, page: Adw.NavigationPage):
        self.history.update_channels()

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
        self.overview_button.set_visible(content_type == TV_GROUP)
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

        self.navigate_to(Page.CATEGORIES) if found_groups else self.on_group_activated()

    @Gtk.Template.Callback()
    def on_group_activated(self, box=None, group_widget=None):
        group = group_widget.data if group_widget else None
        self.active_group = group

        if self.content_type == TV_GROUP:
            title = tr("Channels")
            self.channels_page.set_title(f"{title} [{group.name}]" if group else title)
            self.show_channels(group.channels) if group else self.show_channels(self.active_provider.channels)
        elif self.content_type == MOVIES_GROUP:
            title = tr("Movies")
            self.movies_page.set_title(f"{title} [{group.name}]" if group else title)
            self.show_movies(group.channels) if group else self.show_movies(self.active_provider.movies)
        elif self.content_type == SERIES_GROUP:
            title = tr("Series")
            self.series_page.set_title(f"{title} [{group.name}]" if group else title)
            self.show_movies(group.series) if group else self.show_movies(self.active_provider.series)

    # ******************** Providers ******************** #

    @idle_function
    def refresh_providers_page(self):
        self.providers_list.remove_all()
        self.overview_flowbox.remove_all()

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

        self.providers_button.set_sensitive(True)

    @Gtk.Template.Callback()
    def on_provider_activated(self, list_box: Gtk.ListBox, widget: ProviderWidget):
        provider = widget.provider
        self.active_provider_info.set_title(provider.name)
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

        QuestionDialog(cls).present(self)

    def on_provider_edit(self, win, widget: ProviderWidget):
        self.provider_properties.action_switch_action.set_active(False)
        self.marked_provider = widget.provider
        self.init_provider_properties(self.marked_provider)
        self.navigate_to(Page.PROVIDER)

    def on_provider_remove(self, win, widget: ProviderWidget):
        def clb(resp):
            if resp:
                self.providers.remove(widget.provider)
                self.providers_list.remove(widget)
                self.settings.set_strv("providers", [provider.get_info() for provider in self.providers])

        QuestionDialog(clb).present(self)

    def on_provider_save(self, button):
        def cls(confirm=False):
            self.provider_save() if confirm else self.navigation_view.pop()

        QuestionDialog(cls).present(self)

    def provider_save(self):
        self.navigation_view.pop()
        add_action = self.provider_properties.action_switch_action.get_active()
        provider_type = ProviderType(self.provider_properties.type_combo_row.get_selected())
        name = self.provider_properties.name_entry_row.get_text()
        type_id = provider_type.name.lower()
        user = self.provider_properties.user_entry_row.get_text()
        password = self.provider_properties.password_entry_row.get_text()
        epg = self.provider_properties.epg_source_entry.get_text()

        if provider_type is ProviderType.LOCAL:
            url = self.provider_properties.path_action_row.get_subtitle()
        else:
            url = self.provider_properties.url_entry_row.get_text()

        info = Provider.SEP.join((name, type_id, url, user, password, epg))
        provider = Provider(name, info)
        if add_action:
            log("Adding provider...")
            self.providers.append(provider)
            p_row = ProviderWidget(self, provider)
            p_row.set_sensitive(False)
            p_row.set_title(f"<b>{provider.name}</b>")
            p_row.set_icon_name("tv-symbolic")
            p_row.set_subtitle(f"<i>{tr('Loading playlist...')}</i>")
            self.providers_list.append(p_row)
        else:
            log(f"Updating provider settings...")
            if self.marked_provider in self.providers:
                self.providers[self.providers.index(self.marked_provider)] = provider
            self.marked_provider.set_info(info)

        self.settings.set_strv("providers", [provider.get_info() for provider in self.providers])
        self.reload_provider(provider, provider_type)

    def init_provider_properties(self, provider: Provider):
        self.provider_properties.name_entry_row.set_text(provider.name)
        self.provider_properties.path_action_row.set_subtitle(provider.path)
        self.provider_properties.url_entry_row.set_text(provider.url)
        self.provider_properties.user_entry_row.set_text(provider.username)
        self.provider_properties.password_entry_row.set_text(provider.password)
        self.provider_properties.type_combo_row.set_selected(ProviderType.from_str(provider.type_id))
        self.provider_properties.epg_source_entry.set_text(provider.epg or "")

    # ******************** Channels ******************** #

    def show_channels(self, channels: [Channel]):
        if self.content_type == TV_GROUP:
            gen = self.update_channels_data(channels, self.channels_list_box)
            GLib.idle_add(lambda: next(gen, False), priority=GLib.PRIORITY_LOW)
        else:
            if self.active_channel:
                self.channels_page.set_title(self.active_channel.name or "")
            self.navigate_to(Page.CHANNELS)

    def update_channels_data(self, channels: list, ch_box: Gtk.ListBox, clear: bool = True):
        if clear:
            ch_box.remove_all()
            self.navigate_to(Page.CHANNELS)
            yield True

        logos_to_refresh = []
        for index, ch in enumerate(channels):
            ch_box.append(ChannelWidget.get_widget(ch, logos_to_refresh, self.favorites.is_favorite(ch)))
            if index % 50 == 0:
                yield True

        if len(logos_to_refresh) > 0:
            self.download_channel_logos(logos_to_refresh)
        yield True

    def on_previous_channel(self, button=None):
        if self.current_page is Page.CHANNELS and self.is_tv_mode:
            self.on_playback_backward()

    def on_next_channel(self, button=None):
        if self.current_page is Page.CHANNELS and self.is_tv_mode:
            self.on_playback_forward()

    @Gtk.Template.Callback()
    def play_channel(self, box: Gtk.ListBox, row: ChannelWidget):
        self.active_channel = row.channel
        self.play(row.channel)

    def on_channel_dnd_drop(self, drop: Gtk.DropTarget, user_data: ChannelWidget, x: float, y: float):
        dest_child = self.channels_list_box.get_row_at_y(y)
        if not self.is_fav_mode:
            self.show_message("Not allowed in this context!")
            return True

        if dest_child and self.favorites.current_group:
            index = dest_child.get_index()
            self.channels_list_box.remove(user_data)
            self.channels_list_box.insert(user_data, index)
            # Moving in the fav group.
            channels = self.favorites.current_group.group.channels
            channels.insert(index, channels.pop(channels.index(user_data.channel)))

    def on_channel_dnd_prepare(self, drag_source: Gtk.DragSource, x: float, y: float):
        child = self.channels_list_box.get_row_at_y(y)
        if not child:
            return

        if child.logo:
            drag_source.set_icon(child.logo.get_paintable(), 0, 0)

        content = Gdk.ContentProvider.new_for_value(GObject.Value(ChannelWidget, child))
        return content

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

    @Gtk.Template.Callback()
    def on_movie_activate(self, box: Gtk.FlowBox, widget: GroupWidget):
        if self.content_type == MOVIES_GROUP:
            self.active_channel = widget.data
            self.show_channels(None)
            self.play(widget.data)
        else:
            self.show_series(widget.data)

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
            label.set_markup(tr(f"<b>Season {season_name}</b>"))
            serie_box.append(label)
            flow_box = Gtk.FlowBox()
            serie_box.append(flow_box)
            self.series_list.append(serie_box)
            flow_box.connect("child-activated", self.on_serie_activate)

            for episode_name in season.episodes.keys():
                episode = season.episodes[episode_name]
                logo_path = episode.logo_path
                pixbuf = get_pixbuf_from_file(logo_path) if logo_path else None
                widget = GroupWidget(episode, tr(f"Episode {episode_name}"), pixbuf,
                                     orientation=Gtk.Orientation.VERTICAL)
                if logo_path and not pixbuf:
                    logos_to_refresh.append((episode, widget.logo))

                flow_box.append(widget)

    def on_serie_activate(self, box: Gtk.FlowBox, widget: GroupWidget):
        self.active_channel = widget.data
        self.show_channels(None)
        self.play(self.active_channel)

    # ******************** Overview ******************* #

    @Gtk.Template.Callback()
    def on_overview_showing(self, page: Adw.NavigationPage):
        for w in self.overview_flowbox:
            break
        else:
            gen = self.update_overview_page(self.active_provider.channels, self.overview_flowbox)
            GLib.idle_add(lambda: next(gen, False), priority=GLib.PRIORITY_LOW)

    @Gtk.Template.Callback()
    def on_channel_activated(self, box: Gtk.FlowBox, widget: Gtk.FlowBoxChild):
        self.on_flow_channel_activated(widget.get_child())

    def update_overview_page(self, channels: list, ch_box: Gtk.FlowBox, clear: bool = True):
        if clear:
            ch_box.remove_all()
            yield True

        logos_to_refresh = []
        for index, ch in enumerate(channels):
            w = ChannelWidget.get_widget(ch, logos_to_refresh)
            w.epg_label.set_max_width_chars(30)
            ch_box.append(w)
            yield True

        if len(logos_to_refresh) > 0:
            self.download_channel_logos(logos_to_refresh)
        yield True

    # ******************** Favorites ******************* #

    @Gtk.Template.Callback()
    def on_favorite_add(self, button):
        if self.active_channel:
            if self.favorites.is_favorite(self.active_channel):
                self.show_message("The channel is already in your favorites!")
            else:
                self.favorites.emit("favorite-add", self.active_channel)
        else:
            self.show_message("No channel selected!")

    @Gtk.Template.Callback()
    def on_to_favorites(self, button):
        prev_page = self.navigation_view.get_previous_page(self.navigation_view.get_visible_page())
        self.navigation_view.pop()
        if prev_page.props.tag != Page.FAVORITES:
            self.navigation_view.push_by_tag(Page.FAVORITES)

    def on_favorite_list_updated(self, favorites: FavoritesPage, count: int):
        self.fav_button_content.set_label(str(count))
        gen = self.refresh_channel_info()
        GLib.idle_add(lambda: next(gen, False), priority=GLib.PRIORITY_LOW)

    def refresh_channel_info(self):
        for index, row in enumerate(self.channels_list_box):
            row.fav_logo.set_visible(self.favorites.is_favorite(row.channel))
            if index % 50 == 0:
                yield True

    def on_favorite_group_activated(self, favorites: FavoritesPage, group: Group):
        self.content_type = TV_GROUP
        self.show_channels(group.channels)
        self.channels_page.set_title(f"{tr('Favorites')} [{group.name}]")

    def on_favorites_error(self, favorites: FavoritesPage, message: str):
        self.show_message(message)

    def on_favorite_groups_updated(self, favorites: FavoritesPage, groups: list):
        menu = Gio.Menu()
        detail_level = Gio.SimpleAction.new_stateful("active-fav-group", GLib.VariantType.new("s"),
                                                     GLib.Variant.new_string("Default"))
        detail_level.connect("activate", self.on_fav_group_activated)
        self.add_action(detail_level)
        for g in groups:
            item = Gio.MenuItem.new(g.name)
            item.set_action_and_target_value("win.active-fav-group", GLib.Variant.new_string(g.name))
            if g.is_default:
                detail_level.set_state(GLib.Variant.new_string(g.name))
            menu.append_item(item)
        self.add_fav_button.set_menu_model(menu)

    def on_fav_group_activated(self, action: Gio.SimpleAction, target: GLib.Variant):
        action.set_state(target)
        self.favorites.emit("favorite-group-set-default", target.get_string())

    # ******************** Playback ******************** #

    @idle_function
    def play(self, channel: Channel):
        if self.player:
            if self.player.is_record():
                self.show_message(tr("Stream recording in progress!"))
                return

            self.playback_stack.set_visible_child_name(PLaybackPage.LOAD)
            self.media_bar.set_title(channel.name)
            self.media_bar.set_subtitle(channel.url)
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
        if self.channels_page in self.navigation_view.get_navigation_stack():
            self.navigation_view.pop()
        else:
            self.navigate_to(Page.CHANNELS)

    def on_playback_backward(self, button=None):
        self.activate_channel(Gtk.DirectionType.UP)

    def on_playback_forward(self, button=None):
        self.activate_channel(Gtk.DirectionType.DOWN)

    def activate_channel(self, direction: Gtk.DirectionType):
        row = self.channels_list_box.get_selected_row()
        if not row:
            row = self.channels_list_box.get_row_at_index(0)
        else:
            index = row.get_index() + 1 if direction is Gtk.DirectionType.DOWN else row.get_index() - 1
            row = self.channels_list_box.get_row_at_index(index)

        if row:
            row.activate()

    def on_played(self, player: Player, status: int):
        self.playback_stack.set_visible_child_name(PLaybackPage.PLAYBACK)
        if self.history.is_active:
            self.history.append_channel(self.active_channel)
        if self.ia:
            if self.content_type == MOVIES_GROUP:
                self.get_imdb_details(self.active_channel)
            elif self.content_type == SERIES_GROUP:
                self.get_imdb_details(self.active_serie)

    def on_playback_error(self, player: Player, msg: str):
        self.playback_status_page.set_title(tr("Can't Playback!"))
        self.playback_stack.set_visible_child_name(PLaybackPage.STATUS)

    def on_volume_changed(self, player: Player, volume: float):
        self.player.set_volume(volume)

    def on_playback_mouse_press(self, gest: Gtk.GestureClick, num: int, x: float, y: float):
        if num == 2:
            self.toggle_fullscreen()

    def on_playback_mouse_scroll(self, controller: Gtk.EventControllerScroll, dx: float, dy: float):
        self.player.volume_up() if dy < 0 else self.player.volume_down()
        self.media_bar.volume_button.set_value(self.player.get_volume())

    def on_playback_mouse_motion(self, controller: Gtk.EventControllerMotion, x: float, y: float):
        pos = int(x), int(y)
        if pos != self._mouse_pos:
            self._mouse_pos = pos
            if self.is_mouse_cursor_hidden:
                self.playback_widget.set_cursor(self.default_cursor)
                self.is_mouse_cursor_hidden = False
                GLib.timeout_add_seconds(self._mouse_hide_interval, self.hide_mouse_cursor)

    def hide_mouse_cursor(self):
        self.is_mouse_cursor_hidden = True
        self.playback_widget.set_cursor(self.blank_cursor)

    def on_fullscreened(self, window: Adw.ApplicationWindow, param: GObject):
        if self.is_fullscreen() != self.is_full_screen:
            self.toggle_fullscreen()

    def toggle_fullscreen(self, button=None):
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

    def on_flow_channel_activated(self, widget):
        self.active_channel = widget.channel
        self.navigate_to(Page.CHANNELS)
        self.play(self.active_channel)

    def on_stream_info(self, widget=None):
        if self.player and self.player.is_playing():
            info = " ".join(f"{tr(k)}: {v}" for k, v in self.player.get_stream_info().items())
            self.show_message(info)

    # ********************* Record ********************* #

    def on_recorded(self, player: Player, status: int):
        img = self.media_bar.record_button.get_first_child()
        if img and type(img) is Gtk.Image:
            def update_rec_status():
                is_rec = self.player.is_record()
                if not is_rec:
                    img.set_opacity(1.0)
                else:
                    img.set_opacity(0 if img.get_opacity() else 1.0)
                return is_rec

            GLib.timeout_add_seconds(1, update_rec_status, priority=GLib.PRIORITY_LOW)

    def on_record(self, button=None):
        if not self.player:
            return

        def cls(confirm=False):
            if confirm:
                if self.player.is_record():
                    self.player.record_stop()
                else:
                    f_name = f"{self.active_channel.name}_{datetime.now().strftime('%Y-%m-%d_%H.%M.%S')}.avi"
                    path = os.path.normpath(os.path.join(self.settings.get_string("recordings-path"), f_name))
                    self.player.start_record(path)

        dlg = QuestionDialog(cls)
        if not self.player.is_record():
            dlg.set_body("EXPERIMENTAL!")
        dlg.present(self)

    # ********************** IMDb ********************** #

    @async_function
    def get_imdb_details(self, channel: Channel):
        """ Getting IMDb info for movies and series. """
        if not channel:
            return

        movies = self.ia.search_movie(channel.name)
        for movie in movies:
            self.ia.update(movie)
            if movie.get("plot") is not None:
                title = movie.get("long imdb title", None)
                if title:
                    self.show_message(f"IMDb: {title}")
                break

    # ******************** Search ************************ #

    @Gtk.Template.Callback()
    def on_search(self, entry: Gtk.Entry):
        self.search_running = False
        self.update_search()

    def update_search(self):
        self.search_running = True
        self.search_channels_box.remove_all()
        gen = self.get_channel_search()
        GLib.idle_add(lambda: next(gen, False), priority=GLib.PRIORITY_LOW)

    def get_channel_search(self):
        txt = self.search_entry.get_text().upper()
        if not txt:
            return False

        found = []

        for ch in chain(self.active_provider.channels, self.active_provider.movies, self.active_provider.series):
            if txt in ch.name.upper():
                found.append(ch)
            yield self.search_running

        if found:
            for ch in found:
                self.search_channels_box.append(FlowChannelWidget.get_widget(ch))
                yield self.search_running
            self.search_stack.set_visible_child_name(SearchPage.RESULT)
        else:
            self.search_status.set_title(tr("No Results found"))
            self.search_status.set_description(tr("Try a different search..."))
            self.search_stack.set_visible_child_name(SearchPage.STATUS)

    @Gtk.Template.Callback()
    def on_searched_channel_activated(self, box: Gtk.FlowBox, widget: FlowChannelWidget):
        self.on_flow_channel_activated(widget)

    # ******************** Preferences ******************* #

    @Gtk.Template.Callback()
    def on_preferences_showing(self, page: Adw.NavigationPage):
        self.preferences_page.set_settings(self.settings)

    @Gtk.Template.Callback()
    def on_preferences_hiding(self, page: Adw.NavigationPage):
        if not IS_LINUX:
            os.environ["LANGUAGE"] = Language(self.settings.get_string("language")).name

    @Gtk.Template.Callback()
    def on_preferences_save(self, button):
        def clb(resp):
            if resp:
                if not IS_LINUX:
                    lang = Language(self.settings.get_string("language"))
                    current_lang = Language(self.preferences_page.language)
                    if lang is not current_lang:
                        self.emit("language-changed", current_lang)
                self.history.is_active = self.preferences_page.enable_history
                self.preferences_page.update_settings(self.settings)
                self.navigation_view.pop()

        QuestionDialog(clb).present(self)

    # ********************** EPG ************************* #

    def init_epg(self):
        if self._epg_cache:
            self._epg_cache.provider = self.active_provider
            self._epg_cache.reset()
        else:
            self._epg_cache = EpgCache(self.active_provider)
            self._epg_cache.connect("epg-data-update", self.on_epg_data_update)
            self._epg_cache.connect("epg-data-updated", self.on_epg_data_updated)
            self._epg_cache.connect("epg-error", self.on_epg_error)

        self._epg_timer_id = GLib.timeout_add_seconds(5, self.refresh_epg)

    def refresh_epg(self):
        gen = self.refresh_epg_data()
        GLib.idle_add(lambda: next(gen, False), priority=GLib.PRIORITY_LOW)

        return True

    def refresh_epg_data(self):
        if self.current_page is Page.CHANNELS:
            for w in self.channels_list_box:
                w.set_epg(self._epg_cache.get_current_event(w.channel))
                yield w
        elif self.current_page is Page.OVERVIEW:
            for w in self.overview_flowbox:
                ch_w = w.get_child()
                ch_w.set_epg(self._epg_cache.get_current_event(ch_w.channel))
                yield w

    def on_show_channel_epg(self, win: Adw.ApplicationWindow, channel: Channel):
        if self._epg_cache:
            self.epg_page.show_channel_epg(channel, self._epg_cache.get_current_events(channel))
        else:
            self.show_message("No EPG source initialized!")

        self.navigate_to(Page.EPG)

    def on_epg_data_update(self, cache: EpgCache, msg: str):
        self.status(msg)

    def on_epg_data_updated(self, cache: EpgCache, msg: str):
        self.status(msg)
        GLib.timeout_add_seconds(2, self.status, None)
        if self.current_page is Page.EPG:
            self.epg_page.show_channel_epg(None, self._epg_cache.get_current_events(self.epg_page.current_channel))

    def on_epg_error(self, cache: EpgCache, msg: str):
        GLib.timeout_add_seconds(2, self.status, None)
        self.show_message(msg)

    # ******************* Translation ******************** #

    def on_language_changed(self, window: Adw.ApplicationWindow, lang: Language):
        self.retranslate()

    @idle_function
    def retranslate(self):
        # Search.
        self.search_button.set_tooltip_text(tr("Search"))
        self.search_entry.set_placeholder_text(tr("Search..."))
        self.search_status.set_title(tr("Search in TV, Movies and Series"))
        # Providers.
        self.providers_page.set_title(tr("Providers"))
        self.providers_button.set_tooltip_text(tr("Providers"))
        self.add_provider_button.set_tooltip_text(tr("Add a new provider..."))
        self.reset_providers_button.set_tooltip_text(tr("Reset providers"))
        # History.
        self.history.set_description(tr("Viewing history"))
        self.history.play_all_button.set_tooltip_text(tr("Play All"))
        self.history.clear_button.set_tooltip_text(tr("Clear"))
        # Favorites.
        self.fav_button_content.set_tooltip_text(tr("Favorites"))
        self.favorites.retranslate()

    # ******************** Additional ******************** #

    def on_key_pressed(self, controller: Gtk.EventControllerKey, keyval: int, keycode: int, flags: Gdk.ModifierType):
        ctrl = flags & Gdk.ModifierType.CONTROL_MASK

        if keyval == Gdk.KEY_Left:
            self.on_previous_channel()
        elif keyval == Gdk.KEY_Right:
            self.on_next_channel()
        elif ctrl and keyval in (Gdk.KEY_k, Gdk.KEY_K):
            self.activate_action("win.show-help-overlay")
        elif ctrl and keyval in (Gdk.KEY_l, Gdk.KEY_L):
            self.navigate_to(Page.LOGS)
        elif ctrl and keyval in (Gdk.KEY_r, Gdk.KEY_R):
            self.force_reload()
        elif ctrl and keyval in (Gdk.KEY_f, Gdk.KEY_F):
            if self.current_page is not Page.SEARCH:
                self.navigate_to(Page.SEARCH)
        elif ctrl and keyval in (Gdk.KEY_i, Gdk.KEY_I):
            self.on_stream_info()
        if all((not ctrl, self.current_page is Page.CHANNELS, keyval in (Gdk.KEY_f, Gdk.KEY_F, Gdk.KEY_F11))):
            self.toggle_fullscreen()

    def show_message(self, message: str):
        self.messages_overlay.add_toast(Adw.Toast(title=tr(message)))

    def on_navigation_view_pushed(self, view: Adw.NavigationView):
        page = Page(view.get_visible_page().get_tag())
        self.is_tv_mode = self.current_page not in self.TV_PAGES
        self.is_fav_mode = self.current_page is Page.FAVORITES
        self.current_page = page

        if self.player:
            self.playback_bar.set_visible(self.current_page is not Page.CHANNELS and self.player.is_playing())

    def on_navigation_view_popped(self, view: Adw.NavigationView, prev_page: Adw.NavigationPage):
        self.current_page = Page(view.get_visible_page().get_tag())
        if self.player:
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
        self.manager.save_favorites(self.favorites.get_groups())
        if self.history.is_active:
            self.manager.save_history(self.history.get_channels())
        return False


class Application(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                         **kwargs)
        self.add_main_option("log", ord("l"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "", None)
        self.add_main_option("debug", ord("d"), GLib.OptionFlags.NONE, GLib.OptionArg.STRING, "", None)

        self.style_manager = Adw.StyleManager().get_default()
        self.window = None
        self.init_actions()

    def do_activate(self):
        if not self.window:
            self.window = AppWindow(application=self)

        # App style.
        if self.window.settings.get_value("dark-mode"):
            self.style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

        display = Gdk.Display.get_default()
        provider = Gtk.CssProvider()
        provider.load_from_path(f"{UI_PATH}style.css")
        Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        if not IS_LINUX:
            prefix = "win" if IS_WIN else "mac"
            is_dark = self.style_manager.get_color_scheme() is Adw.ColorScheme.PREFER_DARK

            if IS_DARWIN and not is_dark:
                import subprocess

                cmd = ["defaults", "read", "-g", "AppleInterfaceStyle"]
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
                is_dark = "Dark" in str(p[0])

            css_path = f"{UI_PATH}{prefix}{'-dark' if is_dark else ''}-style.css"

            if os.path.isfile(css_path):
                provider = Gtk.CssProvider()
                provider.load_from_path(css_path)
                Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

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
        self.set_action("about", self.on_about_app)
        self.set_action("logs", self.on_logs)
        self.set_action("preferences", self.on_preferences)
        self.set_action("quit", self.on_close_app)

    def set_action(self, name, fun, enabled=True):
        ac = Gio.SimpleAction.new(name, None)
        ac.connect("activate", fun)
        ac.set_enabled(enabled)
        self.add_action(ac)

        return ac

    def on_logs(self, action, value):
        self.window.navigate_to(Page.LOGS)

    def on_preferences(self, action, value):
        self.window.navigate_to(Page.PREFERENCES)

    def on_about_app(self, action, value):
        about = Adw.AboutDialog()
        about.set_presentation_mode(Adw.DialogPresentationMode.FLOATING)
        about.set_application_name("TVDemon")
        about.set_application_icon("tvdemon")
        about.set_version(__version__)
        about.set_copyright(f"Copyright © 2024-2025 {__author__}")
        about.set_developer_name(__author__)
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_translator_credits(tr("translator-credits"))
        about.set_website("https://dyefremov.github.io/TVDemon/")
        about.set_support_url("https://github.com/DYefremov/TVDemon")
        about.set_comments(('<b>TVDemon</b> based on <a href="https://github.com/linuxmint/hypnotix">Hypnotix</a>\n\n'
                            'This is an IPTV streaming application with support for live TV, movies and series.'))
        about.present(self.window)

    def on_close_app(self, action, value):
        self.window.emit("close-request")
        self.quit()


def run_app():
    app = Application()
    app.run(sys.argv)


if __name__ == "__main__":
    pass
