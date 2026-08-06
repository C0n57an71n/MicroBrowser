# MicroBrowser
A small web browser for Picoware on PicoCalc
Installation
------------
Copy the file: MicroBrowser.py 
 - into the Picoware apps directory on the SD card
 
Copy the files:
 - browser_store.py
 - config.py
 - htmlparser.py
 - micro_browser_app.py
 - textcodec.py
 - urltools.py
          
into a new folder /micro_browser into the existing picoware folder.
 
Restart Picoware.
Open MicroBrowser from the application list.

Controls
--------
The main menu contains **SEARCH THE WEB**, **URL SEARCH**, and **RSS**.
URL SEARCH automatically opens a site's advertised RSS/Atom feed when one is available.
The RSS menu provides the feed list and options to add, rename, or remove feeds.

**Up/Down** --> Scroll            
**Left/Right** --> Select previous/next link               
**Enter** --> Open selected link          
**Enter** with no selected link --> URL text input     
**Back**/**Esc** --> Previous article, page, or parent menu
**Shift** & **Tab**/**Home** --> exit the app & return to the main menu     
