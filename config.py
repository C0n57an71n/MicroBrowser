APP_NAME = "MicroBrowser"
APP_VERSION = "0.5.0"

HOME_URL = "https://frogfind.com/"
USER_AGENT = "MicroBrowser/{} (Picoware; Pico 2 W)".format(APP_VERSION)

TEMP_FILE = "picoware/micro_browser/page.tmp"
CACHE_DIR = "picoware/micro_browser/cache"
CACHE_INDEX_FILE = "picoware/micro_browser/cache.json"
BOOKMARKS_FILE = "picoware/micro_browser/bookmarks.json"

MAX_PAGE_BYTES = 512 * 1024
MAX_BLOCKS = 1400
MAX_LINKS = 180
MAX_TEXT_CHARS = 76000
MAX_BOOKMARKS = 30
MAX_CACHE_FILES = 4
READ_CHUNK_SIZE = 1024

TEXT_MARGIN = 6
HEADER_HEIGHT = 18
FOOTER_HEIGHT = 18
LINE_GAP = 2

CHARACTER_MODE = "ascii"

HTTP_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,text/plain,application/xhtml+xml",
    "Accept-Encoding": "identity",
    "Connection": "close",
}

