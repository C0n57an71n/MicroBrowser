"""
Picoware MicroBrowser application.
"""

from gc import collect
from micropython import const

from config import (
    HOME_URL,
    HTTP_HEADERS,
    TEMP_FILE,
    MAX_PAGE_BYTES,
    READ_CHUNK_SIZE,
    TEXT_MARGIN,
    HEADER_HEIGHT,
    FOOTER_HEIGHT,
    LINE_GAP,
)
from htmlparser import StreamingHTMLParser
from urltools import resolve_url


STATE_VIEW = const(0)
STATE_KEYBOARD = const(1)
STATE_LOADING = const(2)


class MicroBrowserApp:
    def __init__(self, view_manager):
        self.vm = view_manager
        self.http = None
        self.loading = None

        self.page = None
        self.lines = []
        self.line_links = []

        self.top_line = 0
        self.selected_link = 0

        self.current_url = HOME_URL
        self.pending_url = None
        self.pending_add_history = True
        self.history = []

        self.state = STATE_VIEW

    def start(self):
        self.vm.freq(True)

        storage = self.vm.storage
        if not storage:
            self.vm.alert("SD storage required", False)
            return False

        storage.mkdir("picoware/micro_browser")

        return self.open_url(HOME_URL, False)

    def stop(self):
        if self.http:
            try:
                self.http.close()
            except Exception:
                pass

        self.http = None
        self.loading = None

        self.vm.keyboard.reset()
        self.vm.freq()

        self.page = None
        self.lines = []
        self.line_links = []

        collect()

    def run(self):
        if self.state == STATE_LOADING:
            self._run_loading()
            return

        if self.state == STATE_KEYBOARD:
            self._run_keyboard()
            return

        from picoware.system.buttons import (
            BUTTON_UP,
            BUTTON_DOWN,
            BUTTON_LEFT,
            BUTTON_RIGHT,
            BUTTON_CENTER,
            BUTTON_BACK,
        )

        inp = self.vm.input_manager
        button = inp.button

        if button == BUTTON_UP:
            inp.reset()
            self._scroll(-1)

        elif button == BUTTON_DOWN:
            inp.reset()
            self._scroll(1)

        elif button == BUTTON_LEFT:
            inp.reset()
            self._select_link(-1)

        elif button == BUTTON_RIGHT:
            inp.reset()
            self._select_link(1)

        elif button == BUTTON_CENTER:
            inp.reset()
            self._open_selected()

        elif button == BUTTON_BACK:
            inp.reset()

            if self.history:
                url = self.history.pop()
                self.open_url(url, False)
            else:
                self.vm.back()

    def open_url(self, url, add_history=True):
        from picoware.system.http import HTTP
        from picoware.gui.loading import Loading

        if self.http:
            try:
                self.http.close()
            except Exception:
                pass

        self.http = HTTP(thread_manager=self.vm.thread_manager)
        self.loading = Loading(self.vm.draw)
        self.loading.set_text("Loading...")

        self.pending_url = url
        self.pending_add_history = add_history

        storage = self.vm.storage

        try:
            if storage.exists(TEMP_FILE):
                storage.remove(TEMP_FILE)
        except Exception:
            pass

        started = self.http.get_async(
            url,
            save_to_file=TEMP_FILE,
            storage=storage,
            headers=HTTP_HEADERS,
            timeout=20,
        )

        if not started:
            self.vm.alert("Failed to start request", False)
            self.state = STATE_VIEW
            return False

        self.state = STATE_LOADING
        return True

    def _run_loading(self):
        from picoware.system.buttons import BUTTON_BACK

        inp = self.vm.input_manager

        if inp.button == BUTTON_BACK:
            inp.reset()

            try:
                self.http.close()
            except Exception:
                pass

            self.state = STATE_VIEW
            self.draw()
            return

        if self.http and not self.http.is_request_complete():
            if self.loading:
                self.loading.animate()
            return

        try:
            if self.http:
                self.http.close()

            page = self._parse_downloaded_file()

            if self.pending_add_history and self.current_url:
                self.history.append(self.current_url)

                if len(self.history) > 20:
                    del self.history[0]

            self.current_url = self.pending_url
            self.page = page

            self._layout()
            self.top_line = 0
            self.selected_link = 0

            self.state = STATE_VIEW
            self.draw()

        except Exception as error:
            self.state = STATE_VIEW
            self.vm.alert("Browser error:\n{}".format(error), False)

        finally:
            self.loading = None
            collect()

    def _parse_downloaded_file(self):
        storage = self.vm.storage

        if not storage.exists(TEMP_FILE):
            raise Exception("Downloaded page not found")

        size = storage.size(TEMP_FILE)

        if size <= 0:
            raise Exception("Empty response")

        if size > MAX_PAGE_BYTES:
            raise Exception("Page too large: {} KB".format(size // 1024))

        file = storage.file_open(TEMP_FILE)

        if not file:
            raise Exception("Could not open downloaded page")

        parser = StreamingHTMLParser()
        buffer = bytearray(READ_CHUNK_SIZE)

        try:
            while True:
                count = storage.file_readinto(file, buffer)

                if count <= 0:
                    break

                parser.feed(buffer[:count])

                if parser.page.truncated:
                    break

                if self.loading:
                    self.loading.set_text(
                        "Parsing... {} KB".format(
                            storage.file_tell(file) // 1024
                            if hasattr(storage, "file_tell")
                            else 0
                        )
                    )
                    self.loading.animate()

                collect()

        finally:
            storage.file_close(file)

        return parser.finish()

    def draw(self):
        from picoware.system.vector import Vector

        draw = self.vm.draw
        draw.fill_screen(self.vm.background_color)

        title = self.page.title if self.page else "MicroBrowser"

        if len(title) > 38:
            title = title[:35] + "..."

        draw.text(
            Vector(TEXT_MARGIN, 2),
            title,
            self.vm.foreground_color,
        )

        font = draw.get_font(0)
        line_height = font.height + LINE_GAP
        y = HEADER_HEIGHT

        visible = max(
            1,
            (
                draw.size.y
                - HEADER_HEIGHT
                - FOOTER_HEIGHT
            )
            // line_height,
        )

        end = min(len(self.lines), self.top_line + visible)

        for index in range(self.top_line, end):
            selected = (
                self.selected_link > 0
                and self.line_links[index] == self.selected_link
            )

            color = (
                self.vm.selected_color
                if selected
                else self.vm.foreground_color
            )

            draw.text(
                Vector(TEXT_MARGIN, y),
                self.lines[index],
                color,
            )

            y += line_height

        footer = "{}/{}  link {}/{}".format(
            min(self.top_line + 1, max(1, len(self.lines))),
            max(1, len(self.lines)),
            self.selected_link,
            len(self.page.links) if self.page else 0,
        )

        if self.page and self.page.truncated:
            footer += "  truncated"

        draw.text(
            Vector(TEXT_MARGIN, draw.size.y - FOOTER_HEIGHT),
            footer,
            self.vm.foreground_color,
        )

        draw.swap()

    def _layout(self):
        draw = self.vm.draw
        char_width = max(1, draw.len("M"))

        width = max(
            12,
            (draw.size.x - (TEXT_MARGIN * 2)) // char_width,
        )

        self.lines = []
        self.line_links = []

        for block in self.page.blocks:
            link_number = self._link_number(block)

            for line in self._wrap(block, width):
                self.lines.append(line)
                self.line_links.append(link_number)

        if not self.lines:
            self.lines = ["Empty page"]
            self.line_links = [0]

    def _wrap(self, text, width):
        if text == "":
            return [""]

        lines = []

        for source_line in text.split("\n"):
            words = source_line.split()

            if not words:
                lines.append("")
                continue

            line = ""

            for word in words:
                if not line:
                    line = word
                elif len(line) + len(word) + 1 <= width:
                    line += " " + word
                else:
                    lines.append(line)
                    line = word

            if line:
                lines.append(line)

        return lines

    def _link_number(self, text):
        if not text.startswith("["):
            return 0

        end = text.find("]")

        if end < 2:
            return 0

        try:
            return int(text[1:end])
        except Exception:
            return 0

    def _visible_count(self):
        font = self.vm.draw.get_font(0)

        return max(
            1,
            (
                self.vm.draw.size.y
                - HEADER_HEIGHT
                - FOOTER_HEIGHT
            )
            // (font.height + LINE_GAP),
        )

    def _scroll(self, amount):
        maximum = max(
            0,
            len(self.lines) - self._visible_count(),
        )

        self.top_line = min(
            maximum,
            max(0, self.top_line + amount),
        )

        self.draw()

    def _select_link(self, amount):
        count = len(self.page.links) if self.page else 0

        if count == 0:
            return

        self.selected_link += amount

        if self.selected_link < 1:
            self.selected_link = count
        elif self.selected_link > count:
            self.selected_link = 1

        for index, number in enumerate(self.line_links):
            if number == self.selected_link:
                visible = self._visible_count()

                if index < self.top_line:
                    self.top_line = index
                elif index >= self.top_line + visible:
                    self.top_line = max(
                        0,
                        index - visible + 1,
                    )

                break

        self.draw()

    def _open_selected(self):
        if not self.page or self.selected_link < 1:
            self._start_keyboard()
            return

        if self.selected_link > len(self.page.links):
            return

        href = self.page.links[self.selected_link - 1][0]

        self.open_url(
            resolve_url(self.current_url, href)
        )

    def _start_keyboard(self):
        keyboard = self.vm.keyboard
        keyboard.reset()
        keyboard.title = "Enter URL"
        keyboard.response = self.current_url
        keyboard.run(force=True)
        keyboard.run(force=True)

        self.state = STATE_KEYBOARD

    def _run_keyboard(self):
        keyboard = self.vm.keyboard

        if keyboard.is_finished:
            url = keyboard.response.strip()
            keyboard.reset()

            self.state = STATE_VIEW

            if url:
                self.open_url(url)
            else:
                self.draw()

            return

        if not keyboard.run():
            keyboard.reset()
            self.state = STATE_VIEW
            self.draw()
