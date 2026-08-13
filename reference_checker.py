from device_manager import devices


class ReferenceChecker:


    def __init__(
        self,
        scene_manager,
        sequence_manager,
        trigger_manager
    ):

        self.scene_manager = scene_manager
        self.sequence_manager = sequence_manager
        self.trigger_manager = trigger_manager



    def check(self):

        problems = []


        problems += self.check_scenes()

        problems += self.check_sequences()

        problems += self.check_triggers()


        return problems



    # -------------------------
    # Szenen
    # -------------------------

    def check_scenes(self):

        problems = []


        for scene in self.scene_manager.scenes:


            for device_id in scene.get(
                "devices",
                {}
            ):


                device = devices.get_id(
                    int(device_id)
                )


                if not device:

                    problems.append({

                        "type":"scene_device",

                        "title":
                        f'Szene "{scene["name"]}"',

                        "message":
                        f'Gerät "{device_id}" existiert nicht mehr'

                    })


        return problems



    # -------------------------
    # Sequenzen
    # -------------------------

    def check_sequences(self):

        problems = []


        for seq in self.sequence_manager.sequences:


            for step in seq.get(
                "steps",
                []
            ):


                if step.get("action")=="scene":


                    scene = self.scene_manager.get(
                        step.get("target")
                    )


                    if not scene:


                        problems.append({

                            "type":"sequence_scene",

                            "sequence":seq["name"],

                            "target":step["target"],

                            "message":
                            "Szene existiert nicht mehr"

                        })


        return problems




    # -------------------------
    # Trigger
    # -------------------------

    def check_triggers(self):

        problems = []


        for trigger in self.trigger_manager.triggers:


            for action in trigger.get(
                "actions",
                []
            ):


                if action["type"]=="scene":


                    if not self.scene_manager.get(
                        action["target"]
                    ):


                        problems.append({

                            "type": "trigger_scene",

                            "title":
                            f'Trigger "{trigger["name"]}"',

                            "message":
                            f'Szene "{action["target"]}" existiert nicht mehr'

                        })



                if action["type"]=="sequence":


                    if not self.sequence_manager.get(
                        action["target"]
                    ):


                        problems.append({

                            "type":"trigger_sequence",

                            "title":
                            f'Trigger "{trigger["name"]}"',

                            "message":
                            f'Sequenz "{action["target"]}" existiert nicht mehr'

                        })


        return problems