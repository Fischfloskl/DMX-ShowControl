
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

    def play(self, fade):
        with self._lock:
            if self.running:
                return False

            self.running = True

        thread = threading.Thread(
            target=self._run,
            args=(fade,),
            daemon=True
        )
        thread.start()
        return True

    def _run(self, fade):
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

            mode = fade.get("mode", "merge")

            # Merge starts from the current DMX output.
            # Other modes use the configured start values.
            if mode == "merge":
                for channel in end_values:
                    start_values[channel] = self.dmx_manager.current.get(
                        channel,
                        start_values.get(channel, 0)
                    )

            for step in range(steps + 1):
                if not self.running:
                    return

                if self.show_controller and self.show_controller.stopped():
                    return

                progress = step / steps
                values = {}

                for channel, end in end_values.items():
                    start = start_values.get(channel, 0)
                    values[channel] = max(
                        0,
                        min(255, int(start + (end - start) * progress))
                    )

                self.dmx_manager.apply_values(values)
                time.sleep(delay)

            if self.running:
                self.dmx_manager.apply_values(end_values)

        except Exception as exc:
            print(f"Fade error: {exc}")

        finally:
            with self._lock:
                self.running = False

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
        self.running = False

    def set_controller(self, controller):
        self.show_controller = controller
