from device_manager import devices


class DMXManager:

    def __init__(self, serial_manager):
        self.serial = serial_manager
        self.current = {}


    def clear(self):
        print("CLEAR ALL DMX CH")

        result = self.send("C")

        if result is not False:
            self.current = {
                channel: 0
                for channel in range(1, 513)
            }

        return result



        
    def set_channel(self, channel, value):

        value = max(0, min(255, int(value)))

        if self.current.get(channel, 0) == value:
            return True

        result = self.send(f"D;{channel};{value}")

        if result is not False:
            self.current[channel] = value

        return result

        
    def apply_scene(self, scene):
        values = {
            channel: 0
            for channel in range(1, 513)
        }

        for device_id, channels in scene["devices"].items():

            device = devices.get_id(int(device_id))

            if not device:
                continue

            start = device["start_channel"]

            for ch, value in channels.items():
                dmx_channel = start + int(ch) - 1

                if 1 <= dmx_channel <= 512:
                    values[dmx_channel] = max(
                        0,
                        min(255, int(value))
                    )

        return self.apply_full_state(values)


    def apply_full_state(self, values):

        changed = {}

        for channel in range(1, 513):

            new_value = max(
                0,
                min(255, int(values.get(channel, 0)))
            )

            old_value = self.current.get(channel, 0)

            if new_value != old_value:
                changed[channel] = new_value

        if not changed:
            print("DMX: No changes")
            return True

        parts = [
            f"{channel}:{value}"
            for channel, value in sorted(changed.items())
        ]

        print(f"DMX: Sending {len(changed)} channel changes")

        result = self.send("S;" + ";".join(parts))

        if result is not False:
            self.current = {
                channel: max(
                    0,
                    min(255, int(values.get(channel, 0)))
                )
                for channel in range(1, 513)
            }

        return result


    
    """def set_scene(self, scene):
        print("APPLY SCENE")

        # Alle DMX-Kanäle auf 0 setzen
        values = {
            ch: 0
            for ch in range(1, 513)
        }

        for device_id, channels in scene["devices"].items():
            device = devices.get_id(int(device_id))

            if not device:
                continue

            start = device["start_channel"]

            for ch, value in channels.items():
                dmx_channel = start + int(ch) - 1

                if dmx_channel in values:
                    values[dmx_channel] = int(value)

        # Vollständigen Zustand übernehmen
        self.current = values

        parts = [
            f"{ch}:{values[ch]}"
            for ch in sorted(values)
        ]

        return self.send("S;" + ";".join(parts))"""

    def set_scene(self, scene):
        print("APPLY SCENE")
        return self.apply_scene(scene)




    def send(self, command):

        return self.serial.send(
            command
        )

        
    def apply_values(self, values):

        changed = {}

        for channel, value in values.items():

            channel = int(channel)

            if not 1 <= channel <= 512:
                continue

            value = max(0, min(255, int(value)))

            if self.current.get(channel, 0) != value:
                changed[channel] = value

        if not changed:
            return True

        parts = [
            f"{channel}:{value}"
            for channel, value in sorted(changed.items())
        ]

        result = self.send("S;" + ";".join(parts))

        if result is not False:
            self.current.update(changed)

        return result


    def reset_all(self):

        values = {
            channel: 0
            for channel in range(1, 513)
        }

        return self.apply_values(values)