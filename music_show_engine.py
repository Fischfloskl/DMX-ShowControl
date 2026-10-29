
import json
import os
import threading
import time
from copy import deepcopy


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
        strobe_manager
    ):
        self.beat_engine = beat_engine
        self.scene_manager = scene_manager
        self.fade_manager = fade_manager
        self.fade_engine = fade_engine
        self.sequence_manager = sequence_manager
        self.dmx_manager = dmx_manager
        self.strobe_manager = strobe_manager

        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread = None

        self._active_strobe_started_by_sequence = False

        # Legacy global music actions.
        self._config = {
            "enabled": False,
            "every_beats": 1,
            "actions": [],
        }

        # Per-audio-sequence actions.
        # When set, these replace the legacy global actions.
        self._active_sequence_config = None
        self._active_sequence_name = None

        self._state = {
            "running": False,
            "mode": None,
            "active_sequence": None,
            "last_action": None,
            "last_error": None,
        }

        self.load()

    # --------------------------------------------------------
    # Legacy configuration
    # --------------------------------------------------------

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

            global_every = data.get("every_beats", 1)

            if "every_beats" not in data:
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
                    action_id = int(action.get("id", len(migrated_actions) + 1))
                except (TypeError, ValueError):
                    phase = 0
                    action_id = len(migrated_actions) + 1

                phase = max(0, min(global_every - 1, phase))

                migrated_actions.append({
                    "id": action_id,
                    "enabled": bool(action.get("enabled", True)),
                    "type": action.get("type", "scene"),
                    "target": str(action.get("target", "")).strip(),
                    "phase": phase,
                })

            self._config = {
                "enabled": bool(data.get("enabled", False)),
                "every_beats": global_every,
                "actions": migrated_actions,
            }

            self.save()

        except (OSError, json.JSONDecodeError) as exc:
            print(f"Could not load Music Sync configuration: {exc}")

    def save(self):
        os.makedirs("data", exist_ok=True)

        with self._lock:
            data = deepcopy(self._config)

        temp_file = self.CONFIG_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

        os.replace(temp_file, self.CONFIG_FILE)

    def get_config(self):
        with self._lock:
            return deepcopy(self._config)

    
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

            if action_type not in ("scene", "fade", "sequence", "strobe"):
                raise ValueError(f"Invalid action type: {action_type}")

            target = str(action.get("target", "")).strip()

            if not target:
                raise ValueError(f"Action {index}: target is required.")

            # Strobe targets must be valid numeric IDs.
            if action_type == "strobe":
                try:
                    strobe_id = int(target)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Action {index}: strobe target must be an ID."
                    )

                if not self.strobe_manager.get_id(strobe_id):
                    raise ValueError(
                        f"Action {index}: strobe {strobe_id} was not found."
                    )

                target = str(strobe_id)

            try:
                phase = int(action.get("phase", 0))
                action_id = int(action.get("id", index))
            except (TypeError, ValueError):
                raise ValueError(
                    f"Action {index}: ID and phase must be integers."
                )

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


    # --------------------------------------------------------
    # State
    # --------------------------------------------------------

    def get_state(self):
        with self._lock:
            return deepcopy(self._state)

    # --------------------------------------------------------
    # Start legacy global actions
    # --------------------------------------------------------

    def start(self):
        """Start the existing global Music Actions configuration."""

        with self._lock:
            if self._thread and self._thread.is_alive():
                return

            if not self._config["enabled"]:
                raise ValueError("Music actions are not enabled.")

            if not self._config["actions"]:
                raise ValueError("No music actions are configured.")

            self._active_sequence_config = None
            self._active_sequence_name = None

            self._start_locked(mode="global")

    # --------------------------------------------------------
    # Start actions belonging to an audio sequence
    # --------------------------------------------------------

    def start_sequence(self, sequence):
        """
        Start the actions stored in one audio sequence.

        Expected sequence fields:
            name
            every_beats
            actions
        """

        if not isinstance(sequence, dict):
            raise ValueError("Invalid audio sequence.")

        name = str(sequence.get("name", "")).strip()

        if not name:
            raise ValueError("The audio sequence has no name.")

        actions = sequence.get("actions", [])

        if not isinstance(actions, list):
            raise ValueError("Audio sequence actions must be a list.")

        try:
            every = int(sequence.get("every_beats", 1))
        except (TypeError, ValueError):
            raise ValueError("'every_beats' must be an integer.")

        if not 1 <= every <= 64:
            raise ValueError("'every_beats' must be between 1 and 64.")

        normalized_actions = []

        for index, action in enumerate(actions, start=1):
            if not isinstance(action, dict):
                raise ValueError(f"Action {index} must be an object.")

            action_type = action.get("type")

            if action_type not in ("scene", "fade", "strobe"):
                raise ValueError(
                    f"Action {index} has an unsupported type."
                )

            target = str(action.get("target", "")).strip()

            if not target:
                raise ValueError(f"Action {index} has no target.")

            phase = action.get("phase", "any")

            # Accept old numeric phases as well as the new editor values.
            if isinstance(phase, bool):
                raise ValueError(f"Action {index} has an invalid phase.")

            if isinstance(phase, int):
                if not 0 <= phase < every:
                    raise ValueError(
                        f"Action {index}: numeric phase must be between "
                        f"0 and {every - 1}."
                    )
            elif phase not in ("any", "downbeat", "beat"):
                raise ValueError(f"Action {index} has an invalid phase.")

            normalized_actions.append({
                "id": action.get("id", index),
                "enabled": bool(action.get("enabled", True)),
                "type": action_type,
                "target": target,
                "phase": phase,
            })

        if not any(action["enabled"] for action in normalized_actions):
            raise ValueError(
                "The audio sequence has no enabled actions."
            )

        # Stop the previous engine without holding the lock.
        self.stop()

        with self._lock:
            self._active_sequence_config = {
                "enabled": True,
                "every_beats": every,
                "actions": normalized_actions,
            }
            self._active_sequence_name = name

            self._start_locked(mode="audio_sequence")

    def _start_locked(self, mode):
        """Start the worker thread. Caller must hold self._lock."""

        self._stop_event.clear()

        self._state.update({
            "running": True,
            "mode": mode,
            "active_sequence": (
                self._active_sequence_name
                if mode == "audio_sequence"
                else None
            ),
            "last_action": None,
            "last_error": None,
        })

        self._thread = threading.Thread(
            target=self._run,
            name="MusicShowEngine",
            daemon=True,
        )
        self._thread.start()

    # --------------------------------------------------------
    # Stop
    # --------------------------------------------------------

    def stop(self):
        """Stop action processing and clear the active sequence."""

        self._stop_locked()

        with self._lock:
            stop_strobe = self._active_strobe_started_by_sequence
            self._active_strobe_started_by_sequence = False

            self._active_sequence_config = None
            self._active_sequence_name = None

            self._state.update({
                "running": False,
                "mode": None,
                "active_sequence": None,
            })

        if stop_strobe:
            self.strobe_manager.stop(clear=False)

    def _stop_locked(self):
        """Stop the worker thread without changing the configuration."""

        self._stop_event.set()
        thread = self._thread

        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)

        with self._lock:
            self._thread = None
            self._state["running"] = False

    # --------------------------------------------------------
    # Beat loop
    # --------------------------------------------------------

    def _run(self):
        try:
            initial_state = self.beat_engine.get_state()
            last_count = initial_state.get("beat_count", 0)

            while not self._stop_event.is_set():
                state = self.beat_engine.get_state()
                count = state.get("beat_count", last_count)

                if count != last_count:
                    # Do not replay missed beats after a delayed update.
                    last_count = count
                    self._dispatch_beat(count)

                time.sleep(0.01)

        except Exception as exc:
            with self._lock:
                self._state["last_error"] = str(exc)

        finally:
            with self._lock:
                self._state["running"] = False

    # --------------------------------------------------------
    # Beat dispatch
    # --------------------------------------------------------

    def _dispatch_beat(self, beat_count):
        with self._lock:
            if self._active_sequence_config is not None:
                config = deepcopy(self._active_sequence_config)
                mode = "audio_sequence"
            else:
                config = deepcopy(self._config)
                mode = "global"

            if not config.get("enabled"):
                return

            every = config.get("every_beats", 1)
            actions = [
                action
                for action in config.get("actions", [])
                if action.get("enabled", True)
            ]

        for action in actions:
            phase = action.get("phase", 0)

            if mode == "global":
                # Preserve the legacy numeric phase behavior.
                if (beat_count - 1) % every != phase:
                    continue

            elif isinstance(phase, int):
                # Compatibility for audio sequences using numeric phases.
                if (beat_count - 1) % every != phase:
                    continue

            elif phase == "any":
                # Execute on every detected beat.
                pass

            elif phase == "downbeat":
                # Treat the first beat of each configured cycle as its downbeat.
                if (beat_count - 1) % every != 0:
                    continue

            elif phase == "beat":
                # Execute on beats other than the first beat of each cycle.
                if every == 1 or (beat_count - 1) % every == 0:
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

    # --------------------------------------------------------
    # Execute actions
    # --------------------------------------------------------

    def _execute(self, action):
        action_type = action["type"]
        target = action["target"]

        if action_type == "scene":
            scene = self.scene_manager.get(target)

            if not scene:
                raise ValueError(f'Scene "{target}" was not found.')

            self.dmx_manager.apply_scene(scene)
            return

        if action_type == "fade":
            fade = self.fade_manager.get(target)

            if not fade:
                raise ValueError(f'Fade "{target}" was not found.')

            self.fade_engine.play(fade)
            return

                
        if action_type == "strobe":
            try:
                strobe_id = int(target)
            except (TypeError, ValueError):
                raise ValueError("Invalid strobe ID.")

            strobe = self.strobe_manager.get_id(strobe_id)

            if strobe is None:
                raise ValueError(f'Strobe "{strobe_id}" was not found.')

            if not self.strobe_manager.start(strobe):
                raise RuntimeError(f'Could not start strobe "{strobe_id}".')

            with self._lock:
                self._active_strobe_started_by_music_show = True

            return


        # Sequence actions are supported only by the legacy global system.
        if action_type == "sequence":
            sequence = self.sequence_manager.get(target)

            if not sequence:
                raise ValueError(f'Sequence "{target}" was not found.')

            if self.sequence_manager.running:
                raise ValueError(
                    "A sequence is already running; the new sequence was skipped."
                )

            self.sequence_manager.start(sequence)
            return

        raise ValueError(f"Unknown action type: {action_type}")
