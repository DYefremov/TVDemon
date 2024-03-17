#!/usr/bin/env python3
#
# Copyright (C) 2024 Dmitriy Yefremov <https://github.com/DYefremov>
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

import os
import sys


def update_icon():
    need_update = False
    icon_name = "tvdemon.desktop"
    logo_path = "/usr/share/icons/hicolor/scalable/apps/tvdemon.svg"

    with open(icon_name, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith("Icon="):
                icon_path = line.lstrip("Icon=")
                current_path = f"{os.getcwd()}{logo_path}"
                if icon_path != current_path:
                    need_update = True
                    lines[i] = f"Icon={current_path}\n"
                break

    if need_update:
        with open(icon_name, "w", encoding="utf-8") as f:
            f.writelines(lines)


if __name__ == "__main__":
    from usr.lib.tvdemon.app.main import run_app

    if sys.platform == "linux":
        update_icon()

    run_app()
