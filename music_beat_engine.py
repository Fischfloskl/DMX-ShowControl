
import threading
import time
from collections import deque
from statistics import median

import numpy as np
import aubio


DEFAULT_EQ_WEIGHTS = [180, 300, 200, 80, 50, 40, 25, 15]

HOP_SIZE = 512
WIN_SIZE = 2048


class MusicBeatEngine:
    def __init__(self, audio_analyzer):
        self.audio_analyzer = audio_analyzer

        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread = None

        self._config = {
            "source": "bass",
            "sensitivity": 150,
            "min_interval_ms": 120,
            "eq_weights": DEFAULT_EQ_WEIGHTS.copy(),
        }

        self._state = {
            "running": False,
            "beat_count": 0,
            "bpm": 0.0,
            "level": 0.0,
            "threshold": 0.0,
            "last_beat_at": None,
            "last_interval": None,
            "error": None,
        }

        self._intervals = deque(maxlen=8)

    def get_config(self):
        with self._lock:
            result = dict(self._config)
            result["eq_weights"] = self._config["eq_weights"].copy()
            return result

    def configure(self, values):
        with self._lock:
            if "source" in values:
                source = str(values["source"])

                allowed = {
                    "bass", "combined",
                    "band_1", "band_2", "band_3", "band_4",
                    "band_5", "band_6", "band_7", "band_8",
                }

                if source not in allowed:
                    raise ValueError("Ungültige EQ-Quelle.")

                self._config["source"] = source

            if "sensitivity" in values:
                self._config["sensitivity"] = max(
                    1, min(350, int(values["sensitivity"]))
                )

            if "min_interval_ms" in values:
                self._config["min_interval_ms"] = max(
                    10, min(2000, int(values["min_interval_ms"]))
                )

            if "eq_weights" in values:
                weights = values["eq_weights"]

                if not isinstance(weights, list) or len(weights) != 8:
                    raise ValueError(
                        "eq_weights muss genau acht Werte enthalten."
                    )

                self._config["eq_weights"] = [
                    max(0, min(350, int(value)))
                    for value in weights
                ]

    def get_state(self):
        with self._lock:
            return dict(self._state)

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return

            self._stop_event.clear()
            self._intervals.clear()

            self._state.update({
                "running": True,
                "beat_count": 0,
                "bpm": 0.0,
                "level": 0.0,
                "threshold": 0.0,
                "last_beat_at": None,
                "last_interval": None,
                "error": None,
            })

            self._thread = threading.Thread(
                target=self._run,
                name="MusicBeatEngine",
                daemon=True,
            )
            self._thread.start()

    def stop(self):
        self._stop_event.set()
        thread = self._thread

        if thread and thread.is_alive():
            thread.join(timeout=2.0)

        with self._lock:
            self._state["running"] = False

            if thread is None or not thread.is_alive():
                self._thread = None

    @staticmethod
    def _weighted_average(levels, weights):
        total_weight = sum(weights)

        if total_weight <= 0:
            return 0.0

        return sum(
            level * weight
            for level, weight in zip(levels, weights)
        ) / total_weight

    def _selected_level(self, audio_state, config):
        bands = list(audio_state.get("bands", [0.0] * 8)[:8])
        bands += [0.0] * (8 - len(bands))
        bands = [max(0.0, float(v)) for v in bands]

        weights = config["eq_weights"]
        source = config["source"]

        if source == "bass":
            return self._weighted_average(bands[:2], weights[:2])

        if source == "combined":
            return self._weighted_average(bands, weights)

        if source.startswith("band_"):
            index = int(source.split("_")[1]) - 1
            return bands[index] * weights[index] / 100.0

        return 0.0

    @staticmethod
    def _aubio_threshold(sensitivity):
        # Höhere Empfindlichkeit ergibt eine niedrigere
        # Onset-Schwelle. Der Wert wird auf einen stabilen
        # Bereich begrenzt.
        threshold = 0.30 * (100.0 / sensitivity) ** 0.5
        return max(0.05, min(0.8, threshold))

    def _run(self):
        try:
            while not self._stop_event.is_set():
                audio_state = self.audio_analyzer.get_state()

                if not audio_state.get("running"):
                    with self._lock:
                        self._state["error"] = (
                            "Audio-Capture ist nicht aktiv."
                        )
                    self._stop_event.wait(0.05)
                    continue

                sample_rate = audio_state.get("sample_rate")

                if not sample_rate:
                    self._stop_event.wait(0.02)
                    continue

                # Aubio-Objekte müssen zur Samplerate der
                # aktiven Audioquelle passen.
                onset_detector = aubio.onset(
                    "default", WIN_SIZE, HOP_SIZE, int(sample_rate)
                )
                tempo_detector = aubio.tempo(
                    "default", WIN_SIZE, HOP_SIZE, int(sample_rate)
                )

                pending = np.empty(0, dtype=np.float32)
                last_beat = 0.0
                last_audio_update = None
                last_level_update = 0.0
                current_threshold = 0.30

                with self._lock:
                    current_threshold = self._aubio_threshold(
                        self._config["sensitivity"]
                    )

                onset_detector.set_threshold(current_threshold)

                while not self._stop_event.is_set():
                    audio_state = self.audio_analyzer.get_state()

                    if not audio_state.get("running"):
                        with self._lock:
                            self._state["error"] = (
                                "Audio-Capture ist nicht aktiv."
                            )
                        self._stop_event.wait(0.02)
                        continue

                    # Konfiguration lesen.
                    with self._lock:
                        config = {
                            **self._config,
                            "eq_weights": self._config[
                                "eq_weights"
                            ].copy(),
                        }

                    # EQ-Pegel für die Anzeige aktualisieren.
                    updated_at = audio_state.get("updated_at")

                    if (
                        updated_at is not None
                        and updated_at != last_audio_update
                    ):
                        level = self._selected_level(
                            audio_state, config
                        )

                        with self._lock:
                            self._state["level"] = round(level, 5)

                        last_audio_update = updated_at
                        last_level_update = time.monotonic()

                    # Empfindlichkeit dynamisch aktualisieren.
                    threshold = self._aubio_threshold(
                        config["sensitivity"]
                    )

                    if threshold != current_threshold:
                        onset_detector.set_threshold(threshold)
                        current_threshold = threshold

                    with self._lock:
                        self._state["threshold"] = round(
                            current_threshold, 4
                        )
                        self._state["error"] = None

                    # Neue Mono-Audiosamples abholen.
                    chunk = self.audio_analyzer.get_raw_audio_chunk(
                        timeout=0.05
                    )

                    if chunk is None:
                        # Veraltete Pegel nicht als aktuell anzeigen.
                        if (
                            last_level_update
                            and time.monotonic() - last_level_update > 1.0
                        ):
                            with self._lock:
                                self._state["error"] = (
                                    "Keine neuen Audiodaten. "
                                    "Bitte Audio-Capture prüfen."
                                )
                        continue

                    chunk = np.asarray(chunk, dtype=np.float32)

                    if chunk.size == 0:
                        continue

                    pending = np.concatenate((pending, chunk))

                    # Aubio erwartet jeweils HOP_SIZE Samples.
                    while (
                        pending.size >= HOP_SIZE
                        and not self._stop_event.is_set()
                    ):
                        samples = pending[:HOP_SIZE]
                        pending = pending[HOP_SIZE:]

                        onset_result = onset_detector(samples)
                        tempo_detector(samples)

                        is_onset = bool(float(onset_result[0]) > 0.0)
                        now = time.monotonic()

                        # Onsets als schnelle Ereignisse für die
                        # Lichtreaktion zählen; Mindestabstand beachten.
                        min_interval = (
                            config["min_interval_ms"] / 1000.0
                        )

                        if (
                            is_onset
                            and now - last_beat >= min_interval
                        ):
                            interval = (
                                now - last_beat if last_beat else None
                            )
                            last_beat = now

                            with self._lock:
                                self._state["beat_count"] += 1
                                self._state["last_beat_at"] = time.time()

                                if interval is not None:
                                    self._state["last_interval"] = round(
                                        interval, 4
                                    )

                                    if 0.25 <= interval <= 2.0:
                                        self._intervals.append(interval)

                                # Aubio liefert seine eigene
                                # laufende Tempo-Schätzung.
                                bpm = float(tempo_detector.get_bpm())

                                if 30.0 <= bpm <= 240.0:
                                    self._state["bpm"] = round(bpm, 1)

        except Exception as exc:
            with self._lock:
                self._state["error"] = str(exc)

        finally:
            with self._lock:
                self._state["running"] = False
