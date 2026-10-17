import json
import os
import copy
from name_helper import duplicate_name


TRIGGER_FILE = "data/triggers.json"


class TriggerManager:

    def __init__(self):

        self.triggers = []

        self.load()

    def load(self):

        if not os.path.exists(TRIGGER_FILE):

            self.save()
            return


        try:

            with open(
                TRIGGER_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                content = json.load(f)


        except (
            json.JSONDecodeError,
            FileNotFoundError
        ):

            print(
                "triggers.json leer oder beschädigt - neue Datei erstellt"
            )

            self.triggers = []

            self.save()

            return


        if isinstance(content, dict):

            if content.get("type") == "triggers":

                self.triggers = content.get(
                    "data",
                    []
                )

            else:

                self.triggers = []

        elif isinstance(content, list):

            self.triggers = content

        else:

            self.triggers = []


        
        updated = False

        # Migrate and normalize existing triggers
        for trigger in self.triggers:
            if not isinstance(trigger, dict):
                continue

            trigger_type = trigger.get("type", "keyboard")

            if trigger_type == "keyboard":
                if "keys" not in trigger:
                    old_input = trigger.pop("input", None)

                    if isinstance(old_input, list):
                        trigger["keys"] = old_input
                    elif old_input:
                        trigger["keys"] = [old_input]
                    else:
                        trigger["keys"] = []

                    updated = True

                elif not isinstance(trigger["keys"], list):
                    trigger["keys"] = (
                        [trigger["keys"]]
                        if trigger["keys"]
                        else []
                    )
                    updated = True

            elif trigger_type == "midi":
                if "input" in trigger:
                    try:
                        trigger["input"] = int(trigger["input"])
                    except (TypeError, ValueError):
                        pass

        if updated:
            self.save()


    def save(self):

        os.makedirs(
            "data",
            exist_ok=True
        )


        content = {

            "type": "triggers",

            "version": 2,

            "data": self.triggers

        }


        with open(
            TRIGGER_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                content,
                f,
                indent=4,
                ensure_ascii=False
            )

    
    def add(self, trigger):

        if "id" not in trigger:
            trigger["id"] = self.get_next_id()

        if trigger.get("type", "keyboard") == "keyboard":
            if "keys" not in trigger:
                trigger["keys"] = []

        self.triggers.append(trigger)
        self.save()


    def get(self, name):

        for trigger in self.triggers:

            if trigger["name"] == name:

                return trigger

        return None


    # ------------------------------------
    # Trigger prüfen
    # ------------------------------------

    def check_trigger(
        self,
        trigger_type,
        key
    ):

        for trigger in self.triggers:

            if not trigger.get(
                "enabled",
                True
            ):
                continue

            if trigger.get("type") != trigger_type:
                continue

            if key in trigger.get(
                "keys",
                []
            ):
                self.execute(trigger)


    def check_keyboard(self, key):

        self.check_trigger(
            "keyboard",
            key
        )


    def check_midi(self, note):

        self.check_trigger(
            "midi",
            note
        )


    # ------------------------------------
    # Aktionen
    # ------------------------------------

    def execute(self, trigger):

        print(
            "Trigger:",
            trigger["name"]
        )


        for action in trigger.get(
            "actions",
            []
        ):

            print(
                " Aktion:",
                action
            )

    def get_id(self, trigger_id):

        for trigger in self.triggers:

            if trigger["id"] == trigger_id:

                return trigger

        return None

    def get_next_id(self):

        if not self.triggers:

            return 1


        return max(
            t["id"]
            for t in self.triggers
        ) + 1

    def delete(self, trigger_id):

        self.triggers = [

            t for t in self.triggers

            if t["id"] != trigger_id

        ]

        self.save()



    def stop(self):
        self.running = False

    def duplicate(self, trigger_id):

        trigger = self.get_id(trigger_id)

        if not trigger:
            return None

        existing_names = [
            t["name"]
            for t in self.triggers
        ]

        new_trigger = copy.deepcopy(trigger)

        new_trigger["id"] = self.get_next_id()

        new_trigger["name"] = duplicate_name(
            trigger["name"],
            existing_names
        )

        self.triggers.append(new_trigger)

        self.save()

        return new_trigger


    def midi_note_name(self, note):
        note_names = [
            "C", "C#", "D", "D#", "E", "F",
            "F#", "G", "G#", "A", "A#", "B"
        ]

        try:
            note = int(note)
        except (TypeError, ValueError):
            return "Unknown"

        if not 0 <= note <= 127:
            return "Unknown"

        name = note_names[note % 12]
        octave = (note // 12) - 2

        return f"{name}{octave}"