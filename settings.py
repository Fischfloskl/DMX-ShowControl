import json
import os


SETTINGS_FILE = "data/settings.json"


DEFAULT_SETTINGS = {

    "network_mode": "lan",
    "port": 5000,
    "refresh_rate": 50,
    "create_qr": True,
    "mode": "edit",
    "timing-global-record": "r",
    "timing-global-sim": "mediaplaypause",
    "timing-live": "f3",
    "timing-mode": "live"
}


FILE_TYPES = (
    ("DMX Show", "*.dmxshow"),
    ("DMX Settings", "*.dmxsettings"),
    ("DMX Scene", "*.dmxscene"),
    ("DMX Sequence", "*.dmxseq"),
    ("DMX Device", "*.dmxdevice"),
    ("DMX Trigger", "*.dmxtrigger")
)



class SettingsManager:


    def __init__(self):

        self.settings = DEFAULT_SETTINGS.copy()
        self.load()



    def load(self):

        if not os.path.exists(SETTINGS_FILE):

            self.save()
            return


        try:

            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                content = json.load(f)
        
        
        except (json.JSONDecodeError, FileNotFoundError):
        
            print(
                "settings.json ungültig oder leer - neue Datei erstellt"
            )

            content = []

            self.save()

            return

        



        # Prüfen ob richtige Datei

        if content.get("type") != "settings":

            print("⚠️ Keine gültige Settings-Datei")
            return



        self.settings = content.get(
            "data",
            DEFAULT_SETTINGS.copy()
        )



    def save(self):

        content = {

            "type": "settings",
            "version": 1,
            "data": self.settings

        }


        with open(
            SETTINGS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                content,
                f,
                indent=4
            )



    def get(self,key):

        return self.settings.get(key)



    def set(self,key,value):

        self.settings[key] = value



    @property
    def host(self):

        if self.settings["network_mode"] == "lan":

            return "0.0.0.0"

        return "127.0.0.1"



    @property
    def port(self):

        return self.settings["port"]



    @property
    def create_qr(self):

        return self.settings["create_qr"]



    @property
    def refresh_rate(self):

        return self.settings["refresh_rate"]



    @property
    def network_mode(self):

        return self.settings["network_mode"]

    @property
    def mode(self):

        return self.settings["mode"]
    
    def get_timing(self, key):
        return self.settings.get("timing", {}).get(key)

    def get_timing_mode(self):
        return self.settings["timing-mode"]

    def get_timing_live_key(self):
        return self.settings["timing-live"]

    def get_timing_global_playkey(self):
        return self.settings["timing-global-record"]

    def get_timing_global_simkey(self):
        return self.settings["timing-global-sim"]

    def set_timing_live(self, key, value):
        if "timing-live" not in self.settings:
            self.settings["timing-live"] = {}

        self.settings["timing-live"] = value
        self.save()

    def set_timing_global_record(self, key, value):
        if "timing-global-record" not in self.settings:
            self.settings["timing-global-record"] = {}

        self.settings["timing-global-record"] = value
        self.save()

    def set_timing_global_sim(self, key, value):
        if "timing-global-sim" not in self.settings:
            self.settings["timing-global-sim"] = {}

        self.settings["timing-global-sim"] = value
        self.save()

settings = SettingsManager()