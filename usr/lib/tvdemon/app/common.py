# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Dmitriy Yefremov <https://github.com/DYefremov>
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

__all__ = ("_", "Gtk", "Gdk", "Gio", "GdkPixbuf", "GLib", "Pango", "GObject",
           "APP", "UI_PATH", "Manager", "Provider", "Group", "async_function", "idle_function",
           "BADGES", "MOVIES_GROUP", "PROVIDERS_PATH", "SERIES_GROUP", "TV_GROUP")

import gettext
import locale
import os
import re
import sys
import threading
import warnings
from pathlib import Path

import gi
import requests
import setproctitle

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib, GObject, Pango

# Force X11 on a Wayland session
if "WAYLAND_DISPLAY" in os.environ:
    os.environ["WAYLAND_DISPLAY"] = ""

# Suppress GTK deprecation warnings
warnings.filterwarnings("ignore")

APP = "tvdemon"
setproctitle.setproctitle(APP)

IS_FROZEN = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")

PREFIX = "" if IS_FROZEN else f"{os.sep}usr{os.sep}"
BASE_PATH = f"{PREFIX}share{os.sep}"
UI_PATH = f"{BASE_PATH}tvdemon{os.sep}"
LOCALE_DIR = f"{BASE_PATH}locale"
PROVIDERS_PATH = os.path.join(os.path.normpath(GLib.get_user_cache_dir()), "tvdemon", "providers")

if not os.path.exists(UI_PATH):
    UI_PATH = f".{UI_PATH}"
    LOCALE_DIR = f".{LOCALE_DIR}"
    # Icons.
    theme = Gtk.IconTheme.get_default()
    theme.append_search_path(f".{BASE_PATH}icons")

if sys.platform == "linux":
    locale.bindtextdomain(APP, LOCALE_DIR)
elif sys.platform == "win32":
    locale.setlocale(locale.LC_NUMERIC, "C")
    Path(PROVIDERS_PATH).mkdir(parents=True, exist_ok=True)

gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
_ = gettext.gettext

# M3U parsing regex
PARAMS = re.compile(r'(\S+)="(.*?)"')
EXT_INF = re.compile(r'^#EXTINF:(?P<duration>-?\d+?) ?(?P<params>.*),(?P<title>.*?)$')
SERIES = re.compile(r"(?P<series>.*?) S(?P<season>.\d{1,2}).*E(?P<episode>.\d{1,2}.*)$", re.IGNORECASE)

TV_GROUP, MOVIES_GROUP, SERIES_GROUP = range(3)

BADGES = {'musik': "music", 'zeland': "newzealand"}


def async_function(func):
    """  Used as a decorator to run things in the background.  """

    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    return wrapper


def idle_function(func):
    """ Used as a decorator to run things in the main loop, from another thread. """

    def wrapper(*args):
        GObject.idle_add(func, *args)

    return wrapper


def slugify(string):
    """ Normalizes string, converts to lowercase,
        removes non-alpha characters,
        and converts spaces to hyphens.
    """
    return "".join(x.lower() for x in string if x.isalnum())


class Provider:
    def __init__(self, name, provider_info):
        if provider_info:
            self.name, self.type_id, self.url, self.username, self.password, self.epg = provider_info.split(":::")
        else:
            self.name = name
        self.path = os.path.join(PROVIDERS_PATH, slugify(self.name))
        self.groups = []
        self.channels = []
        self.movies = []
        self.series = []

    def get_info(self):
        return f"{self.name}:::{self.type_id}:::{self.url}:::{self.username}:::{self.password}:::{self.epg}"


class Group:
    def __init__(self, name="", channels=None, series=None):
        if "VOD" in name.split():
            self.group_type = MOVIES_GROUP
        elif "SERIES" in name.split():
            self.group_type = SERIES_GROUP
        else:
            self.group_type = TV_GROUP

        self.name = name
        self.logo = None
        self.logo_path = None
        self.channels = channels or []
        self.series = series or []
        self.is_default = False

    @staticmethod
    def from_dict(data: dict):
        gr = Group()
        [setattr(gr, k, v) for k, v in data.items()]
        gr.channels = [Channel.from_dict(c) for c in gr.channels]
        return gr


class Serie:
    def __init__(self, name):
        self.name = name
        self.logo = None
        self.logo_path = None
        self.seasons = {}
        self.episodes = []


class Season:
    def __init__(self, name):
        self.name = name
        self.episodes = {}


class Channel:
    def __init__(self, provider=None, info=None):
        self.info = None
        self.id = None
        self.name = None
        self.logo = None
        self.logo_path = None
        self.group_title = None
        self.title = None
        self.url = None

        if provider and info:
            self.init_data(info, provider)

    def init_data(self, info, provider):
        match = EXT_INF.fullmatch(info or "")
        if match:
            res = match.groupdict()
            if 'params' in res:
                params = dict(PARAMS.findall(res['params']))
                if "tvg-name" in params and params['tvg-name'].strip() != "":
                    self.name = params['tvg-name'].strip()
                if "tvg-logo" in params and params['tvg-logo'].strip() != "":
                    self.logo = params['tvg-logo'].strip()
                if "group-title" in params and params['group-title'].strip() != "":
                    self.group_title = params['group-title'].strip().replace(";", " ").replace("  ", " ")
            if 'title' in res:
                self.title = res['title']
        if self.name is None and "," in info:
            self.name = info.split(",")[-1].strip()
        if self.logo:
            if self.logo.startswith("file://"):
                self.logo_path = self.logo[7:]
            else:
                ext = None
                for known_ext in [".png", ".jpg", ".gif", ".jpeg"]:
                    if self.logo.lower().endswith(known_ext):
                        ext = known_ext
                        break
                if ext == ".jpeg":
                    ext = ".jpg"
                self.logo_path = os.path.join(PROVIDERS_PATH, f"{slugify(provider.name)}-{slugify(self.name)}{ext}")

    @staticmethod
    def from_dict(data: dict):
        ch = Channel()
        [setattr(ch, k, v) for k, v in data.items()]
        return ch


class Manager:

    def __init__(self, settings):
        os.system(f"mkdir -p {PROVIDERS_PATH}")
        self.verbose = False
        self.settings = settings

    def debug(self, *args):
        if self.verbose:
            print(args)

    def get_playlist(self, provider, refresh=False) -> bool:
        """Get the playlist from the provided URL

        Args:
            provider ([type]): [description]
            refresh (bool, optional): [description]. Defaults to False.

        Returns:
            bool: True for SUCCESS, False for ERROR
        """
        ret_code = True

        if "file://" in provider.url:
            # local file
            provider.path = provider.url.replace("file://", "")

        elif "://" in provider.url:
            # Other protocol, assume it's http
            if refresh or not os.path.exists(provider.path):
                # Assume it is not going to make it
                ret_code = False

                headers = {
                    'User-Agent': self.settings.get_string("user-agent"),
                    'Referer': self.settings.get_string("http-referer")
                }
                try:
                    response = requests.get(provider.url, headers=headers, timeout=(5, 120), stream=True)

                    # If there is an answer from the remote server
                    if response.status_code == 200:
                        # Set downloaded size
                        downloaded_bytes = 0
                        # Get total playlist byte size
                        total_content_size = int(response.headers.get('content-length', 15))
                        # Set stream blocks
                        block_bytes = int(4 * 1024 * 1024)  # 4 MB

                        response.encoding = response.apparent_encoding

                        with open(provider.path, "w", encoding="utf-8") as file:
                            # Grab data by block_bytes
                            for data in response.iter_content(block_bytes, decode_unicode=True):
                                downloaded_bytes += block_bytes
                                print(f"{downloaded_bytes} bytes")
                                file.write(str(data))
                        if downloaded_bytes < total_content_size:
                            print("The file size is incorrect, deleting")
                            os.remove(provider.path)
                        else:
                            # Set the datatime when it was last retreived
                            # self.settings.set_
                            ret_code = True
                    else:
                        print(f"HTTP error {response.status_code} while retrieving from {provider.url}!")
                except Exception as e:
                    print(e)
        else:
            # No protocol, assume it's local
            provider.path = provider.url

        return ret_code

    def check_playlist(self, provider):
        legit = False
        if os.path.exists(provider.path):
            with open(provider.path, "r", encoding="utf-8", errors="ignore") as file:
                content = file.read()
                if "#EXTM3U" in content and "#EXTINF" in content:
                    legit = True
                    self.debug(f"Content looks legit: {provider.name}")
                else:
                    self.debug(f"Nope: {provider.path}")
        return legit

    def load_channels(self, provider):
        with open(provider.path, "r", encoding="utf-8", errors="ignore") as file:
            channel = None
            group = None
            groups = {}
            series = {}
            for line in file:
                line = line.strip()
                if line.startswith("#EXTM3U"):
                    continue
                if line.startswith("#EXTINF"):
                    channel = Channel(provider, line)
                    self.debug("New channel: ", line)
                    continue
                if "://" in line and not (line.startswith("#")):
                    self.debug("    ", line)
                    if channel is None:
                        self.debug("    --> channel is None")
                        continue
                    if channel.url:
                        # We already found the URL, skip the line
                        self.debug("    --> channel URL was already found")
                        continue
                    if channel.name is None or "***" in channel.name:
                        self.debug("    --> channel name is None")
                        continue
                    channel.url = line
                    self.debug("    --> URL found: ", line)

                    serie = None
                    f = SERIES.fullmatch(channel.name)
                    if f:
                        res = f.groupdict()
                        series_name = res['series']
                        if series_name in series.keys():
                            serie = series[series_name]
                        else:
                            serie = Serie(series_name)
                            # TODO put in group
                            provider.series.append(serie)
                            series[series_name] = serie
                            serie.logo = channel.logo
                            serie.logo_path = channel.logo_path
                        season_name = res['season']
                        if season_name in serie.seasons.keys():
                            season = serie.seasons[season_name]
                        else:
                            season = Season(season_name)
                            serie.seasons[season_name] = season

                        episode_name = res['episode']
                        season.episodes[episode_name] = channel
                        serie.episodes.append(channel)

                    if channel.group_title and channel.group_title.strip() != "":
                        if group is None or group.name != channel.group_title:
                            if channel.group_title in groups.keys():
                                group = groups[channel.group_title]
                            else:
                                group = Group(channel.group_title)
                                provider.groups.append(group)
                                groups[channel.group_title] = group
                        if serie and serie not in group.series:
                            group.series.append(serie)
                        group.channels.append(channel)
                        if group.group_type == TV_GROUP:
                            provider.channels.append(channel)
                        elif group.group_type == MOVIES_GROUP:
                            provider.movies.append(channel)
                    else:
                        provider.channels.append(channel)

    @staticmethod
    def get_m3u_tvg_info(path):
        """ Returns "x-tvg-url" parameter value from the local file. """
        with open(path, "r") as file:
            line = file.readline()
            if line.startswith("#EXTM3U"):
                return dict(PARAMS.findall(line)).get("x-tvg-url", "")
            return ""


if __name__ == '__main__':
    pass
