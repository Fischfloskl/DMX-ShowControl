import json
import os
import copy
import threading
import time


STROBE_LIST_FILE = "data/strobes.json"


DEFAULT_STROBES = {
    "type": "strobes",
    "version": 1,
    "data": []
}


class StrobeManager:

    def __init__(
        self,
        scene_manager,
        fade_manager,
        fade_engine,
        dmx_manager
    ):

        self.scene_manager = scene_manager
        self.fade_manager = fade_manager
        self.fade_engine = fade_engine
        self.dmx_manager = dmx_manager

        self.strobes = []

        # Laufender Strobe
        self.running = False
        self.thread = None
        self.current_strobe = None

        self.load()


    # -----------------------------------------
    # LOAD
    # -----------------------------------------

    def load(self):

        try:

            os.makedirs(
                os.path.dirname(STROBE_LIST_FILE),
                exist_ok=True
            )

            if not os.path.exists(
                STROBE_LIST_FILE
            ):

                print(
                    "Strobe-Datei nicht gefunden. "
                    "Erstelle neue Datei."
                )

                self.strobes = []

                self.save()

                return


            with open(
                STROBE_LIST_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                content = json.load(f)


            # Altes Format: direkte Liste

            if isinstance(
                content,
                list
            ):

                self.strobes = content

                print(
                    "Altes Strobe-Format erkannt. "
                    "Konvertiere..."
                )

                self.save()

                return


            # Neues Format

            if not isinstance(
                content,
                dict
            ):

                raise ValueError(
                    "Ungültiges Strobe-Dateiformat."
                )


            if content.get(
                "type"
            ) != "strobes":

                raise ValueError(
                    "Ungültiger Dateityp."
                )


            self.strobes = content.get(
                "data",
                []
            )


            if not isinstance(
                self.strobes,
                list
            ):

                raise ValueError(
                    "Strobe-Daten müssen eine Liste sein."
                )


        except Exception as e:

            print(
                "Fehler beim Laden der Strobes:",
                e
            )

            print(
                "Erstelle neue Strobe-Datei."
            )

            self.strobes = []

            self.save()


    # -----------------------------------------
    # SAVE
    # -----------------------------------------

    def save(self):

        os.makedirs(
            os.path.dirname(STROBE_LIST_FILE),
            exist_ok=True
        )

        content = {
            "type": "strobes",
            "version": 1,
            "data": self.strobes
        }

        with open(
            STROBE_LIST_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                content,
                f,
                indent=4,
                ensure_ascii=False
            )


    # -----------------------------------------
    # GET
    # -----------------------------------------

    def get_id(self, strobe_id):

        for strobe in self.strobes:

            if int(
                strobe.get("id", -1)
            ) == int(strobe_id):

                return strobe

        return None


    def get_next_id(self):

        if not self.strobes:
            return 1

        return max(
            int(strobe.get("id", 0))
            for strobe in self.strobes
        ) + 1


    # -----------------------------------------
    # ADD
    # -----------------------------------------

    def add(self, strobe):

        if "id" not in strobe:

            strobe["id"] = (
                self.get_next_id()
            )

        self.strobes.append(
            strobe
        )

        self.save()

        return strobe


    # -----------------------------------------
    # DELETE
    # -----------------------------------------

    def delete(self, strobe_id):

        strobe = self.get_id(
            strobe_id
        )

        if not strobe:
            return False

        # Falls dieser Strobe gerade läuft
        if self.current_strobe is strobe:
            self.stop()

        self.strobes.remove(
            strobe
        )

        self.save()

        return True


    # -----------------------------------------
    # DUPLICATE
    # -----------------------------------------

    def duplicate(self, strobe_id):

        strobe = self.get_id(
            strobe_id
        )

        if not strobe:
            return None

        new_strobe = copy.deepcopy(
            strobe
        )

        new_strobe["id"] = (
            self.get_next_id()
        )

        new_strobe["name"] = (
            strobe.get(
                "name",
                "Strobe"
            )
            + " Kopie"
        )

        self.strobes.append(
            new_strobe
        )

        self.save()

        return new_strobe


    # -----------------------------------------
    # START
    # -----------------------------------------

    def start(self, strobe):

        if not strobe:
            return False

        # Alten Strobe beenden
        self.stop(
            clear=False
        )

        self.current_strobe = strobe
        self.running = True

        self.thread = threading.Thread(
            target=self._run,
            daemon=True
        )

        self.thread.start()

        print(
            "Strobe gestartet:",
            strobe.get("name")
        )

        return True


    # -----------------------------------------
    # STOP
    # -----------------------------------------

    def stop(self, clear=True):

        self.running = False

        self.current_strobe = None

        if clear:

            self.dmx_manager.clear()

        print(
            "Strobe gestoppt"
        )


    # -----------------------------------------
    # RUN
    # -----------------------------------------

    def _run(self):

        strobe = self.current_strobe

        if not strobe:
            return

        mode = strobe.get(
            "mode",
            "timed"
        )

        cycles = max(
            1,
            int(
                strobe.get(
                    "cycles",
                    1
                )
            )
        )

        duration = max(
            1,
            int(
                strobe.get(
                    "time",
                    1000
                )
            )
        ) / 1000

        time_a = max(
            1,
            int(
                strobe.get(
                    "time_a",
                    100
                )
            )
        ) / 1000

        time_b = max(
            1,
            int(
                strobe.get(
                    "time_b",
                    100
                )
            )
        ) / 1000

        states = strobe.get(
            "states",
            []
        )

        if not states:

            print(
                "Strobe enthält keine Zustände."
            )

            self.running = False
            self.current_strobe = None

            return

        # ---------------------------------
        # COUNTED
        # ---------------------------------

        if mode == "counted":

            for cycle in range(cycles):

                if not self.running:
                    return

                for index, state in enumerate(states):

                    if not self.running:
                        return

                    self._apply_state(
                        state
                    )

                    if index % 2 == 0:
                        delay = time_a
                    else:
                        delay = time_b

                    if not self._wait(delay):
                        return

        # ---------------------------------
        # TIMED
        # ---------------------------------

        elif mode == "timed":

            end_time = (
                time.perf_counter()
                + duration
            )

            cycle = 0

            while self.running:

                for index, state in enumerate(states):

                    if not self.running:
                        return

                    # Zeit bereits vorbei?
                    remaining = (
                        end_time
                        - time.perf_counter()
                    )

                    if remaining <= 0:
                        break

                    # Zustand anwenden
                    self._apply_state(
                        state
                    )

                    # A / B
                    if index % 2 == 0:
                        delay = time_a
                    else:
                        delay = time_b

                    # Nicht über die Gesamtzeit hinauslaufen
                    delay = min(
                        delay,
                        max(
                            0,
                            end_time
                            - time.perf_counter()
                        )
                    )

                    if delay <= 0:
                        break

                    if not self._wait(delay):
                        return

                else:
                    # Alle States dieser Runde wurden
                    # vollständig ausgeführt.
                    cycle += 1
                    continue

                # Schleife wurde wegen Zeitende verlassen
                break

        else:

            print(
                "Unbekannter Strobe-Modus:",
                mode
            )

        # ---------------------------------
        # Fertig
        # ---------------------------------

        self.running = False
        self.current_strobe = None

        print(
            "Strobe beendet"
        )


    # -----------------------------------------
    # STATE
    # -----------------------------------------

    def _apply_state(self, state):

        state_type = state.get(
            "type"
        )

        state_id = state.get(
            "target"
        )


        # ---------------------------------
        # Szene
        # ---------------------------------

        if state_type == "scene":

            scene = self.scene_manager.get_id(
                int(state_id)
            )

            if not scene:

                print(
                    "Strobe: Szene nicht gefunden:",
                    state_id
                )

                return


            print(
                "Strobe Szene:",
                scene.get("name")
            )

            self.dmx_manager.apply_scene(
                scene
            )


        # ---------------------------------
        # Fade
        # ---------------------------------

        elif state_type == "fade":

            fade = self.fade_manager.get_id(
                int(state_id)
            )

            if not fade:

                print(
                    "Strobe: Fade nicht gefunden:",
                    state_id
                )

                return


            print(
                "Strobe Fade:",
                fade.get("name")
            )

            self.fade_engine.play(
                fade
            )


        else:

            print(
                "Unbekannter Strobe-State:",
                state_type
            )


    # -----------------------------------------
    # WAIT
    # -----------------------------------------

    def change_mode(self, strobe_id, mode):

        if not strobe_id:
            print(
                "Keine ID übergeben --> Strobes-change-mode"
            )
            return False

        strobe = self.get_id(
            strobe_id
        )

        if not strobe:
            return False

        if mode not in (
            "timed",
            "counted"
        ):
            return False

        strobe["mode"] = mode

        self.save()

        return True

    def _wait(self, duration):

        end = time.perf_counter() + duration

        while self.running:

            remaining = (
                end - time.perf_counter()
            )

            if remaining <= 0:
                return True

            time.sleep(
                min(
                    0.01,
                    remaining
                )
            )

        return False