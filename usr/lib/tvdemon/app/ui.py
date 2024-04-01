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

__all__ = ("Page", "PLaybackPage", "ProviderType", "ProviderWidget", "ProviderProperties",
           "ChannelWidget", "GroupWidget", "FavoritesGroupWidget", "PreferencesPage",
           "FavoritesPage", "QuestionDialog", "ShortcutsWindow")

from enum import StrEnum, IntEnum
from .common import (UI_PATH, Adw, Gtk, Gdk, GObject, idle_function, translate, select_path, Group,
                     get_pixbuf_from_file)


class Page(StrEnum):
    """ Displayed page. """
    START = "start-page"
    FAVORITES = "favorites-page"
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
        self.data = data
        self.name = name
        self.label.set_text(name)
        self.box.set_orientation(orientation)
        self.logo.set_from_pixbuf(logo_pixbuf) if logo_pixbuf else None


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


@Gtk.Template(filename=f"{UI_PATH}favorite_channel_widget.ui")
class FavoriteChannelWidget(Gtk.FlowBoxChild):
    __gtype_name__ = "FavoriteChannelWidget"

    label = Gtk.Template.Child()
    logo = Gtk.Template.Child()

    def __init__(self, channel, logo_pixbuf=None, **kwargs):
        super().__init__(**kwargs)
        self.channel = channel

        self.label.set_text(channel.name)
        self.set_tooltip_text(channel.name)
        self.logo.set_from_pixbuf(logo_pixbuf) if logo_pixbuf else None


@Gtk.Template(filename=f"{UI_PATH}favorites.ui")
class FavoritesPage(Adw.NavigationPage):
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
        GObject.signal_new("favorite-list-updated", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))

        self.current_group = None
        self.channels_count = 0

        self.connect("favorite-add", self.on_favorite_add)
        self.connect("favorite-group-edit", self.on_group_edit)
        self.connect("favorite-group-remove", self.on_group_remove)
        # Group channels DnD.
        dnd = Gtk.DropTarget.new(FavoriteChannelWidget, Gdk.DragAction.MOVE)
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
        self.group_list.append(FavoritesGroupWidget(self, Group("New group")))
        [g.remove_button.set_sensitive(True) for g in self.group_list]

    @idle_function
    def set_groups(self, groups):
        self.group_list.remove_all()
        for g in groups:
            w = FavoritesGroupWidget(self, g)
            if g.is_default:
                self.current_group = w
            self.channels_count += len(g.channels)
            self.group_list.append(w)
        if not self.current_group:
            self.current_group = self.group_list.get_first_child()
        self.current_group.remove_button.set_sensitive(len(groups) > 1)
        self.emit("favorite-list-updated", self.channels_count)

    def get_groups(self):
        return [g.group for g in self.group_list]

    def on_favorite_add(self, page, channel):
        self.current_group.append_channel(channel)
        self.channels_count += 1
        self.emit("favorite-list-updated", self.channels_count)

    def on_group_edit(self, page, group_widget):
        self.group_channels_box.remove_all()
        group = group_widget.group
        self.group_name_row.set_text(group.name)
        for ch in group.channels:
            path = ch.logo_path
            pixbuf = get_pixbuf_from_file(path) if path else None
            self.group_channels_box.append(FavoriteChannelWidget(ch, pixbuf))
        self.navigation_view.push_by_tag(self.FavoritePage.PROPERTIES)

    def on_group_remove(self, page, group_widget):
        self.channels_count -= len(group_widget.group.channels)
        self.group_list.remove(group_widget)
        self.current_group = self.group_list.get_first_child()
        self.current_group.remove_button.set_sensitive(len((list(self.group_list))) > 1)

    def on_favorite_channel_dnd_drop(self, drop: Gtk.DropTarget, user_data: FavoriteChannelWidget, x: float, y: float):
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

        content = Gdk.ContentProvider.new_for_value(GObject.Value(FavoriteChannelWidget, child))
        return content


if __name__ == "__main__":
    pass
