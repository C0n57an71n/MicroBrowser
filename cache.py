"""Small SD-card page cache and bookmark store."""

from json import loads, dumps
from config import CACHE_DIR, CACHE_INDEX_FILE, BOOKMARKS_FILE, MAX_CACHE_FILES, MAX_BOOKMARKS


def fnv1a(text):
    value = 2166136261
    for byte in text.encode("utf-8"):
        value ^= byte
        value = (value * 16777619) & 0xFFFFFFFF
    return "%08x" % value


class PageCache:
    def __init__(self, storage):
        self.storage = storage
        self.storage.mkdir(CACHE_DIR)
        self.index = self._read_json(CACHE_INDEX_FILE, [])

    def path_for(self, url):
        return CACHE_DIR + "/" + fnv1a(url) + ".html"

    def get(self, url):
        path = self.path_for(url)
        if self.storage.exists(path):
            self._touch(url, path)
            return path
        return None

    def put(self, url, source_path):
        path = self.path_for(url)
        try:
            if self.storage.exists(path):
                self.storage.remove(path)
            self.storage.copy(source_path, path)
            self._touch(url, path)
            self._trim()
            self._write_json(CACHE_INDEX_FILE, self.index)
            return path
        except Exception:
            return None

    def _touch(self, url, path):
        for index in range(len(self.index) - 1, -1, -1):
            if self.index[index][0] == url:
                del self.index[index]
        self.index.insert(0, [url, path])

    def _trim(self):
        while len(self.index) > MAX_CACHE_FILES:
            old = self.index.pop()
            try:
                if self.storage.exists(old[1]):
                    self.storage.remove(old[1])
            except Exception:
                pass

    def _read_json(self, path, default):
        try:
            if self.storage.exists(path):
                return loads(self.storage.read(path))
        except Exception:
            pass
        return default

    def _write_json(self, path, value):
        try:
            self.storage.write(path, dumps(value))
        except Exception:
            pass


class Bookmarks:
    def __init__(self, storage):
        self.storage = storage
        self.items = self._load()

    def toggle(self, url, title):
        for index in range(len(self.items) - 1, -1, -1):
            if self.items[index][0] == url:
                del self.items[index]
                self._save()
                return False
        self.items.insert(0, [url, title])
        while len(self.items) > MAX_BOOKMARKS:
            self.items.pop()
        self._save()
        return True

    def contains(self, url):
        for item in self.items:
            if item[0] == url:
                return True
        return False

    def _load(self):
        try:
            if self.storage.exists(BOOKMARKS_FILE):
                return loads(self.storage.read(BOOKMARKS_FILE))
        except Exception:
            pass
        return []

    def _save(self):
        try:
            self.storage.write(BOOKMARKS_FILE, dumps(self.items))
        except Exception:
            pass

