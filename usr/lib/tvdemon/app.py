#!/usr/bin/python3

# Copyright (C) 2022 Dmitriy Yefremov
#               2020 Linux Mint <root@linuxmint.com>
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
import json
import locale
import os
import shutil
import sys
import time
import traceback
import warnings
from enum import Enum
from functools import partial
from pathlib import Path

# Force X11 on a Wayland session
if "WAYLAND_DISPLAY" in os.environ:
    os.environ["WAYLAND_DISPLAY"] = ""

# Suppress GTK deprecation warnings
warnings.filterwarnings("ignore")

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio, GdkPixbuf, GLib, Pango, GObject

import mpv
import requests
import setproctitle
from imdb import IMDb
from unidecode import unidecode

from common import (Manager, Provider, BADGES, MOVIES_GROUP, PROVIDERS_PATH, SERIES_GROUP, TV_GROUP,
                    async_function, idle_function, Channel)

setproctitle.setproctitle("tvdemon")

APP = 'tvdemon'
UI_PATH = "/usr/share/tvdemon/"
LOCALE_DIR = "/usr/share/locale"
locale.bindtextdomain(APP, LOCALE_DIR)
gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
_ = gettext.gettext

PROVIDER_OBJ, PROVIDER_NAME = range(2)
PROVIDER_TYPE_ID, PROVIDER_TYPE_NAME = range(2)

GROUP_OBJ, GROUP_NAME = range(2)
CHANNEL_OBJ, CHANNEL_NAME, CHANNEL_LOGO = range(3)

COL_PROVIDER_NAME, COL_PROVIDER = range(2)

PROVIDER_TYPE_URL = "url"
PROVIDER_TYPE_LOCAL = "local"
PROVIDER_TYPE_XTREAM = "xtream"

UPDATE_BR_INTERVAL = 5

AUDIO_SAMPLE_FORMATS = {"u16": "unsigned 16 bits",
                        "s16": "signed 16 bits",
                        "s16p": "signed 16 bits, planar",
                        "flt": "float",
                        "float": "float",
                        "fltp": "float, planar",
                        "floatp": "float, planar",
                        "dbl": "double",
                        "dblp": "double, planar"}


class ChannelWidget(Gtk.ListBoxRow):
    """ A custom widget for displaying and holding channel data. """

    TARGET = "GTK_LIST_BOX_ROW"

    def __init__(self, channel, logo, **kwargs):
        super().__init__(**kwargs)
        self._channel = channel
        self.set_tooltip_text(channel.name)
        label = Gtk.Label(channel.name, max_width_chars=30, ellipsize=Pango.EllipsizeMode.END)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(logo, False, False, 6)
        box.pack_start(label, False, False, 6)
        self.add(box)

        self.show_all()

    @property
    def channel(self):
        return self._channel

    @channel.setter
    def channel(self, value):
        self._channel = value


class Page(str, Enum):
    """ Displayed page. """
    SPINNER = "spinner_page"
    LANDING = "landing_page"
    CATEGORIES = "categories_page"
    CHANNELS = "channels_page"
    PROVIDERS = "providers_page"
    VOD = "vod_page"
    EPISODES = "episodes_page"
    PREFERENCES = "preferences_page"
    ADD = "add_page"
    DELETE = "delete_page"
    RESET = "reset_page"
    PLAYER = "player_page"


class Application(Gtk.Application):

    def __init__(self, **kwargs):
        super().__init__(flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE, **kwargs)
        # Signals.
        GObject.signal_new("error", self, GObject.SIGNAL_RUN_LAST, GObject.TYPE_PYOBJECT, (GObject.TYPE_PYOBJECT,))
        self.connect("error", self.on_error)

        self.settings = Gio.Settings(schema_id="org.x.tvdemon")
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
        self.mpv = None
        self.ia = IMDb()

        self.video_properties = {}
        self.audio_properties = {}
        # Historic bitrates of the currently playing media
        self.video_bitrates = []
        self.audio_bitrates = []
        # Used for redownloading timer
        self.reload_timeout_sec = 60 * 5
        self._timer_id = -1
        glade_file = f"{UI_PATH}app.ui"
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain(APP)
        self.builder.add_from_file(glade_file)
        self.window = self.builder.get_object("main_window")
        self.window.connect("delete-event", self.on_close_app)
        self.window.resize(*self.settings.get_value("main-window-size"))
        # The window used to display stream information
        self.info_window = self.builder.get_object("stream_info_window")

        provider = Gtk.CssProvider()
        provider.load_from_path(f"{UI_PATH}style.css")
        screen = Gdk.Display.get_default_screen(Gdk.Display.get_default())
        # I was unable to found instrospected version of this
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Prefs variables
        self.selected_pref_provider = None
        self.edit_mode = False

        # Create variables to quickly access dynamic widgets
        widget_names = ("headerbar", "status_label", "status_bar", "sidebar", "go_back_button", "search_button",
                        "search_bar", "main_paned", "provider_button", "preferences_button",
                        "mpv_drawing_area", "stack", "fullscreen_button", "provider_ok_button",
                        "provider_cancel_button", "name_entry", "path_label", "path_entry", "browse_button",
                        "url_label", "url_entry", "username_label", "username_entry", "password_label",
                        "password_entry", "epg_label", "epg_entry", "tv_logo", "movies_logo", "series_logo",
                        "tv_button", "movies_button", "series_button", "tv_label", "movies_label", "series_label",
                        "categories_flowbox", "channels_list_box", "vod_flowbox", "episodes_box",
                        "stop_button", "pause_button", "show_button", "playback_label", "playback_bar",
                        "providers_flowbox", "new_provider_button", "reset_providers_button",
                        "delete_no_button", "delete_yes_button", "reset_no_button", "reset_yes_button",
                        "info_section", "info_revealer", "info_name_label", "info_plot_label", "info_rating_label",
                        "info_year_label", "close_info_button", "info_genre_label", "info_duration_label",
                        "info_votes_label", "info_pg_label", "divider_label", "useragent_entry", "referer_entry",
                        "mpv_entry", "mpv_link", "mpv_stack", "spinner", "info_window_close_button",
                        "video_properties_box", "video_properties_label", "colour_properties_box",
                        "colour_properties_label", "audio_properties_box", "audio_properties_label",
                        "layout_properties_box", "layout_properties_label", "info_bar", "info_message_label",
                        "fav_button", "fav_box", "fav_list_box", "add_fav_button", "fav_menu", "fav_count_label")

        for name in widget_names:
            widget = self.builder.get_object(name)
            if widget is None:
                print(f"Could not find widget {name}!")
                sys.exit(1)
            else:
                setattr(self, name, widget)

        self.divider_label.set_text("/10")

        # Widget signals
        self.window.connect("key-press-event", self.on_key_press_event)
        self.mpv_drawing_area.connect("realize", self.on_mpv_drawing_area_realize)
        self.mpv_drawing_area.connect("draw", self.on_mpv_drawing_area_draw)
        # Activating mouse events for drawing area.
        self.mpv_drawing_area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        self.mpv_drawing_area.connect("motion-notify-event", self.on_drawing_area_mouse_motion)
        self.mpv_drawing_area.connect("button-press-event", self.on_drawing_area_button_press)
        self._mouse_hide_interval = 3  # Delay before hiding the mouse cursor.
        self._is_mouse_cursor_hidden = True

        self.fullscreen_button.connect("clicked", self.on_fullscreen_button_clicked)

        self.info_window.connect("delete-event", self.on_close_info_window)
        self.info_window_close_button.connect("clicked", self.on_close_info_window_button_clicked)

        self.provider_ok_button.connect("clicked", self.on_provider_ok_button)
        self.provider_cancel_button.connect("clicked", self.on_provider_cancel_button)

        self.name_entry.connect("changed", self.toggle_ok_sensitivity)
        self.url_entry.connect("changed", self.toggle_ok_sensitivity)
        self.path_entry.connect("changed", self.toggle_ok_sensitivity)

        self.tv_button.connect("clicked", self.show_groups, TV_GROUP)
        self.movies_button.connect("clicked", self.show_groups, MOVIES_GROUP)
        self.series_button.connect("clicked", self.show_groups, SERIES_GROUP)
        self.go_back_button.connect("clicked", self.on_go_back_button)

        self.search_button.connect("toggled", self.on_search_button_toggled)
        self.search_bar.connect("activate", self.on_search_bar)

        self.stop_button.connect("clicked", self.on_stop_button)
        self.pause_button.connect("clicked", self.on_pause_button)
        self.show_button.connect("clicked", self.on_show_button)

        self.provider_button.connect("clicked", self.on_provider_button)
        self.preferences_button.connect("clicked", self.on_preferences_button)

        self.new_provider_button.connect("clicked", self.on_new_provider_button)
        self.reset_providers_button.connect("clicked", self.on_reset_providers_button)
        self.delete_no_button.connect("clicked", self.on_delete_no_button)
        self.delete_yes_button.connect("clicked", self.on_delete_yes_button)
        self.reset_no_button.connect("clicked", self.on_reset_no_button)
        self.reset_yes_button.connect("clicked", self.on_reset_yes_button)

        self.browse_button.connect("clicked", self.on_browse_button)
        self.close_info_button.connect("clicked", self.on_close_info_button)
        # Info bar
        self.info_bar.connect("response", lambda b, r: b.set_visible(False))
        # Settings widgets
        self.bind_setting_widget("user-agent", self.useragent_entry)
        self.bind_setting_widget("http-referer", self.referer_entry)
        self.bind_setting_widget("mpv-options", self.mpv_entry)
        # Menubar
        accel_group = Gtk.AccelGroup()
        self.window.add_accel_group(accel_group)
        menu = self.builder.get_object("main_menu")
        icon_size = Gtk.IconSize.MENU
        item = Gtk.ImageMenuItem()
        item.set_image(Gtk.Image.new_from_icon_name("preferences-desktop-keyboard-shortcuts-symbolic", icon_size))
        item.set_label(_("Keyboard Shortcuts"))
        item.connect("activate", self.open_keyboard_shortcuts)
        key, mod = Gtk.accelerator_parse("<Control>K")
        item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        menu.append(item)
        self.info_menu_item = Gtk.ImageMenuItem(_("Stream Information"))
        self.info_menu_item.set_image(Gtk.Image.new_from_icon_name("dialog-information", icon_size))
        self.info_menu_item.connect("activate", self.open_info)
        key, mod = Gtk.accelerator_parse("F2")
        self.info_menu_item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        self.info_menu_item.set_sensitive(False)
        menu.append(self.info_menu_item)
        item = Gtk.ImageMenuItem(_("About"), image=Gtk.Image.new_from_icon_name("help-about-symbolic", icon_size))
        item.connect("activate", self.on_about)
        key, mod = Gtk.accelerator_parse("F1")
        item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        menu.append(item)
        item = Gtk.ImageMenuItem(_("Quit"))
        image = Gtk.Image.new_from_icon_name("application-exit-symbolic", icon_size)
        item.set_image(image)
        item.connect('activate', self.on_menu_quit)
        key, mod = Gtk.accelerator_parse("<Control>Q")
        item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        key, mod = Gtk.accelerator_parse("<Control>W")
        item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        menu.append(item)
        menu.show_all()
        # Type combox box (in preferences)
        model = Gtk.ListStore(str, str)  # PROVIDER_TYPE_ID, PROVIDER_TYPE_NAME
        model.append([PROVIDER_TYPE_URL, _("M3U URL")])
        model.append([PROVIDER_TYPE_LOCAL, _("Local M3U File")])
        model.append([PROVIDER_TYPE_XTREAM, _("Xtream API")])
        self.provider_type_combo = self.builder.get_object("provider_type_combo")
        renderer = Gtk.CellRendererText()
        self.provider_type_combo.pack_start(renderer, True)
        self.provider_type_combo.add_attribute(renderer, "text", PROVIDER_TYPE_NAME)
        self.provider_type_combo.set_model(model)
        self.provider_type_combo.set_active(0)  # Select 1st type
        self.provider_type_combo.connect("changed", self.on_provider_type_combo_changed)

        self.tv_logo.set_from_surface(self.get_surface_for_file(f"{UI_PATH}pictures/tv.svg", 258, 258))
        self.movies_logo.set_from_surface(self.get_surface_for_file(f"{UI_PATH}pictures/movies.svg", 258, 258))
        self.series_logo.set_from_surface(self.get_surface_for_file(f"{UI_PATH}pictures/series.svg", 258, 258))

        self.channels_list_box.connect("row-activated", self.play_channel)
        # Favorites.
        self.non_fav_pages = {Page.CATEGORIES, Page.PROVIDERS, Page.PREFERENCES}
        self._fav_store_path = f"{Path.home()}/.config/tvdemon/favorites.json"
        self.fav_list_box.connect("row-activated", self.play_fav_channel)
        self.add_fav_button.connect("clicked", self.on_add_fav)
        self.fav_button.bind_property("active", self.fav_box, "visible")
        self.fav_button.bind_property("active", self.fav_count_label, "visible")
        self.fav_button.bind_property("active", self.sidebar, "visible", 4)
        self.fav_list_box.connect("realize", self.on_fav_list_box_realize)
        self.fav_list_box.connect("button-press-event", self.on_fav_list_button_press)
        self.fav_list_box.connect("key-press-event", self.on_fav_list_key_press)
        self.channels_list_box.connect("set-focus-child", lambda b, c: self.add_fav_button.set_sensitive(c))
        # Favorites menu.
        item = Gtk.ImageMenuItem(_("Remove"), image=Gtk.Image.new_from_icon_name("edit-delete-symbolic", icon_size))
        item.connect("activate", self.on_fav_delete)
        key, mod = Gtk.accelerator_parse("Delete")
        item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        self.fav_menu.append(item)
        self.fav_menu.show_all()
        # DnD
        targets = [Gtk.TargetEntry.new(ChannelWidget.TARGET, Gtk.TargetFlags.SAME_APP, 0)]
        self.fav_list_box.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, targets, Gdk.DragAction.MOVE)
        self.fav_list_box.drag_dest_set(Gtk.DestDefaults.ALL, targets, Gdk.DragAction.MOVE)
        self.fav_list_box.connect("drag-data-get", self.on_fav_drag_data_get)
        self.fav_list_box.connect("drag-data-received", self.on_fav_drag_data_received)

    def do_startup(self):
        Gtk.Application.do_startup(self)

        self.reload(page=Page.LANDING)
        # Redownload playlists by default
        # This is going to get readjusted
        self._timer_id = GLib.timeout_add_seconds(self.reload_timeout_sec, self.force_reload)

        self.playback_bar.hide()
        self.search_bar.hide()

    def do_activate(self):
        self.window.set_application(self)
        self.window.set_wmclass("TVDemon", "TVDemon")
        self.window.present()

    def do_shutdown(self):
        Gtk.Application.do_shutdown(self)

    def do_command_line(self, command_line):
        self.activate()
        return 0

    def get_surface_for_file(self, filename, width, height):
        scale = self.window.get_scale_factor()
        if width != -1:
            width = width * scale
        if height != -1:
            height = height * scale

        pix_buf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, width, height)
        return Gdk.cairo_surface_create_from_pixbuf(pix_buf, scale)

    def get_surf_based_image(self, filename, width, height):
        surf = self.get_surface_for_file(filename, width, height)
        return Gtk.Image.new_from_surface(surf)

    def add_badge(self, word, box, added_words):
        if word not in added_words:
            for extension in ["svg", "png"]:
                badge = f"{UI_PATH}pictures/badges/{word}.{extension}"
                if os.path.exists(badge):
                    try:
                        image = self.get_surf_based_image(badge, -1, 32)
                        box.pack_start(image, False, False, 0)
                        added_words.append(word)
                        break
                    except Exception as e:
                        print(f"Could not load badge '{badge}'. {e}")

    def show_groups(self, widget, content_type):
        self.content_type = content_type
        self.navigate_to(Page.CATEGORIES)
        for child in self.categories_flowbox.get_children():
            self.categories_flowbox.remove(child)

        self.active_group = None
        found_groups = False
        for group in self.active_provider.groups:
            if group.group_type != self.content_type:
                continue
            found_groups = True
            button = Gtk.Button()
            button.connect("clicked", self.on_category_button_clicked, group)
            label = Gtk.Label()
            if self.content_type == TV_GROUP:
                label.set_text(f"{group.name} ({len(group.channels)})")
            elif self.content_type == MOVIES_GROUP:
                label.set_text(f"{self.remove_word('VOD', group.name)} ({len(group.channels)})")
            else:
                label.set_text(f"{self.remove_word('SERIES', group.name)} ({len(group.series)})")
            box = Gtk.Box()
            name = group.name.lower().replace("(", " ").replace(")", " ")
            added_words = []
            for word in name.split():
                self.add_badge(word, box, added_words)
                if word in BADGES.keys():
                    self.add_badge(BADGES[word], box, added_words)
            box.pack_start(label, False, False, 0)
            box.set_spacing(6)
            button.add(box)
            self.categories_flowbox.add(button)
            self.categories_flowbox.show_all()

        if not found_groups:
            self.on_category_button_clicked(None, None)

    def on_category_button_clicked(self, widget, group):
        self.active_group = group
        if self.content_type == TV_GROUP:
            self.show_channels(group.channels) if group else self.show_channels(self.active_provider.channels)
        elif self.content_type == MOVIES_GROUP:
            self.show_vod(group.channels) if group else self.show_vod(self.active_provider.movies)
        elif self.content_type == SERIES_GROUP:
            self.show_vod(group.series) if group else self.show_vod(self.active_provider.series)

    def show_channels(self, channels):
        self.navigate_to(Page.CHANNELS)
        if self.content_type == TV_GROUP:
            self.sidebar.show()
            self.update_channels_data(channels, self.channels_list_box)
            self.visible_search_results = len(self.channels_list_box.get_children())
        else:
            self.sidebar.hide()

    def update_channels_data(self, channels, ch_box, clear=True):
        if clear:
            list(map(ch_box.remove, ch_box.get_children()))

        logos_to_refresh = []
        list(map(ch_box.add, (self.get_ch_widget(ch, logos_to_refresh) for ch in channels)))

        if len(logos_to_refresh) > 0:
            self.download_channel_logos(logos_to_refresh)

    def get_ch_widget(self, channel, logos_to_refresh):
        logo = Gtk.Image().new_from_surface(self.get_channel_surface(channel.logo_path))
        logos_to_refresh.append((channel, logo))
        widget = ChannelWidget(channel, logo)

        return widget

    def show_vod(self, items):
        logos_to_refresh = []
        self.navigate_to(Page.VOD)

        for child in self.vod_flowbox.get_children():
            self.vod_flowbox.remove(child)

        for item in items:
            button = Gtk.Button()
            button.set_tooltip_text(item.name)
            if self.content_type == MOVIES_GROUP:
                button.connect("clicked", self.on_vod_movie_button_clicked, item)
            else:
                button.connect("clicked", self.on_vod_series_button_clicked, item)
            label = Gtk.Label(item.name, max_width_chars=30, ellipsize=Pango.EllipsizeMode.END)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            image = Gtk.Image().new_from_surface(self.get_channel_surface(item.logo_path))
            logos_to_refresh.append((item, image))
            box.pack_start(image, False, False, 0)
            box.pack_start(label, False, False, 0)
            button.add(box)
            self.vod_flowbox.add(button)
        self.vod_flowbox.show_all()
        if len(logos_to_refresh) > 0:
            self.download_channel_logos(logos_to_refresh)

    def remove_word(self, word, string):
        if " " not in string:
            return string
        words = string.split()
        if word in string:
            words.remove(word)
        return " ".join(words)

    def show_episodes(self, serie):
        logos_to_refresh = []
        self.active_serie = serie
        # If we are using xtream provider
        # Load every Episodes of every Season for this Series
        if self.active_provider.type_id == "xtream":
            self.x.get_series_info_by_id(self.active_serie)

        self.navigate_to(Page.EPISODES)
        for child in self.episodes_box.get_children():
            self.episodes_box.remove(child)
        for season_name in serie.seasons.keys():
            season = serie.seasons[season_name]
            label = Gtk.Label()
            label.set_text(_(f"Season {season_name}"))
            label.get_style_context().add_class("season-label")
            flow_box = Gtk.FlowBox()
            self.episodes_box.pack_start(label, False, False, 0)
            self.episodes_box.pack_start(flow_box, False, False, 0)

            for episode_name in season.episodes.keys():
                episode = season.episodes[episode_name]
                button = Gtk.Button()
                button.set_tooltip_text(episode_name)
                button.connect("clicked", self.on_episode_button_clicked, episode)
                label = Gtk.Label()
                label.set_text(_(f"Episode {episode_name}"))
                label.set_max_width_chars(30)
                label.set_ellipsize(Pango.EllipsizeMode.END)
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                image = Gtk.Image().new_from_surface(self.get_channel_surface(episode.logo_path))
                logos_to_refresh.append((episode, image))
                box.pack_start(image, False, False, 0)
                box.pack_start(label, False, False, 0)
                box.set_spacing(6)
                button.add(box)
                flow_box.add(button)

        self.episodes_box.show_all()

        if len(logos_to_refresh) > 0:
            self.download_channel_logos(logos_to_refresh)

    def on_vod_movie_button_clicked(self, widget, channel):
        self.active_channel = channel
        self.show_channels(None)
        self.play_async(channel)

    def on_episode_button_clicked(self, widget, channel):
        self.active_channel = channel
        self.show_channels(None)
        self.play_async(channel)

    def on_vod_series_button_clicked(self, widget, serie):
        self.show_episodes(serie)

    def bind_setting_widget(self, key, widget):
        widget.set_text(self.settings.get_string(key))
        widget.connect("changed", self.on_entry_changed, key)

    def on_entry_changed(self, widget, key):
        self.settings.set_string(key, widget.get_text())

    @async_function
    def download_channel_logos(self, logos_to_refresh):
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
                print(e)

    @idle_function
    def refresh_channel_logo(self, channel, image):
        image.set_from_surface(self.get_channel_surface(channel.logo_path))

    def get_channel_surface(self, path):
        try:
            return self.get_surface_for_file(path, 64, 32)
        except Exception:
            return self.get_surface_for_file(f"{UI_PATH}generic_tv_logo.png", 22, 22)

    def on_go_back_button(self, widget):
        self.navigate_to(self.back_page)
        if self.active_channel is not None:
            self.playback_bar.show()
        if self.active_group and self.back_page is Page.CATEGORIES:
            self.init_channels_list_box()

    def on_search_button_toggled(self, widget):
        if self.search_button.get_active():
            self.search_bar.show()
            self.search_bar.grab_focus()
        else:
            self.channels_list_box.set_filter_func(None)
            self.fav_list_box.set_filter_func(None)
            self.search_bar.hide()

    def on_search_bar(self, widget):
        self.content_type = TV_GROUP
        search_bar_text = unidecode(self.search_bar.get_text()).lower()
        if search_bar_text != self.latest_search_bar_text:
            self.latest_search_bar_text = search_bar_text
            self.search_bar.set_sensitive(False)
            GLib.timeout_add_seconds(0.1, self.on_search)

    def on_search(self):
        def filter_func(child):
            search_bar_text = unidecode(self.search_bar.get_text()).lower()
            label_text = unidecode(child.channel.name).lower()
            if search_bar_text in label_text:
                self.visible_search_results += 1
                return True
            return False

        self.visible_search_results = 0
        if self.fav_button.get_active():
            self.fav_list_box.set_filter_func(filter_func)
        else:
            self.channels_list_box.set_filter_func(filter_func)

        self.status(_("No channels found") if self.visible_search_results == 0 else None)
        self.search_bar.set_sensitive(True)
        self.search_bar.grab_focus_without_selecting()
        self.navigate_to(Page.CHANNELS)

    def init_channels_list_box(self):
        self.latest_search_bar_text = None
        self.active_group = None
        for child in self.channels_list_box.get_children():
            self.channels_list_box.remove(child)
        self.channels_list_box.invalidate_filter()
        self.visible_search_results = 0

    @idle_function
    def navigate_to(self, page, name=""):
        self.go_back_button.show()
        self.search_button.show()
        self.fullscreen_button.hide()
        self.stack.set_visible_child_name(page)

        if page in self.non_fav_pages:
            self.fav_button.set_active(False)
            self.fav_button.set_sensitive(False)
        else:
            self.fav_button.set_sensitive(True)

        provider = self.active_provider
        if page is Page.LANDING:
            self.back_page = None
            self.headerbar.set_title("TVDemon")

            if provider is None:
                self.headerbar.set_subtitle(_("No provider selected"))
                self.tv_label.set_text(_("TV Channels (0)"))
                self.movies_label.set_text(_("Movies (0)"))
                self.series_label.set_text(_("Series (0)"))
                self.preferences_button.set_sensitive(False)
                self.tv_button.set_sensitive(False)
                self.movies_button.set_sensitive(False)
                self.series_button.set_sensitive(False)
            else:
                self.headerbar.set_subtitle(provider.name)
                self.tv_label.set_text(_(f"TV Channels ({len(provider.channels)})"))
                self.movies_label.set_text(_(f"Movies ({len(provider.movies)})"))
                self.series_label.set_text(_(f"Series ({len(provider.series)})"))
                self.preferences_button.set_sensitive(True)
                self.tv_button.set_sensitive(len(provider.channels) > 0)
                self.movies_button.set_sensitive(len(provider.movies) > 0)
                self.series_button.set_sensitive(len(provider.series) > 0)
            self.go_back_button.hide()
        elif page is Page.CATEGORIES:
            self.back_page = Page.LANDING
            self.headerbar.set_title(provider.name)

            if self.content_type == TV_GROUP:
                self.headerbar.set_subtitle(_("TV Channels"))
            elif self.content_type == MOVIES_GROUP:
                self.headerbar.set_subtitle(_("Movies"))
            else:
                self.headerbar.set_subtitle(_("Series"))
        elif page is Page.CHANNELS:
            self.fullscreen_button.show()
            self.playback_bar.hide()
            self.headerbar.set_title(provider.name)

            if self.content_type == TV_GROUP:
                if self.active_group is None:
                    self.back_page = Page.LANDING
                    self.headerbar.set_subtitle(_("TV Channels"))
                else:
                    self.back_page = Page.CATEGORIES
                    self.headerbar.set_subtitle(_(f"TV Channels > {self.active_group.name}"))
            elif self.content_type == MOVIES_GROUP:
                self.headerbar.set_subtitle(self.active_channel.name if self.active_channel else None)
                self.back_page = Page.VOD
            else:
                self.headerbar.set_subtitle(self.active_channel.name if self.active_channel else None)
                self.back_page = Page.EPISODES
        elif page is Page.VOD:
            self.headerbar.set_title(provider.name)
            if self.content_type == MOVIES_GROUP:
                if self.active_group is None:
                    self.back_page = Page.LANDING
                    self.headerbar.set_subtitle(_("Movies"))
                else:
                    self.back_page = Page.CATEGORIES
                    self.headerbar.set_subtitle(_(f"Movies > {self.active_group.name}"))
            else:
                if self.active_group is None:
                    self.back_page = Page.LANDING
                    self.headerbar.set_subtitle(_("Series"))
                else:
                    self.back_page = Page.CATEGORIES
                    self.headerbar.set_subtitle(_(f"Series > {self.active_group.name}"))
        elif page is Page.EPISODES:
            self.back_page = Page.VOD
            self.headerbar.set_title(provider.name)
            self.headerbar.set_subtitle(self.active_serie.name)
        elif page is Page.PREFERENCES:
            self.back_page = Page.LANDING
            self.headerbar.set_title("TVDemon")
            self.headerbar.set_subtitle(_("Preferences"))
            if self.active_channel is not None:
                self.playback_bar.show()
        elif page is Page.PROVIDERS:
            self.back_page = Page.LANDING
            self.headerbar.set_title("TVDemon")
            self.headerbar.set_subtitle(_("Providers"))
            if self.active_channel is not None:
                self.playback_bar.show()
        elif page is Page.ADD:
            self.back_page = Page.PROVIDERS
            self.headerbar.set_title("TVDemon")
            if self.edit_mode:
                self.headerbar.set_subtitle(_(f"Edit {name}"))
            else:
                self.headerbar.set_subtitle(_("Add a new provider"))
        elif page is Page.DELETE:
            self.back_page = Page.PROVIDERS
            self.headerbar.set_title("TVDemon")
            self.headerbar.set_subtitle(_(f"Delete {name}"))
        elif page is Page.RESET:
            self.back_page = Page.PROVIDERS
            self.headerbar.set_title("TVDemon")
            self.headerbar.set_subtitle(_("Reset providers"))

    def open_keyboard_shortcuts(self, widget):
        builder = Gtk.Builder()
        builder.set_translation_domain(APP)
        builder.add_from_file(f"{UI_PATH}shortcuts.ui")
        window = builder.get_object("shortcuts")
        window.set_title(_("TVDemon"))
        window.show()

    def play_channel(self, box, row):
        self.info_bar.hide()
        self.active_channel = row.channel
        self.play_async(row.channel)

    @async_function
    def play_async(self, channel):
        if not self.mpv:
            return

        self.mpv.stop()

        if channel and channel.url:
            print(f"CHANNEL: '{channel.name}' URL: {channel.url}")
            self.info_menu_item.set_sensitive(False)
            self.before_play(channel)
            self.mpv.play(channel.url)
            self.mpv.wait_until_playing()
            self.after_play(channel)

    @idle_function
    def before_play(self, channel):
        self.mpv_stack.set_visible_child_name(Page.SPINNER)
        self.video_properties.clear()
        self.video_properties[_("General")] = {}
        self.video_properties[_("Color")] = {}

        self.audio_properties.clear()
        self.audio_properties[_("General")] = {}
        self.audio_properties[_("Layout")] = {}

        self.video_bitrates.clear()
        self.audio_bitrates.clear()
        self.spinner.start()

    @idle_function
    def after_play(self, channel):
        self.mpv_stack.set_visible_child_name(Page.PLAYER)
        self.spinner.stop()
        self.playback_label.set_text(channel.name)
        self.info_revealer.set_reveal_child(False)
        if self.content_type == MOVIES_GROUP:
            self.get_imdb_details(channel.name)
        elif self.content_type == SERIES_GROUP:
            self.get_imdb_details(self.active_serie.name)
        self.info_menu_item.set_sensitive(True)
        self.monitor_playback()

    def monitor_playback(self):
        self.mpv.observe_property("video-params", self.on_video_params)
        self.mpv.observe_property("video-format", self.on_video_format)
        self.mpv.observe_property("audio-params", self.on_audio_params)
        self.mpv.observe_property("audio-codec", self.on_audio_codec)
        self.mpv.observe_property("video-bitrate", self.on_bitrate)
        self.mpv.observe_property("audio-bitrate", self.on_bitrate)

    @idle_function
    def on_bitrate(self, prop, bitrate):
        if not bitrate or prop not in ["video-bitrate", "audio-bitrate"]:
            return

        # Only update the bitrates when the info window is open unless we don't have any data yet.
        if _("Average Bitrate") in self.video_properties:
            if _("Average Bitrate") in self.audio_properties:
                if not self.info_window.props.visible:
                    return

        rates = {"video": self.video_bitrates, "audio": self.audio_bitrates}
        rate = "video"
        if prop == "audio-bitrate":
            rate = "audio"

        rates[rate].append(int(bitrate) / 1000.0)
        rates[rate] = rates[rate][-30:]
        br = sum(rates[rate]) / float(len(rates[rate]))

        if rate == "video":
            self.video_properties[_("General")][_("Average Bitrate")] = f"{br:.0f} Kbps"
        else:
            self.audio_properties[_("General")][_("Average Bitrate")] = f"{br:.0f} Kbps"

    @idle_function
    def on_video_params(self, prp, params):
        if not params or not type(params) == dict:
            return
        if "w" in params and "h" in params:
            self.video_properties[_("General")][_("Dimensions")] = f"{params['w']}x{params['h']}"
        if "aspect" in params:
            aspect = round(float(params["aspect"]), 2)
            self.video_properties[_("General")][_("Aspect")] = f"{aspect}"
        if "pixelformat" in params:
            self.video_properties[_("Color")][_("Pixel Format")] = params["pixelformat"]
        if "gamma" in params:
            self.video_properties[_("Color")][_("Gamma")] = params["gamma"]
        if "average-bpp" in params:
            self.video_properties[_("Color")][_("Bits Per Pixel")] = params["average-bpp"]

    @idle_function
    def on_video_format(self, property, vformat):
        if not vformat:
            return
        self.video_properties[_("General")][_("Codec")] = vformat

    @idle_function
    def on_audio_params(self, property, params):
        if not params or not type(params) == dict:
            return
        if "channels" in params:
            chans = params["channels"]
            if "5.1" in chans or "7.1" in chans:
                chans += " " + _("surround sound")
            self.audio_properties[_("Layout")][_("Channels")] = chans
        if "samplerate" in params:
            sr = float(params["samplerate"]) / 1000.0
            self.audio_properties[_("General")][_("Sample Rate")] = f"{sr:.1f}.1f KHz"
        if "format" in params:
            fmt = params["format"]
            if fmt in AUDIO_SAMPLE_FORMATS:
                fmt = AUDIO_SAMPLE_FORMATS[fmt]
            self.audio_properties[_("General")][_("Format")] = fmt
        if "channel-count" in params:
            self.audio_properties[_("Layout")][_("Channel Count")] = params["channel-count"]

    @idle_function
    def on_audio_codec(self, prp, codec):
        if not codec:
            return
        self.audio_properties[_("General")][_("Codec")] = codec.split()[0]

    @async_function
    def get_imdb_details(self, name):
        movies = self.ia.search_movie(name)
        match = None
        for movie in movies:
            self.ia.update(movie)
            if movie.get('plot'):
                match = movie
                break
        self.refresh_info_section(match)

    @idle_function
    def refresh_info_section(self, movie):
        if movie:
            self.set_imdb_info(movie, 'title', self.info_name_label)
            self.set_imdb_info(movie, 'plot outline', self.info_plot_label)
            self.set_imdb_info(movie, 'rating', self.info_rating_label)
            self.set_imdb_info(movie, 'votes', self.info_votes_label)
            self.set_imdb_info(movie, 'year', self.info_year_label)
            self.set_imdb_info(movie, 'genres', self.info_genre_label)
            self.set_imdb_info(movie, 'runtimes', self.info_duration_label)
            self.set_imdb_info(movie, 'certificates', self.info_pg_label)
            self.info_revealer.set_reveal_child(True)

    def set_imdb_info(self, movie, field, widget):
        value = movie.get(field)
        if value:
            if field == "plot":
                value = value[0].split("::")[0]
            elif field == "genres":
                value = ", ".join(value)
            elif field == "certificates":
                pg = ""
                for v in value:
                    if "United States:" in v:
                        pg = v.split(":")[1]
                        break
                value = pg
            elif field == "runtimes":
                value = value[0]
                n = int(value)
                value = f"{n // 60}h {n % 60}min"
        value = str(value).strip()
        if value == "" or value.lower() == "none":
            widget.hide()
        else:
            widget.set_text(value)
            widget.show()

    def on_close_info_button(self, widget):
        self.info_revealer.set_reveal_child(False)

    def on_stop_button(self, widget):
        self.mpv.stop()
        self.info_revealer.set_reveal_child(False)
        self.active_channel = None
        self.info_menu_item.set_sensitive(False)
        self.playback_bar.hide()

    def on_pause_button(self, widget):
        self.mpv.pause = not self.mpv.pause

    def on_show_button(self, widget):
        self.navigate_to(Page.CHANNELS)

    def on_provider_button(self, widget):
        self.navigate_to(Page.PROVIDERS)

    @idle_function
    def refresh_providers_page(self):
        for child in self.providers_flowbox.get_children():
            self.providers_flowbox.remove(child)

        for provider in self.providers:
            labels_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            image = Gtk.Image()
            image.set_from_icon_name("tv-symbolic", Gtk.IconSize.BUTTON)
            labels_box.pack_start(image, False, False, 0)
            label = Gtk.Label()
            label.set_markup("<b>%s</b>" % provider.name)
            labels_box.pack_start(label, False, False, 0)
            num = len(provider.channels)
            if num > 0:
                label = Gtk.Label()
                label.set_text(gettext.ngettext("%d TV channel", "%d TV channels", num) % num)
                labels_box.pack_start(label, False, False, 0)
            num = len(provider.movies)
            if num > 0:
                label = Gtk.Label()
                label.set_text(gettext.ngettext("%d movie", "%d movies", num) % num)
                labels_box.pack_start(label, False, False, 0)
            num = len(provider.series)
            if num > 0:
                label = Gtk.Label()
                label.set_text(gettext.ngettext("%d series", "%d series", num) % num)
                labels_box.pack_start(label, False, False, 0)
            button = Gtk.Button()
            button.connect("clicked", self.on_provider_selected, provider)
            label = Gtk.Label()
            if provider == self.active_provider:
                label.set_text("%s %d (active)" % (provider.name, len(provider.channels)))
            else:
                label.set_text(provider.name)
            button.add(labels_box)
            box = Gtk.Box()
            box.pack_start(button, True, True, 0)
            box.set_spacing(6)
            # Edit button
            button = Gtk.Button(valign=Gtk.Align.CENTER)
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.connect("clicked", self.on_edit_button_clicked, provider)
            image = Gtk.Image()
            image.set_from_icon_name("xapp-edit-symbolic", Gtk.IconSize.BUTTON)
            button.set_tooltip_text(_("Edit"))
            button.add(image)
            box.pack_start(button, False, False, 0)
            # Clear icon cache button
            button = Gtk.Button(valign=Gtk.Align.CENTER)
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.connect("clicked", self.on_clear_icon_cache_button_clicked, provider)
            image = Gtk.Image()
            image.set_from_icon_name("edit-clear-symbolic", Gtk.IconSize.BUTTON)
            button.set_tooltip_text(_("Clear icon cache"))
            button.add(image)
            box.pack_start(button, False, False, 0)
            # Remove button
            button = Gtk.Button(valign=Gtk.Align.CENTER)
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.connect("clicked", self.on_delete_button_clicked, provider)
            image = Gtk.Image()
            image.set_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON)
            button.set_tooltip_text(_("Remove"))
            button.add(image)
            box.pack_start(button, False, False, 0)

            self.providers_flowbox.add(box)

        self.providers_flowbox.show_all()

    def on_provider_selected(self, widget, provider):
        self.active_provider = provider
        self.settings.set_string("active-provider", provider.name)
        self.init_channels_list_box()
        self.navigate_to(Page.LANDING)

    def on_preferences_button(self, widget):
        self.navigate_to(Page.PREFERENCES)

    def on_new_provider_button(self, widget):
        self.name_entry.set_text("")
        self.url_entry.set_text("")
        self.set_provider_type(PROVIDER_TYPE_URL)
        model = self.provider_type_combo.get_model()
        itr = model.get_iter_first()
        while itr:
            type_id = model.get_value(itr, PROVIDER_TYPE_ID)
            if type_id == PROVIDER_TYPE_URL:
                self.provider_type_combo.set_active_iter(itr)
                break
            itr = model.iter_next(itr)
        self.navigate_to(Page.ADD)
        self.edit_mode = False
        self.provider_ok_button.set_sensitive(False)
        self.name_entry.grab_focus()

    def on_reset_providers_button(self, widget):
        self.navigate_to(Page.RESET)

    def on_close_info_window(self, widget, event):
        self.info_window.hide()
        return True

    @async_function
    def on_clear_icon_cache_button_clicked(self, widget, provider: Provider):
        for channel in provider.channels:
            if channel.logo_path:
                Path(channel.logo_path).unlink(missing_ok=True)

    def on_delete_button_clicked(self, widget, provider):
        self.navigate_to(Page.DELETE, provider.name)
        self.marked_provider = provider

    def on_edit_button_clicked(self, widget, provider):
        self.marked_provider = provider
        self.name_entry.set_text(provider.name)
        self.username_entry.set_text(provider.username)
        self.password_entry.set_text(provider.password)
        self.epg_entry.set_text(provider.epg)
        if provider.type_id == PROVIDER_TYPE_LOCAL:
            self.url_entry.set_text("")
            self.path_entry.set_text(provider.url)
        else:
            self.path_entry.set_text("")
            self.url_entry.set_text(provider.url)

        model = self.provider_type_combo.get_model()
        itr = model.get_iter_first()
        while iter:
            type_id = model.get_value(itr, PROVIDER_TYPE_ID)
            if provider.type_id == type_id:
                self.provider_type_combo.set_active_iter(itr)
                break
            itr = model.iter_next(itr)
        self.edit_mode = True
        self.navigate_to(Page.ADD, provider.name)
        self.provider_ok_button.set_sensitive(True)
        self.name_entry.grab_focus()
        self.set_provider_type(provider.type_id)

    def on_delete_no_button(self, widget):
        self.navigate_to(Page.PROVIDERS)

    def on_reset_no_button(self, widget):
        self.navigate_to(Page.PROVIDERS)

    def on_delete_yes_button(self, widget):
        self.providers.remove(self.marked_provider)
        if self.active_provider == self.marked_provider:
            self.active_provider = None
        self.marked_provider = None
        self.save()

    def on_reset_yes_button(self, widget):
        self.settings.reset("providers")
        self.reload(page=Page.PROVIDERS)

    def on_browse_button(self, widget):
        dialog = Gtk.FileChooserDialog(parent=self.window, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        filter_m3u = Gtk.FileFilter()
        filter_m3u.set_name(_("M3U Playlists"))
        filter_m3u.add_pattern("*.m3u*")
        dialog.add_filter(filter_m3u)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            self.path_entry.set_text(path)
            self.epg_entry.set_text(self.manager.get_m3u_tvg_info(path))
        dialog.destroy()

    # ******** PREFERENCES ******** #

    def save(self):
        provider_strings = [provider.get_info() for provider in self.providers]
        self.settings.set_strv("providers", provider_strings)
        self.reload(page=Page.PROVIDERS, refresh=True)

    def on_provider_type_combo_changed(self, widget):
        type_id = self.provider_type_combo.get_model()[self.provider_type_combo.get_active()][PROVIDER_TYPE_ID]
        self.set_provider_type(type_id)

    def set_provider_type(self, type_id):
        widgets = [self.path_entry, self.path_label,
                   self.url_entry, self.url_label,
                   self.username_entry, self.username_label,
                   self.password_entry, self.password_label,
                   self.epg_label, self.epg_entry,
                   self.browse_button]

        [widget.hide() for widget in widgets]
        visible_widgets = [self.epg_label, self.epg_entry]

        if type_id == PROVIDER_TYPE_URL:
            visible_widgets.append(self.url_entry)
            visible_widgets.append(self.url_label)
        elif type_id == PROVIDER_TYPE_LOCAL:
            visible_widgets.append(self.path_entry)
            visible_widgets.append(self.path_label)
            visible_widgets.append(self.browse_button)
        elif type_id == PROVIDER_TYPE_XTREAM:
            visible_widgets.append(self.url_entry)
            visible_widgets.append(self.url_label)
            visible_widgets.append(self.username_entry)
            visible_widgets.append(self.username_label)
            visible_widgets.append(self.password_entry)
            visible_widgets.append(self.password_label)
        else:
            print("Incorrect provider type: ", type_id)

        [widget.show() for widget in visible_widgets]

    def on_provider_ok_button(self, widget):
        type_id = self.provider_type_combo.get_model()[self.provider_type_combo.get_active()][PROVIDER_TYPE_ID]
        name = self.name_entry.get_text()
        if self.edit_mode:
            provider = self.marked_provider
            provider.name = name
        else:
            provider = Provider(name=name, provider_info=None)
            self.providers.append(provider)
        provider.type_id = type_id
        provider.url = self.get_url()
        provider.username = self.username_entry.get_text()
        provider.password = self.password_entry.get_text()
        provider.epg = self.epg_entry.get_text()
        self.save()

    def on_provider_cancel_button(self, widget):
        self.navigate_to(Page.PROVIDERS)

    def toggle_ok_sensitivity(self, widget=None):
        if self.name_entry.get_text() == "":
            self.provider_ok_button.set_sensitive(False)
        elif self.get_url() == "":
            self.provider_ok_button.set_sensitive(False)
        else:
            self.provider_ok_button.set_sensitive(True)

    def get_url(self):
        type_id = self.provider_type_combo.get_model()[self.provider_type_combo.get_active()][PROVIDER_TYPE_ID]
        if type_id == PROVIDER_TYPE_LOCAL:
            widget = self.path_entry
        else:
            widget = self.url_entry

        url = widget.get_text().strip()
        if url == "":
            return ""
        if "://" not in url:
            return f"file://{url}" if type_id == PROVIDER_TYPE_LOCAL else f"http://{url}"
        return url

    # ******** FAVORITES ******* #

    def on_fav_list_box_realize(self, box):
        self.show_fav_channels(self.get_favorites())

    def play_fav_channel(self, box, row):
        if not self.back_page:
            self.navigate_to(Page.CHANNELS)
        self.play_channel(box, row)

    def on_fav_list_button_press(self, list_box, event):
        if event.get_event_type() == Gdk.EventType.BUTTON_PRESS and event.button == Gdk.BUTTON_SECONDARY:
            self.fav_menu.popup(None, None, None, None, event.button, event.time)
            return True

    def on_fav_list_key_press(self, list_box, event):
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        if ctrl and event.keyval in (Gdk.KEY_Up, Gdk.KEY_Down):
            indexes = [r.get_index() for r in list_box.get_selected_rows()]
            dst = min(indexes) - 1 if event.keyval == Gdk.KEY_Up else max(indexes) + 1
            list_box.set_focus_child(list_box.get_row_at_index(dst))
            list_box.set_focus_vadjustment(list_box.get_adjustment())

            if 0 <= dst < len(list_box):
                self.move_list_data(dst, indexes, list_box)

    def on_fav_delete(self, item=None):
        dialog = Gtk.MessageDialog(self.window,
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                   Gtk.MessageType.QUESTION,
                                   Gtk.ButtonsType.OK_CANCEL,
                                   _("Are you sure?"))

        if dialog.run() == Gtk.ResponseType.OK:
            list(map(self.fav_list_box.remove, self.fav_list_box.get_selected_rows()))
            self.fav_count_label.set_text(str(len(self.fav_list_box)))
        dialog.destroy()

    def show_fav_channels(self, channels):
        self.navigate_to(Page.CHANNELS)
        self.update_channels_data(channels, self.fav_list_box, False)
        self.fav_count_label.set_text(str(len(self.fav_list_box)))

    def on_add_fav(self, button):
        channels = [row.channel for row in self.channels_list_box.get_selected_rows()]
        current_count = len(self.fav_list_box)
        self.update_channels_data(channels, self.fav_list_box, False)
        self.fav_count_label.set_text(str(len(self.fav_list_box)))
        self.show_info_message(f"{_('Done!')} {_('Channels added:')} {len(self.fav_list_box) - current_count}")

    def get_favorites(self):
        """ Restores the current favorites list. """
        path = Path(self._fav_store_path)
        try:
            return [Channel.from_dict(f) for f in json.loads(path.read_text())] if path.is_file() else []
        except Exception as e:
            print("Restoring favorites error:", e)

    def on_favorites_store(self):
        """ Stores the current favorites list. """
        if self.fav_list_box.get_realized():
            try:
                path = Path(self._fav_store_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps([vars(r.channel) for r in self.fav_list_box]))
            except Exception as e:
                print("Storing favorites error:", e)

    def on_fav_drag_data_get(self, list_box, context, selection, info, d_time):
        indexes = [r.get_index() for r in list_box.get_selected_rows()]
        selection.set(Gdk.Atom.intern_static_string(ChannelWidget.TARGET), 32, indexes)

    def on_fav_drag_data_received(self, list_box, context, x, y, selection, info, d_time):
        if str(selection.get_target()) == ChannelWidget.TARGET:
            dst = list_box.get_row_at_y(y)
            self.move_list_data(dst.get_index() if dst else len(list_box), list(selection.get_data()), list_box)
            context.finish(True, False, d_time)

    def move_list_data(self, dst, indexes, list_box):
        rows = [list_box.get_row_at_index(i) for i in indexes]
        list(map(list_box.remove, rows))
        list(map(lambda r: list_box.insert(r, dst), reversed(rows)))

    # ************************** #

    def open_info(self, widget):
        """
        Display a dialog containing information about the currently
        playing stream based on properties emitted by MPV during playback
        """
        sections = [self.video_properties_box, self.colour_properties_box,
                    self.audio_properties_box, self.layout_properties_box]

        for section in sections:
            for child in section.get_children():
                section.remove(child)

        props = [self.video_properties[_("General")],
                 self.video_properties[_("Color")],
                 self.audio_properties[_("General")],
                 self.audio_properties[_("Layout")]]

        for section, props in zip(sections, props):
            for prop_k, prop_v in props.items():
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                              margin_left=24, margin_right=24, margin_top=6, margin_bottom=6)
                box.set_halign(Gtk.Align.FILL)
                box_inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14 * 12, expand=True)
                k = Gtk.Label(label=prop_k, margin_top=12, margin_bottom=12)
                k.set_halign(Gtk.Align.START)
                v = Gtk.Label(label=prop_v, margin_top=12, margin_bottom=12)

                def update_bitrate(label, properties):
                    """
                    Periodically update a label displaying the average
                    bitrate whilst the info dialog is visible.
                    """
                    if not self.info_window.props.visible:
                        return False
                    if _("Average Bitrate") in properties:
                        label.set_text(properties[_("Average Bitrate")])
                    return True

                if prop_k == _("Average Bitrate") and props == self.video_properties[_("General")]:
                    cb = partial(update_bitrate, v, props)
                    GLib.timeout_add_seconds(UPDATE_BR_INTERVAL, cb)

                elif prop_k == _("Average Bitrate") and props == self.audio_properties[_("General")]:
                    cb = partial(update_bitrate, v, props)
                    GLib.timeout_add_seconds(UPDATE_BR_INTERVAL, cb)

                v.set_halign(Gtk.Align.CENTER)
                box_inner.pack_start(k, True, True, 0)
                box_inner.pack_end(v, False, False, 0)
                box.add(box_inner)
                seperator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                section.add(seperator)
                section.add(box)
        self.info_window.show_all()

    def on_about(self, widget):
        builder = Gtk.Builder()
        builder.add_from_file(f"{UI_PATH}about.ui")
        dialog = builder.get_object("dialog")
        dialog.run()
        dialog.destroy()

    def on_menu_quit(self, widget):
        self.on_close_app()
        self.quit()

    def on_key_press_event(self, widget, event):
        # Get any active, but not pressed modifiers, like CapsLock and NumLock
        persistant_modifiers = Gtk.accelerator_get_default_mod_mask()

        # Determine the actively pressed modifier
        modifier = event.get_state() & persistant_modifiers
        # Bool of Control or Shift modifier states
        ctrl = modifier == Gdk.ModifierType.CONTROL_MASK
        shift = modifier == Gdk.ModifierType.SHIFT_MASK
        key = event.keyval

        if ctrl and event.keyval == Gdk.KEY_r:
            self.reload(page=None, refresh=True)
        elif ctrl and key == Gdk.KEY_f:
            if self.search_button.get_active():
                self.search_button.set_active(False)
            else:
                self.search_button.set_active(True)
        elif key == Gdk.KEY_F11 or (key == Gdk.KEY_f and not ctrl and type(
                widget.get_focus()) != Gtk.SearchEntry) or (self.fullscreen and key == Gdk.KEY_Escape):
            self.toggle_fullscreen()
        elif event.keyval == Gdk.KEY_Left:
            self.on_previous_channel()
        elif event.keyval == Gdk.KEY_Right:
            self.on_next_channel()

    @async_function
    def reload(self, page=None, refresh=False):
        self.status(_("Loading providers..."))
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
                        self.status(_("Downloading playlist..."), provider)
                    else:
                        self.status(_("Getting playlist..."), provider)
                    ret = self.manager.get_playlist(provider, refresh=refresh)
                    p_name = provider.name
                    if ret:
                        self.status(_("Checking playlist..."), provider)
                        if self.manager.check_playlist(provider):
                            self.status(_("Loading channels..."), provider)
                            self.manager.load_channels(provider)
                            if p_name == self.settings.get_string("active-provider"):
                                self.active_provider = provider
                            self.status(None)
                            lc, lg, ls = len(provider.channels), len(provider.groups), len(provider.series)
                            print(f"{p_name}: {lc} channels, {lg} groups, {ls} series, {len(provider.movies)} movies")
                    else:
                        self.status(_(f"Failed to Download playlist from {p_name}"), provider)

                else:
                    # Load xtream class
                    from xtream import XTream
                    # Download via Xtream
                    self.x = XTream(provider.name, provider.username, provider.password, provider.url,
                                    hide_adult_content=False, cache_path=PROVIDERS_PATH)
                    if self.x.auth_data != {}:
                        print("XTREAM `{}` Loading Channels".format(provider.name))
                        # Save default cursor
                        current_cursor = self.window.get_window().get_cursor()
                        # Set waiting cursor
                        self.window.get_window().set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), 'wait'))
                        # Load data
                        self.x.load_iptv()
                        # Restore default cursor
                        self.window.get_window().set_cursor(current_cursor)
                        # Inform Provider of data
                        provider.channels = self.x.channels
                        provider.movies = self.x.movies
                        provider.series = self.x.series
                        provider.groups = self.x.groups

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
                        print("XTREAM Authentication Failed")

            except Exception as e:
                print(e)
                traceback.print_exc()
                print("Couldn't parse provider info: ", provider_info)

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
            self.status_label.set_text("")
            self.status_label.hide()
            return
        self.status_label.show()
        if provider:
            status = f"{provider.name}: {string}"
            self.status_label.set_text(status)
            print(status)
        else:
            self.status_label.set_text(string)
            print(string)

    def on_mpv_drawing_area_realize(self, widget):
        self.reinit_mpv()

    def reinit_mpv(self):
        if self.mpv:
            self.mpv.stop()
        options = {}
        try:
            mpv_options = self.settings.get_string("mpv-options")
            if "=" in mpv_options:
                pairs = mpv_options.split()
                for pair in pairs:
                    key, value = pair.split("=")
                    options[key] = value
        except Exception as e:
            print("Could not parse MPV options!")
            print(e)

        options["user_agent"] = self.settings.get_string("user-agent")
        options["referrer"] = self.settings.get_string("http-referer")

        while not self.mpv_drawing_area.get_window() and not Gtk.events_pending():
            time.sleep(0.1)

        self.mpv = mpv.MPV(**options, input_cursor=False, cursor_autohide="no", input_default_bindings=False, ytdl=True,
                           wid=str(self.mpv_drawing_area.get_window().get_xid()))

        @self.mpv.event_callback(mpv.MpvEventID.END_FILE)
        def on_end(event):
            event = event.as_dict(mpv.strict_decoder)
            if event.get("reason", None) == "error":
                error = event.get("file_error", _("Can't Playback!")).capitalize()
                GLib.idle_add(self.emit, "error", f"{error}.")

    def on_mpv_drawing_area_draw(self, widget, cr):
        cr.set_source_rgb(0.0, 0.0, 0.0)
        cr.paint()

    def toggle_fullscreen(self):
        if self.stack.get_visible_child_name() == Page.CHANNELS:
            # Toggle state
            self.fullscreen = (not self.fullscreen)
            if self.fullscreen:
                # Fullscreen mode
                self.window.fullscreen()
                self.sidebar.hide()
                self.headerbar.hide()
                self.status_label.hide()
                self.info_revealer.set_reveal_child(False)
                self.main_paned.set_border_width(0)
            else:
                # Normal mode
                self.window.unfullscreen()
                if self.content_type == TV_GROUP and not self.fav_button.get_active():
                    self.sidebar.show()
                self.headerbar.show()
                self.main_paned.set_border_width(12)

        if self.fav_button.get_active():
            self.fav_box.set_visible(not self.fullscreen)

    def on_fullscreen_button_clicked(self, widget):
        self.toggle_fullscreen()

    def on_drawing_area_mouse_motion(self, widget, event):
        if self._is_mouse_cursor_hidden:
            self._is_mouse_cursor_hidden = False
            display = widget.get_display()
            window = event.get_window()
            window.set_cursor(Gdk.Cursor.new_from_name(display, "default"))

            GLib.timeout_add_seconds(self._mouse_hide_interval, self.hide_mouse_cursor, window, display)

    def hide_mouse_cursor(self, window, display):
        self._is_mouse_cursor_hidden = True
        window.set_cursor(Gdk.Cursor.new_for_display(display, Gdk.CursorType.BLANK_CURSOR))

    def on_drawing_area_button_press(self, widget, event):
        if event.get_event_type() == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == Gdk.BUTTON_PRIMARY:
            self.toggle_fullscreen()

    def on_previous_channel(self):
        if self.stack.get_visible_child_name() == Page.CHANNELS:
            self.activate_channel(self.fav_list_box if self.fav_button.get_active() else self.channels_list_box, -1)

    def on_next_channel(self):
        if self.stack.get_visible_child_name() == Page.CHANNELS:
            self.activate_channel(self.fav_list_box if self.fav_button.get_active() else self.channels_list_box, 1)

    def activate_channel(self, box, movement=0):
        box.do_move_cursor(box, Gtk.MovementStep.DISPLAY_LINES, movement)
        box.do_activate_cursor_row(box)

    def on_error(self, ap, msg=""):
        self.show_info_message(msg, Gtk.MessageType.ERROR)

    def show_info_message(self, msg, message_type=Gtk.MessageType.INFO):
        self.info_bar.set_visible(True)
        self.info_bar.set_message_type(message_type)
        self.info_message_label.set_text(msg)

    def on_close_app(self, window=None, event=None):
        # Saving main window size.
        width, height = self.window.get_size()
        w_size = GLib.Variant.new_tuple(GLib.Variant.new_int32(width), GLib.Variant.new_int32(height))
        self.settings.set_value("main-window-size", w_size)
        # Saving favorites list.
        self.on_favorites_store()

    def on_close_info_window_button_clicked(self, widget):
        self.info_window.hide()


if __name__ == "__main__":
    app = Application()
    sys.exit(app.run(sys.argv))
