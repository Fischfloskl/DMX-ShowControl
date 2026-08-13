import json
import os
import threading
import time
from fade_manager import fade_manager
import copy
from name_helper import duplicate_name


SEQUENCE_FILE = "data/sequences.json"


class SequenceManager:


    def __init__(
        self,
        scene_manager,
        dmx_manager,
        fade_manager,
        fade_engine,
        strobe_manager
        ):

        self.sequences = []
        self.scene_manager = scene_manager
        self.dmx = dmx_manager
        self.fade_manager = fade_manager
        self.fade_engine = fade_engine
        self.strobe_manager = strobe_manager
        self.show_controller = None

        self.running = False
        self.thread = None

        self.load()



    def load(self):

        if not os.path.exists(SEQUENCE_FILE):

            self.save()
            return


        with open(
            SEQUENCE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            content = json.load(f)


        if isinstance(content, dict):

            self.sequences = content.get(
                "data",
                []
            )

        elif isinstance(content, list):

            self.sequences = content

        else:

            self.sequences = []




    def save(self):

        os.makedirs(
            "data",
            exist_ok=True
        )


        with open(
            SEQUENCE_FILE,
            "w",
            encoding="utf-8"
        ) as f:


            json.dump(
                {
                    "type":"sequences",
                    "version":1,
                    "data":self.sequences
                },
                f,
                indent=4
            )



    def get(self, name):

        for seq in self.sequences:

            if seq["name"] == name:

                return seq

        return None



    def get_id(self, seq_id):

        for seq in self.sequences:

            if seq["id"] == seq_id:

                return seq

        return None



    def get_next_id(self):

        if not self.sequences:

            return 1


        return max(
            s["id"]
            for s in self.sequences
        ) + 1



    def add(self, sequence):

        self.sequences.append(
            sequence
        )

        self.save()



    def delete(self, seq_id):

        self.sequences = [
            seq for seq in self.sequences
            if seq["id"] != seq_id
        ]

        self.save()



    # -------------------------
    # Playback
    # -------------------------

    def start(self, sequence):

        self.running = True

        self.thread = threading.Thread(
            target=self.run,
            args=(sequence,)
        )

        self.thread.start()



    def run(self, sequence):

        self.running = True

        for step in sequence["steps"]:
            if self.show_controller:
                if self.show_controller.should_stop():
                    break
                if self.show_controller and self.show_controller.stopped():
                    return

            if not self.running:
                break


            if step["action"] == "scene":

                scene = self.scene_manager.get(
                    step["target"]
                )

                if scene:

                    self.dmx.apply_scene(scene)

            elif step["action"]=="fade":

                fade = self.fade_manager.get(
                    step["target"]
                )

                if fade:

                    self.fade_engine.play(
                        fade
                    )
                else:
                    break

            elif step["action"] == "strobe":

                target = step.get("target")

                if not target:
                    continue

                strobe = self.strobe_manager.get_id(
                    target
                )

                if strobe:

                    self.strobe_manager.start(
                        strobe
                    )

                else:
                    break


            wait = step["time"] / 1000
            elapsed = 0

            while elapsed < wait:

                if not self.running:
                    return

                if self.show_controller and self.show_controller.stopped():
                    return

                time.sleep(0.01)
                elapsed += 0.01


        self.running = False

    def stop(self):
        self.running = False

    def set_controller(self, controller):
        self.show_controller = controller

    def duplicate(self, seq_id):

        sequence = self.get_id(seq_id)

        if not sequence:
            return None

        existing_names = [
            s["name"]
            for s in self.sequences
        ]

        new_sequence = copy.deepcopy(sequence)

        new_sequence["id"] = self.get_next_id()

        new_sequence["name"] = duplicate_name(
            sequence["name"],
            existing_names
        )

        self.sequences.append(new_sequence)

        self.save()

        return new_sequence