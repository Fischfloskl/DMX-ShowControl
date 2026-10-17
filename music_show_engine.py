
import json
import os
import threading
import time


class MusicShowEngine:
    CONFIG_FILE = "data/music_sync.json"

    def __init__(
        self,
        beat_engine,
        scene_manager,
        fade_manager,
        fade_engine,
        sequence_manager,
        dmx_manager,
    ):
        self.beat_engine = beat_engine
        self.scene_manager = scene_manager
        self.fade_manager = fade_manager
        self.fade_engine = fade_engine
        self.sequence_manager = sequence_manager
        self.dmx_manager = dmx_manager

        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread = None

        self._config = {
            "enabled": False,
            "actions": [],
        }

        self._state = {
            "running": False,
            "last_action": None,
            "last_error": None,
        }

        self.load()

    def load(self):
        os.makedirs("data", exist_ok=True)

        if not os.path.exists(self.CONFIG_FILE):
            self.save()
            return

        try:
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                actions = data.get("actions", [])
                if not isinstance(actions, list):
                    actions = []

                self._config = {
                    "enabled": bool(data.get("enabled", False)),
                    "actions": actions,
                }

        except (OSError, json.JSONDecodeError) as exc:
            print(f"Music-Sync-Konfiguration konnte nicht geladen werden: {exc}")

    def save(self):
        os.makedirs("data", exist_ok=True)

        with self._lock:
            data = {
                "enabled": bool(self._config["enabled"]),
                "actions": self._config["actions"],
            }

            temp_file = self.CONFIG_FILE + ".tmp"

            with open(temp_file, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)

            os.replace(temp_file, self.CONFIG_FILE)

    def get_config(self):
        with self._lock:
            return json.loads(json.dumps(self._config))

    def set_config(self, data):
        if not isinstance(data, dict):
            raise ValueError("Ungültige Konfiguration.")

        actions = data.get("actions", [])
        if not isinstance(actions, list):
            raise ValueError("actions muss eine Liste sein.")

        normalized = []

        for index, action in enumerate(actions, start=1):
            if not isinstance(action, dict):
                raise ValueError("Jede Aktion muss ein Objekt sein.")

            action_type = str(action.get("type", "scene"))
            if action_type not in ("scene", "fade", "sequence"):
                raise ValueError(f"Ungültiger Aktionstyp: {action_type}")

            target = str(action.get("target", "")).strip()
            every_beats = int(action.get("every_beats", 1))
            phase = int(action.get("phase", 0))

            if not target:
                raise ValueError(f"Aktion {index}: Ziel fehlt.")

            if not 1 <= every_beats <= 256:
                raise ValueError(
                    f"Aktion {index}: every_beats muss zwischen 1 und 256 liegen."
                )

            if not 0 <= phase < every_beats:
                raise ValueError(
                    f"Aktion {index}: phase muss zwischen 0 und "
                    f"{every_beats - 1} liegen."
                )

            normalized.append({
                "id": int(action.get("id", index)),
                "enabled": bool(action.get("enabled", True)),
                "type": action_type,
                "target": target,
                "every_beats": every_beats,
                "phase": phase,
            })

        with self._lock:
            self._config = {
                "enabled": bool(data.get("enabled", False)),
                "actions": normalized,
            }

        self.save()

    def get_state(self):
        with self._lock:
            return dict(self._state)

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return

            if not self._config["enabled"]:
                raise ValueError("Musikaktionen sind nicht aktiviert.")

            if not self._config["actions"]:
                raise ValueError("Es sind keine Musikaktionen konfiguriert.")

            self._stop_event.clear()
            self._state.update({
                "running": True,
                "last_action": None,
                "last_error": None,
            })

            self._thread = threading.Thread(
                target=self._run,
                name="MusicShowEngine",
                daemon=True,
            )
            self._thread.start()

    def stop(self):
        self._stop_event.set()

        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=1.0)

        with self._lock:
            self._state["running"] = False
            self._thread = None

    def _run(self):
        last_count = self.beat_engine.get_state()["beat_count"]

        try:
            while not self._stop_event.is_set():
                state = self.beat_engine.get_state()
                count = state["beat_count"]

                if count != last_count:
                    # Bei ausgelassenen Updates nur den neuesten Beat
                    # verwenden, damit keine Aktionen nachträglich feuern.
                    last_count = count
                    self._dispatch_beat(count)

                time.sleep(0.01)

        except Exception as exc:
            with self._lock:
                self._state["last_error"] = str(exc)

        finally:
            with self._lock:
                self._state["running"] = False

    def _dispatch_beat(self, beat_count):
        with self._lock:
            if not self._config["enabled"]:
                return

            actions = [
                dict(action)
                for action in self._config["actions"]
                if action.get("enabled", True)
            ]

        for action in actions:
            every = action["every_beats"]
            phase = action["phase"]

            if (beat_count - 1) % every != phase:
                continue

            try:
                self._execute(action)

                with self._lock:
                    self._state["last_action"] = {
                        "beat": beat_count,
                        "type": action["type"],
                        "target": action["target"],
                        "time": time.time(),
                    }
                    self._state["last_error"] = None

            except Exception as exc:
                with self._lock:
                    self._state["last_error"] = (
                        f'{action["type"]} "{action["target"]}": {exc}'
                    )

    def _execute(self, action):
        action_type = action["type"]
        target = action["target"]

        if action_type == "scene":
            scene = self.scene_manager.get(target)
            if not scene:
                raise ValueError(f'Szene "{target}" nicht gefunden.')

            self.dmx_manager.apply_scene(scene)
            return

        if action_type == "fade":
            fade = self.fade_manager.get(target)
            if not fade:
                raise ValueError(f'Fade "{target}" nicht gefunden.')

            self.fade_engine.play(fade)
            return

        if action_type == "sequence":
            sequence = self.sequence_manager.get(target)
            if not sequence:
                raise ValueError(f'Sequence "{target}" nicht gefunden.')

            if self.sequence_manager.running:
                raise ValueError(
                    "Eine Sequence läuft bereits; die neue wurde übersprungen."
                )

            self.sequence_manager.start(sequence)
            return

        raise ValueError(f"Unbekannter Aktionstyp: {action_type}")
