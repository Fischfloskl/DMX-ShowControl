
import threading

import mido


class MidiManager:
    """Verwaltet MIDI-Eingänge und das Einlernen von Referenznoten."""

    def __init__(self, on_message=None):
        self.on_message = on_message
        self.port = None
        self.port_name = None

        self.lock = threading.RLock()
        self.learn_lock = threading.Lock()

        self.learn_target = None
        self.learned_note = None

    @staticmethod
    def get_input_names():
        try:
            return mido.get_input_names()
        except Exception as exc:
            print(f"[MIDI] Eingänge konnten nicht geladen werden: {exc}")
            return []

    def connect(self, port_name):
        with self.lock:
            self._disconnect()

            if not port_name:
                print("[MIDI] Kein Eingang ausgewählt.")
                return False

            try:
                if port_name not in mido.get_input_names():
                    print(f"[MIDI] Port nicht gefunden: {port_name}")
                    return False

                self.port = mido.open_input(
                    port_name,
                    callback=self._handle_message
                )
                self.port_name = port_name

                print(f"[MIDI] Verbunden: {port_name}")
                return True

            except Exception as exc:
                self.port = None
                self.port_name = None
                print(f"[MIDI] Verbindung fehlgeschlagen: {exc}")
                return False

    def disconnect(self):
        with self.lock:
            self._disconnect()

    def _disconnect(self):
        if self.port is not None:
            try:
                self.port.close()
            except Exception as exc:
                print(f"[MIDI] Fehler beim Schliessen: {exc}")

        self.port = None
        self.port_name = None

    def start_learning(self, target):
        if target not in ("highest", "lowest"):
            raise ValueError("Ungültiges MIDI-Lernziel")

        with self.learn_lock:
            self.learn_target = target
            self.learned_target = None
            self.learned_note = None

        print(f"[MIDI] Lerne jetzt die {'höchste' if target == 'highest' else 'tiefste'} Note.")

    
    def get_learning_status(self):
        with self.learn_lock:
            return {
                "target": self.learn_target,
                "learned_note": self.learned_note,
                "waiting": self.learn_target is not None,
                "learned_target": self.learned_target
            }


    def cancel_learning(self):
        with self.learn_lock:
            self.learn_target = None
            self.learned_note = None

    def _handle_message(self, message):
        # Für das Lernen nur echte Note-On-Nachrichten verwenden.
        if message.type == "note_on" and message.velocity > 0:
            with self.learn_lock:
                if self.learn_target is not None:
                    self.learned_note = int(message.note)
                    self.learned_target = self.learn_target
                    self.learn_target = None

                    print(
                        f"[MIDI] Referenznote gelernt: "
                        f"{self.learned_note}"
                    )
                    return

        print(f"[MIDI] {message}")

        if self.on_message is not None:
            try:
                self.on_message(message)
            except Exception as exc:
                print(f"[MIDI] Fehler bei der Verarbeitung: {exc}")

    def close(self):
        self.cancel_learning()
        self.disconnect()
