from device_manager import devices


class ReferenceChecker:

    def __init__(
        self,
        scene_manager,
        sequence_manager,
        trigger_manager,
        fade_manager,
        strobe_manager
    ):

        self.scene_manager = scene_manager
        self.sequence_manager = sequence_manager
        self.trigger_manager = trigger_manager
        self.fade_manager = fade_manager
        self.strobe_manager = strobe_manager

    # -------------------------
    # ALLE
    # -------------------------

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

                        "type": "scene_device",

                        "title":
                        f'Szene "{scene["name"]}"',

                        "message":
                        f'Device "{device_id}" no longer exists'

                    })

        return problems

    # -------------------------
    # Sequenzen
    # -------------------------

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

                action = step.get("action")

                # -------------------------
                # Szene
                # -------------------------

                if action == "scene":

                    if "target" not in step:

                        problems.append({

                            "type": "sequence_scene",

                            "title":
                            f'Sequence "{seq["name"]}"',

                            "message":
                            "Scene-Reference missing"

                        })

                        continue


                    scene = self.scene_manager.get(
                        step["target"]
                    )


                    if not scene:

                        problems.append({

                            "type": "sequence_scene",

                            "title":
                            f'Sequence "{seq["name"]}"',

                            "target":
                            step["target"],

                            "message":
                            "Scene no longer exists"

                        })


                # -------------------------
                # Fade
                # -------------------------

                if action == "fade":

                    if "target" not in step:

                        problems.append({

                            "type": "sequence_fade",

                            "title":
                            f'Sequence "{seq["name"]}"',

                            "message":
                            "Fade-Reference missing"

                        })

                        continue


                    fade = self.fade_manager.get(
                        step["target"]
                    )


                    if not fade:

                        problems.append({

                            "type": "sequence_fade",

                            "title":
                            f'Sequence "{seq["name"]}"',

                            "target":
                            step["target"],

                            "message":
                            "Fade no longer exists"

                        })


                # -------------------------
                # Strobe
                # -------------------------

                if action == "strobe":

                    if "target" not in step:

                        problems.append({

                            "type": "sequence_strobe",

                            "title":
                            f'Sequence "{seq["name"]}"',

                            "message":
                            "Strobe-Reference missing"

                        })

                        continue



                    print("=== SEQUENCE STROBE CHECK ===")
                    print("Sequence:", seq["name"])
                    print("Step:", step)
                    print("Target:", repr(step["target"]))
                    print("Target type:", type(step["target"]))
                    print("Strobes:", self.strobe_manager.strobes)
                    print("Strobe IDs:", [
                        (s.get("id"), type(s.get("id")))
                        for s in self.strobe_manager.strobes
                    ])

                    
                    strobe = self.strobe_manager.get(
                        step["target"]
                    )


                    if not strobe:

                        problems.append({

                            "type": "sequence_strobe",

                            "title":
                            f'Sequence "{seq["name"]}"',

                            "target":
                            step["target"],

                            "message":
                            "Strobe no longer exists"

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

                action_type = action.get("type")
                target = action.get("target")

                # Keyboard braucht kein Target
                if action_type == "keyboard":
                    continue

                # Target fehlt
                if target is None:

                    problems.append({

                        "type":
                        f"trigger_{action_type}",

                        "title":
                        f'Trigger "{trigger["name"]}"',

                        "message":
                        f'{action_type.capitalize()}-Reference missing'

                    })

                    continue

                # -------------------------
                # Szene
                # -------------------------

                if action_type == "scene":

                    if not self.scene_manager.get(
                        target
                    ):

                        problems.append({

                            "type": "trigger_scene",

                            "title":
                            f'Trigger "{trigger["name"]}"',

                            "message":
                            f'Scene "{target}" no longer exists'

                        })

                # -------------------------
                # Fade
                # -------------------------

                elif action_type == "fade":

                    if not self.fade_manager.get_id(
                        target
                    ):

                        problems.append({

                            "type": "trigger_fade",

                            "title":
                            f'Trigger "{trigger["name"]}"',

                            "message":
                            f'Fade "{target}" no longer exists'

                        })

                # -------------------------
                # Sequenz
                # -------------------------

                elif action_type == "sequence":

                    if not self.sequence_manager.get(
                        target
                    ):

                        problems.append({

                            "type": "trigger_sequence",

                            "title":
                            f'Trigger "{trigger["name"]}"',

                            "message":
                            f'Sequence "{target}" no longer exists'

                        })

                # -------------------------
                # Strobe
                # -------------------------

                elif action_type == "strobe":

                    if not self.strobe_manager.get(
                        target
                    ):

                        problems.append({

                            "type": "trigger_strobe",

                            "title":
                            f'Trigger "{trigger["name"]}"',

                            "message":
                            f'Strobe "{target}" no longer exists'

                        })

        return problems