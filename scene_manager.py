import json
import os
import copy
from name_helper import duplicate_name


class SceneManager:

    def __init__(self):

        self.file = "data/scenes.json"
        self.scenes = []

        self.load()



    def load(self):
        if not os.path.exists(self.file):

            self.scenes = []
            return


        try:

            with open(
                self.file,
                "r",
                encoding="utf-8"
            ) as f:

                content = json.load(f)


        except (json.JSONDecodeError, FileNotFoundError):

            print(
                "scenes.json ungültig oder leer - neue Datei erstellt"
            )

            self.scenes = []

            self.save()

            return


        # Einzelne Szene -> Liste machen
        if isinstance(content, dict):

            content = [content]


        self.scenes = content



    def reload(self):

        self.load()

        print(
            "Szenen neu geladen"
        )



    def save(self):

        os.makedirs(
            "data",
            exist_ok=True
        )


        with open(
            self.file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                self.scenes,
                f,
                indent=4,
                ensure_ascii=False
            )



    def add(self, scene):

        scene["id"] = self.get_next_id()

        # Standardstruktur
        if "devices" not in scene:
            scene["devices"] = {}


        self.scenes.append(scene)

        self.save()



    def get_id(self, scene_id):

        for scene in self.scenes:

            if scene["id"] == scene_id:

                return scene


        return None



    def update(self, scene_id, data):

        scene = self.get_id(scene_id)

        if not scene:
            return False


        scene.update(data)

        self.save()

        return True



    def delete(self, scene_id):

        self.scenes = [
            s for s in self.scenes
            if s["id"] != scene_id
        ]

        self.save()



    def add_device(self, scene_id, device_id):

        scene = self.get_id(scene_id)

        if not scene:
            return


        device_id = str(device_id)


        if device_id not in scene["devices"]:

            scene["devices"][device_id] = {}


        self.save()



    def remove_device(self, scene_id, device_id):

        scene = self.get_id(scene_id)

        if not scene:
            return


        device_id = str(device_id)


        if device_id in scene["devices"]:

            del scene["devices"][device_id]


        self.save()



    def set_channel(
        self,
        scene_id,
        device_id,
        channel,
        value
    ):

        scene = self.get_id(scene_id)

        if not scene:
            return


        device_id = str(device_id)


        if device_id not in scene["devices"]:

            scene["devices"][device_id] = {}


        scene["devices"][device_id][str(channel)] = int(value)


        self.save()



    def get_next_id(self):

        if not self.scenes:

            return 1


        return max(
            s["id"]
            for s in self.scenes
        ) + 1



    def get(self, name):

        for scene in self.scenes:

            if scene["name"] == name:

                return scene


        return None

    def duplicate(self, scene_id):

        scene = self.get_id(scene_id)

        if not scene:
            return None

        existing_names = [
            s["name"]
            for s in self.scenes
        ]

        new_scene = copy.deepcopy(scene)

        new_scene["id"] = self.get_next_id()

        new_scene["name"] = duplicate_name(
            scene["name"],
            existing_names
        )

        self.scenes.append(new_scene)

        self.save()

        return new_scene