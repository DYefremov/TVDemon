#!/usr/bin/python3
import json
import os
from pathlib import Path
from typing import Any


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


class Defaults(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self["playback-library"] = "GStreamer"
        self["mpv-options"] = "hwdec=auto-safe"
        self["recordings-path"] = str(Path.home())
        self["user-agent"] = "Mozilla/5.0"
        self["http-referer"] = ""
        self["active-provider"] = "Free-TV"
        self["providers"] = [
            "Free-TV:::url:::https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8:::::::::'"]
        self["main-window-size"] = (700, 500)


class Settings(dict):
    CONFIG_PATH = f"{Path.home()}{os.sep}.config{os.sep}tvdemon{os.sep}"
    CONFIG_FILE = f"{CONFIG_PATH}config"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._defaults = Defaults()
        Path(self.CONFIG_PATH).mkdir(parents=True, exist_ok=True)
        Path(self.CONFIG_FILE).touch(exist_ok=True)

        if os.path.isfile(self.CONFIG_FILE) and os.stat(self.CONFIG_FILE).st_size > 0:
            with open(self.CONFIG_FILE, "r") as config_file:
                self.update(json.load(config_file))

    def save(self):
        with open(self.CONFIG_FILE, "w") as config_file:
            json.dump(self, config_file)

    def reset(self, key):
        if key in self._defaults:
            self[key] = self._defaults.get(key)

    def get_value(self, key) -> Any:
        return self.get(key, self._defaults.get(key, None))

    def set_value(self, key: str, value: object) -> None:
        self[key] = value

    def set_string(self, key, value) -> None:
        self[key] = value

    def get_string(self, key) -> str:
        return self.get(key, self._defaults.get(key, ""))

    def set_strv(self, key: str, value: list = None) -> None:
        self[key] = value

    def get_strv(self, key: str) -> list:
        return self.get(key, self._defaults.get(key, []))


if __name__ == '__main__':
    pass
