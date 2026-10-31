import json
import os
import threading
import time
#from fade_manager import fade_manager
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
        if self.thread and self.thread.is_alive():
            return False

        self.running = True

        self.thread = threading.Thread(
            target=self.run,
            args=(sequence,),
            daemon=True
        )

        self.thread.start()
        return True



    def run(self, sequence):
        try:
            for step in sequence.get("steps", []):

                if not self.running:
                    break

                if self.show_controller and self.show_controller.stopped():
                    break

                action = step.get("action")
                target = step.get("target")

                # -------------------------
                # Scene
                # -------------------------
                if action == "scene":

                    self.fade_engine.stop()
                    self.strobe_manager.stop()

                    scene = self.scene_manager.get(target)

                    if scene:
                        self.dmx.apply_scene(scene)
                    else:
                        print(f"Sequence: Scene not found: {target}")
                        break

                # -------------------------
                # Fade
                # -------------------------
                elif action == "fade":

                    self.fade_engine.stop()
                    self.strobe_manager.stop()

                    fade = self.fade_manager.get(target)

                    if fade:
                        if not self.fade_engine.play(fade):
                            print(f"Sequence: Could not start fade: {target}")
                            break
                    else:
                        print(f"Sequence: Fade not found: {target}")
                        break

                # -------------------------
                # Strobe
                # -------------------------
                elif action == "strobe":

                    self.fade_engine.stop()
                    self.strobe_manager.stop()

                    if not target:
                        continue

                    strobe = self.strobe_manager.get_id(target)
                    #strobe = self.strobe_manager.get_id(int(target))

                    if strobe:
                        self.strobe_manager.start(strobe)
                    else:
                        print(f"Sequence: Strobe not found: {target}")
                        break

                # -------------------------
                # Wait
                # -------------------------
                try:
                    wait = max(0, float(step.get("time", 0)) / 1000)
                except (TypeError, ValueError):
                    wait = 0

                elapsed = 0

                while elapsed < wait:

                    if not self.running:
                        return

                    if self.show_controller and self.show_controller.stopped():
                        return

                    interval = min(0.01, wait - elapsed)
                    time.sleep(interval)
                    elapsed += interval

        except Exception as exc:
            print(f"Sequence error: {exc}")

        finally:
            self.running = False

    def stop(self):
        self.running = False

        thread = self.thread

        if thread and thread is not threading.current_thread():
            thread.join()

        if thread and not thread.is_alive():
            self.thread = None

            
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