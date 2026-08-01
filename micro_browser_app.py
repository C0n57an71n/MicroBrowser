"""Picoware MicroBrowser v0.5."""

from gc import collect
from micropython import const
from config import HOME_URL, HTTP_HEADERS, TEMP_FILE, MAX_PAGE_BYTES, READ_CHUNK_SIZE, TEXT_MARGIN, HEADER_HEIGHT, FOOTER_HEIGHT, LINE_GAP
from htmlparser import StreamingHTMLParser
from urltools import resolve_url
from cache import PageCache, Bookmarks

STATE_VIEW=const(0); STATE_KEYBOARD=const(1); STATE_LOADING=const(2)
PURPOSE_URL=const(0); PURPOSE_FIND=const(1)
STYLE_NORMAL=const(0); STYLE_H1=const(1); STYLE_H2=const(2); STYLE_QUOTE=const(3); STYLE_RULE=const(4)

class MicroBrowserApp:
    def __init__(self, view_manager):
        self.vm=view_manager; self.http=None; self.loading=None; self.page=None
        self.lines=[]; self.line_links=[]; self.line_styles=[]; self.top_line=0; self.selected_link=0
        self.current_url=HOME_URL; self.pending_url=None; self.pending_add_history=True; self.history=[]
        self.state=STATE_VIEW; self.keyboard_purpose=PURPOSE_URL; self.find_text=""
        self.cache=None; self.bookmarks=None; self.source_path=TEMP_FILE

    def start(self):
        self.vm.freq(True); storage=self.vm.storage
        if not storage: self.vm.alert("SD storage required",False); return False
        storage.mkdir("picoware/micro_browser"); storage.mkdir("picoware/micro_browser/cache")
        self.cache=PageCache(storage); self.bookmarks=Bookmarks(storage)
        return self.open_url(HOME_URL,False)

    def stop(self):
        if self.http:
            try: self.http.close()
            except Exception: pass
        self.http=None; self.loading=None; self.vm.keyboard.reset(); self.vm.freq()
        self.page=None; self.lines=[]; self.line_links=[]; self.line_styles=[]; collect()

    def run(self):
        if self.state == STATE_LOADING: self._run_loading(); return
        if self.state == STATE_KEYBOARD: self._run_keyboard(); return
        from picoware.system.buttons import BUTTON_UP,BUTTON_DOWN,BUTTON_LEFT,BUTTON_RIGHT,BUTTON_CENTER,BUTTON_BACK,BUTTON_F,BUTTON_S,BUTTON_R,BUTTON_H
        inp=self.vm.input_manager; b=inp.button
        if b == BUTTON_UP: inp.reset(); self._scroll(-1)
        elif b == BUTTON_DOWN: inp.reset(); self._scroll(1)
        elif b == BUTTON_LEFT: inp.reset(); self._select_link(-1)
        elif b == BUTTON_RIGHT: inp.reset(); self._select_link(1)
        elif b == BUTTON_CENTER: inp.reset(); self._open_selected()
        elif b == BUTTON_F: inp.reset(); self._start_keyboard(PURPOSE_FIND)
        elif b == BUTTON_S: inp.reset(); self._toggle_bookmark()
        elif b == BUTTON_R: inp.reset(); self.open_url(self.current_url,False,False)
        elif b == BUTTON_H: inp.reset(); self.open_url(HOME_URL)
        elif b == BUTTON_BACK:
            inp.reset()
            if self.history: self.open_url(self.history.pop(),False)
            else: self.vm.back()

    def open_url(self,url,add_history=True,use_cache=True):
        url=url.strip()
        if "://" not in url: url="https://"+url
        if use_cache and self.cache:
            cached=self.cache.get(url)
            if cached:
                try:
                    self.pending_url=url; self.pending_add_history=add_history; self.source_path=cached
                    self.page=self._parse_file(cached); self._finish_open(); return True
                except Exception: pass
        from picoware.system.http import HTTP
        from picoware.gui.loading import Loading
        if self.http:
            try: self.http.close()
            except Exception: pass
        self.http=HTTP(thread_manager=self.vm.thread_manager); self.loading=Loading(self.vm.draw); self.loading.set_text("Loading...")
        self.pending_url=url; self.pending_add_history=add_history; self.source_path=TEMP_FILE
        storage=self.vm.storage
        try:
            if storage.exists(TEMP_FILE): storage.remove(TEMP_FILE)
        except Exception: pass
        if not self.http.get_async(url,save_to_file=TEMP_FILE,storage=storage,headers=HTTP_HEADERS,timeout=20):
            self._show_error("Failed to start request"); return False
        self.state=STATE_LOADING; return True

    def _run_loading(self):
        from picoware.system.buttons import BUTTON_BACK
        inp=self.vm.input_manager
        if inp.button == BUTTON_BACK:
            inp.reset()
            try: self.http.close()
            except Exception: pass
            self.state=STATE_VIEW; self.draw(); return
        if self.http and not self.http.is_request_complete():
            if self.loading: self.loading.animate()
            return
        try:
            if self.http: self.http.close()
            self.page=self._parse_file(TEMP_FILE)
            if self.cache: self.cache.put(self.pending_url,TEMP_FILE)
            self._finish_open()
        except Exception as error: self._show_error(str(error))
        finally: self.loading=None; collect()

    def _finish_open(self):
        if self.pending_add_history and self.current_url and self.pending_url != self.current_url:
            self.history.append(self.current_url)
            if len(self.history)>20: del self.history[0]
        self.current_url=self.pending_url; self._layout(); self.top_line=0; self.selected_link=0; self.state=STATE_VIEW; self.draw()

    def _parse_file(self,path):
        storage=self.vm.storage
        if not storage.exists(path): raise Exception("Page file not found")
        size=storage.size(path)
        if size<=0: raise Exception("Empty response")
        if size>MAX_PAGE_BYTES: raise Exception("Page too large: {} KB".format(size//1024))
        file=storage.file_open(path)
        if not file: raise Exception("Could not open page")
        parser=StreamingHTMLParser(); buffer=bytearray(READ_CHUNK_SIZE); done=0
        try:
            while True:
                count=storage.file_readinto(file,buffer)
                if count<=0: break
                parser.feed(buffer[:count]); done += count
                if parser.page.truncated: break
                if self.loading: self.loading.set_text("Parsing... {}%".format((done*100)//size)); self.loading.animate()
                collect()
        finally: storage.file_close(file)
        return parser.finish()

    def draw(self):
        from picoware.system.vector import Vector
        draw=self.vm.draw; draw.fill_screen(self.vm.background_color)
        title=self.page.title if self.page else "MicroBrowser"
        if len(title)>38: title=title[:35]+"..."
        if self.bookmarks and self.bookmarks.contains(self.current_url): title="* "+title
        draw.text(Vector(TEXT_MARGIN,2),title,self.vm.foreground_color)
        font=draw.get_font(0); line_height=font.height+LINE_GAP; y=HEADER_HEIGHT; visible=self._visible_count(); end=min(len(self.lines),self.top_line+visible)
        for index in range(self.top_line,end):
            selected=self.selected_link>0 and self.line_links[index]==self.selected_link
            style=self.line_styles[index]
            color=self.vm.selected_color if selected else (self.vm.foreground_color)
            draw.text(Vector(TEXT_MARGIN,y),self.lines[index],color); y += line_height
        footer="{}/{} L{}/{} F=find S=save".format(min(self.top_line+1,max(1,len(self.lines))),max(1,len(self.lines)),self.selected_link,len(self.page.links) if self.page else 0)
        if self.page and self.page.truncated: footer="TRUNC "+footer
        draw.text(Vector(TEXT_MARGIN,draw.size.y-FOOTER_HEIGHT),footer[:42],self.vm.foreground_color); draw.swap()

    def _layout(self):
        draw=self.vm.draw; width=max(12,(draw.size.x-(TEXT_MARGIN*2))//max(1,draw.len("M")))
        self.lines=[]; self.line_links=[]; self.line_styles=[]
        for block in self.page.blocks:
            style,text=self._style_block(block); link=self._link_number(text)
            for line in self._wrap(text,width): self.lines.append(line); self.line_links.append(link); self.line_styles.append(style)
        if not self.lines: self.lines=["Empty page"]; self.line_links=[0]; self.line_styles=[STYLE_NORMAL]

    def _style_block(self,text):
        if text.startswith("# "): return STYLE_H1,text[2:].upper()
        if text.startswith("## "): return STYLE_H2,text[3:]
        if text.startswith("### "): return STYLE_H2,text[4:]
        if text.startswith("> "): return STYLE_QUOTE,text
        if text.startswith("----"): return STYLE_RULE,text
        return STYLE_NORMAL,text

    def _wrap(self,text,width):
        if text=="": return [""]
        lines=[]
        for source in text.split("\n"):
            words=source.split()
            if not words: lines.append(""); continue
            line=""
            for word in words:
                if not line: line=word
                elif len(line)+len(word)+1<=width: line += " "+word
                else: lines.append(line); line=word
            if line: lines.append(line)
        return lines

    def _link_number(self,text):
        pos=text.find("[")
        if pos<0: return 0
        end=text.find("]",pos)
        if end<=pos+1: return 0
        try: return int(text[pos+1:end])
        except Exception: return 0

    def _visible_count(self):
        font=self.vm.draw.get_font(0); return max(1,(self.vm.draw.size.y-HEADER_HEIGHT-FOOTER_HEIGHT)//(font.height+LINE_GAP))
    def _scroll(self,amount):
        self.top_line=min(max(0,len(self.lines)-self._visible_count()),max(0,self.top_line+amount)); self.draw()
    def _select_link(self,amount):
        count=len(self.page.links) if self.page else 0
        if not count: return
        self.selected_link += amount
        if self.selected_link<1: self.selected_link=count
        elif self.selected_link>count: self.selected_link=1
        for i,n in enumerate(self.line_links):
            if n==self.selected_link:
                visible=self._visible_count()
                if i<self.top_line: self.top_line=i
                elif i>=self.top_line+visible: self.top_line=max(0,i-visible+1)
                break
        self.draw()
    def _open_selected(self):
        if not self.page or self.selected_link<1: self._start_keyboard(PURPOSE_URL); return
        if self.selected_link<=len(self.page.links): self.open_url(resolve_url(self.current_url,self.page.links[self.selected_link-1][0]))

    def _start_keyboard(self,purpose):
        keyboard=self.vm.keyboard; keyboard.reset(); self.keyboard_purpose=purpose
        keyboard.title="Find text" if purpose==PURPOSE_FIND else "Enter URL"
        keyboard.response=self.find_text if purpose==PURPOSE_FIND else self.current_url
        keyboard.run(force=True); keyboard.run(force=True); self.state=STATE_KEYBOARD
    def _run_keyboard(self):
        keyboard=self.vm.keyboard
        if keyboard.is_finished:
            value=keyboard.response.strip(); keyboard.reset(); self.state=STATE_VIEW
            if self.keyboard_purpose==PURPOSE_FIND:
                self.find_text=value
                if value: self._find_next(value)
                else: self.draw()
            elif value: self.open_url(value)
            else: self.draw()
            return
        if not keyboard.run(): keyboard.reset(); self.state=STATE_VIEW; self.draw()
    def _find_next(self,term):
        term=term.lower(); start=min(len(self.lines),self.top_line+1)
        for pass_start,pass_end in ((start,len(self.lines)),(0,start)):
            for i in range(pass_start,pass_end):
                if term in self.lines[i].lower(): self.top_line=i; self.draw(); return
        self.vm.alert("Text not found",False); self.draw()
    def _toggle_bookmark(self):
        if not self.bookmarks or not self.page: return
        added=self.bookmarks.toggle(self.current_url,self.page.title)
        self.vm.alert("Bookmark saved" if added else "Bookmark removed",False); self.draw()
    def _show_error(self,message):
        self.page=type("ErrorPage",(),{})(); self.page.title="Browser error"; self.page.links=[]; self.page.truncated=False; self.page.blocks=["# Browser error",message,"Press Back to return."]
        self._layout(); self.top_line=0; self.selected_link=0; self.state=STATE_VIEW; self.draw()

