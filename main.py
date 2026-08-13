import threading
import os
import time
import webview
from dmx_manager import DMXManager
from reference_checker import ReferenceChecker
from sequence_manager import SequenceManager


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
    trigger_engine
)

from settings import settings

checker = ReferenceChecker(
    scene_manager,
    sequence_manager,
    trigger_manager
)

print("Verbinde Arduino...")

WINDOW_TITLE = "DMX ShowControl"

WINDOW_WIDTH = 1380
WINDOW_HEIGHT = 720

if serial.connect():
    print("Arduino verbunden")
else:
    print("Arduino NICHT verbunden")


def serial_watchdog():

    while True:

        serial.update()

        time.sleep(1)


threading.Thread(
    target=serial_watchdog,
    daemon=True
).start()

    
def run_flask():

    socketio.run(
        app,
        host=settings.host,
        port=settings.port,
        debug=False
    )


threading.Thread(
    target=run_flask,
    daemon=True
).start()



webview.create_window(
    WINDOW_TITLE,
    f"http://127.0.0.1:{settings.port}",
    width=WINDOW_WIDTH,
    height=WINDOW_HEIGHT
)


webview.start()

os._exit(0)