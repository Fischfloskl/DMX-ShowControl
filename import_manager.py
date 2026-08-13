import json
import copy


class ImportManager:


    def __init__(
        self,
        scene_manager,
        fade_manager,
        sequence_manager,
        trigger_manager,
        devices
    ):

        self.scene_manager = scene_manager
        self.fade_manager = fade_manager
        self.sequence_manager = sequence_manager
        self.trigger_manager = trigger_manager
        self.devices = devices



    def get_free_id(
        self,
        items,
        wanted
    ):

        used = [

            item["id"]
            for item in items

        ]


        if wanted not in used:

            return wanted


        new_id = 1


        while new_id in used:

            new_id += 1


        return new_id



    def import_file(
        self,
        file
    ):


        content = json.load(
            file
        )


        if content.get(
            "type"
        ) != "DMX-ShowControl":

            raise Exception(
                "Keine gültige DMX-ShowControl Datei"
            )



        data = content.get(
            "data",
            {}
        )


        mappings = {

            "devices": {},
            "scenes": {},
            "fades": {},
            "sequences": {},
            "triggers": {}

        }



        #
        # Geräte
        #

        for device in data.get(
            "devices",
            []
        ):


            new = copy.deepcopy(
                device
            )


            old_id = new["id"]


            new["id"] = self.get_free_id(
                self.devices.devices,
                old_id
            )


            mappings["devices"][old_id] = new["id"]


            self.devices.devices.append(
                new
            )



        self.devices.save()



        #
        # Szenen
        #

        for scene in data.get(
            "scenes",
            []
        ):


            new = copy.deepcopy(
                scene
            )


            old_id = new["id"]


            new["id"] = self.get_free_id(
                self.scene_manager.scenes,
                old_id
            )


            mappings["scenes"][old_id] = new["id"]

            # Geräte IDs in Szene anpassen

            if "devices" in new:

                fixed_devices = {}


                for old_device, values in new["devices"].items():

                    old_device = int(old_device)


                    if old_device in mappings["devices"]:

                        new_device = mappings["devices"][old_device]

                    else:

                        new_device = old_device



                    fixed_devices[str(new_device)] = values



                new["devices"] = fixed_devices

            self.scene_manager.scenes.append(
                new
            )



        self.scene_manager.save()



        #
        # Fades
        #

        for fade in data.get(
            "fades",
            []
        ):


            new = copy.deepcopy(
                fade
            )


            old_id = new["id"]


            new["id"] = self.get_free_id(
                self.fade_manager.fades,
                old_id
            )


            mappings["fades"][old_id] = new["id"]

            # Geräte IDs in Fade anpassen

            for fade_device in new.get(
                "devices",
                []
            ):

                old_device = fade_device.get(
                    "device"
                )


                if old_device in mappings["devices"]:

                    fade_device["device"] = (
                        mappings["devices"][old_device]
                    )

            self.fade_manager.fades.append(
                new
            )



        self.fade_manager.save()



        #
        # Sequenzen
        #

        for sequence in data.get(
            "sequences",
            []
        ):


            new = copy.deepcopy(
                sequence
            )


            old_id = new["id"]


            new["id"] = self.get_free_id(
                self.sequence_manager.sequences,
                old_id
            )


            mappings["sequences"][old_id] = new["id"]



            for step in new.get(
                "steps",
                []
            ):


                if step.get(
                    "action"
                ) == "scene":


                    old = step.get(
                        "target"
                    )


                    if old in mappings["scenes"]:

                        step["target"] = (
                            mappings["scenes"][old]
                        )



                if step.get(
                    "action"
                ) == "fade":


                    old = step.get(
                        "target"
                    )


                    if old in mappings["fades"]:

                        step["target"] = (
                            mappings["fades"][old]
                        )



            self.sequence_manager.sequences.append(
                new
            )



        self.sequence_manager.save()



        #
        # Trigger
        #

        triggers = data.get(
            "triggers",
            []
        )


        # falls Export verschachtelt ist
        if isinstance(triggers, dict):

            triggers = triggers.get(
                "triggers",
                []
            )


        for trigger in triggers:


            new = copy.deepcopy(
                trigger
            )


            old_id = new["id"]


            new["id"] = self.get_free_id(
                self.trigger_manager.triggers,
                old_id
            )


            mappings["triggers"][old_id] = new["id"]



            for action in new.get(
                "actions",
                []
            ):


                if action.get(
                    "type"
                ) == "scene":


                    old = action.get(
                        "target"
                    )


                    if old in mappings["scenes"]:

                        action["target"] = (
                            mappings["scenes"][old]
                        )



                elif action.get(
                    "type"
                ) == "sequence":


                    old = action.get(
                        "target"
                    )


                    if old in mappings["sequences"]:

                        action["target"] = (
                            mappings["sequences"][old]
                        )



                elif action.get(
                    "type"
                ) == "fade":


                    old = action.get(
                        "target"
                    )


                    if old in mappings["fades"]:

                        action["target"] = (
                            mappings["fades"][old]
                        )



            self.trigger_manager.triggers.append(
                new
            )



        self.trigger_manager.save()



        return mappings