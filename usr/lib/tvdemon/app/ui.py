# -*- coding: utf-8 -*-
#
# Copyright © 2022-2024 Dmitriy Yefremov <https://github.com/DYefremov>
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
# Author: Dmitriy Yefremov
#

__all__ = ("Page", "PLaybackPage", "SearchPage", "ProviderType", "ProviderWidget", "ProviderProperties",
           "ChannelWidget", "GroupWidget", "FlowChannelWidget", "FavoritesGroupWidget", "PreferencesPage",
           "FavoritesPage", "QuestionDialog", "ShortcutsWindow")

from datetime import datetime
from enum import StrEnum, IntEnum
from html import escape

from .epg import EpgEvent, EPG_START_FMT, EPG_END_FMT
from .common import (UI_PATH, Adw, Gtk, Gdk, GObject, GLib, idle_function, translate, select_path, Group,
                     get_pixbuf_from_file, Channel)


class Page(StrEnum):
    """ Displayed page. """
    START = "start-page"
    FAVORITES = "favorites-page"
    CATEGORIES = "categories-page"
    CHANNELS = "channels-page"
    SEARCH = "search-page"
    TV = "tv-page"
    EPG = "epg-page"
    MOVIES = "movies-page"
    SERIES = "series-page"
    PROVIDERS = "providers-page"
    PROVIDER = "provider-properties-page"
    PREFERENCES = "preferences-page"


class PLaybackPage(StrEnum):
    STATUS = "status"
    LOAD = "load"
    PLAYBACK = "playback"


class SearchPage(StrEnum):
    STATUS = "search-status"
    RESULT = "search-result"


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
        select_path(self.get_root(), callback=row.set_subtitle, select_file=True)


@Gtk.Template(filename=f"{UI_PATH}channel_widget.ui")
class ChannelWidget(Gtk.ListBoxRow):
    """ A custom widget for displaying and holding channel data. """
    __gtype_name__ = "ChannelWidget"

    label = Gtk.Template.Child()
    logo = Gtk.Template.Child()
    fav_logo = Gtk.Template.Child()
    epg_label = Gtk.Template.Child()

    def __init__(self, channel, logo_pixbuf=None, **kwargs):
        super().__init__(**kwargs)
        self.channel = channel

        self.label.set_text(channel.name)
        self.set_tooltip_text(channel.name)
        self.logo.set_from_pixbuf(logo_pixbuf) if logo_pixbuf else None

    @Gtk.Template.Callback()
    def on_epg_show(self, button: Gtk.Button):
        self.get_root().emit("show-channel-epg", self.channel)

    def set_epg(self, event: EpgEvent):
        if event.start:
            start = datetime.fromtimestamp(event.start).strftime(EPG_START_FMT)
            end = datetime.fromtimestamp(event.end).strftime(EPG_END_FMT)
            sep = "-"
            self.epg_label.set_markup((f'<span weight="bold">{escape(event.title)}</span>\n'
                                       f'<span style="italic">{start} {sep} {end}</span>'))


@Gtk.Template(filename=f"{UI_PATH}group_widget.ui")
class GroupWidget(Gtk.FlowBoxChild):
    """ A custom widget for displaying and holding group data. """
    __gtype_name__ = "GroupWidget"

    box = Gtk.Template.Child()
    label = Gtk.Template.Child()
    logo = Gtk.Template.Child()

    def __init__(self, data, name, logo_pixbuf=None, orientation=Gtk.Orientation.HORIZONTAL, **kwargs):
        super().__init__(**kwargs)
        self.data = data
        self.name = name
        self.label.set_text(name)
        self.box.set_orientation(orientation)
        self.logo.set_from_pixbuf(logo_pixbuf) if logo_pixbuf else None


@Gtk.Template(filename=f"{UI_PATH}preferences.ui")
class PreferencesPage(Adw.PreferencesPage):
    __gtype_name__ = "PreferencesPage"

    reload_interval_spin = Gtk.Template.Child()
    dark_mode_switch = Gtk.Template.Child()
    media_lib_row = Gtk.Template.Child()
    recordings_path_row = Gtk.Template.Child()
    useragent_entry = Gtk.Template.Child()
    referer_entry = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @Gtk.Template.Callback("on_recordings_path_activated")
    def on_recordings_path_select(self, row: Adw.ActionRow):
        select_path(self.get_root(), callback=row.set_subtitle)

    @property
    def reload_interval(self) -> int:
        return int(self.reload_interval_spin.get_value()) * 3600

    @reload_interval.setter
    def reload_interval(self, value: int):
        self.reload_interval_spin.set_value(value // 3600)

    @property
    def dark_mode(self) -> bool:
        return self.dark_mode_switch.get_active()

    @dark_mode.setter
    def dark_mode(self, value: bool):
        return self.dark_mode_switch.set_active(value)

    @property
    def useragent(self):
        return self.useragent_entry.get_text()

    @useragent.setter
    def useragent(self, value):
        self.useragent_entry.set_text(value)

    @property
    def referer(self) -> str:
        return self.referer_entry.get_text()

    @referer.setter
    def referer(self, value: str):
        self.referer_entry.set_text(value)

    @property
    def recordings_path(self) -> str:
        return self.recordings_path_row.get_subtitle()

    @recordings_path.setter
    def recordings_path(self, value: str):
        self.recordings_path_row.set_subtitle(value)

    @property
    def playback_library(self) -> int:
        return self.media_lib_row.get_selected()

    @playback_library.setter
    def playback_library(self, value: int):
        self.media_lib_row.set_selected(value)


@Gtk.Template(filename=f"{UI_PATH}media_bar.ui")
class MediaBar(Gtk.Frame):
    __gtype_name__ = "MediaBar"

    title_label = Gtk.Template.Child()
    subtitle_label = Gtk.Template.Child()
    stop_button = Gtk.Template.Child()
    pause_button = Gtk.Template.Child()
    backward_button = Gtk.Template.Child()
    forward_button = Gtk.Template.Child()
    volume_button = Gtk.Template.Child()

    def set_title(self, title: str):
        self.title_label.set_text(title)

    def set_subtitle(self, subtitle: str):
        self.subtitle_label.set_text(subtitle)


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


# ******************** Favorites ******************** #

@Gtk.Template(filename=f"{UI_PATH}favorites_group_widget.ui")
class FavoritesGroupWidget(Adw.ActionRow):
    """ A custom widget for displaying and holding favorite group data. """
    __gtype_name__ = "FavoritesGroupWidget"

    remove_button = Gtk.Template.Child()

    def __init__(self, page, group, **kwargs):
        super().__init__(**kwargs)
        self.page = page
        self.group = group
        self.set_title(group.name)
        self.update_channels_count()

    @Gtk.Template.Callback()
    def on_edit(self, button):
        self.page.emit("favorite-group-edit", self)

    @Gtk.Template.Callback()
    def on_remove(self, button):
        self.page.emit("favorite-group-remove", self)

    def append_channel(self, channel):
        self.group.channels.append(channel)
        self.update_channels_count()

    def update_channels_count(self):
        self.set_subtitle(f"{translate('Channels')}: {len(self.group.channels)}")


@Gtk.Template(filename=f"{UI_PATH}flow_channel_widget.ui")
class FlowChannelWidget(Gtk.FlowBoxChild):
    __gtype_name__ = "FlowChannelWidget"

    label = Gtk.Template.Child()
    logo = Gtk.Template.Child()
    show_button = Gtk.Template.Child()
    remove_button = Gtk.Template.Child()

    def __init__(self, channel, logo_pixbuf=None, show_buttons=False, **kwargs):
        super().__init__(**kwargs)
        self.channel = channel

        self.label.set_text(channel.name)
        self.logo.set_from_pixbuf(logo_pixbuf) if logo_pixbuf else None
        self.show_button.set_visible(show_buttons)
        self.remove_button.set_visible(show_buttons)

    @Gtk.Template.Callback()
    def on_remove(self, button):
        self.get_parent().remove(self)

    @Gtk.Template.Callback()
    def on_playback(self, button):
        pass


@Gtk.Template(filename=f"{UI_PATH}favorites.ui")
class FavoritesPage(Adw.NavigationPage):
    """ Favorites page class.

       Processes and holds favorite channels data.
    """
    __gtype_name__ = "FavoritesPage"

    class FavoritePage(StrEnum):
        GROUPS = "groups-page"
        PROPERTIES = "properties-page"

    navigation_view = Gtk.Template.Child()
    group_list = Gtk.Template.Child()
    group_channels_box = Gtk.Template.Child()
    group_name_row = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Signals.
        GObject.signal_new("favorite-add", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))
        GObject.signal_new("favorite-group-activated", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))
        GObject.signal_new("favorite-group-remove", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))
        GObject.signal_new("favorite-group-edit", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))
        GObject.signal_new("favorite-group-set-default", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))
        GObject.signal_new("favorite-groups-updated", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))
        GObject.signal_new("favorite-list-updated", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))
        GObject.signal_new("favorites-error", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))

        self.current_group = None
        self.edit_group = None
        self.channels_count = 0
        self.urls = set()

        self.connect("favorite-add", self.on_favorite_add)
        self.connect("favorite-group-edit", self.on_group_edit)
        self.connect("favorite-group-remove", self.on_group_remove)
        self.connect("favorite-group-set-default", self.on_favorite_group_set_default)
        # Group channels DnD.
        dnd = Gtk.DropTarget.new(FlowChannelWidget, Gdk.DragAction.MOVE)
        dnd.connect("drop", self.on_favorite_channel_dnd_drop)
        self.group_channels_box.add_controller(dnd)
        dnd = Gtk.DragSource.new()
        dnd.set_actions(Gdk.DragAction.MOVE)
        dnd.connect("prepare", self.on_favorite_channel_dnd_prepare)
        self.group_channels_box.add_controller(dnd)

    @Gtk.Template.Callback()
    def on_group_activated(self, box: Gtk.ListBox, group_widget: FavoritesGroupWidget):
        self.emit("favorite-group-activated", group_widget.group)

    @Gtk.Template.Callback()
    def on_new_group(self, button):
        self.group_list.append(FavoritesGroupWidget(self, Group(self.get_new_group_name("New group"))))
        [g.remove_button.set_sensitive(True) for g in self.group_list]
        self.emit("favorite-groups-updated", self.get_groups())

    @Gtk.Template.Callback()
    def on_group_save(self, button):
        QuestionDialog(self.get_root(), self.save_group).present()

    def save_group(self, confirm):
        if confirm and self.edit_group:
            group = self.edit_group.group
            name = self.group_name_row.get_text()

            if group.name != name:
                if name in self.get_group_names():
                    self.emit("favorites-error", "A group with that name exists!")
                    return

                self.emit("favorite-groups-updated", self.get_groups())

            group.name = name
            channels = [ch.channel for ch in self.group_channels_box]
            urls = {c.url for c in channels}
            ch_count = len(group.channels)

            if ch_count > len(channels):
                ch_count -= len(channels)
                self.channels_count -= ch_count
                [self.urls.discard(c.url) for c in group.channels if c.url not in urls]
                self.emit("favorite-list-updated", self.channels_count)

            group.channels = channels
            self.edit_group.update_channels_count()
            self.edit_group.set_title(name)
            self.navigation_view.pop()

    def on_group_edit(self, page, group_widget):
        self.group_channels_box.remove_all()
        self.edit_group = group_widget
        group = group_widget.group
        self.group_name_row.set_text(group.name)
        for ch in group.channels:
            path = ch.logo_path
            pixbuf = get_pixbuf_from_file(path) if path else None
            self.group_channels_box.append(FlowChannelWidget(ch, pixbuf, True))
        self.navigation_view.push_by_tag(self.FavoritePage.PROPERTIES)

    def on_group_remove(self, page, group_widget):
        self.channels_count -= len(group_widget.group.channels)
        [self.urls.discard(c.url) for c in group_widget.group.channels]
        self.group_list.remove(group_widget)
        self.current_group = self.group_list.get_first_child()
        self.current_group.remove_button.set_sensitive(len((list(self.group_list))) > 1)
        self.emit("favorite-list-updated", self.channels_count)
        self.emit("favorite-groups-updated", self.get_groups())

    def on_favorite_group_set_default(self, page, group_name):
        for gw in self.group_list:
            grp = gw.group
            is_default = grp.name == group_name
            grp.is_default = is_default
            if is_default:
                self.current_group = gw

    @idle_function
    def set_groups(self, groups: list):
        self.group_list.remove_all()
        self.urls.clear()
        for g in groups:
            w = FavoritesGroupWidget(self, g)
            if g.is_default:
                self.current_group = w
            self.channels_count += len(g.channels)
            self.group_list.append(w)
            [self.urls.add(c.url) for c in g.channels]
        if not self.current_group:
            self.current_group = self.group_list.get_first_child()
        self.current_group.remove_button.set_sensitive(len(groups) > 1)
        self.emit("favorite-list-updated", self.channels_count)
        self.emit("favorite-groups-updated", groups)

    def get_groups(self) -> list:
        return [g.group for g in self.group_list]

    def get_group_names(self) -> set:
        return {g.name for g in self.get_groups()}

    def get_new_group_name(self, base_name: str) -> str:
        names = self.get_group_names()
        count = 0
        name = base_name
        while name in names:
            count += 1
            name = f"{base_name}{count}"

        return name

    def on_favorite_add(self, page, channel):
        self.current_group.append_channel(channel)
        self.channels_count += 1
        self.urls.add(channel.url)
        self.emit("favorite-list-updated", self.channels_count)

    def on_favorite_channel_dnd_drop(self, drop: Gtk.DropTarget, user_data: FlowChannelWidget, x: float, y: float):
        dest_child = self.group_channels_box.get_child_at_pos(x, y)
        if dest_child:
            index = dest_child.get_index()
            self.group_channels_box.remove(user_data)
            self.group_channels_box.insert(user_data, index)

    def on_favorite_channel_dnd_prepare(self, drag_source: Gtk.DragSource, x: float, y: float):
        child = self.group_channels_box.get_child_at_pos(x, y)
        if not child:
            return

        if child.logo:
            drag_source.set_icon(child.logo.get_paintable(), 0, 0)

        content = Gdk.ContentProvider.new_for_value(GObject.Value(FlowChannelWidget, child))
        return content

    def is_favorite(self, channel: Channel):
        return channel.url in self.urls


@Gtk.Template(filename=f"{UI_PATH}epg.ui")
class EpgPage(Adw.NavigationPage):
    """ EPG page class. """
    __gtype_name__ = "EpgPage"

    event_list = Gtk.Template.Child()
    search_button = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_list.set_filter_func(self.filter_func)

    @Gtk.Template.Callback()
    def on_showing(self, page: Adw.NavigationPage):
        self.event_list.remove_all()

    @Gtk.Template.Callback()
    def on_hidden(self, page: Adw.NavigationPage):
        self.on_search_stop(self.search_entry)

    @Gtk.Template.Callback()
    def on_search_button_clicked(self, button: Gtk.Button):
        button.set_visible(False)

    @Gtk.Template.Callback()
    def on_search(self, entry: Gtk.SearchEntry):
        self.event_list.invalidate_filter()

    @Gtk.Template.Callback()
    def on_search_stop(self, entry: Gtk.SearchEntry):
        entry.set_text("")
        self.search_button.set_visible(True)

    def filter_func(self, row: Adw.ActionRow):
        txt = self.search_entry.get_text().upper()
        return any((not txt,  txt in row.get_title().upper(), txt in row.get_subtitle().upper()))

    def show_channel_epg(self, events: list | None):
        if events:
            gen = self.update_epg(events)
            GLib.idle_add(lambda: next(gen, False), priority=GLib.PRIORITY_LOW)

    def update_epg(self, events: list | None):
        for e in events:
            self.event_list.append(self.get_epg_row(e))
            yield True

    def get_epg_row(self, e):
        row = Adw.ActionRow()
        row.set_icon_name("media-view-subtitles-symbolic")
        row.set_title(e.title)
        start = datetime.fromtimestamp(e.start).strftime(EPG_START_FMT)
        end = datetime.fromtimestamp(e.end).strftime(EPG_END_FMT)
        desc = f"\n{start} - {end} \n\n {e.desc or ''}"
        row.set_subtitle(desc)
        return row


if __name__ == "__main__":
    pass
