
import json
import re
from pathlib import Path
from copy import deepcopy


class AudioSequenceManager:
    """
    Verwaltet Audio-Sequences (.dmxaudio) und globale Audio-Einstellungen.

    Globale Einstellungen gelten standardmässig für alle Sequences.
    Einzelne Sequences können diese Einstellungen überschreiben.
    """

    SEQUENCE_EXTENSION = ".dmxaudio"

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

    def __init__(
        self,
        sequence_directory="data/audio_sequences",
        settings_file="data/audio_settings.json",
    ):
        self.sequence_directory = Path(sequence_directory)
        self.settings_file = Path(settings_file)

        self.sequence_directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.settings_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.global_settings = self._load_global_settings()

        self.active_sequence = None
        self.running = False
        self.error = None

    # --------------------------------------------------------
    # Globale Einstellungen
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

            return settings

        except (OSError, json.JSONDecodeError) as exc:
            self.error = f"Globale Audio-Einstellungen konnten nicht geladen werden: {exc}"
            return deepcopy(self.DEFAULT_GLOBAL_SETTINGS)

    def get_global_settings(self):
        return deepcopy(self.global_settings)

    def save_global_settings(self, settings):
        if not isinstance(settings, dict):
            raise ValueError("Die Einstellungen müssen ein Dictionary sein.")

        updated = deepcopy(self.DEFAULT_GLOBAL_SETTINGS)
        updated.update(settings)
        self._validate_settings(updated)

        self._write_json(self.settings_file, updated)
        self.global_settings = updated

        return self.get_global_settings()

    # --------------------------------------------------------
    # Audio-Sequence-Dateien
    # --------------------------------------------------------

    @staticmethod
    def _safe_name(name):
        name = str(name).strip()

        if not name or name in {".", ".."}:
            raise ValueError("Bitte einen gültigen Sequence-Namen eingeben.")

        if not re.fullmatch(r"[\w äöüÄÖÜß.-]+", name, flags=re.UNICODE):
            raise ValueError(
                "Der Name darf nur Buchstaben, Zahlen, Leerzeichen, "
                "Bindestriche, Punkte und Unterstriche enthalten."
            )

        return name

    def _sequence_path(self, name):
        safe_name = self._safe_name(name)
        path = (self.sequence_directory / f"{safe_name}{self.SEQUENCE_EXTENSION}").resolve()

        if path.parent != self.sequence_directory.resolve():
            raise ValueError("Ungültiger Dateipfad.")

        return path

    def list_sequences(self):
        sequences = []

        for path in sorted(self.sequence_directory.glob(f"*{self.SEQUENCE_EXTENSION}")):
            try:
                with path.open("r", encoding="utf-8") as file:
                    data = json.load(file)

                sequences.append({
                    "name": data.get("name", path.stem),
                    "description": data.get("description", ""),
                    "file": path.name,
                })

            except (OSError, json.JSONDecodeError):
                sequences.append({
                    "name": path.stem,
                    "description": "Fehlerhafte Sequence-Datei",
                    "file": path.name,
                    "error": True,
                })

        return sequences

    def create_sequence(self, name, description=""):
        name = self._safe_name(name)
        path = self._sequence_path(name)

        if path.exists():
            raise ValueError(f"Die Audio-Sequence '{name}' existiert bereits.")

        sequence = {
            "version": 1,
            "name": name,
            "description": str(description).strip(),
            "use_global_settings": True,
            "overrides": {},
            "reaction": deepcopy(self.DEFAULT_REACTION_SETTINGS),
        }

        self.save_sequence(name, sequence)
        return sequence

    def load_sequence(self, name):
        path = self._sequence_path(name)

        if not path.exists():
            raise FileNotFoundError(f"Audio-Sequence '{name}' wurde nicht gefunden.")

        with path.open("r", encoding="utf-8") as file:
            sequence = json.load(file)

        if not isinstance(sequence, dict):
            raise ValueError("Die Audio-Sequence enthält ungültige Daten.")

        sequence.setdefault("version", 1)
        sequence.setdefault("name", path.stem)
        sequence.setdefault("description", "")
        sequence.setdefault("use_global_settings", True)
        sequence.setdefault("overrides", {})
        sequence.setdefault(
            "reaction",
            deepcopy(self.DEFAULT_REACTION_SETTINGS),
        )

        return sequence

        
    def save_sequence(self, name, data):
        name = self._safe_name(name)

        if not isinstance(data, dict):
            raise ValueError("Sequence data must be a dictionary.")

        # Load an existing sequence if available.
        # A missing file means that a new sequence is being created.
        try:
            existing = self.load_sequence(name)
        except FileNotFoundError:
            existing = {
                "name": name,
                "overrides": {},
                "reaction": {},
                "actions": [],
                "every_beats": 1,
            }

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

        # Validate audio settings against the global settings.
        effective_settings = self.get_global_settings()
        effective_settings.update(overrides)

        validated_settings = self._validate_settings(effective_settings)

        # Store only explicitly overridden settings.
        validated_overrides = {
            key: validated_settings[key]
            for key in overrides
            if key in validated_settings
        }

        sequence = {
            "version": data.get("version", existing.get("version", 1)),
            "name": name,
            "use_global_settings": data.get(
                "use_global_settings",
                existing.get("use_global_settings", False),
            ),
            "overrides": validated_overrides,
            "reaction": reaction,
            "every_beats": every_beats,
            "actions": actions,
        }

        self._write_json(self._sequence_path(name), sequence)
        return sequence


    def delete_sequence(self, name):
        path = self._sequence_path(name)

        if not path.exists():
            raise FileNotFoundError(f"Audio-Sequence '{name}' wurde nicht gefunden.")

        if self.active_sequence == name and self.running:
            raise ValueError("Eine aktive Audio-Sequence kann nicht gelöscht werden.")

        path.unlink()
        return True

    # --------------------------------------------------------
    # Effektive Einstellungen
    # --------------------------------------------------------

    def get_effective_settings(self, sequence):
        if not isinstance(sequence, dict):
            raise ValueError("Ungültige Audio-Sequence.")

        if sequence.get("use_global_settings", True):
            settings = self.get_global_settings()
        else:
            settings = deepcopy(self.DEFAULT_GLOBAL_SETTINGS)

        overrides = sequence.get("overrides", {})
        if not isinstance(overrides, dict):
            raise ValueError("'overrides' muss ein Dictionary sein.")

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
            raise ValueError("Ungültige Audioquelle für die Beat-Erkennung.")

        sensitivity = settings.get("sensitivity", 150)
        if not isinstance(sensitivity, (int, float)) or not 1 <= sensitivity <= 350:
            raise ValueError("Die Empfindlichkeit muss zwischen 1 und 350 liegen.")

        interval = settings.get("min_interval_ms", 120)
        if not isinstance(interval, int) or not 50 <= interval <= 2000:
            raise ValueError("Der Mindestabstand muss zwischen 50 und 2000 ms liegen.")

        weights = settings.get("eq_weights", self.DEFAULT_GLOBAL_SETTINGS["eq_weights"])
        if (
            not isinstance(weights, list)
            or len(weights) != 8
            or any(not isinstance(value, (int, float)) or not 0 <= value <= 1000
                   for value in weights)
        ):
            raise ValueError("Es werden acht EQ-Gewichte zwischen 0 und 1000 benötigt.")

        device_index = settings.get("device_index")
        if device_index is not None and (
            not isinstance(device_index, int) or device_index < 0
        ):
            raise ValueError("Der Audio-Geräteindex muss leer oder eine Zahl ab 0 sein.")

        return settings

    # --------------------------------------------------------
    # Start / Stopp
    # --------------------------------------------------------

    def start(self, name):
        sequence = self.load_sequence(name)

        # Vor dem Aktivieren sicherstellen, dass die Einstellungen gültig sind.
        effective_settings = self.get_effective_settings(sequence)

        self.active_sequence = sequence["name"]
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
    # Datei-Hilfsfunktion
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
