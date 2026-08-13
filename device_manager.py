import json
import os
import copy
from name_helper import duplicate_name

DEVICE_LIST_FILE = "data/devices.json"

DEFAULT_DEVICES = {
    "type": "devices",
    "version": 1,
    "data": []
}


class DeviceManager:

    def __init__(self):

        self.devices = []

        self.load()

    def load(self):

        try:

            # Ordner sicherstellen
            os.makedirs(
                os.path.dirname(
                    DEVICE_LIST_FILE
                ),
                exist_ok=True
            )


            # Datei existiert nicht
            if not os.path.exists(
                DEVICE_LIST_FILE
            ):

                print(
                    "Geräte-Datei nicht gefunden. "
                    "Erstelle neue Datei."
                )

                self.devices = []

                self.save()

                return


            with open(
                DEVICE_LIST_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                content = json.load(f)


            # ---------------------------------
            # Altes Format
            # ---------------------------------

            if isinstance(
                content,
                list
            ):

                self.devices = content

                print(
                    "Altes Geräteformat erkannt. "
                    "Konvertiere..."
                )

                self.save()

                return


            # ---------------------------------
            # Neues Format
            # ---------------------------------

            if not isinstance(
                content,
                dict
            ):

                raise ValueError(
                    "Ungültiges Geräte-Dateiformat."
                )


            if content.get(
                "type"
            ) != "devices":

                raise ValueError(
                    "Ungültiger Dateityp."
                )


            data = content.get(
                "data"
            )


            if not isinstance(
                data,
                list
            ):

                raise ValueError(
                    "Gerätedaten müssen eine Liste sein."
                )


            self.devices = data


        except Exception as e:

            print(
                "Fehler beim Laden der Geräte:",
                e
            )

            print(
                "Erstelle neue Geräte-Datei."
            )


            self.devices = []

            self.save()

    def delete(self, device_id):

        print("DELETE ID:", device_id)
        print("VORHER:", self.devices)


        self.devices = [
            d for d in self.devices
            if int(d["id"]) != int(device_id)
        ]


        print("NACHHER:", self.devices)


        self.save()

    def save(self):

        content = {
            "type": "devices",
            "version": 1,
            "data": self.devices
        }

        with open(
            DEVICE_LIST_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                content,
                f,
                indent=4
            )

    def add(self, device):

        self.devices.append(device)

        self.save()

    def remove(self, index):

        del self.devices[index]

        self.save()

    def get_id(self, device_id):

        for d in self.devices:

            if d["id"] == device_id:
                return d

        return None

    def update(self, index, device):

        self.devices[index] = device

        self.save()

    def next_id(self):
        if not self.devices:
            return 1

        return max(d["id"] for d in self.devices) + 1

    def duplicate(self, device_id):

        device = self.get_id(device_id)

        if not device:
            return None

        existing_names = [
            d["name"]
            for d in self.devices
        ]

        new_device = copy.deepcopy(device)

        new_device["id"] = self.next_id()

        new_device["name"] = duplicate_name(
            device["name"],
            existing_names
        )

        self.devices.append(new_device)

        self.save()

        return new_device
    
devices = DeviceManager()