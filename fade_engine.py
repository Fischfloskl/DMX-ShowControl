import threading
import time


class FadeEngine:


    def __init__(self, dmx_manager, devices, settings):

        self.dmx_manager = dmx_manager
        self.devices = devices
        self.settings = settings
        self.show_controller = None

        self.running = False


    def play(self, fade):

        if self.running:
            return


        thread = threading.Thread(
            target=self._run,
            args=(fade,)
        )

        thread.start()



    def _run(self, fade):

        self.running = True

        duration = fade.get(
            "duration",
            1000
        )

        refresh = max(
            1,
            self.settings.refresh_rate
        )

        delay = refresh / 1000

        steps = max(
            1,
            int(duration / refresh)
        )

        start_values = {}
        end_values = {}

        mode = fade.get(
            "mode",
            "overwrite"
        )

        # Werte vorbereiten
        for fade_device in fade["devices"]:

            device = self.devices.get_id(
                fade_device["device"]
            )

            if not device:
                continue

            for ch in fade_device["channels"]:

                if not ch["enabled"]:
                    continue

                dmx_channel = (
                    device["start_channel"]
                    + ch["channel"]
                    - 1
                )

                if mode == "merge":

                    # Aktuellen DMX-Wert übernehmen
                    start = self.dmx_manager.current.get(
                        dmx_channel,
                        0
                    )

                else:

                    # Im Fade gespeicherten Startwert benutzen
                    start = ch["start"]

                start_values[dmx_channel] = start
                end_values[dmx_channel] = ch["end"]

        # Fade ausführen
        for step in range(steps + 1):

            if not self.running:
                return

            if self.show_controller:
                if self.show_controller.stopped():
                    self.running = False
                    return

            progress = step / steps

            values = {}

            for channel in start_values:

                start = start_values[channel]
                end = end_values[channel]

                values[channel] = int(
                    start +
                    (end - start) * progress
                )

            self.dmx_manager.apply_values(
                values
            )

            time.sleep(delay)

        # Endwerte sicher setzen
        self.dmx_manager.apply_values(
            end_values
        )

        self.running = False

    def stop(self):
        self.running = False

    def set_controller(self, controller):
        self.show_controller = controller