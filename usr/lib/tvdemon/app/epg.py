# -*- coding: utf-8 -*-
#
# Copyright © 2024 Dmitriy Yefremov <https://github.com/DYefremov>
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


"""  Module for working with EPG. """
import abc
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import namedtuple, defaultdict
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha1
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

import requests

from .common import log, IS_WIN, async_function, EPG_PATH, Provider, Channel, GObject, GLib

EPG_START_FMT = "%a, %H:%M"
EPG_END_FMT = "%H:%M"


@dataclass
class EpgEvent:
    channel: str = "N/A"
    title: str = "N/A"
    desc: str = "N/A"
    start: int = 0
    end: int = 0
    length: int = 0


class AbstractEpgCache(GObject.GObject):
    def __init__(self, provider: Provider):
        super().__init__()
        # Signals.
        GObject.signal_new("epg-data-update", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))
        GObject.signal_new("epg-data-updated", self, GObject.SignalFlags.RUN_FIRST, GObject.TYPE_PYOBJECT,
                           (GObject.TYPE_PYOBJECT,))

        self.provider = provider
        self.events = {}

        self._reader = None
        self.url = None
        self.path = None

    @abc.abstractmethod
    def reset(self) -> None: pass

    @abc.abstractmethod
    def update_epg_data(self) -> None: pass

    @abc.abstractmethod
    def get_current_event(self, channel: Channel) -> EpgEvent: pass

    @abc.abstractmethod
    def get_current_events(self, channel: Channel) -> list | None: pass

    @staticmethod
    def get_gz_file_name(url):
        return f'{EPG_PATH}{os.sep}{sha1(url.encode("utf-8", errors="ignore")).hexdigest()}_epg.gz'


class EpgCache(AbstractEpgCache):

    def __init__(self, provider: Provider):
        super().__init__(provider)
        self.init()

    def init(self):
        self.url = self.provider.epg
        self.path = self.get_gz_file_name(self.url)
        self._reader = XmlTvReader(self.path, url=self.url)
        self.load_data()

    @async_function
    def load_data(self):
        log("Loading EPG data...")
        GLib.idle_add(self.emit, "epg-data-update", "Loading EPG data...")
        if os.path.isfile(self.path):
            # Difference calculation between the current time and file modification.
            dif = datetime.now() - datetime.fromtimestamp(os.path.getmtime(self.path))
            # We will update daily.
            self._reader.download(self._reader.parse) if dif.days > 0 else self._reader.parse()
        else:
            self._reader.download(self._reader.parse)

        self.update_epg_data()

    def reset(self) -> None:
        log("Reset EPG cache...")
        self.init()

    def update_epg_data(self) -> None:
        log("Updating EPG data...")

        ids = {c.id or c.name for c in self.provider.channels}
        for name, events in self._reader.get_current_events(ids).items():
            self.events[name] = events

        GLib.idle_add(self.emit, "epg-data-updated", "EPG data update completed!")

    def get_current_event(self, channel: Channel) -> EpgEvent:
        events = self.get_current_events(channel)
        if events:
            return events[0]
        return EpgEvent()

    def get_current_events(self, channel: Channel) -> list | None:
        return self.events.get(channel.id, self.events.get(channel.name, None))


class Reader(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def cache(self) -> dict: pass

    @abc.abstractmethod
    def download(self, clb=None): pass

    @abc.abstractmethod
    def get_current_events(self, ids: set) -> dict: pass


class XmlTvReader(Reader):
    PR_TAG = "programme"
    CH_TAG = "channel"
    DSP_NAME_TAG = "display-name"
    TITLE_TAG = "title"
    DESC_TAG = "desc"

    TIME_FORMAT_STR = "%Y%m%d%H%M%S %z"

    SUFFIXES = {".gz", ".xz", ".lzma", ".xml"}

    Service = namedtuple("Service", ["id", "names", "events"])
    Event = namedtuple("EpgEvent", ["start", "duration", "title", "desc"])

    def __init__(self, path, url=None):
        self._path = path
        self._url = url
        self._cache = {}

    @property
    def cache(self) -> dict:
        return self._cache

    def download(self, clb=None):
        """ Downloads an XMLTV file. """
        res = urlparse(self._url)
        if not all((res.scheme, res.netloc)):
            log(f"{self.__class__.__name__} [download] error: Invalid URL {self._url}")
            return

        with requests.get(url=self._url, stream=True) as resp:
            if resp.reason == "OK":
                suf = self._url[self._url.rfind("."):]
                if suf not in self.SUFFIXES:
                    log(f"{self.__class__.__name__} [download] error: Unsupported file extension.")
                    return

                data_size = resp.headers.get("content-length")
                if not data_size:
                    log(f"{self.__class__.__name__} [download *.{suf}] error: Error getting data size.")
                    if clb:
                        clb()
                    return

                with NamedTemporaryFile(suffix=suf, delete=not IS_WIN) as tf:
                    downloaded = 0
                    data_size = int(data_size)
                    log("Downloading XMLTV file...")
                    for data in resp.iter_content(chunk_size=1024):
                        downloaded += len(data)
                        tf.write(data)
                        done = int(50 * downloaded / data_size)
                        sys.stdout.write(f"\rDownloading XMLTV file [{'=' * done}{' ' * (50 - done)}]")
                        sys.stdout.flush()
                    tf.seek(0)
                    sys.stdout.write("\n")

                    os.makedirs(os.path.dirname(self._path), exist_ok=True)

                    if suf.endswith(".gz"):
                        try:
                            shutil.copyfile(tf.name, self._path)
                        except OSError as e:
                            log(f"{self.__class__.__name__} [download *.gz] error: {e}")
                    elif self._url.endswith((".xz", ".lzma")):
                        import lzma

                        try:
                            with lzma.open(tf, "rb") as lzf:
                                shutil.copyfileobj(lzf, self._path)
                        except (lzma.LZMAError, OSError) as e:
                            log(f"{self.__class__.__name__} [download *.xz] error: {e}")
                    else:
                        try:
                            import gzip
                            with gzip.open(self._path, "wb") as f_out:
                                shutil.copyfileobj(tf, f_out)
                        except OSError as e:
                            log(f"{self.__class__.__name__} [download *.xml] error: {e}")

                    if IS_WIN and os.path.isfile(tf.name):
                        tf.close()
                        os.remove(tf.name)
            else:
                log(f"{self.__class__.__name__} [download] error: {resp.reason}")

        if clb:
            clb()

    def get_current_events(self, names: set) -> dict:
        events = defaultdict(list)

        dt = datetime.utcnow()
        utc = dt.timestamp()
        offset = datetime.now() - dt

        for srv in filter(lambda s: s.id in names or any(n in names for n in s.names), self._cache.values()):
            [self.process_event(ev, events, offset, srv) for ev in filter(lambda s: s.duration > utc, srv.events)]

        return events

    @staticmethod
    def process_event(ev, events, offset, srv):
        start = datetime.fromtimestamp(ev.start) + offset
        end_time = datetime.fromtimestamp(ev.duration) + offset
        start = int(start.timestamp())
        end_time = int(end_time.timestamp())
        duration = end_time - start
        [events[n].append(EpgEvent(n, ev.title, ev.desc, start, end_time, duration)) for n in srv.names]

    def parse(self):
        """ Parses XML. """
        try:
            log("Processing XMLTV data...")
            suf = os.path.splitext(self._path)[1]
            if suf == ".gz":
                import gzip

                with gzip.open(self._path, "rb") as gzf:
                    list(map(self.process_node, ET.iterparse(gzf)))
            elif suf == ".xml":
                with open(self._path, "rb") as xml:
                    list(map(self.process_node, ET.iterparse(xml)))
            else:
                log(f"{self.__class__.__name__} [parse] error: Unsupported file type [{suf}].")
        except OSError as e:
            log(f"{self.__class__.__name__} [parse] error: {e}")
        else:
            log("XMLTV data parsing is complete.")

    def process_node(self, node):
        event, element = node
        if element.tag == self.CH_TAG:
            ch_id = element.get("id", None)
            # Since a service can have several names, we will store a set of names in the "names" field!
            self._cache[ch_id] = self.Service(ch_id, {c.text for c in element if c.tag == self.DSP_NAME_TAG}, [])
        elif element.tag == self.PR_TAG:
            channel = self._cache.get(element.get(self.CH_TAG, None), None)
            if channel:
                events = channel[-1]
                start = element.get("start", None)
                if start:
                    start = self.get_utc_time(start)

                stop = element.get("stop", None)
                if stop:
                    stop = self.get_utc_time(stop)

                title, desc = None, None
                for c in element:
                    if c.tag == self.TITLE_TAG:
                        title = c.text
                    elif c.tag == self.DESC_TAG:
                        desc = c.text

                if all((start, stop, title)):
                    events.append(self.Event(start, stop, title, desc))

    @staticmethod
    def get_utc_time(time_str):
        """ Returns the UTC time in seconds. """
        t, sep, delta = time_str.partition(" ")
        t = datetime(*map(int, (t[:4], t[4:6], t[6:8], t[8:10], t[10:12], t[12:]))).timestamp()
        if delta:
            t -= (3600 * int(delta) // 100)
        return t


if __name__ == "__main__":
    pass
