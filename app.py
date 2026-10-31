from flask import Flask, render_template, jsonify, request, redirect, make_response
from extensions import socketio, emit
from strobe_manager import StrobeManager
from serial_manager import SerialManager
from trigger_manager import TriggerManager
from scene_manager import SceneManager
from sequence_manager import SequenceManager
from watcher import DataWatcher
from settings import settings
from device_manager import devices
from dmx_manager import DMXManager
from network import create_qr, get_local_ip
from reference_checker import ReferenceChecker
from fade_manager import fade_manager
from fade_engine import FadeEngine
from trigger_engine import TriggerEngine
from export_manager import ExportManager
from import_manager import ImportManager
from show_controller import ShowController
from external_application_manager import ExternalApplicationManager
from audio.audio_analyzer import AudioAnalyzer
from music_beat_engine import MusicBeatEngine
from music_show_engine import MusicShowEngine
from audio_sequence_manager import AudioSequenceManager
from midi_manager import MidiManager

import re
import os
import json
import threading
import time
import mido


app = Flask(__name__)

socketio.init_app(
    app,
    async_mode="threading"
)


url = create_qr()
print("Webinterface:")
print(url)


# ----------------------------
# Main
# ----------------------------

serial = SerialManager()

dmx_manager = DMXManager(
    serial
)

trigger_manager = TriggerManager()
scene_manager = SceneManager()

# ----------------------------
# Audio / Music Sync
# ----------------------------

audio_analyzer = AudioAnalyzer()

music_beat_engine = MusicBeatEngine(
    audio_analyzer
)

audio_sequence_manager = AudioSequenceManager()



# ----------------------------
# Engines
# ----------------------------

fade_engine = FadeEngine(
    dmx_manager,
    devices,
    settings
)
# Allow the fade engine to resolve scene references.
fade_engine.scene_manager = scene_manager

strobe_manager = StrobeManager(
    scene_manager,
    fade_manager,
    fade_engine,
    dmx_manager
)

sequence_manager = SequenceManager(
    scene_manager,
    dmx_manager,
    fade_manager,
    fade_engine,
    strobe_manager
)


# ----------------------------
# Music Show Engine
# ----------------------------

music_show_engine = MusicShowEngine(
    beat_engine=music_beat_engine,
    scene_manager=scene_manager,
    fade_manager=fade_manager,
    fade_engine=fade_engine,
    sequence_manager=sequence_manager,
    dmx_manager=dmx_manager,
    strobe_manager=strobe_manager,
)


# ----------------------------
# Show Controller
# ----------------------------



show_controller = ShowController(
    sequence_manager,
    fade_engine,
    dmx_manager,
    strobe_manager
)

fade_engine.set_controller(
    show_controller
)

sequence_manager.set_controller(
    show_controller
)
strobe_manager.set_controller(
    show_controller
)

# ----------------------------
# Weitere Manager
# ----------------------------

reference_checker = ReferenceChecker(
    scene_manager,
    sequence_manager,
    trigger_manager,
    fade_manager,
    strobe_manager
)

trigger_engine = TriggerEngine(
    trigger_manager,
    scene_manager,
    sequence_manager,
    dmx_manager,
    fade_manager,
    fade_engine,
    settings,
    show_controller,
    strobe_manager,
    socketio=socketio
)

export_manager = ExportManager(
    scene_manager,
    fade_manager,
    strobe_manager,
    sequence_manager,
    audio_sequence_manager,
    trigger_manager,
    devices
)

import_manager = ImportManager(
    scene_manager,
    fade_manager,
    strobe_manager,
    sequence_manager,
    audio_sequence_manager,
    trigger_manager,
    devices
)
external_application_manager = ExternalApplicationManager(settings)



# MIDI-Eingang initialisieren
midi_manager = MidiManager(
    on_message=trigger_engine.handle_midi_message
)

# Gespeicherten MIDI-Port beim Start öffnen
midi_manager.connect(
    settings.midi_input_port or ""
)


PYTHON_TO_JS_KEYS = {
    "play/pause media": "MediaPlayPause",
    "next track": "MediaTrackNext",
    "previous track": "MediaTrackPrevious",
    "stop media": "MediaStop",
    "volume up": "AudioVolumeUp",
    "volume down": "AudioVolumeDown",
    "volume mute": "AudioVolumeMute",

    "ctrl": "Control",
    "shift": "Shift",
    "alt": "Alt",
    "windows": "Meta",

    "enter": "Enter",
    "esc": "Escape",
    "up": "ArrowUp",
    "down": "ArrowDown",
    "left": "ArrowLeft",
    "right": "ArrowRight",
    "backspace": "Backspace",
    "tab": "Tab",
    "space": "Space",

    "enter": "Enter",
    "escape": "Escape",
    "arrowup": "ArrowUp",
    "arrowdown": "ArrowDown",
    "arrowleft": "ArrowLeft",
    "arrowright": "ArrowRight",
    "backspace": "Backspace",
    "tab": "Tab",
    "space": "Space"
}

# ----------------------------
# Start
# ----------------------------
trigger_engine.start()

watcher = DataWatcher("data")
watcher.start()


# ============================================================
# PROJEKTDATEI - temporär
# ============================================================

PROJECT_FILE = "data/3d-data.json"


# ============================================================
# STANDARD-PROJEKT
# ============================================================

DEFAULT_PROJECT = {
    "universeSize": 30,
    "globalBeamLength": 5,
    "globalBeamsVisible": True,
    "fixtures": [],
    "trusses": []
}


# ============================================================
# PROJEKT LADEN
# ============================================================

def load_project():

    if not os.path.exists(PROJECT_FILE):
        return DEFAULT_PROJECT.copy()

    try:

        with open(
            PROJECT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as error:

        print(
            "Error while loading project:",
            error
        )

        return DEFAULT_PROJECT.copy()


# ============================================================
# PROJEKT SPEICHERN
# ============================================================

def save_project(project):

    with open(
        PROJECT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            project,
            file,
            indent=4,
            ensure_ascii=False
        )

# ============================================================
# PROJEKT SPEICHERN
# ============================================================

@app.route(
    "/api/project/save",
    methods=["POST"]
)
def save_project_api():

    project = request.get_json()

    if not project:

        return jsonify({
            "success": False,
            "error": "No project data received."
        }), 400


    try:

        save_project(
            project
        )

        return jsonify({
            "success": True
        })


    except Exception as error:

        print(
            "Error while saving:",
            error
        )

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500




# ----------------------------
# Seiten
# ----------------------------

@app.route("/")
def dashboard():

    if settings.get("mode") == "show":
        return redirect("/show")

    serial.update()
    problems = reference_checker.check()

    return render_template(
        "dashboard.html",
        serial=serial, ip=get_local_ip(), port=settings.port, network_mode = settings.network_mode, create_qr=settings.create_qr, problems=problems
    )

@app.context_processor
def inject_globals():
    return {
        "settings": settings,
        "config": settings.settings,
        "mode": settings.get("mode"),
        "problems": reference_checker.check()
    }


@app.route("/visualizer")
def visualizer():
    project = load_project()
    return render_template(
        "visualizer.html",
        mode="edit",
        project=project,
        devices=devices.devices
    )


@app.route("/timing")
def timing():
    timing_live_key = settings.get_timing_live_key()
    timing_global_playkey = settings.get_timing_global_playkey()
    timing_global_simkey = settings.get_timing_global_simkey()

    timing_live_key_js = PYTHON_TO_JS_KEYS.get(
        timing_live_key,
        timing_live_key
    )

    timing_global_playkey_js = PYTHON_TO_JS_KEYS.get(
            timing_global_playkey,
            timing_global_playkey
        )
    
    timing_global_simkey_js = PYTHON_TO_JS_KEYS.get(
            timing_global_simkey,
            timing_global_simkey
        )
    
    return render_template("timing.html",
        timing_mode=settings.get_timing_mode(),
        timing_live_key=timing_live_key_js,
        timing_global_playkey=timing_global_playkey_js,
        timing_global_simkey=timing_global_simkey_js,
        global_time=trigger_engine.timing_elapsed
    )

@app.route("/timing/reset", methods=["POST"])
def timing_reset():

    trigger_engine.reset_timing()
    print("Reset the trigger-timing")

    return {
        "success": True
    }


@app.route("/timing/trigger", methods=["POST"])
def timing_trigger():

    trigger_engine.execute_timing()

    return {
        "success": True
    }

@app.route("/timing/live/save-key", methods=["POST"])
def timing_save_livekey():

    data = request.get_json()

    if not data or "key" not in data:
        return {
            "success": False,
            "error": "No key provided"
        }, 400

    settings.set_timing_live(
        "record_key",
        data["key"]
    )

    return {
        "success": True
    }

@app.route("/timing/global/save-record", methods=["POST"])
def timing_save_global_record():

    data = request.get_json()

    if not data or "key" not in data:
        return {
            "success": False,
            "error": "No key provided"
        }, 400

    settings.set_timing_global_record(
        "record_key",
        data["key"]
    )

    return {
        "success": True
    }

@app.route("/timing/global/save-sim", methods=["POST"])
def timing_save_global_sim():

    data = request.get_json()

    if not data or "key" not in data:
        return {
            "success": False,
            "error": "No key provided"
        }, 400

    settings.set_timing_global_sim(
        "simulate_key",
        data["key"]
    )

    return {
        "success": True
    }

@app.route("/set-mode/<mode>")
def set_mode(mode):

    if mode not in ["show", "edit"]:
        return "Invalid Mode", 400

    settings.set(
        "mode",
        mode
    )
    print(mode)

    
    

    settings.save()

    if "/show" in request.referrer:
        return redirect('/')

    return redirect(request.referrer or '/')

# --------------------------------
# SCENES
# --------------------------------


@app.route("/scenes")
def scenes():

    return render_template(
        "scenes.html",
        scenes=scene_manager.scenes
    )



@app.route("/scenes/add", methods=["POST"])
def add_scene():

    name = request.form["name"]


    scene_manager.add(
        {
            "name": name,
            "devices": {}
        }
    )


    return redirect(
        "/scenes"
    )

@app.route("/scenes/apply")
def apply_scene():

    scene = scene_manager.get_id(
        int(request.args["id"])
    )

    if scene:
        dmx_manager.apply_scene(scene)

    return "OK"

@app.route("/fades")
def fades():

    return render_template(
        "fades.html",
        fades=fade_manager.fades
    )

@app.route("/fades/delete")
def delete_fade():

    fade_id = int(
        request.args.get("id")
    )

    fade = fade_manager.get_id(
        fade_id
    )

    if not fade:
        return "Fade not found", 404


    fade_manager.fades.remove(
        fade
    )


    fade_manager.save()


    return redirect("/fades")

@app.route("/fades/duplicate")
def duplicate_fade():

    fade_id = request.args.get(
        "id",
        type=int
    )

    fade = fade_manager.duplicate(
        fade_id
    )

    if not fade:
        return "Fade not found", 404

    return redirect(
        request.referrer or "/fades"
    )

@app.route("/fades/add")
def add_fade():

    fade = {

        "id": fade_manager.next_id(),

        "name": "",

        "duration": 1000,

        "mode":"merge",

        "devices": []

    }


    fade_manager.fades.append(fade)

    fade_manager.save()


    return redirect(
        f"/fades/edit?id={fade['id']}"
    )



@app.route("/fades/edit")
def edit_fade():
    fade = fade_manager.get_id(
        int(request.args["id"])
    )

    if not fade:
        return "Fade not found", 404

    return render_template(
        "fade_edit.html",
        fade=fade,
        devices=devices.devices,
        scenes=scene_manager.scenes
    )


@app.route("/fades/device/add", methods=["POST"])
def add_device_to_fade():


    fade_id = int(
        request.form["fade_id"]
    )

    device_id = int(
        request.form["device_id"]
    )


    fade = fade_manager.get_id(
        fade_id
    )


    if not fade:
        return "Fade not found",404


    if "devices" not in fade:
        fade["devices"] = []


    # prüfen ob schon vorhanden
    for d in fade["devices"]:
        if d["device"] == device_id:
            return redirect(
                f"/fades/edit?id={fade_id}"
            )


    fade["devices"].append(
        {
            "device": device_id,
            "channels": []
        }
    )


    fade_manager.save()


    return redirect(
        f"/fades/edit?id={fade_id}"
    )

@app.route("/fades/device")
def edit_fade_device():

    fade_id = int(
        request.args["fade"]
    )

    device_id = int(
        request.args["device"]
    )


    fade = fade_manager.get_id(
        fade_id
    )


    device = devices.get_id(
        device_id
    )


    if not fade or not device:
        return "not found",404



    fade_device = None


    for d in fade.get("devices",[]):

        if d["device"] == device_id:

            fade_device = d
            break



    if not fade_device:

        fade_device = {

            "device":device_id,

            "channels":[]

        }



    # vorhandene Kanäle ergänzen

    channels={}


    for ch in fade_device["channels"]:

        channels[
            ch["channel"]
        ] = ch



    return render_template(
        "fade_device.html",
        fade=fade,
        device=device,
        channels=channels
    )



@app.route("/fades/device/save", methods=["POST"])
def save_fade_device():
    fade_id = int(request.form["fade_id"])
    device_id = int(request.form["device_id"])

    fade = fade_manager.get_id(fade_id)
    device = devices.get_id(device_id)

    if not fade:
        return "Fade not found", 404

    if not device:
        return "Device not found", 404

    channel_count = int(device["channels"])
    functions = device.get("channel_functions", [])

    # Map channels belonging to complete RGB zones.
    rgb_zone_by_channel = {}

    for zone in (1, 2, 3):
        zone_channels = {}

        for index in range(channel_count):
            function = (
                functions[index]
                if index < len(functions)
                else "Fader"
            )

            if function in {"Disabled", "Fader"}:
                continue

            if function in {
                f"R{zone}", f"G{zone}", f"B{zone}"
            }:
                zone_channels[function[0]] = index + 1

        if all(color in zone_channels for color in ("R", "G", "B")):
            for channel in zone_channels.values():
                rgb_zone_by_channel[channel] = zone

    result = []

    for channel in range(1, channel_count + 1):
        function = (
            functions[channel - 1]
            if channel - 1 < len(functions)
            else "Fader"
        )

        # Disabled device channels must never be active in a fade.
        if function == "Disabled":
            enabled = False

        elif channel in rgb_zone_by_channel:
            zone = rgb_zone_by_channel[channel]
            enabled = f"zone_enable_{zone}" in request.form

        else:
            enabled = f"enable_{channel}" in request.form

        try:
            start = int(request.form.get(f"start_{channel}", 0))
            end = int(request.form.get(f"end_{channel}", 255))
        except (TypeError, ValueError):
            return f"Invalid value for channel {channel}", 400

        if not (0 <= start <= 255 and 0 <= end <= 255):
            return f"Channel {channel} values must be between 0 and 255.", 400

        result.append({
            "channel": channel,
            "enabled": enabled,
            "start": start,
            "end": end
        })

    if "devices" not in fade:
        fade["devices"] = []

    for fade_device in fade["devices"]:
        if fade_device["device"] == device_id:
            fade_device["channels"] = result
            break
    else:
        fade["devices"].append({
            "device": device_id,
            "channels": result
        })

    fade_manager.save()

    return redirect(f"/fades/edit?id={fade_id}")


@app.route("/fades/start")
def start_fade():

    fade = fade_manager.get_id(
        int(request.args["id"])
    )

    if not fade:
        return "Fade not found", 404

    fade_engine.play(fade)

    return "OK"


@app.route("/fades/save", methods=["POST"])
def save_fade():
    fade_id = int(request.form["id"])
    fade = fade_manager.get_id(fade_id)

    if not fade:
        return "Fade not found", 404

    fade_type = request.form.get("fade_type", "custom")

    if fade_type not in {"custom", "scenes"}:
        return "Invalid fade type", 400

    name = request.form.get("name", "").strip()

    if not name:
        return "Fade name is required", 400

    try:
        duration = int(request.form["duration"])
    except (TypeError, ValueError):
        return "Invalid duration", 400

    if duration < 1:
        return "Duration must be greater than zero", 400

    unit = request.form.get("duration_unit", "ms")

    if unit == "sec":
        duration *= 1000
    elif unit == "min":
        duration *= 60000
    elif unit != "ms":
        return "Invalid duration unit", 400

    fade["name"] = name
    fade["duration_unit"] = unit
    fade["type"] = fade_type

    if fade_type == "scenes":
        try:
            start_scene_id = int(request.form["start_scene"])
            end_scene_id = int(request.form["end_scene"])
        except (KeyError, TypeError, ValueError):
            return "Please select both scenes", 400

        start_scene = scene_manager.get_id(start_scene_id)
        end_scene = scene_manager.get_id(end_scene_id)

        if not start_scene or not end_scene:
            return "Selected scene not found", 400

        fade["start_scene"] = start_scene_id
        fade["end_scene"] = end_scene_id

    else:
        # Keep existing custom-channel configuration.
        fade.pop("start_scene", None)
        fade.pop("end_scene", None)

    mode = request.form.get("mode", "merge")

    if mode not in {"merge", "overwrite"}:
        return "Invalid fade mode", 400

    fade["mode"] = mode

    fade_manager.save()

    #return redirect(f"/fades/edit?id={fade_id}")
    return redirect(f"/fades")

@app.route("/dmx/clear")
def dmx_clear():

    show_controller.stop_all(reset_dmx=False)

    dmx_manager.clear()

    time.sleep(0.05)

    show_controller.reset()

    return redirect(request.referrer or "/")


@app.route("/dmx/apply_device", methods=["POST"])
def dmx_apply_device():

    scene_id = int(request.json["scene_id"])
    device_id = int(request.json["device_id"])

    scene = scene_manager.get_id(scene_id)

    if not scene:
        return jsonify(success=False)

    device = devices.get_id(device_id)

    if not device:
        return jsonify(success=False)

    channels = scene.get("devices", {}).get(str(device_id), {})

    values = {}

    for ch, value in channels.items():

        dmx_channel = (
            device["start_channel"]
            + int(ch)
            - 1
        )

        values[dmx_channel] = value

    dmx_manager.apply_values(values)

    return jsonify(success=True)

@app.route("/dmx/apply_device_live", methods=["POST"])
def dmx_apply_device_live():

    data = request.json


    device_id = str(
        data["device_id"]
    )


    channels = data["channels"]


    device = devices.get_id(
        int(device_id)
    )


    if not device:

        return jsonify(
            success=False,
            error="device not found"
        )


    values = {}


    for ch,value in channels.items():

        dmx_channel = (
            device["start_channel"]
            + int(ch)
            - 1
        )


        values[dmx_channel] = int(value)



    dmx_manager.apply_values(values)


    return jsonify(
        success=True
    )

@app.route("/scenes/edit")
def edit_scene():

    scene_id = int(
        request.args.get("id")
    )


    scene = scene_manager.get_id(
        scene_id
    )


    if not scene:

        return "Scene not found",404



    return render_template(
        "scene_edit.html",
        scene=scene,
        devices=devices.devices
    )

@app.route("/scenes/duplicate")
def duplicate_scene():

    scene_id = request.args.get(
        "id",
        type=int
    )

    scene = scene_manager.duplicate(
        scene_id
    )

    if not scene:
        return "Scene not found", 404

    return redirect(
        request.referrer or "/scenes"
    )

# --------------------------------
# device zu Scene hinzufügen
# --------------------------------


@app.route("/scenes/device/add")
def add_device_to_scene():

    scene_id = int(request.args.get("scene"))
    device_id = int(request.args.get("device"))


    scene = scene_manager.get_id(scene_id)

    if not scene:
        return "Scene not found",404



    if "devices" not in scene:

        scene["devices"] = {}



    scene["devices"][str(device_id)] = {}



    scene_manager.save()



    return redirect(
        "/scenes/edit?id=" + str(scene_id)
    )



# --------------------------------
# device entfernen
# --------------------------------


@app.route("/scenes/device/remove")
def remove_device_from_scene():


    scene_id = int(
        request.args.get("scene")
    )

    device_id = int(
        request.args.get("device")
    )


    scene = scene_manager.get_id(
        scene_id
    )


    if not scene:

        return "Scene not found",404



    if str(device_id) in scene["devices"]:

        del scene["devices"][str(device_id)]



    scene_manager.save()


    return redirect(
        "/scenes/edit?id=" + str(scene_id)
    )



# --------------------------------
# device bearbeiten
# --------------------------------


@app.route("/scenes/device")
def edit_scene_device():

    scene_id = int(
        request.args.get("scene")
    )

    device_id = int(
        request.args.get("device")
    )


    scene = scene_manager.get_id(scene_id)

    if not scene:
        return "Scene not found",404



    device = devices.get_id(device_id)

    if not device:
        return "device not found",404



    # gespeicherte Werte
    values = scene.get("devices", {}).get(
        str(device_id),
        {}
    )


    # fehlende Kanäle mit 0 ergänzen
    for i in range(device["channels"]):

        ch = str(i+1)

        if ch not in values:

            values[ch] = 0



    return render_template(
        "scene_device_edit.html",
        scene=scene,
        device=device,
        values=values
    )


# --------------------------------
# Kanalwerte speichern
# --------------------------------


@app.route("/scenes/device/save", methods=["POST"])
def save_scene_device():


    scene_id = int(
        request.form["scene_id"]
    )

    device_id = int(
        request.form["device_id"]
    )


    scene = scene_manager.get_id(scene_id)

    if not scene:
        return "Scene not found",404



    if "devices" not in scene:

        scene["devices"] = {}



    channels = {}



    for key,value in request.form.items():

        if key.startswith("ch_"):


            ch = key.replace(
                "ch_",
                ""
            )


            value = int(value)


            # auch 0 speichern!
            channels[ch] = value



    if channels:
        scene["devices"][str(device_id)] = channels
    else:
        print("No channels received—nothing saved")



    scene_manager.save()



    return redirect(
        "/scenes/edit?id=" + str(scene_id)
    )



# --------------------------------
# Scene allgemein speichern
# --------------------------------


@app.route("/scenes/edit/save", methods=["POST"])
def save_scene():


    scene_id = int(
        request.form["id"]
    )


    scene = scene_manager.get_id(
        scene_id
    )


    if not scene:

        return "Scene not found",404



    scene["name"] = request.form["name"]


    scene_manager.save()



    return redirect(
        "/scenes"
    )



# --------------------------------
# Scene löschen
# --------------------------------


@app.route("/scenes/delete")
def delete_scene():


    scene_id = int(
        request.args.get("id")
    )


    scene_manager.delete(
        scene_id
    )


    return redirect(
        "/scenes"
    )


# --------------------------------
# TRIGGERS
# --------------------------------


@app.route("/triggers")
def trigger_editor():
    for trigger in trigger_manager.triggers:
        if trigger.get("type") == "midi":
            trigger["input_name"] = trigger_manager.midi_note_name(
                trigger.get("input")
            )

    return render_template(
        "triggers.html",
        triggers=trigger_manager.triggers
    )



@app.route("/triggers/add")
def add_trigger_page():

    trigger = {
        "id": 0,
        "name": "",
        "enabled": True,
        "type": "keyboard",
        "keys": [],
        "actions": []
    }

    return render_template(
        "trigger_edit.html",
        trigger=trigger,
        scenes=scene_manager.scenes,
        fades=fade_manager.fades,
        sequences=sequence_manager.sequences,
        strobes=strobe_manager.strobes,
        midi_note_name=trigger_manager.midi_note_name,
        audio_sequences=audio_sequence_manager.list_sequences(),
    )


@app.route("/triggers/edit")
def edit_trigger():


    trigger_id = int(
        request.args.get("id")
    )


    trigger = trigger_manager.get_id(
        trigger_id
    )


    if not trigger:

        return "Trigger not found",404

    if trigger.get("type") == "midi":
        trigger["input_name"] = trigger_manager.midi_note_name(
            trigger.get("input")
        )


    return render_template(
        "trigger_edit.html",
        trigger=trigger,
        scenes=scene_manager.scenes,
        fades=fade_manager.fades,
        sequences=sequence_manager.sequences,
        strobes=strobe_manager.strobes,
        midi_note_name=trigger_manager.midi_note_name,
        audio_sequences=audio_sequence_manager.list_sequences()
    )



@app.route("/triggers/save", methods=["POST"])
def save_trigger():

    trigger_id = int(
        request.form.get(
            "id",
            0
        )
    )


    trigger = trigger_manager.get_id(
        trigger_id
    )


    # Neuer Trigger
    if not trigger:

        trigger = {

            "id": trigger_manager.get_next_id(),

            "actions": []

        }

        trigger_manager.triggers.append(
            trigger
        )


    trigger["name"] = request.form["name"]

    trigger["enabled"] = (
        "enabled" in request.form
    )

    trigger["type"] = request.form["type"]


    # Keyboard Haupttrigger
    if trigger["type"] == "keyboard":

        trigger["keys"] = [

            k for k in request.form
            .get("keys","")
            .split(",")

            if k

        ]

        # alte Variable entfernen
        trigger.pop(
            "input",
            None
        )

    if trigger["type"] == "midi":
        midi_input = request.form.get("input", "").strip()
        print("[DEBUG] Form data:", request.form.to_dict())
        print("[DEBUG] MIDI input:", repr(request.form.get("midi_input")))
        try:
            midi_input = int(midi_input)
        except (TypeError, ValueError):
            return "Invalid MIDI note. Please select a note between 0 and 127.", 400

        if not 0 <= midi_input <= 127:
            return "MIDI note must be between 0 and 127.", 400

        trigger["input"] = midi_input

        # Remove keyboard-specific data
        trigger.pop("keys", None)

    # Aktionen neu aufbauen

   
    types = request.form.getlist("action_type")
    targets = request.form.getlist("action_target")
    keys = request.form.getlist("action_keys")
    operations = request.form.getlist("action_operation")

    actions = []

    for i, action_type in enumerate(types):
        action = {
            "type": action_type
        }

        if action_type == "keyboard":
            if i < len(keys):
                action["keys"] = [
                    key for key in keys[i].split(",") if key
                ]

        else:
            if i < len(targets):
                action["target"] = targets[i].strip()

        if action_type == "audio_sequence":
            operation = (
                operations[i]
                if i < len(operations)
                else "start"
            )

            if operation not in ("start", "stop"):
                operation = "start"

            action["operation"] = operation

        actions.append(action)

    trigger["actions"] = actions



    trigger_manager.save()


    return redirect(
        "/triggers"
    )

@app.route("/triggers/duplicate")
def duplicate_trigger():

    trigger_id = request.args.get(
        "id",
        type=int
    )

    trigger = trigger_manager.duplicate(
        trigger_id
    )

    if not trigger:
        return "Trigger not found", 404

    return redirect(
        request.referrer or "/triggers"
    )

@app.route("/triggers/delete")
def delete_trigger():


    trigger_id = int(
        request.args.get("id")
    )


    trigger_manager.delete(
        trigger_id
    )


    return redirect(
        "/triggers"
    )

@app.route("/triggers/execute")
def execute_trigger():

    trigger_id = request.args.get(
        "id",
        type=int
    )

    trigger = trigger_manager.get_id(
        trigger_id
    )

    if not trigger:
        return "Trigger not found", 404

    trigger_engine.execute(trigger)

    return redirect(
        request.referrer or "/"
    )


@app.route("/devices")
def device_manager():

    return render_template(
        "devices.html",
        devices=devices.devices
    )

@app.route("/devices/duplicate")
def duplicate_device():

    device_id = request.args.get(
        "id",
        type=int
    )

    device = devices.duplicate(
        device_id
    )

    if not device:
        return "device not found", 404

    return redirect(
        request.referrer or "/devices"
    )


@app.route("/devices/add", methods=["POST"])
def add_device():
    channel_count = int(request.form["channels"])

    device = {
        "id": len(devices.devices) + 1,
        "name": request.form["name"],
        "start_channel": int(request.form["address"]),
        "channels": channel_count,
        "color": request.form["color"],
        "channel_names": [
            f"CH{i+1}"
            for i in range(channel_count)
        ],
        "channel_functions": [
            "Fader"
            for _ in range(channel_count)
        ]
    }

    devices.add(device)

    return redirect("/devices")

@app.route("/devices/delete")
def delete_device():

    device_id = int(
        request.args.get("id")
    )

    print("Lösche device:", device_id)
    devices.delete(
        device_id
    )


    return redirect(
        "/devices"
    )

@app.route("/devices/edit")
def edit_device():

    device_id = int(request.args.get("id"))

    device = None

    for d in devices.devices:

        if d["id"] == device_id:

            device = d
            break


    if device is None:

        return "device not found", 404


    return render_template(
        "device_edit.html",
        device=device
    )


@app.route("/devices/edit/save", methods=["POST"])
def save_device():
    device_id = int(request.form["id"])

    valid_functions = {
        "Fader",
        "Disabled",
        "R1", "G1", "B1", "W1",
        "R2", "G2", "B2", "W2",
        "R3", "G3", "B3", "W3"
    }

    for d in devices.devices:
        if d["id"] != device_id:
            continue

        new_channels = int(request.form["channels"])

        if new_channels < 1:
            return "Channel count must be at least 1.", 400

        d["name"] = request.form["name"]
        d["start_channel"] = int(request.form["start_channel"])
        d["channels"] = new_channels
        d["color"] = request.form["color"]

        old_names = d.get("channel_names", [])
        old_functions = d.get("channel_functions", [])

        new_names = []
        new_functions = []

        for i in range(new_channels):
            channel_number = i + 1

            # Preserve channel names where possible.
            name_key = f"channel_{channel_number}"
            channel_name = request.form.get(
                name_key,
                old_names[i] if i < len(old_names) else f"CH{channel_number}"
            )
            new_names.append(channel_name)

            # Read the selected function and validate it.
            function_key = f"function_{channel_number}"
            default_function = (
                old_functions[i]
                if i < len(old_functions)
                else "Fader"
            )

            function = request.form.get(
                function_key,
                default_function
            )

            if function not in valid_functions:
                return (
                    f"Invalid channel function for channel {channel_number}.",
                    400
                )

            new_functions.append(function)

        d["channel_names"] = new_names
        d["channel_functions"] = new_functions
        break
    else:
        return "Device not found.", 404

    devices.save()

    return redirect("/devices")



@app.route("/settings")
def settings_page():
    try:
        midi_ports = mido.get_input_names()
    except Exception as e:
        print(f"MIDI-Ports couldn't be loaded: {e}")
        midi_ports = []

    return render_template(
        "settings.html",
        create_qr=settings.create_qr,
        refresh_rate=settings.refresh_rate,
        network_mode=settings.network_mode,
        port=settings.port,
        midi_ports=midi_ports,
        midi_input_port=settings.midi_input_port
    )


@app.route("/settings/midi-ports", methods=["GET"])
def refresh_midi_ports():
    ports = midi_manager.get_input_names()
    return jsonify({"ports": ports})


@app.route("/settings/export_old")
def export_show_old():


    items = request.args.getlist(
        "items"
    )


    content = export_manager.create_export(
        items
    )



    response = make_response(
        content
    )


    response.headers[
        "Content-Disposition"
    ] = (
        "attachment; "
        "filename=ShowControl.dmx"
    )


    response.headers[
        "Content-Type"
    ] = "application/octet-stream"



    return response


@app.route("/settings/export")
def export_show():

    items = request.args.getlist(
        "items"
    )


    content = export_manager.create_export(
        items
    )


    # --------------------------------------------------
    # Filename
    # --------------------------------------------------

    if "all" in items:

        filename = "ShowControl_Everything.dmx"


    elif len(items) == 1:

        names = {
            "scenes": "Scenes",
            "fades": "Fades",
            "sequences": "Sequences",
            "triggers": "Triggers",
            "devices": "Devices",
            "strobes": "Strobes",
            "audio_sequences": "AudioSequences"
        }

        filename = (
            "ShowControl_"
            + names.get(
                items[0],
                "Export"
            )
            + ".dmx"
        )


    else:

        names = {
            "scenes": "Scenes",
            "fades": "Fades",
            "sequences": "Sequences",
            "triggers": "Triggers",
            "devices": "Devices",
            "strobes": "Strobes",
            "audio_sequences": "AudioSequences"
        }


        selected_names = [
            names.get(
                item,
                item
            )
            for item in items
        ]


        filename = (
            "ShowControl_"
            + "_".join(
                selected_names
            )
            + ".dmx"
        )


    # --------------------------------------------------
    # Response
    # --------------------------------------------------

    response = make_response(
        content
    )


    response.headers[
        "Content-Disposition"
    ] = (
        "attachment; "
        f"filename={filename}"
    )


    response.headers[
        "Content-Type"
    ] = "application/octet-stream"


    return response


@app.route("/live-faders")
def live_faders():
    project = load_project()

    return render_template(
        "live_faders.html",
        mode="edit",
        project=project,
        devices=devices.devices
    )



@app.route(
    "/settings/import",
    methods=["POST"]
)
def import_show():


    file = request.files.get(
        "file"
    )


    if not file:

        return "No File",400



    try:

        import_manager.import_file(
            file
        )


    except Exception as e:

        print(e)

        return str(e),400



    return redirect(
        "/settings"
    )

@app.route("/settings/external-applications/edit", methods=["POST"])
def edit_external_application():
    data = request.get_json(silent=True) or {}

    try:
        index = int(data.get("index"))
    except (TypeError, ValueError):
        return "Invalid application index.", 400

    path = str(data.get("path", "")).strip()

    if not path:
        return "Application path is required.", 400

    applications = settings.get_external_applications()

    if not 0 <= index < len(applications):
        return "Application not found.", 404

    applications[index] = {
        "path": path,
        "start_with_app": bool(data.get("start_with_app", False)),
        "stop_with_app": bool(data.get("stop_with_app", False))
    }

    # Save using your existing settings persistence method.

    return {"success": True}

@app.route("/settings/save", methods=["POST"])
def save_settings():

    settings.set(
        "network_mode",
        request.form["network_mode"]
    )

    settings.set(
        "port",
        int(request.form["port"])
    )

    settings.set(
        "refresh_rate",
        int(request.form["refresh_rate"])
    )

    settings.set(
        "create_qr",
        request.form["create_qr"] == "true"
    )

    # MIDI-Eingangsport speichern
    settings.set(
        "midi_input_port",
        request.form.get("midi_input_port", "").strip()
    )
    
    settings.save()
    midi_manager.connect(
        settings.midi_input_port or ""
    )

    return redirect(request.referrer or "/settings")


@app.route("/settings/save-timing", methods=["POST"])
def save_settings_timing():

    settings.set(
        "timing-mode",
        request.form["timing-mode"]
    )

    settings.save()

    #return redirect("/settings")
    return redirect("/timing")


@app.route("/settings/external-applications")
def get_external_applications():

    return jsonify(
        settings.get_external_applications()
    )


@app.route(
    "/settings/external-applications/add",
    methods=["POST"]
)
def add_external_application():

    data = request.get_json()

    applications = (
        settings.get_external_applications()
    )

    applications.append({
        "path": data.get("path", ""),
        "start_with_app":
            bool(data.get("start_with_app", True)),
        "stop_with_app":
            bool(data.get("stop_with_app", True))
    })

    settings.set_external_applications(
        applications
    )

    return jsonify(
        success=True
    )


@app.route(
    "/settings/external-applications/remove",
    methods=["POST"]
)
def remove_external_application():

    data = request.get_json()

    index = data.get("index")

    applications = (
        settings.get_external_applications()
    )

    if (
        not isinstance(index, int)
        or index < 0
        or index >= len(applications)
    ):
        return jsonify(
            success=False
        ), 400

    applications.pop(index)

    settings.set_external_applications(
        applications
    )

    return jsonify(
        success=True
    )


@app.route("/settings/midi-learn/<target>", methods=["POST"])
def start_midi_learning(target):
    if target not in ("highest", "lowest"):
        return jsonify({"error": "Invalid target"}), 400

    if not midi_manager.port:
        return jsonify({
            "error": "No MIDI-Input connected"
        }), 400

    midi_manager.start_learning(target)
    return jsonify({"success": True})


@app.route("/settings/midi-learn/status")
def midi_learning_status():
    return jsonify(midi_manager.get_learning_status())




@app.route("/settings/midi-calibration/save", methods=["POST"])
def save_midi_calibration():
    data = request.get_json(silent=True) or {}

    name_highest = str(data.get("name_highest", "")).strip()
    name_lowest = str(data.get("name_lowest", "")).strip()

    lowest = data.get("lowest")
    highest = data.get("highest")

    # Unterstützt beispielsweise C-2, C#3, Db4 und G8.
    note_pattern = r"([A-Ga-g])([#b]?)(-?\d+)"

    note_values = {
        "C": 0,
        "D": 2,
        "E": 4,
        "F": 5,
        "G": 7,
        "A": 9,
        "B": 11
    }

    def parse_note_name(name):
        match = re.fullmatch(note_pattern, name)

        if not match:
            return None

        letter = match.group(1).upper()
        accidental = match.group(2)

        pitch_class = note_values[letter]

        if accidental == "#":
            pitch_class = (pitch_class + 1) % 12
        elif accidental == "b":
            pitch_class = (pitch_class - 1) % 12

        octave = int(match.group(3))

        # Ableton-Konvention:
        # C-2 = MIDI 0, C-1 = MIDI 12, C0 = MIDI 24.
        midi_number = (octave + 2) * 12 + pitch_class

        return midi_number

    # Beide Notennamen validieren.
    expected_lowest = parse_note_name(name_lowest)
    expected_highest = parse_note_name(name_highest)

    if expected_lowest is None:
        return jsonify({
            "error": (
                "Invalid name of lowest note. "
                "E.g.: C-2, C#3 oder Db4."
            )
        }), 400

    if expected_highest is None:
        return jsonify({
            "error": (
                "Invalid name of highest note. "
                "E.g.: G8 oder C5."
            )
        }), 400

    # Eingelernte MIDI-Notennummern validieren.
    try:
        if isinstance(lowest, bool) or isinstance(highest, bool):
            raise ValueError

        lowest = int(lowest)
        highest = int(highest)

        # Keine Dezimalwerte wie 60.5 akzeptieren.
        if str(data.get("lowest")) != str(lowest):
            raise ValueError

        if str(data.get("highest")) != str(highest):
            raise ValueError

    except (TypeError, ValueError):
        return jsonify({
            "error": "Invalid MIDI-notenumbers."
        }), 400

    if not (0 <= lowest <= 127 and 0 <= highest <= 127):
        return jsonify({
            "error": "MIDI-notes must be between 0 and 127."
        }), 400

    if highest <= lowest:
        return jsonify({
            "error": (
                "The highest reference-note must be higher"
                "than the lowest reference-note."
            )
        }), 400

    # Prüfen, ob die eingegebenen Namen zu den eingelernten
    # MIDI-Notennummern passen.
    if expected_lowest != lowest:
        return jsonify({
            "error": (
                f"{name_lowest} according to the convention, this corresponds to "
                f"MIDI {expected_lowest}, but MIDI was programmed as "
                f"{lowest}."
            )
        }), 400

    if expected_highest != highest:
        return jsonify({
            "error": (
                f"{name_highest} according to the convention, this corresponds to "
                f"MIDI {expected_highest}, But MIDI was programmed in "
                f"{highest}."
            )
        }), 400

    # Einstellungen speichern.
    settings.set("midi_note_name_lowest", name_lowest)
    settings.set("midi_note_name_highest", name_highest)
    settings.set("midi_note_number_lowest", lowest)
    settings.set("midi_note_number_highest", highest)
    settings.set("midi_calibration_saved", True)
    settings.save()

    return jsonify({
        "success": True,
        "message": (
            f"Assignment saved: {name_lowest} = MIDI {lowest}, "
            f"{name_highest} = MIDI {highest}."
        )
    })





@app.route("/sequences")
def sequences():

    return render_template(
        "sequences.html",
        sequences=sequence_manager.sequences,
        scenes=scene_manager.scenes
    )

@app.route("/sequences/duplicate")
def duplicate_sequence():

    sequence_id = request.args.get(
        "id",
        type=int
    )

    sequence = sequence_manager.duplicate(
        sequence_id
    )

    if not sequence:
        return "Sequence not found", 404

    return redirect(
        request.referrer or "/sequences"
    )

@app.route("/sequences/start")
def start_sequence():

    seq_id = int(
        request.args.get("id")
    )


    sequence = sequence_manager.get_id(
        seq_id
    )


    if sequence:

        sequence_manager.start(
            sequence
        )


    return "OK"

@app.route("/sequences/add")
def add_sequence():

    sequence = {

        "id":
        sequence_manager.get_next_id(),

        "name":
        "",

        "steps":[]

    }


    return render_template(
        "sequence_edit.html",
        sequence=sequence,
        scenes=scene_manager.scenes,
        fades=fade_manager.fades,
        strobes=strobe_manager.strobes
    )

@app.route("/sequences/delete")
def delete_sequence():

    seq_id = int(
        request.args.get("id")
    )


    sequence_manager.delete(
        seq_id
    )


    return redirect(
        "/sequences"
    )

@app.route("/sequences/edit")
def edit_sequence():

    id = int(
        request.args.get("id")
    )


    sequence = sequence_manager.get_id(id)


    if not sequence:
        return "Sequence not found",404


    return render_template(
        "sequence_edit.html",
        sequence=sequence,
        scenes=scene_manager.scenes,
        fades=fade_manager.fades,
        strobes=strobe_manager.strobes
    )

@app.route("/sequences/save", methods=["POST"])
def save_sequence():

    seq_id = int(
        request.form["id"]
    )


    sequence = sequence_manager.get_id(
        seq_id
    )


    if not sequence:

        sequence = {

            "id":seq_id,

            "steps":[]

        }

        sequence_manager.sequences.append(
            sequence
        )


    sequence["name"] = request.form["name"]


    actions = request.form.getlist(
        "step_type"
    )

    targets = request.form.getlist(
        "step_target"
    )

    times = request.form.getlist(
        "step_time"
    )


    steps=[]


    for i, action in enumerate(actions):

        step = {
            "action": action,
            "time": int(times[i])
        }

        if action in ("scene", "fade", "strobe"):

            if i < len(targets):

                target = targets[i]

                if target:
                    step["target"] = (target)

        elif action == "keyboard":

            keys = request.form.getlist(
                "step_keys"
            )

            if i < len(keys):

                step["keys"] = [
                    k for k in keys[i].split(",")
                    if k
                ]

        steps.append(step)


    sequence["steps"]=steps


    sequence_manager.save()


    return redirect(
        "/sequences"
    )

@app.template_filter("duration")
def duration_filter(steps):

    total = sum(
        step.get("time",0)
        for step in steps
    )


    minutes = total // 60000

    seconds = (
        total % 60000
    ) // 1000


    if minutes:

        return f"{minutes} min {seconds:02d} s"


    return f"{seconds} s"

# ----------------------------
# API Status
# ----------------------------

@app.route("/api/status")
def status():

    return jsonify(
        {
            "connected": serial.connected,
            "handshake": serial.handshake
        }
    )


# ----------------------------
# Trigger API
# ----------------------------

@app.route("/api/triggers")
def triggers():

    return jsonify(
        trigger_manager.triggers
    )


@app.route("/api/triggers/add", methods=["POST"])
def add_trigger():

    data = request.json

    trigger_manager.add(
        data
    )

    return jsonify(
        {
            "success": True
        }
    )


@app.route("/api/reconnect", methods=["POST"])
def reconnect():

    try:

        serial.reconnect()


        socketio.emit(
            "status_update",
            {
                "connected": serial.connected,
                "handshake": serial.handshake
            }
        )


        return jsonify(
            {
                "success": True
            }
        )


    except Exception as e:


        return jsonify(
            {
                "success": False,
                "message": str(e)
            }
        )

@socketio.on("connect")
def client_connected(auth=None):

    socketio.emit(
        "status_update",
        {
            "connected": serial.connected,
            "handshake": serial.handshake
        }
    )



@app.route("/api/dmx/live-values", methods=["POST"])
def api_dmx_live_values():
    data = request.get_json(silent=True) or {}
    raw_values = data.get("values", {})

    if not isinstance(raw_values, dict):
        return jsonify(
            success=False,
            error="Invalid channel values"
        ), 400

    values = {}

    try:
        for raw_channel, raw_value in raw_values.items():
            channel = int(raw_channel)
            value = int(raw_value)

            if not 1 <= channel <= 512:
                return jsonify(
                    success=False,
                    error=f"Invalid DMX channel: {channel}"
                ), 400

            if not 0 <= value <= 255:
                return jsonify(
                    success=False,
                    error=f"Invalid DMX value: {value}"
                ), 400

            values[channel] = value

    except (TypeError, ValueError):
        return jsonify(
            success=False,
            error="Channel and value must be integers"
        ), 400

    if values:
        dmx_manager.apply_values(values)

    return jsonify(
        success=True,
        count=len(values)
    )




@app.route("/show")
def show():

    serial.update()
    problems = reference_checker.check()

    return render_template(
        "show.html",
        scenes=scene_manager.scenes,
        fades=fade_manager.fades,
        sequences=sequence_manager.sequences,
        triggers=trigger_manager.triggers,
        serial=serial, ip=get_local_ip(), port=settings.port, network_mode = settings.network_mode, create_qr=settings.create_qr, problems=problems
    )






# --------------------------------
# STROBES
# --------------------------------

@app.route("/strobes")
def strobes():

    return render_template(
        "strobes.html",
        strobes=strobe_manager.strobes
    )


@app.route("/strobes/add")
def add_strobe():

    strobe = {

        "id": strobe_manager.get_next_id(),

        "name": "",

        "cycles": 10,

        "time": 10000,

        "mode": "timed",

        "time_a": 100,

        "time_b": 100,

        "states": []
    }

    strobe_id = str(strobe_manager.get_next_id())

    save_strobe()
    return redirect("/strobes/edit?id=" + strobe_id)
    
    """return render_template(
        "strobe_edit.html",
        strobe=strobe,
        scenes=scene_manager.scenes,
        fades=fade_manager.fades
    )"""

@app.route("/strobes/edit")
def edit_strobe():

    strobe_id = request.args.get(
        "id",
        type=int
    )


    strobe = strobe_manager.get_id(
        strobe_id
    )


    if not strobe:

        return (
            "Strobe not found",
            404
        )


    return render_template(
        "strobe_edit.html",
        strobe=strobe,
        scenes=scene_manager.scenes,
        fades=fade_manager.fades
    )


@app.route(
    "/strobes/save",
    methods=["POST"]
)
def save_strobe():
    strobe_id = int(
        request.form.get(
            "id",
            0
        )
    )


    strobe = strobe_manager.get_id(
        strobe_id
    )


    # --------------------------------
    # Neuer Strobe
    # --------------------------------

    if not strobe:

        strobe = {

            "id":
                strobe_manager.get_next_id(),

            "name":
                "",

            "cycles":
                10,

            "time":
                10000,

            "mode":
                "timed",

            "time_a":
                100,

            "time_b":
                100,

            "states":
                []

        }


        strobe_manager.strobes.append(
            strobe
        )


    # --------------------------------
    # Allgemein
    # --------------------------------

    strobe["name"] = request.form.get(
        "name",
        ""
    )


    strobe["mode"] = request.form.get(
            "mode",
            "timed"
        )

    if strobe["mode"] == "counted":

        strobe["cycles"] = int(
            request.form.get(
                "cycles",
                10
            )
        )

    elif strobe["mode"] == "timed":

        strobe["time"] = int(
            request.form.get(
                "time",
                10000
            )
        )
    


    strobe["time_a"] = int(
        request.form.get(
            "time_a",
            100
        )
    )


    strobe["time_b"] = int(
        request.form.get(
            "time_b",
            100
        )
    )


    # --------------------------------
    # Zustände
    # --------------------------------

    state_types = request.form.getlist(
        "state_type"
    )

    state_targets = request.form.getlist(
        "state_target"
    )


    states = []


    for i, state_type in enumerate(
        state_types
    ):

        if i >= len(state_targets):

            continue


        target = state_targets[i]


        if not target:

            continue


        states.append(
            {
                "type": state_type,
                "target": int(target)
            }
        )


    strobe["states"] = states


    strobe_manager.save()


    return redirect(
        "/strobes"
    )

@app.route(
    "/strobes/change-mode"
)
def change_strobe_mode():

    strobe_id = request.args.get(
        "id",
        type=int
    )

    mode = request.args.get(
        "mode"
    )

    print(
        "Strobe-ID:",
        strobe_id,
        "Mode:",
        mode
    )

    if not strobe_manager.change_mode(
        strobe_id,
        mode
    ):
        return redirect(request.referrer or "/strobes")

    return redirect(
        request.referrer or "/strobes"
    )


@app.route("/strobes/delete")
def delete_strobe():

    strobe_id = request.args.get(
        "id",
        type=int
    )


    if not strobe_manager.delete(
        strobe_id
    ):

        return (
            "Strobe not found",
            404
        )


    return redirect(
        "/strobes"
    )


@app.route("/strobes/duplicate")
def duplicate_strobe():

    strobe_id = request.args.get(
        "id",
        type=int
    )


    strobe = strobe_manager.duplicate(
        strobe_id
    )


    if not strobe:

        return (
            "Strobe not found",
            404
        )


    return redirect(
        "/strobes"
    )


@app.route("/strobes/start")
def start_strobe():

    strobe_id = request.args.get(
        "id",
        type=int
    )

    strobe = strobe_manager.get_id(
        strobe_id
    )

    if not strobe:
        return "Strobe not found", 404

    strobe_manager.start(
        strobe
    )

    return "OK"


@app.route("/strobes/stop")
def stop_strobe():

    strobe_manager.stop()

    return "OK"



@app.get("/api/audio/devices")
def audio_devices():
    try:
        return jsonify({
            "devices": AudioAnalyzer.list_devices()
        })
    except Exception as exc:
        app.logger.exception("Audio-Geräteliste konnte nicht geladen werden")
        return jsonify({
            "error": str(exc)
        }), 500


@app.get("/api/audio/status")
def audio_status():
    return jsonify(audio_analyzer.get_state())


@app.post("/api/audio/start")
def audio_start():
    data = request.get_json(silent=True) or {}
    device_index = data.get("device_index")

    if device_index is None:
        return jsonify({
            "error": "Bitte ein Audiogerät auswählen."
        }), 400

    try:
        audio_analyzer.start(int(device_index))
        return jsonify(audio_analyzer.get_state())

    except (TypeError, ValueError) as exc:
        return jsonify({
            "error": str(exc)
        }), 400

    except Exception as exc:
        app.logger.exception("Audio-Capture konnte nicht gestartet werden")
        return jsonify({
            "error": str(exc)
        }), 500


@app.post("/api/audio/stop")
def audio_stop():
    try:
        audio_analyzer.stop()
        return jsonify(audio_analyzer.get_state())

    except Exception as exc:
        app.logger.exception("Audio-Capture konnte nicht gestoppt werden")
        return jsonify({
            "error": str(exc)
        }), 500


# ============================================================
# MUSIC SYNC API
# ============================================================

@app.get("/api/music/config")
def music_config_get():
    return jsonify({
        "beat": music_beat_engine.get_config(),
        "show": music_show_engine.get_config(),
    })


@app.post("/api/music/config")
def music_config_save():
    data = request.get_json(silent=True) or {}

    try:
        beat_config = data.get("beat", {})
        show_config = data.get("show", {})

        if not isinstance(beat_config, dict):
            raise ValueError("Ungültige Beat-Konfiguration.")

        if not isinstance(show_config, dict):
            raise ValueError("Ungültige Show-Konfiguration.")

        music_beat_engine.configure(beat_config)
        music_show_engine.set_config(show_config)

        return jsonify({
            "success": True,
            "beat": music_beat_engine.get_config(),
            "show": music_show_engine.get_config(),
        })

    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    except Exception as exc:
        app.logger.exception("Music-Sync-Konfiguration konnte nicht gespeichert werden")
        return jsonify({"error": str(exc)}), 500


@app.get("/api/music/status")
def music_status():
    return jsonify({
        "audio": audio_analyzer.get_state(),
        "beat": music_beat_engine.get_state(),
        "show": music_show_engine.get_state(),
    })


@app.post("/api/music/start")
def music_start():
    if not audio_analyzer.get_state().get("running"):
        return jsonify({
            "error": "Bitte zuerst unter /audio die Audio-Erfassung starten."
        }), 400

    try:
        music_beat_engine.start()

        # Beat-Aktionen sind optional.
        show_config = music_show_engine.get_config()

        if (
            show_config.get("enabled")
            and show_config.get("actions")
        ):
            music_show_engine.start()

        return jsonify({
            "success": True,
            "beat": music_beat_engine.get_state(),
            "show": music_show_engine.get_state(),
        })

    except (TypeError, ValueError) as exc:
        music_show_engine.stop()
        music_beat_engine.stop()

        return jsonify({"error": str(exc)}), 400

    except Exception as exc:
        music_show_engine.stop()
        music_beat_engine.stop()

        app.logger.exception("Music-Sync konnte nicht gestartet werden")
        return jsonify({"error": str(exc)}), 500


@app.post("/api/music/stop")
def music_stop():
    # Stoppt die Musiksteuerung, nicht den gesamten ShowController.
    music_show_engine.stop()
    music_beat_engine.stop()

    return jsonify({
        "success": True,
        "beat": music_beat_engine.get_state(),
        "show": music_show_engine.get_state(),
    })
# ============================================================
# AUDIO SEQUENCES API
# ============================================================

# ----------------------------
# Audio Sequence Pages
# ----------------------------

@app.get("/audio")
def audio_page():
    return render_template("audio.html")




@app.get("/audio-sequences/edit")
def audio_sequence_edit_page():
    mode = request.args.get("mode", "").strip().lower()
    sequence_id = request.args.get("id", "").strip()

    if mode == "new":
        sequence = {
            "version": 1,
            "name": "",
            "description": "",
            "use_global_settings": False,
            "overrides": {
                "source": "bass",
                "sensitivity": 150,
                "min_interval_ms": 120,
                "device_index": None,
                "eq_weights": [180, 300, 200, 80, 50, 40, 25, 15],
            },
            "reaction": {
                "enabled": True,
                "movement_speed": 0.85,
                "color_change": 0.75,
                "intensity": 0.9,
                "strobe_enabled": False,
            },
            "every_beats": 1,
            "actions": [],
        }

        return render_template(
            "audio_sequence_edit.html",
            sequence=sequence,
            settings=dict(sequence["overrides"]),
            scenes=scene_manager.scenes,
            fades=fade_manager.fades,
            is_new=True,
            strobes=strobe_manager.strobes
        )

    if not sequence_id:
        return "Audio sequence ID is required", 400

    try:
        sequence = audio_sequence_manager.load_sequence(sequence_id)
        settings = audio_sequence_manager.get_effective_settings(sequence)

        return render_template(
            "audio_sequence_edit.html",
            sequence=sequence,
            settings=settings,
            scenes=scene_manager.scenes,
            fades=fade_manager.fades,
            is_new=False,
            strobes=strobe_manager.strobes
        )

    except FileNotFoundError:
        return "Audio sequence not found", 404
    except ValueError as error:
        return str(error), 400



# ============================================================
# AUDIO SEQUENCE API
# All sequence operations use stable sequence IDs.
# ============================================================

@app.get("/api/audio-sequences")
def audio_sequences_list():
    try:
        return jsonify({
            "success": True,
            "sequences": audio_sequence_manager.list_sequences(),
            "state": audio_sequence_manager.get_state(),
        })
    except Exception:
        app.logger.exception("Failed to list audio sequences")
        return jsonify({
            "success": False,
            "error": "Failed to load audio sequences.",
        }), 500



@app.post("/api/audio-sequences")
def audio_sequences_create():
    try:
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()

        if not name:
            return jsonify({
                "success": False,
                "error": "Sequence name is required."
            }), 400

        # create_sequence() returns the complete sequence dictionary.
        sequence = audio_sequence_manager.create_sequence(name, data)
        sequence_id = sequence["id"]

        return jsonify({
            "success": True,
            "sequence_id": sequence_id,
            "sequence": sequence
        }), 201

    except Exception as exc:
        app.logger.exception("Failed to create audio sequence")
        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500



@app.get("/api/audio-sequences/<sequence_id>")
def audio_sequences_get(sequence_id):
    try:
        sequence = audio_sequence_manager.load_sequence(sequence_id)

        return jsonify({
            "success": True,
            "sequence": sequence,
        })

    except (ValueError, FileNotFoundError) as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 404
    except Exception:
        app.logger.exception("Failed to load audio sequence")
        return jsonify({
            "success": False,
            "error": "Failed to load audio sequence.",
        }), 500


@app.put("/api/audio-sequences/<sequence_id>")
def audio_sequences_update(sequence_id):
    try:
        data = request.get_json(silent=True) or {}

        # The ID is fixed; only the sequence data/name can change.
        data.pop("id", None)
        data.pop("sequence_id", None)

        audio_sequence_manager.save_sequence(sequence_id, data)

        return jsonify({
            "success": True,
            "sequence": audio_sequence_manager.load_sequence(sequence_id),
        })

    except ValueError as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400
    except (FileNotFoundError, KeyError) as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 404
    except Exception:
        app.logger.exception("Failed to save audio sequence")
        return jsonify({
            "success": False,
            "error": "Failed to save audio sequence.",
        }), 500


@app.delete("/api/audio-sequences/<sequence_id>")
def audio_sequences_delete(sequence_id):
    try:
        audio_sequence_manager.delete_sequence(sequence_id)

        return jsonify({
            "success": True,
            "sequence_id": sequence_id,
        })

    except ValueError as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400
    except (FileNotFoundError, KeyError) as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 404
    except Exception:
        app.logger.exception("Failed to delete audio sequence")
        return jsonify({
            "success": False,
            "error": "Failed to delete audio sequence.",
        }), 500


@app.post("/api/audio-sequences/<sequence_id>/duplicate")
def audio_sequences_duplicate(sequence_id):
    try:
        data = request.get_json(silent=True) or {}
        new_name = data.get("name")

        new_id = audio_sequence_manager.duplicate_sequence(
            sequence_id,
            new_name=new_name,
        )

        return jsonify({
            "success": True,
            "sequence_id": new_id,
            "sequence": audio_sequence_manager.load_sequence(new_id),
        }), 201

    except ValueError as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400
    except (FileNotFoundError, KeyError) as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 404
    except Exception:
        app.logger.exception("Failed to duplicate audio sequence")
        return jsonify({
            "success": False,
            "error": "Failed to duplicate audio sequence.",
        }), 500


@app.get("/api/audio-sequences/<sequence_id>/settings")
def audio_sequences_effective_settings(sequence_id):
    try:
        sequence = audio_sequence_manager.load_sequence(sequence_id)
        settings = audio_sequence_manager.get_effective_settings(sequence)

        return jsonify({
            "success": True,
            "settings": settings,
        })

    except (ValueError, FileNotFoundError) as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 404
    except Exception:
        app.logger.exception("Failed to load effective audio settings")
        return jsonify({
            "success": False,
            "error": "Failed to load effective audio settings.",
        }), 500


@app.post("/api/audio-sequences/<sequence_id>/start")
def audio_sequences_start(sequence_id):
    try:
        result = start_audio_sequence(sequence_id)
        return jsonify(result)

    except (ValueError, FileNotFoundError) as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400
    except Exception:
        app.logger.exception("Failed to start audio sequence")
        return jsonify({
            "success": False,
            "error": "Failed to start audio sequence.",
        }), 500


@app.get("/api/audio-sequences/active")
def audio_sequences_active():
    state = audio_sequence_manager.get_state()
    active_id = state.get("active_sequence")

    active_name = None

    if active_id:
        try:
            active_name = audio_sequence_manager.load_sequence(
                active_id
            ).get("name")
        except (ValueError, FileNotFoundError):
            active_name = None

    return jsonify({
        "success": True,
        "state": {
            "running": state.get("running", False),
            "active_sequence_id": active_id,
            "active_sequence_name": active_name,
            "error": state.get("error"),
        },
    })



# ============================================================
# AUDIO SEQUENCE CONTROLLER
# ============================================================

audio_sequence_lock = threading.RLock()
active_audio_sequence = None




def start_audio_sequence(sequence_id):
    global active_audio_sequence

    with audio_sequence_lock:
        # Load the sequence by its stable ID.
        sequence = audio_sequence_manager.load_sequence(sequence_id)
        sequence_id = sequence["id"]

        audio_settings = audio_sequence_manager.get_effective_settings(
            sequence
        )

        device_index = audio_settings.get("device_index")

        # Reuse the current capture device if no device is configured.
        current_audio = audio_analyzer.get_state()

        if device_index is None and current_audio.get("running"):
            device_index = current_audio.get("device_index")

        if device_index is None:
            raise ValueError(
                "No audio device configured. "
                "Please select a device in the global audio settings."
            )

        # Stop the previous sequence and music control.
        music_show_engine.stop()
        music_beat_engine.stop()

        current_audio = audio_analyzer.get_state()

        if (
            not current_audio.get("running")
            or current_audio.get("device_index") != int(device_index)
        ):
            audio_analyzer.start(int(device_index))

        # Apply this sequence's beat detection settings.
        music_beat_engine.configure({
            "source": audio_settings["source"],
            "sensitivity": audio_settings["sensitivity"],
            "min_interval_ms": audio_settings["min_interval_ms"],
            "eq_weights": audio_settings["eq_weights"],
        })

        # Store the stable ID, not the editable display name.
        audio_sequence_manager.start(sequence_id)
        active_audio_sequence = sequence_id

        music_beat_engine.start()

        if sequence.get("actions"):
            music_show_engine.start_sequence(sequence)

        return {
            "success": True,
            "active_sequence": active_audio_sequence,
            "sequence_id": sequence_id,
            "sequence_name": sequence["name"],
            "audio": audio_analyzer.get_state(),
            "beat": music_beat_engine.get_state(),
            "show": music_show_engine.get_state(),
            "settings": audio_settings,
            "reaction": sequence.get("reaction", {}),
        }



def stop_audio_sequence():
    global active_audio_sequence

    with audio_sequence_lock:
        # Erst die Reaktionen und Beat-Erkennung stoppen.
        music_show_engine.stop()
        music_beat_engine.stop()

        # Danach den Audio-Capture beenden.
        audio_analyzer.stop()

        audio_sequence_manager.stop()
        active_audio_sequence = None

        return {
            "success": True,
            "active_sequence": None,
            "audio": audio_analyzer.get_state(),
            "beat": music_beat_engine.get_state(),
            "show": music_show_engine.get_state(),
        }


trigger_engine.set_audio_sequence_callbacks(
    start_callback=start_audio_sequence,
    stop_callback=stop_audio_sequence,
)

@app.post("/api/audio-sequences/<name>/start")
def audio_sequence_start(name):
    try:
        result = start_audio_sequence(name)
        return jsonify(result)

    except FileNotFoundError as error:
        return jsonify({
            "success": False,
            "error": str(error),
        }), 404

    except (ValueError, TypeError) as error:
        return jsonify({
            "success": False,
            "error": str(error),
        }), 400

    except Exception as error:
        app.logger.exception(
            "Audio-Sequenz konnte nicht gestartet werden"
        )
        return jsonify({
            "success": False,
            "error": str(error),
        }), 500



@app.route("/timeline-test")
def timeline_test():
    return render_template("timeline_test.html", mode="edit")
