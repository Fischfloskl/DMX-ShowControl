import threading
import time
import keyboard

class TriggerEngine:


    def __init__(
        self,
        trigger_manager,
        scene_manager,
        sequence_manager,
        dmx_manager,
        fade_manager,
        fade_engine,
        settings,
        show_controller,
        strobe_manager,
        socketio
    ):

        self.trigger_manager = trigger_manager
        self.scene_manager = scene_manager
        self.sequence_manager = sequence_manager
        self.dmx_manager = dmx_manager
        self.settings = settings
        self.fade_manager = fade_manager
        self.fade_engine = fade_engine
        self.show_controller = show_controller
        self.strobe_manager = strobe_manager
        self.socket = socketio

        self.running = False
        self.thread = None

        self.timing_running = False
        self.timing_start = 0
        self.timing_elapsed = 0
        self.last_trigger_time = None

        self.active_keys = set()



    def start(self):

        if self.running:
            return


        self.running = True

        print("TriggerEngine gestartet")


        self.thread = threading.Thread(
            target=self._loop,
            daemon=True
        )


        self.thread.start()



    def stop(self):

        self.running = False



    def _loop(self):

        while self.running:

            try:
                self.update()

            except Exception as e:
                print("!!! FEHLER IM TRIGGER-THREAD !!!")
                print(type(e).__name__, e)

            time.sleep(0.02)



    def update(self):

        # Keine Trigger im Edit Mode
        if self.settings.get("mode") != "show":

            self.active_keys.clear()

            self.timing_running = False
            self.timing_start = 0
            return


        for trigger in self.trigger_manager.triggers:


            if not trigger.get(
                "enabled",
                True
            ):
                continue



            if trigger.get(
                "type"
            ) != "keyboard":

                continue



            keys = trigger.get(
                "keys",
                []
            )


            if not keys:
                continue



            pressed = all(
                keyboard.is_pressed(key)
                for key in keys
            )


            trigger_id = trigger.get(
                "id"
            )



            # Taste gerade gedrückt

            if pressed:


                if trigger_id not in self.active_keys:


                    self.active_keys.add(
                        trigger_id
                    )


                    self.execute(
                        trigger
                    )



            # Taste losgelassen

            else:


                self.active_keys.discard(
                    trigger_id
                )

        # -------------------
        # Timing Trigger
        # -------------------

        if self.settings.get("mode") != "show":
            self.active_keys.discard("timing")

        else:

            record_key = self.settings.get_timing_global_playkey()

            if record_key:

                pressed = keyboard.is_pressed(
                    record_key
                )

                if pressed:

                    if "timing" not in self.active_keys:

                        self.active_keys.add(
                            "timing"
                        )

                        self.execute_timing()

                else:

                    self.active_keys.discard(
                        "timing"
                    )





    def execute(self, trigger):

        self.update_timing()

        print(
            "Trigger:",
            trigger.get("name")
        )

         # Alles vom vorherigen Trigger stoppen
        #self.show_controller.stop_all()
        #self.show_controller.reset()

        for action in trigger.get(
            "actions",
            []
        ):


            action_type = action.get(
                "type"
            )



            # -------------------
            # Szene
            # -------------------

            if action_type == "scene":


                scene = self.scene_manager.get(
                    action.get("target")
                )


                if scene:


                    print(
                        "Scene:",
                        scene["name"]
                    )

                    self.show_controller.stop_all()
                    self.show_controller.reset()

                    self.dmx_manager.apply_scene(
                        scene
                    )

                    #self.show_controller.reset()
                    

            if action["type"] == "fade":

                fade = self.fade_manager.get(
                    action["target"]
                )


                if fade:
                    self.show_controller.stop_all()
                    self.show_controller.reset()
                    self.fade_engine.play(
                        fade
                    )
                    #self.show_controller.reset()

            # -------------------
            # Strobe
            # -------------------

            if action_type == "strobe":

                strobe = self.strobe_manager.get_id(
                    action.get("target")
                )

                if strobe:

                    print(
                        "Strobe:",
                        strobe["name"]
                    )
                    self.show_controller.stop_all()
                    self.show_controller.reset()
                    self.strobe_manager.start(
                        strobe
                    )

            # -------------------
            # Sequenz
            # -------------------

            if action_type == "sequence":


                sequence = self.sequence_manager.get(
                    action.get("target")
                )


                if sequence:


                    print(
                        "Sequence:",
                        sequence["name"]
                    )

                    self.show_controller.stop_all()
                    self.show_controller.reset()
                    self.sequence_manager.start(
                        sequence
                    )
                    #self.show_controller.reset()


            # -------------------
            # Keyboard Ausgabe
            # -------------------

            if action_type == "keyboard":
                # Holt die Liste der Tasten aus der Action (z.B. ["Control", "Shift", "MediaPlayPause"])
                keys = action.get("keys", [])

                # Erweitertes Dictionary für Modifikatoren und Sondertasten
                JS_TO_PYTHON_KEYS = {
                    # Medientasten
                    "MediaPlayPause": "play/pause media",
                    "MediaTrackNext": "next track",
                    "MediaTrackPrevious": "previous track",
                    "MediaStop": "stop media",
                    "AudioVolumeUp": "volume up",
                    "AudioVolumeDown": "volume down",
                    "AudioVolumeMute": "volume mute",
                    
                    # Modifikatoren (wichtig für Tastenkombis)
                    "Control": "ctrl",
                    "Shift": "shift",
                    "Alt": "alt",
                    "Meta": "windows",
                    
                    # Navigation & Pfeile
                    "Enter": "enter",
                    "Escape": "esc",
                    "ArrowUp": "up",
                    "ArrowDown": "down",
                    "ArrowLeft": "left",
                    "ArrowRight": "right",
                    "Backspace": "backspace",
                    "Tab": "tab",
                    "Space": "space",

                    #alles in kleinbuschstaben:

                    # Medientasten
                    "mediaplaypause": "play/pause media",
                    "mediatracknext": "next track",
                    "mediatrackprevious": "previous track",
                    "mediastop": "stop media",
                    "audiovolumeup": "volume up",
                    "audiovolumedown": "volume down",
                    "audiovolumemute": "volume mute",
                    
                    # Modifikatoren (wichtig für Tastenkombis)
                    "control": "ctrl",
                    "shift": "shift",
                    "alt": "alt",
                    "meta": "windows",
                    
                    # Navigation & Pfeile
                    "enter": "enter",
                    "escape": "esc",
                    "arrowup": "up",
                    "arrowdown": "down",
                    "arrowleft": "left",
                    "arrowright": "right",
                    "backspace": "backspace",
                    "tab": "tab",
                    "space": "space"
                }

                # Übersetze jede einzelne Taste aus der Liste
                translated_keys = []
                for key in keys:
                    # Falls die Taste im Dict ist, nimm die Übersetzung. 
                    # Falls nicht, wandle sie in Kleinbuchstaben um (z.B. "C" -> "c")
                    translated_key = JS_TO_PYTHON_KEYS.get(key, key.lower())
                    translated_keys.append(translated_key)

                # Wenn Tasten vorhanden sind, verbinde sie mit einem "+" für keyboard.press_and_release
                if translated_keys:
                    # Erzeugt z.B. "ctrl+shift+play/pause media" oder "ctrl+c"
                    combination_string = "+".join(translated_keys)
                    
                    print("Keyboard Simulation Combo:", combination_string)
                    
                    try:
                        # Führt die gesamte Kombination gleichzeitig aus
                        keyboard.press_and_release(combination_string)
                    except Exception as e:
                        print(f"Fehler bei Keyboard-Simulation: {e}")


    def reset_timing(self):

        self.timing_running = False

        self.timing_start = 0

        self.timing_elapsed = 0

        self.last_trigger_time = None

        #self.socket.emit("timing_reset")
        print("Timing RESET")



    def update_timing(self):

        now = time.perf_counter()

        # Erster Trigger:
        # Nur Startpunkt setzen.
        if self.last_trigger_time is None:

            self.last_trigger_time = now

            print("Timing START")

            return


        # Zeit seit dem letzten Trigger
        self.timing_elapsed = (
            now - self.last_trigger_time
        )

        # Neuer Startpunkt für den nächsten Abstand
        self.last_trigger_time = now


        print(
            f"Timing: "
            f"{self.timing_elapsed:.3f} s"
        )



    def simulate_keyboard(self, keys):
        JS_TO_PYTHON_KEYS = {

            "MediaPlayPause": "play/pause media",
            "MediaTrackNext": "next track",
            "MediaTrackPrevious": "previous track",
            "MediaStop": "stop media",
            "AudioVolumeUp": "volume up",
            "AudioVolumeDown": "volume down",
            "AudioVolumeMute": "volume mute",

            "Control": "ctrl",
            "Shift": "shift",
            "Alt": "alt",
            "Meta": "windows",

            "Enter": "enter",
            "Escape": "esc",
            "ArrowUp": "up",
            "ArrowDown": "down",
            "ArrowLeft": "left",
            "ArrowRight": "right",
            "Backspace": "backspace",
            "Tab": "tab",
            "Space": "space",

            "mediaplaypause": "play/pause media",
            "mediatracknext": "next track",
            "mediatrackprevious": "previous track",
            "mediastop": "stop media",
            "audiovolumeup": "volume up",
            "audiovolumedown": "volume down",
            "audiovolumemute": "volume mute",

            "control": "ctrl",
            "shift": "shift",
            "alt": "alt",
            "meta": "windows",

            "enter": "enter",
            "escape": "esc",
            "arrowup": "up",
            "arrowdown": "down",
            "arrowleft": "left",
            "arrowright": "right",
            "backspace": "backspace",
            "tab": "tab",
            "space": "space"
        }

        translated_keys = []

        for key in keys:

            translated_key = JS_TO_PYTHON_KEYS.get(
                key,
                key.lower()
            )

            translated_keys.append(
                translated_key
            )

        if not translated_keys:
            return

        combination_string = "+".join(
            translated_keys
        )

        print(
            "Keyboard Simulation Combo:",
            combination_string
        )

        try:

            keyboard.press_and_release(
                combination_string
            )

        except Exception as e:

            print(
                f"Fehler bei Keyboard-Simulation: {e}"
            )