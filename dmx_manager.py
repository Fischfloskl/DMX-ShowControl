from device_manager import devices


class DMXManager:

    def __init__(self, serial_manager):
        self.serial = serial_manager
        self.current = {}


    def clear(self):
        print("CLEAR ALL DMX CH")

        self.current = {}

        return self.send("C")



    def set_channel(self, channel, value):

        value = max(
            0,
            min(255, int(value))
        )

        self.current[channel] = value

        return self.send(
            f"D;{channel};{value}"
        )



    def apply_scene(self, scene):
        print("APPLY SCENE")

        values = {}


        for device_id, channels in scene["devices"].items():


            device = devices.get_id(
                int(device_id)
            )


            if not device:

                continue


            start = device["start_channel"]


            for ch, value in channels.items():

                dmx_channel = (
                    start
                    + int(ch)
                    - 1
                )


                values[dmx_channel] = int(value)



        self.current = values



        parts = []


        for ch in sorted(values):

            parts.append(
                f"{ch}:{values[ch]}"
            )


        return self.send(
            "S;" + ";".join(parts)
        )



    def send(self, command):

        return self.serial.send(
            command
        )

    def apply_values(self, values):

        self.current.update(values)

        parts = []

        for ch in sorted(values):
            parts.append(f"{ch}:{values[ch]}")

        return self.send(
            "S;" + ";".join(parts)
        )

    def reset_all(self):

        values = {}

        # alle 512 DMX Kanäle auf 0
        for channel in range(1, 513):

            values[channel] = 0


        self.apply_values(values)


        # internen Zustand löschen
        self.current.clear()