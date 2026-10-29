
import json
import re
import uuid
from pathlib import Path
from copy import deepcopy


class AudioSequenceManager:
    """
    Manages audio sequences (.json) and global audio settings.

    Each sequence has a stable ID independent of its editable name.
    Existing name-based sequence files are migrated automatically.
    """

    SEQUENCE_EXTENSION = ".json"

    DEFAULT_GLOBAL_SETTINGS = {
        "device_index": None,
        "source": "bass",
        "sensitivity": 150,
        "min_interval_ms": 120,
        "eq_weights": [180, 300, 200, 80, 50, 40, 25, 15],
    }

    DEFAULT_REACTION_SETTINGS = {
        "enabled": True,
        "movement_speed": 0.85,
        "color_change": 0.75,
        "intensity": 0.9,
        "strobe_enabled": False,
    }

    ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")

    def __init__(
        self,
        sequence_directory="data/audio_sequences",
        settings_file="data/audio_settings.json",
    ):
        self.sequence_directory = Path(sequence_directory)
        self.settings_file = Path(settings_file)

        self.sequence_directory.mkdir(parents=True, exist_ok=True)
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)

        self.active_sequence = None
        self.running = False
        self.error = None

        self.global_settings = self._load_global_settings()

        # Upgrade existing name-based files.
        self._migrate_legacy_sequences()

    # --------------------------------------------------------
    # Global settings
    # --------------------------------------------------------

    def _load_global_settings(self):
        if not self.settings_file.exists():
            settings = deepcopy(self.DEFAULT_GLOBAL_SETTINGS)
            self._write_json(self.settings_file, settings)
            return settings

        try:
            with self.settings_file.open("r", encoding="utf-8") as file:
                saved = json.load(file)

            settings = deepcopy(self.DEFAULT_GLOBAL_SETTINGS)

            if isinstance(saved, dict):
                settings.update(saved)

            self._validate_settings(settings)
            return settings

        except (OSError, json.JSONDecodeError, ValueError) as exc:
            self.error = f"Could not load global audio settings: {exc}"
            return deepcopy(self.DEFAULT_GLOBAL_SETTINGS)

    def get_global_settings(self):
        return deepcopy(self.global_settings)

    def save_global_settings(self, settings):
        if not isinstance(settings, dict):
            raise ValueError("Settings must be a dictionary.")

        updated = deepcopy(self.DEFAULT_GLOBAL_SETTINGS)
        updated.update(settings)
        self._validate_settings(updated)

        self._write_json(self.settings_file, updated)
        self.global_settings = updated

        return self.get_global_settings()

    # --------------------------------------------------------
    # IDs, names and paths
    # --------------------------------------------------------

    @staticmethod
    def _new_id():
        return uuid.uuid4().hex

    @classmethod
    def _validate_id(cls, sequence_id):
        sequence_id = str(sequence_id).strip().lower()

        if not cls.ID_PATTERN.fullmatch(sequence_id):
            raise ValueError("Invalid audio sequence ID.")

        return sequence_id

    @staticmethod
    def _safe_name(name):
        if not isinstance(name, str):
            raise ValueError("A sequence name is required.")

        name = name.strip()

        if not name or name in {".", ".."}:
            raise ValueError("Please enter a valid sequence name.")

        if not re.fullmatch(r"[\w äöüÄÖÜß.-]+", name, flags=re.UNICODE):
            raise ValueError(
                "The name may only contain letters, numbers, spaces, "
                "hyphens, periods and underscores."
            )

        return name

    def _sequence_path(self, sequence_id):
        sequence_id = self._validate_id(sequence_id)
        path = (
            self.sequence_directory / f"{sequence_id}{self.SEQUENCE_EXTENSION}"
        ).resolve()

        if path.parent != self.sequence_directory.resolve():
            raise ValueError("Invalid sequence file path.")

        return path

    def _find_sequence_path(self, identifier):
        """
        Find a sequence by ID.

        Name lookup is retained temporarily for compatibility with older
        callers while app.py and trigger references are being migrated.
        """
        identifier = str(identifier).strip()

        if self.ID_PATTERN.fullmatch(identifier.lower()):
            path = self._sequence_path(identifier.lower())
            if path.is_file():
                return path

        # Transitional compatibility: resolve an old sequence name.
        for path in self.sequence_directory.glob(
            f"*{self.SEQUENCE_EXTENSION}"
        ):
            try:
                with path.open("r", encoding="utf-8") as file:
                    data = json.load(file)

                if isinstance(data, dict):
                    if data.get("name") == identifier:
                        return path

            except (OSError, json.JSONDecodeError):
                continue

        return None

    def _ensure_unique_name(self, name, exclude_id=None):
        normalized = name.casefold()

        for sequence in self.list_sequences():
            if sequence["id"] == exclude_id:
                continue

            if sequence["name"].casefold() == normalized:
                raise ValueError(
                    f"An audio sequence named '{name}' already exists."
                )

    # --------------------------------------------------------
    # Migration of existing sequence files
    # --------------------------------------------------------

    def _migrate_legacy_sequences(self):
        """
        Give every existing sequence a stable ID and store it under
        <id>.json instead of <old name>.json.

        Existing IDs are preserved. Sequence content is retained during
        migration, including fields that may be handled elsewhere.
        """
        files = list(
            self.sequence_directory.glob(f"*{self.SEQUENCE_EXTENSION}")
        )

        for old_path in files:
            try:
                with old_path.open("r", encoding="utf-8") as file:
                    data = json.load(file)

                if not isinstance(data, dict):
                    self.error = (
                        f"Cannot migrate invalid sequence file: {old_path.name}"
                    )
                    continue

                sequence_id = data.get("id")

                if not isinstance(sequence_id, str) or not self.ID_PATTERN.fullmatch(
                    sequence_id.lower()
                ):
                    sequence_id = self._new_id()
                else:
                    sequence_id = sequence_id.lower()

                data["id"] = sequence_id
                data.setdefault("version", 1)
                data.setdefault("name", old_path.stem)
                data.setdefault("use_global_settings", True)
                data.setdefault("overrides", {})
                data.setdefault(
                    "reaction",
                    deepcopy(self.DEFAULT_REACTION_SETTINGS),
                )
                data.setdefault("every_beats", 1)
                data.setdefault("actions", [])

                new_path = self._sequence_path(sequence_id)

                if old_path.resolve() == new_path.resolve():
                    # File already uses the ID as its filename.
                    self._write_json(new_path, data)
                    continue

                if new_path.exists():
                    with new_path.open("r", encoding="utf-8") as file:
                        existing = json.load(file)

                    if existing.get("id") != sequence_id:
                        raise ValueError(
                            f"Sequence ID collision: {sequence_id}"
                        )

                    # Another file already contains this same sequence ID.
                    old_path.unlink()
                    continue

                # Write the new file first, then remove the old one.
                self._write_json(new_path, data)
                old_path.unlink()

            except (OSError, json.JSONDecodeError, ValueError) as exc:
                self.error = (
                    f"Could not migrate {old_path.name}: {exc}"
                )

    # --------------------------------------------------------
    # List, create, load, save, duplicate and delete
    # --------------------------------------------------------

    def list_sequences(self):
        sequences = []

        for path in sorted(
            self.sequence_directory.glob(f"*{self.SEQUENCE_EXTENSION}")
        ):
            try:
                with path.open("r", encoding="utf-8") as file:
                    data = json.load(file)

                if not isinstance(data, dict):
                    raise ValueError("Invalid sequence data.")

                sequence_id = data.get("id", path.stem)

                sequences.append({
                    "id": sequence_id,
                    "name": data.get("name", path.stem),
                    "file": path.name,
                })

            except (OSError, json.JSONDecodeError, ValueError):
                sequences.append({
                    "id": path.stem,
                    "name": path.stem,
                    "file": path.name,
                    "error": True,
                })

        return sequences

    def create_sequence(self, name, data=None):
        name = self._safe_name(name)
        self._ensure_unique_name(name)

        sequence_id = self._new_id()

        sequence_data = deepcopy(data) if isinstance(data, dict) else {}

        sequence_data.update({
            "id": sequence_id,
            "version": 2,
            "name": name,
            "use_global_settings": sequence_data.get(
                "use_global_settings", True
            ),
            "overrides": sequence_data.get("overrides", {}),
            "reaction": sequence_data.get(
                "reaction",
                deepcopy(self.DEFAULT_REACTION_SETTINGS),
            ),
            "every_beats": sequence_data.get("every_beats", 1),
            "actions": sequence_data.get("actions", []),
        })

        return self.save_sequence(sequence_id, sequence_data)

    def load_sequence(self, identifier):
        path = self._find_sequence_path(identifier)

        if path is None:
            raise FileNotFoundError(
                f"Audio sequence '{identifier}' was not found."
            )

        with path.open("r", encoding="utf-8") as file:
            sequence = json.load(file)

        if not isinstance(sequence, dict):
            raise ValueError("The audio sequence contains invalid data.")

        sequence.setdefault("id", path.stem)
        sequence.setdefault("version", 1)
        sequence.setdefault("name", path.stem)
        sequence.setdefault("use_global_settings", True)
        sequence.setdefault("overrides", {})
        sequence.setdefault(
            "reaction",
            deepcopy(self.DEFAULT_REACTION_SETTINGS),
        )
        sequence.setdefault("every_beats", 1)
        sequence.setdefault("actions", [])

        return sequence

    def save_sequence(self, sequence_id, data):
        """
        Save a sequence by stable ID.

        For a new sequence, supply a new ID and a name in data.
        The name may change without changing the ID.
        """
        if not isinstance(data, dict):
            raise ValueError("Sequence data must be a dictionary.")

        sequence_id = str(sequence_id).strip()
        existing_path = self._find_sequence_path(sequence_id)

        if existing_path is not None:
            existing = self.load_sequence(sequence_id)
            sequence_id = existing["id"]
        else:
            # New sequences must use a valid ID.
            sequence_id = self._validate_id(sequence_id)
            existing = {
                "version": 2,
                "id": sequence_id,
                "name": "",
                "use_global_settings": True,
                "overrides": {},
                "reaction": deepcopy(self.DEFAULT_REACTION_SETTINGS),
                "every_beats": 1,
                "actions": [],
            }

        name = self._safe_name(data.get("name", existing.get("name", "")))
        self._ensure_unique_name(name, exclude_id=sequence_id)

        overrides = data.get("overrides", existing.get("overrides", {}))
        reaction = data.get("reaction", existing.get("reaction", {}))
        actions = data.get("actions", existing.get("actions", []))
        every_beats = data.get(
            "every_beats",
            existing.get("every_beats", 1),
        )

        if not isinstance(overrides, dict):
            raise ValueError("overrides must be a dictionary.")

        if not isinstance(reaction, dict):
            raise ValueError("reaction must be a dictionary.")

        if not isinstance(actions, list):
            raise ValueError("actions must be a list.")

        try:
            every_beats = int(every_beats)
        except (TypeError, ValueError):
            raise ValueError("every_beats must be an integer.")

        if every_beats < 1:
            raise ValueError("every_beats must be at least 1.")

        use_global_settings = data.get(
            "use_global_settings",
            existing.get("use_global_settings", True),
        )

        if not isinstance(use_global_settings, bool):
            raise ValueError("use_global_settings must be a boolean.")

        # Validate explicit overrides against the default/global settings.
        effective_settings = (
            self.get_global_settings()
            if use_global_settings
            else deepcopy(self.DEFAULT_GLOBAL_SETTINGS)
        )
        effective_settings.update(overrides)
        validated_settings = self._validate_settings(effective_settings)

        validated_overrides = {
            key: validated_settings[key]
            for key in overrides
            if key in validated_settings
        }

        sequence = {
            "id": sequence_id,
            "version": 2,
            "name": name,
            "use_global_settings": use_global_settings,
            "overrides": validated_overrides,
            "reaction": reaction,
            "every_beats": every_beats,
            "actions": actions,
        }

        self._write_json(self._sequence_path(sequence_id), sequence)

        # Remove an old name-based file if this save migrated it.
        if existing_path is not None:
            target_path = self._sequence_path(sequence_id)
            if existing_path.resolve() != target_path.resolve():
                existing_path.unlink(missing_ok=True)

        return deepcopy(sequence)

    def duplicate_sequence(self, sequence_id, new_name=None):
        original = self.load_sequence(sequence_id)

        if new_name is None:
            base_name = f"{original['name']} Copy"
            new_name = base_name
            counter = 2

            existing_names = {
                item["name"].casefold()
                for item in self.list_sequences()
            }

            while new_name.casefold() in existing_names:
                new_name = f"{base_name} {counter}"
                counter += 1

        new_name = self._safe_name(new_name)
        self._ensure_unique_name(new_name)

        duplicate = deepcopy(original)
        duplicate.pop("id", None)
        duplicate["name"] = new_name
        duplicate["version"] = 2

        return self.create_sequence(new_name, duplicate)

    def delete_sequence(self, sequence_id):
        sequence = self.load_sequence(sequence_id)
        stable_id = sequence["id"]

        if self.active_sequence == stable_id and self.running:
            raise ValueError("An active audio sequence cannot be deleted.")

        path = self._sequence_path(stable_id)

        if not path.exists():
            raise FileNotFoundError("Audio sequence was not found.")

        path.unlink()
        return True

    # --------------------------------------------------------
    # Effective settings
    # --------------------------------------------------------

    def get_effective_settings(self, sequence):
        if not isinstance(sequence, dict):
            raise ValueError("Invalid audio sequence.")

        if sequence.get("use_global_settings", True):
            settings = self.get_global_settings()
        else:
            settings = deepcopy(self.DEFAULT_GLOBAL_SETTINGS)

        overrides = sequence.get("overrides", {})

        if not isinstance(overrides, dict):
            raise ValueError("'overrides' must be a dictionary.")

        settings.update(overrides)
        self._validate_settings(settings)

        return settings

    def _validate_settings(self, settings):
        allowed_sources = {
            "bass",
            "combined",
            "band_1",
            "band_2",
            "band_3",
            "band_4",
            "band_5",
            "band_6",
            "band_7",
            "band_8",
        }

        if settings.get("source") not in allowed_sources:
            raise ValueError("Invalid audio source for beat detection.")

        sensitivity = settings.get("sensitivity", 150)
        if (
            isinstance(sensitivity, bool)
            or not isinstance(sensitivity, (int, float))
            or not 1 <= sensitivity <= 350
        ):
            raise ValueError("Sensitivity must be between 1 and 350.")

        interval = settings.get("min_interval_ms", 120)
        if (
            isinstance(interval, bool)
            or not isinstance(interval, int)
            or not 50 <= interval <= 2000
        ):
            raise ValueError(
                "Minimum interval must be between 50 and 2000 ms."
            )

        weights = settings.get(
            "eq_weights",
            self.DEFAULT_GLOBAL_SETTINGS["eq_weights"],
        )

        if (
            not isinstance(weights, list)
            or len(weights) != 8
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not 0 <= value <= 1000
                for value in weights
            )
        ):
            raise ValueError(
                "Eight EQ weights between 0 and 1000 are required."
            )

        device_index = settings.get("device_index")

        if device_index is not None and (
            isinstance(device_index, bool)
            or not isinstance(device_index, int)
            or device_index < 0
        ):
            raise ValueError(
                "Audio device index must be empty or an integer >= 0."
            )

        return settings

    # --------------------------------------------------------
    # Start / stop / state
    # --------------------------------------------------------

    def start(self, sequence_id):
        sequence = self.load_sequence(sequence_id)
        effective_settings = self.get_effective_settings(sequence)

        self.active_sequence = sequence["id"]
        self.running = True
        self.error = None

        return {
            "sequence": sequence,
            "settings": effective_settings,
            "reaction": deepcopy(sequence["reaction"]),
        }

    def stop(self):
        self.running = False
        self.active_sequence = None
        return self.get_state()

    def get_state(self):
        return {
            "running": self.running,
            "active_sequence": self.active_sequence,
            "error": self.error,
        }

    # --------------------------------------------------------
    # JSON helper
    # --------------------------------------------------------

    @staticmethod
    def _write_json(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False,
            )
