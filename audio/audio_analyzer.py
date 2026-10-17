
import queue
import threading
import time

import numpy as np
import pyaudiowpatch as pyaudio


EQ_BANDS = [
    (30, 90),
    (90, 180),
    (180, 350),
    (350, 700),
    (700, 1400),
    (1400, 2800),
    (2800, 6000),
    (6000, 12000),
]


class AudioAnalyzer:
    """Live-Audioanalyse des Windows-Audioausgangs via WASAPI Loopback."""

    def __init__(self):
        self._lock = threading.RLock()
        self._audio = None
        self._stream = None
        self._worker = None
        self._stop_event = threading.Event()
        self._queue = queue.Queue(maxsize=3)
        self._raw_queue = queue.Queue(maxsize=32)

        self._state = {
            "running": False,
            "device_index": None,
            "device_name": None,
            "sample_rate": None,
            "rms": 0.0,
            "peak": 0.0,
            "bass": 0.0,
            "mid": 0.0,
            "treble": 0.0,
            "bands": [0.0] * 8,
            "error": None,
            "updated_at": None,
        }

    @staticmethod
    def list_devices():
        audio = pyaudio.PyAudio()
        try:
            return [
                {
                    "index": int(info["index"]),
                    "name": str(info["name"]),
                    "sample_rate": int(info["defaultSampleRate"]),
                    "channels": int(info["maxInputChannels"]),
                }
                for info in audio.get_loopback_device_info_generator()
            ]
        finally:
            audio.terminate()

    def get_state(self):
        with self._lock:
            return dict(
                self._state,
                bands=list(self._state["bands"]),
            )

    def get_raw_audio_chunk(self, timeout=0.1):
        """Liefert einen Mono-Audio-Block als float32-Samples."""
        try:
            return self._raw_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def start(self, device_index):
        self.stop()

        with self._lock:
            self._stop_event.clear()
            self._queue = queue.Queue(maxsize=3)
            self._raw_queue = queue.Queue(maxsize=32)

            try:
                self._audio = pyaudio.PyAudio()
                info = self._audio.get_device_info_by_index(
                    int(device_index)
                )

                channels = min(2, int(info["maxInputChannels"]))
                if channels < 1:
                    raise ValueError(
                        "Das Gerät besitzt keine Eingangskanäle."
                    )

                sample_rate = int(info["defaultSampleRate"])

                self._state.update({
                    "running": False,
                    "device_index": int(device_index),
                    "device_name": str(info["name"]),
                    "sample_rate": sample_rate,
                    "rms": 0.0,
                    "peak": 0.0,
                    "bass": 0.0,
                    "mid": 0.0,
                    "treble": 0.0,
                    "bands": [0.0] * 8,
                    "error": None,
                    "updated_at": None,
                })

                def callback(in_data, frame_count, time_info, status_flags):
                    if not self._stop_event.is_set():
                        try:
                            self._queue.put_nowait(in_data)
                        except queue.Full:
                            try:
                                self._queue.get_nowait()
                            except queue.Empty:
                                pass
                            try:
                                self._queue.put_nowait(in_data)
                            except queue.Full:
                                pass

                    return (None, pyaudio.paContinue)

                self._stream = self._audio.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=sample_rate,
                    input=True,
                    input_device_index=int(device_index),
                    frames_per_buffer=4096,
                    stream_callback=callback,
                )

                self._worker = threading.Thread(
                    target=self._analysis_loop,
                    args=(sample_rate, channels),
                    name="AudioAnalysis",
                    daemon=True,
                )

                self._worker.start()
                self._stream.start_stream()
                self._state["running"] = True

            except Exception as exc:
                self._state["running"] = False
                self._state["error"] = str(exc)
                self._stop_event.set()
                self._close_resources()
                raise

    @staticmethod
    def _band_level(spectrum, frequencies, low, high, sample_count):
        high = min(high, frequencies[-1])

        mask = (frequencies >= low) & (frequencies < high)
        if not np.any(mask):
            return 0.0

        # FFT-Amplitude auf eine gut nutzbare 0..1-Skala bringen.
        magnitude = float(np.sqrt(np.mean(spectrum[mask] ** 2)))
        return float(np.clip(magnitude * 40.0 / sample_count, 0.0, 1.0))

    def _analysis_loop(self, sample_rate, channels):
        try:
            while not self._stop_event.is_set():
                try:
                    data = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                samples = np.frombuffer(data, dtype=np.int16)

                if channels > 1:
                    samples = samples.reshape(-1, channels).astype(
                        np.float32
                    ).mean(axis=1)

                samples = samples.astype(np.float32) / 32768.0
                if samples.size == 0:
                    continue

                # Mono-Rohdaten für MusicBeatEngine bereitstellen.
                raw_samples = samples.copy()

                try:
                    self._raw_queue.put_nowait(raw_samples)
                except queue.Full:
                    try:
                        self._raw_queue.get_nowait()
                    except queue.Empty:
                        pass

                    try:
                        self._raw_queue.put_nowait(raw_samples)
                    except queue.Full:
                        pass

                rms = float(np.sqrt(np.mean(samples * samples)))
                peak = float(np.max(np.abs(samples)))

                windowed = samples * np.hanning(samples.size)
                spectrum = np.abs(np.fft.rfft(windowed))
                frequencies = np.fft.rfftfreq(
                    samples.size,
                    d=1.0 / sample_rate,
                )

                bands = [
                    self._band_level(
                        spectrum, frequencies, low, high, samples.size
                    )
                    for low, high in EQ_BANDS
                ]

                bass = max(bands[0], bands[1])
                mid = max(bands[2:6])
                treble = max(bands[6:8])

                with self._lock:
                    self._state.update({
                        "rms": round(rms, 5),
                        "peak": round(peak, 5),
                        "bass": round(bass, 5),
                        "mid": round(mid, 5),
                        "treble": round(treble, 5),
                        "bands": [round(value, 5) for value in bands],
                        "updated_at": time.time(),
                        "error": None,
                    })

        except Exception as exc:
            with self._lock:
                self._state["error"] = str(exc)

    def _close_resources(self):
        stream, audio = self._stream, self._audio
        self._stream = None
        self._audio = None

        if stream is not None:
            try:
                if stream.is_active():
                    stream.stop_stream()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass

        if audio is not None:
            try:
                audio.terminate()
            except Exception:
                pass

    def stop(self):
        self._stop_event.set()

        with self._lock:
            stream = self._stream
            worker = self._worker

            if stream is not None:
                try:
                    if stream.is_active():
                        stream.stop_stream()
                except Exception:
                    pass

        if worker is not None and worker.is_alive():
            worker.join(timeout=1.0)

        with self._lock:
            self._close_resources()
            self._worker = None
            self._state["running"] = False
