APP_NAME = "MicroBrowser"
APP_VERSION = "0.4.0"

HOME_URL = "https://frogfind.com/"
USER_AGENT = "MicroBrowser/{} (Picoware; Pico 2 W)".format(APP_VERSION)

TEMP_FILE = "picoware/micro_browser/page.tmp"

MAX_PAGE_BYTES = 512 * 1024
MAX_BLOCKS = 1200
MAX_LINKS = 160
MAX_TEXT_CHARS = 70000

READ_CHUNK_SIZE = 1024

TEXT_MARGIN = 6
HEADER_HEIGHT = 18
FOOTER_HEIGHT = 18
LINE_GAP = 2

HTTP_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,text/plain,application/xhtml+xml",
    "Accept-Encoding": "identity",
    "Connection": "close",
}
