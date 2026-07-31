"""
Streaming HTML parser for Picoware MicroBrowser.
"""

from config import MAX_BLOCKS, MAX_LINKS, MAX_TEXT_CHARS


_ENTITIES = {
    "amp": "&",
    "lt": "<",
    "gt": ">",
    "quot": '"',
    "apos": "'",
    "nbsp": " ",
}


def decode_entities(text):
    if "&" not in text:
        return text

    out = []
    i = 0

    while i < len(text):
        if text[i] != "&":
            out.append(text[i])
            i += 1
            continue

        end = text.find(";", i + 1)
        if end < 0 or end - i > 12:
            out.append("&")
            i += 1
            continue

        name = text[i + 1:end]
        value = None

        if name.startswith("#x") or name.startswith("#X"):
            try:
                value = chr(int(name[2:], 16))
            except Exception:
                pass
        elif name.startswith("#"):
            try:
                value = chr(int(name[1:]))
            except Exception:
                pass
        else:
            value = _ENTITIES.get(name)

        if value is None:
            out.append(text[i:end + 1])
        else:
            out.append(value)

        i = end + 1

    return "".join(out)


def collapse_spaces(text):
    out = []
    previous_space = False

    for ch in text:
        if ch in " \t\r\n":
            if not previous_space:
                out.append(" ")
            previous_space = True
        else:
            out.append(ch)
            previous_space = False

    return "".join(out).strip()


def parse_attributes(raw):
    attrs = {}
    i = 0
    n = len(raw)

    while i < n and not raw[i].isspace():
        i += 1

    while i < n:
        while i < n and raw[i].isspace():
            i += 1

        if i >= n:
            break

        start = i
        while i < n and not raw[i].isspace() and raw[i] != "=":
            i += 1

        key = raw[start:i].lower()

        while i < n and raw[i].isspace():
            i += 1

        value = ""

        if i < n and raw[i] == "=":
            i += 1

            while i < n and raw[i].isspace():
                i += 1

            if i < n and raw[i] in ("'", '"'):
                quote = raw[i]
                i += 1
                start = i

                while i < n and raw[i] != quote:
                    i += 1

                value = raw[start:i]

                if i < n:
                    i += 1
            else:
                start = i

                while i < n and not raw[i].isspace():
                    i += 1

                value = raw[start:i]

        if key:
            attrs[key] = decode_entities(value)

    return attrs


class ParsedPage:
    def __init__(self):
        self.title = ""
        self.blocks = []
        self.links = []
        self.truncated = False


class StreamingHTMLParser:
    BLOCK_PREFIX = {
        "p": "",
        "div": "",
        "section": "",
        "article": "",
        "header": "",
        "footer": "",
        "blockquote": "> ",
        "li": "* ",
        "h1": "# ",
        "h2": "## ",
        "h3": "### ",
        "h4": "#### ",
        "h5": "##### ",
        "h6": "###### ",
    }

    def __init__(self):
        self.page = ParsedPage()

        self._text = []
        self._tag = []
        self._in_tag = False
        self._quote = None

        self._prefix = ""
        self._href = None
        self._in_title = False
        self._in_pre = False
        self._skip_tag = None

        self._text_chars = 0

    def feed(self, data):
        if isinstance(data, (bytes, bytearray, memoryview)):
            data = bytes(data).decode("utf-8", "ignore")

        for ch in data:
            if self.page.truncated:
                return

            if self._in_tag:
                if self._quote:
                    self._tag.append(ch)

                    if ch == self._quote:
                        self._quote = None
                else:
                    if ch in ("'", '"'):
                        self._quote = ch
                        self._tag.append(ch)
                    elif ch == ">":
                        self._handle_tag("".join(self._tag).strip())
                        self._tag = []
                        self._in_tag = False
                    else:
                        self._tag.append(ch)
            else:
                if ch == "<":
                    self._flush_text()
                    self._in_tag = True
                    self._tag = []
                elif self._skip_tag is None:
                    self._text.append(ch)

    def finish(self):
        if self._in_tag and self._tag:
            self._text.append("<")
            self._text.extend(self._tag)

        self._flush_text()

        if not self.page.title:
            self.page.title = "MicroBrowser"

        return self.page

    def _flush_text(self):
        if not self._text:
            return

        value = "".join(self._text)
        self._text = []

        if self._skip_tag is not None:
            return

        if not self._in_pre:
            value = collapse_spaces(value)

        value = decode_entities(value)

        if not value:
            return

        self._text_chars += len(value)

        if (
            self._text_chars > MAX_TEXT_CHARS
            or len(self.page.blocks) >= MAX_BLOCKS
        ):
            self.page.truncated = True
            return

        if self._in_title:
            self.page.title = (self.page.title + " " + value).strip()
            return

        if self._href and len(self.page.links) < MAX_LINKS:
            number = len(self.page.links) + 1
            self.page.links.append((self._href, value))
            value = "[{}] {}".format(number, value)

        self.page.blocks.append(self._prefix + value)

    def _handle_tag(self, raw):
        if not raw:
            return

        lower = raw.lower()

        if lower.startswith("!--") or lower.startswith("!doctype"):
            return

        closing = lower.startswith("/")
        clean = lower[1:].lstrip() if closing else lower
        name = clean.split(None, 1)[0].rstrip("/") if clean else ""

        if not name:
            return

        if self._skip_tag:
            if closing and name == self._skip_tag:
                self._skip_tag = None
            return

        if name in ("script", "style", "noscript"):
            if not closing:
                self._skip_tag = name
            return

        if closing:
            if name == "title":
                self._in_title = False
            elif name == "a":
                self._href = None
            elif name == "pre":
                self._in_pre = False
            elif name in self.BLOCK_PREFIX:
                self._prefix = ""

                if (
                    self.page.blocks
                    and self.page.blocks[-1] != ""
                    and len(self.page.blocks) < MAX_BLOCKS
                ):
                    self.page.blocks.append("")
            return

        if name == "title":
            self._in_title = True
        elif name == "a":
            self._href = parse_attributes(raw).get("href", "")
        elif name == "pre":
            self._in_pre = True
            self._prefix = ""
        elif name == "br":
            if len(self.page.blocks) < MAX_BLOCKS:
                self.page.blocks.append("")
        elif name == "hr":
            if len(self.page.blocks) < MAX_BLOCKS:
                self.page.blocks.append("--------------------------------")
        elif name == "img":
            alt = parse_attributes(raw).get("alt", "")
            if alt:
                self._text.append("[Image: {}]".format(alt))
        elif name in self.BLOCK_PREFIX:
            self._prefix = self.BLOCK_PREFIX[name]
