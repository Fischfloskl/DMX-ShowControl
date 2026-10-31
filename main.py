import threading
import os
import time
import webview
from dmx_manager import DMXManager
from reference_checker import ReferenceChecker
from sequence_manager import SequenceManager
from app import midi_manager
import sys
from pathlib import Path
import webbrowser

LOG = Path(sys.executable).resolve().parent / "startup.log"

with open(LOG, "w", encoding="utf-8") as f:
    f.write("MAIN START\n")

from app import (
    app,
    socketio,
    serial,
    trigger_manager,
    scene_manager,
    sequence_manager,
    dmx_manager,
    fade_engine,
    fade_manager,
    trigger_engine,
    strobe_manager,
    external_application_manager
)

from settings import settings

checker = ReferenceChecker(
    scene_manager,
    sequence_manager,
    trigger_manager,
    fade_manager,
    strobe_manager
)

print("connecting to Arduino...")

WINDOW_TITLE = "DMX ShowControl"

WINDOW_WIDTH = 1460
WINDOW_HEIGHT = 720

if serial.connect():
    print("Arduino connected")
else:
    print("Arduino not connected")



class API:

    def open_browser(self, url):

        webbrowser.open_new_tab(url)

        return True



def serial_watchdog():

    while True:

        serial.update()

        time.sleep(1)

external_application_manager.start_all()

threading.Thread(
    target=serial_watchdog,
    daemon=True
).start()

    
def run_flask():

    socketio.run(
        app,
        host=settings.host,
        port=settings.port,
        debug=False,
        allow_unsafe_werkzeug=True
    )


server_thread = threading.Thread(
    target=run_flask,
    daemon=True
)

server_thread.start()


# Kurz warten, damit Flask den Port öffnen kann
time.sleep(1)

api = API()

webview.create_window(
    WINDOW_TITLE,
    f"http://127.0.0.1:{settings.port}",
    width=WINDOW_WIDTH,
    height=WINDOW_HEIGHT,
    js_api=api
)


try:
    """if settings.midi_input_port: #midi-start
        midi_manager.connect(
                settings.midi_input_port or ""
            )"""
    webview.start()

finally:

    print("DMX-ShowControl is shutting down...")
    external_application_manager.stop_all()

#os._exit(0)