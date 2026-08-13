import json
import copy
from datetime import datetime


class ExportManager:


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



    def create_export(
        self,
        items
    ):


        data = {}



        if "scenes" in items:

            data["scenes"] = copy.deepcopy(
                self.scene_manager.scenes
            )



        if "fades" in items:

            data["fades"] = copy.deepcopy(
                self.fade_manager.fades
            )



        if "sequences" in items:

            data["sequences"] = copy.deepcopy(
                self.sequence_manager.sequences
            )



        if "triggers" in items:

            data["triggers"] = copy.deepcopy(
                self.trigger_manager.triggers
            )



        if "devices" in items:

            data["devices"] = copy.deepcopy(
                self.devices.devices
            )



        export = {

            "type":
            "DMX-ShowControl",


            "version":
            1,


            "created":
            datetime.now().isoformat(),


            "data":
            data

        }



        return json.dumps(
            export,
            indent=4,
            ensure_ascii=False
        )