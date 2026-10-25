
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
            "every_beats": 1,
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

            if not isinstance(data, dict):
                return

            actions = data.get("actions", [])
            if not isinstance(actions, list):
                actions = []

            # Migrate the old per-action interval to one global interval.
            global_every = data.get("every_beats")
            if global_every is None:
                global_every = next(
                    (
                        action.get("every_beats", 1)
                        for action in actions
                        if isinstance(action, dict)
                    ),
                    1,
                )

            try:
                global_every = max(1, min(256, int(global_every)))
            except (TypeError, ValueError):
                global_every = 1

            migrated_actions = []
            for action in actions:
                if not isinstance(action, dict):
                    continue

                try:
                    phase = int(action.get("phase", 0))
                except (TypeError, ValueError):
                    phase = 0

                # A phase must fit inside the global interval.
                phase = max(0, min(global_every - 1, phase))

                migrated_action = dict(action)
                migrated_action.pop("every_beats", None)
                migrated_action["phase"] = phase
                migrated_actions.append(migrated_action)

            self._config = {
                "enabled": bool(data.get("enabled", False)),
                "every_beats": global_every,
                "actions": migrated_actions,
            }

            # Persist the migrated format.
            self.save()

        except (OSError, json.JSONDecodeError) as exc:
            print(f"Could not load Music Sync configuration: {exc}")

    def save(self):
        os.makedirs("data", exist_ok=True)

        with self._lock:
            data = {
                "enabled": bool(self._config["enabled"]),
                "every_beats": int(self._config["every_beats"]),
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
            raise ValueError("Invalid configuration.")

        actions = data.get("actions", [])
        if not isinstance(actions, list):
            raise ValueError("'actions' must be a list.")

        try:
            global_every = int(data.get("every_beats", 1))
        except (TypeError, ValueError):
            raise ValueError("'every_beats' must be an integer.")

        if not 1 <= global_every <= 256:
            raise ValueError("'every_beats' must be between 1 and 256.")

        normalized = []

        for index, action in enumerate(actions, start=1):
            if not isinstance(action, dict):
                raise ValueError("Each action must be an object.")

            action_type = str(action.get("type", "scene"))
            if action_type not in ("scene", "fade", "sequence"):
                raise ValueError(f"Invalid action type: {action_type}")

            target = str(action.get("target", "")).strip()

            try:
                phase = int(action.get("phase", 0))
                action_id = int(action.get("id", index))
            except (TypeError, ValueError):
                raise ValueError(
                    f"Action {index}: ID and phase must be integers."
                )

            if not target:
                raise ValueError(f"Action {index}: target is required.")

            if not 0 <= phase < global_every:
                raise ValueError(
                    f"Action {index}: phase must be between "
                    f"0 and {global_every - 1}."
                )

            normalized.append({
                "id": action_id,
                "enabled": bool(action.get("enabled", True)),
                "type": action_type,
                "target": target,
                "phase": phase,
            })

        with self._lock:
            self._config = {
                "enabled": bool(data.get("enabled", False)),
                "every_beats": global_every,
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

            every = self._config["every_beats"]
            actions = [
                dict(action)
                for action in self._config["actions"]
                if action.get("enabled", True)
            ]

        for action in actions:
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
