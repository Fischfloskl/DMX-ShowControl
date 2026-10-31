
import threading
import time


class FadeEngine:
    def __init__(self, dmx_manager, devices, settings):
        self.dmx_manager = dmx_manager
        self.devices = devices
        self.settings = settings
        self.show_controller = None
        self.scene_manager = None
        self.running = False
        self._lock = threading.Lock()
        self._thread = None
        self._cancel_event = None


    def play(self, fade):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False

            cancel_event = threading.Event()

            self._cancel_event = cancel_event
            self.running = True

            self._thread = threading.Thread(
                target=self._run,
                args=(fade, cancel_event),
                daemon=True
            )

            self._thread.start()

        return True

    
    
    def _run(self, fade, cancel_event):
        try:
            duration = max(1, int(fade.get("duration", 1000)))
            refresh = max(1, int(self.settings.refresh_rate))
            delay = refresh / 1000
            steps = max(1, int(duration / refresh))

            if fade.get("type", "custom") == "scenes":
                start_values, end_values = self._scene_values(fade)
            else:
                start_values, end_values = self._custom_values(fade)

            if not end_values:
                return

            mode = str(fade.get("mode", "merge")).lower()

            if mode not in ("merge", "overwrite"):
                mode = "merge"

            actual_start = {}

            for channel in end_values:
                if mode == "merge":
                    start = self.dmx_manager.current.get(
                        channel,
                        start_values.get(channel, 0)
                    )
                else:
                    start = start_values.get(channel, 0)

                actual_start[channel] = max(0, min(255, int(start)))

            # Apply the initial values (delta updates skip unchanged channels)
            self.dmx_manager.apply_values(actual_start)

            for step in range(1, steps + 1):
                if cancel_event.is_set():
                    return

                if self.show_controller and self.show_controller.stopped():
                    return

                progress = step / steps
                values = {}

                for channel, end in end_values.items():
                    start = actual_start[channel]

                    values[channel] = max(
                        0,
                        min(255, int(start + (end - start) * progress))
                    )

                self.dmx_manager.apply_values(values)

                if step < steps:
                    if cancel_event.wait(delay):
                        return

        except Exception as exc:
            print(f"Fade error: {exc}")

        finally:
            with self._lock:
                if self._thread is threading.current_thread():
                    self.running = False
                    self._thread = None
                    self._cancel_event = None



    def _custom_values(self, fade):
        start_values = {}
        end_values = {}

        for fade_device in fade.get("devices", []):
            device = self.devices.get_id(fade_device["device"])

            if not device:
                continue

            functions = device.get("channel_functions", [])
            channel_count = int(device["channels"])

            for ch in fade_device.get("channels", []):
                if not ch.get("enabled", False):
                    continue

                relative_channel = int(ch["channel"])

                if not 1 <= relative_channel <= channel_count:
                    continue

                function = (
                    functions[relative_channel - 1]
                    if relative_channel - 1 < len(functions)
                    else "Fader"
                )

                if function == "Disabled":
                    continue

                absolute_channel = (
                    int(device["start_channel"]) + relative_channel - 1
                )

                start_values[absolute_channel] = int(ch.get("start", 0))
                end_values[absolute_channel] = int(ch.get("end", 255))

        return start_values, end_values

    def _scene_values(self, fade):
        if not self.scene_manager:
            raise RuntimeError("Scene manager is not configured")

        start_scene = self.scene_manager.get_id(int(fade["start_scene"]))
        end_scene = self.scene_manager.get_id(int(fade["end_scene"]))

        if not start_scene or not end_scene:
            raise RuntimeError("Fade references a missing scene")

        start_devices = start_scene.get("devices", {})
        end_devices = end_scene.get("devices", {})

        start_values = {}
        end_values = {}

        # Include devices referenced by either scene.
        device_ids = set(start_devices) | set(end_devices)

        for device_id in device_ids:
            device = self.devices.get_id(int(device_id))

            if not device:
                continue

            channel_count = int(device["channels"])
            start_channel = int(device["start_channel"])
            functions = device.get("channel_functions", [])

            scene_start = start_devices.get(
                str(device_id),
                start_devices.get(device_id, {})
            )
            scene_end = end_devices.get(
                str(device_id),
                end_devices.get(device_id, {})
            )

            channel_keys = set(scene_start) | set(scene_end)

            for channel_key in channel_keys:
                try:
                    relative_channel = int(channel_key)
                except (TypeError, ValueError):
                    continue

                if not 1 <= relative_channel <= channel_count:
                    continue

                function = (
                    functions[relative_channel - 1]
                    if relative_channel - 1 < len(functions)
                    else "Fader"
                )

                if function == "Disabled":
                    continue

                absolute_channel = start_channel + relative_channel - 1

                try:
                    start_value = int(
                        scene_start.get(channel_key, 0)
                    )
                    end_value = int(
                        scene_end.get(channel_key, 0)
                    )
                except (TypeError, ValueError):
                    continue

                start_values[absolute_channel] = max(
                    0, min(255, start_value)
                )
                end_values[absolute_channel] = max(
                    0, min(255, end_value)
                )

        return start_values, end_values

    def stop(self):
        with self._lock:
            cancel_event = self._cancel_event
            thread = self._thread

            if cancel_event:
                cancel_event.set()

        if thread and thread is not threading.current_thread():
            thread.join()

        with self._lock:
            if self._thread is thread:
                self._thread = None
                self._cancel_event = None
                self.running = False

    def set_controller(self, controller):
        self.show_controller = controller
