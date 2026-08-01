# MicroBrowser
A small web browser for Picoware on PicoCalc
Installation
------------
Copy the file: MicroBrowser.py 
 - into the Picoware apps directory on the SD card
 
Copy the files:
          - cache.py
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
**Up/Down** --> Scroll            
**Left/Right** --> Select previous/next link               
**Enter** --> Open selected link          
**Enter** with no selected link --> URL text input     
**Back**/**Esc** --> Previous page, or exit when history is empty      
**Shift** & **Tab**/**Home** --> exit the app & return to the main menu     
**F** --> find word in text        
**S** --> save Bookmark
