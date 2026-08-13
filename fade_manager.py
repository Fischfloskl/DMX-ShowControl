import json
import os
import copy
from name_helper import duplicate_name

class FadeManager:

    FILE = "data/fades.json"


    def __init__(self):

        self.fades = []

        self.load()

    def load(self):

        if not os.path.exists(self.FILE):

            self.fades = []
            self.save()
            return

        try:

            with open(
                self.FILE,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            self.fades = data.get("data", [])

            for fade in self.fades:

                if "mode" not in fade:
                    fade["mode"] = "merge"

                if "devices" not in fade:
                    fade["devices"] = []

        except Exception as e:

            print(
                "Fehler beim Laden von fades.json:",
                e
            )

            # Backup erstellen
            try:
                os.rename(
                    self.FILE,
                    self.FILE + ".broken"
                )
            except:
                pass

            self.fades = []
            self.save()


    def save(self):

        data = {

            "type": "fades",

            "version": 1,

            "data": self.fades

        }


        os.makedirs(
            os.path.dirname(self.FILE),
            exist_ok=True
        )


        with open(
            self.FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )


    def next_id(self):

        if not self.fades:

            return 1

        return max(
            fade["id"]
            for fade in self.fades
        ) + 1


    def add(self, name):

        fade = {

            "id": self.next_id(),

            "name": name,

            "duration": 2000,

            "mode": "merge",

            "devices": [],

            "targets": []

        }

        self.fades.append(fade)

        self.save()

        return fade


    def delete(self, fade_id):

        self.fades = [

            fade
            for fade in self.fades
            if fade["id"] != fade_id

        ]

        self.save()


    def get(self, name):

        for fade in self.fades:

            if fade["name"] == name:

                return fade

        return None


    def get_id(self, fade_id):

        for fade in self.fades:

            if fade["id"] == fade_id:

                return fade

        return None


    def rename(self, fade_id, name):

        fade = self.get_id(fade_id)

        if fade:

            fade["name"] = name
            self.save()


    def exists(self, name):

        return self.get(name) is not None

    def duplicate(self, fade_id):

        fade = self.get_id(fade_id)

        if not fade:
            return None

        existing_names = [
            f["name"]
            for f in self.fades
        ]

        new_fade = copy.deepcopy(fade)

        new_fade["id"] = self.next_id()

        new_fade["name"] = duplicate_name(
            fade["name"],
            existing_names
        )

        self.fades.append(new_fade)

        self.save()

        return new_fade


fade_manager = FadeManager()