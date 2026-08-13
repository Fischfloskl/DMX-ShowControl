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

import re
import os
import threading
import time


app = Flask(__name__)

socketio.init_app(app)


url = create_qr()
print("Webinterface:")
print(url)


# ----------------------------
# Grundsystem
# ----------------------------

serial = SerialManager()

dmx_manager = DMXManager(
    serial
)

trigger_manager = TriggerManager()
scene_manager = SceneManager()

# ----------------------------
# Engines
# ----------------------------

fade_engine = FadeEngine(
    dmx_manager,
    devices,
    settings
)

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


# ----------------------------
# Weitere Manager
# ----------------------------

reference_checker = ReferenceChecker(
    scene_manager,
    sequence_manager,
    trigger_manager
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
    sequence_manager,
    trigger_manager,
    devices
)

import_manager = ImportManager(
    scene_manager,
    fade_manager,
    sequence_manager,
    trigger_manager,
    devices
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
def inject_mode():

    return {
        "mode": settings.get("mode"),
        "problems":reference_checker.check()
    }

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
    print("reset der Trigger-zeitmessung")

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
        return "Ungültiger Modus", 400

    settings.set(
        "mode",
        mode
    )

    settings.save()

    return redirect("/")

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
        return "Fade nicht gefunden", 404


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
        return "Fade nicht gefunden", 404

    return redirect(
        request.referrer or "/fades"
    )

@app.route("/fades/add")
def add_fade():

    fade = {

        "id": fade_manager.next_id(),

        "name": "Neuer Fade",

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
        return "Fade nicht gefunden",404


    print("FADE:")
    print(fade)

    print("DEVICES:")
    print(devices.devices)


    return render_template(
        "fade_edit.html",
        fade=fade,
        devices=devices.devices
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
        return "Fade nicht gefunden",404


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
        return "Nicht gefunden",404



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


    fade_id=int(
        request.form["fade_id"]
    )


    device_id=int(
        request.form["device_id"]
    )

    fade=fade_manager.get_id(
        fade_id
    )


    if not fade:
        return "Fade nicht gefunden",404

    fade["mode"] = request.form.get(
        "mode",
        "merge"
    )
    
    print(fade["mode"])



    result=[]


    device=devices.get_id(
        device_id
    )


    for i in range(
        1,
        device["channels"]+1
    ):


        enabled = (
            f"enable_{i}"
            in request.form
        )


        result.append({

            "channel":i,

            "enabled":enabled,

            "start":int(
                request.form.get(
                    f"start_{i}",
                    0
                )
            ),

            "end":int(
                request.form.get(
                    f"end_{i}",
                    255
                )
            )

        })



    found=False


    for d in fade["devices"]:

        if d["device"] == device_id:

            d["channels"]=result
            found=True



    if not found:

        fade["devices"].append({

            "device":device_id,

            "channels":result

        })


    fade_manager.save()


    return redirect(
        f"/fades/edit?id={fade_id}"
    )

@app.route("/fades/start")
def start_fade():

    fade = fade_manager.get_id(
        int(request.args["id"])
    )

    if not fade:
        return "Fade nicht gefunden", 404

    fade_engine.play(fade)

    return "OK"

@app.route("/fades/save", methods=["POST"])
def save_fade():


    fade_id=int(
        request.form["id"]
    )


    fade=fade_manager.get_id(
        fade_id
    )


    fade["name"]=request.form["name"]

    duration=int(
        request.form["duration"]
    )


    unit=request.form.get(
        "duration_unit"
    )


    if unit=="sec":
        duration*=1000

    elif unit=="min":
        duration*=60000



    fade["duration"]=duration


    fade_manager.save()


    return redirect(
        "/fades"
    )


@app.route("/dmx/clear")
def dmx_clear():


    show_controller.stop_all()

    dmx_manager.clear()
    strobe_manager.stop()

    time.sleep(0.05)

    show_controller.reset()
    
    dmx_manager.reset_all()

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

        return "Szene nicht gefunden",404



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
        return "Szene nicht gefunden", 404

    return redirect(
        request.referrer or "/scenes"
    )

# --------------------------------
# Gerät zu Szene hinzufügen
# --------------------------------


@app.route("/scenes/device/add")
def add_device_to_scene():

    scene_id = int(request.args.get("scene"))
    device_id = int(request.args.get("device"))


    scene = scene_manager.get_id(scene_id)

    if not scene:
        return "Szene nicht gefunden",404



    if "devices" not in scene:

        scene["devices"] = {}



    scene["devices"][str(device_id)] = {}



    scene_manager.save()



    return redirect(
        "/scenes/edit?id=" + str(scene_id)
    )



# --------------------------------
# Gerät entfernen
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

        return "Szene nicht gefunden",404



    if str(device_id) in scene["devices"]:

        del scene["devices"][str(device_id)]



    scene_manager.save()


    return redirect(
        "/scenes/edit?id=" + str(scene_id)
    )



# --------------------------------
# Gerät bearbeiten
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
        return "Szene nicht gefunden",404



    device = devices.get_id(device_id)

    if not device:
        return "Gerät nicht gefunden",404



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
        return "Szene nicht gefunden",404



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
        print("Keine Kanäle empfangen - nichts gespeichert")



    scene_manager.save()



    return redirect(
        "/scenes/edit?id=" + str(scene_id)
    )



# --------------------------------
# Szene allgemein speichern
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

        return "Szene nicht gefunden",404



    scene["name"] = request.form["name"]


    scene_manager.save()



    return redirect(
        "/scenes"
    )



# --------------------------------
# Szene löschen
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
        strobes=strobe_manager.strobes
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

        return "Trigger nicht gefunden",404



    return render_template(
        "trigger_edit.html",
        trigger=trigger,
        scenes=scene_manager.scenes,
        fades=fade_manager.fades,
        sequences=sequence_manager.sequences,
        strobes=strobe_manager.strobes
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
        trigger["input"] = request.form.get(
            "midi_input",
            ""
        )

    # Aktionen neu aufbauen

    types = request.form.getlist(
        "action_type"
    )

    targets = request.form.getlist(
        "action_target"
    )

    keys = request.form.getlist(
        "action_keys"
    )


    actions = []


    for i, action_type in enumerate(types):


        action = {
            "type": action_type
        }


        if action_type == "keyboard":

            if i < len(keys):

                action["keys"] = [
                    k for k in keys[i].split(",")
                    if k
                ]


        else:

            if i < len(targets):

                action["target"] = targets[i]



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
        return "Trigger nicht gefunden", 404

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
        return "Trigger nicht gefunden", 404

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
        return "Gerät nicht gefunden", 404

    return redirect(
        request.referrer or "/devices"
    )

@app.route("/devices/add", methods=["POST"])
def add_device():

    device = {
        "id": len(devices.devices) + 1,
        "name": request.form["name"],
        "start_channel": int(request.form["address"]),
        "channels": int(request.form["channels"]),
        "color": request.form["color"],
        "channel_names": [
            f"CH{i+1}"
            for i in range(int(request.form["channels"]))
        ]
    }

    devices.add(device)

    return redirect("/devices")

@app.route("/devices/delete")
def delete_device():

    device_id = int(
        request.args.get("id")
    )

    print("Lösche Gerät:", device_id)
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

        return "Gerät nicht gefunden", 404


    return render_template(
        "device_edit.html",
        device=device
    )

@app.route("/devices/edit/save", methods=["POST"])
def save_device():

    device_id = int(request.form["id"])


    for d in devices.devices:

        if d["id"] == device_id:

            old_channels = d["channels"]

            new_channels = int(
                request.form["channels"]
            )


            d["name"] = request.form["name"]

            d["start_channel"] = int(
                request.form["start_channel"]
            )

            d["channels"] = new_channels

            d["color"] = request.form["color"]



            # Kanalnamen neu erzeugen
            new_names = []

            for i in range(new_channels):

                key = f"channel_{i+1}"

                if key in request.form:

                    new_names.append(
                        request.form[key]
                    )

                elif i < len(d["channel_names"]):

                    new_names.append(
                        d["channel_names"][i]
                    )

                else:

                    new_names.append(
                        f"CH{i+1}"
                    )


            d["channel_names"] = new_names


            break


    devices.save()


    return redirect("/devices")

@app.route("/settings")
def settings_page():

    return render_template(
        "settings.html",
        create_qr = settings.create_qr,
        refresh_rate = settings.refresh_rate,
        network_mode = settings.network_mode,
        port = settings.port
    )

@app.route("/settings/export")
def export_show():


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


@app.route(
    "/settings/import",
    methods=["POST"]
)
def import_show():


    file = request.files.get(
        "file"
    )


    if not file:

        return "Keine Datei",400



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


    settings.save()

    #return redirect("/settings")
    return redirect("/")

@app.route("/settings/save-timing", methods=["POST"])
def save_settings_timing():

    settings.set(
        "timing-mode",
        request.form["timing-mode"]
    )

    settings.save()

    #return redirect("/settings")
    return redirect("/timing")

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
        return "Sequenz nicht gefunden", 404

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
        "Neue Sequenz",

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
        return "Sequenz nicht gefunden",404


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

        "name": "Neuer Strobe",

        "cycles": 10,

        "time": 10000,

        "mode": "timed",

        "time_a": 100,

        "time_b": 100,

        "states": []
    }


    return render_template(
        "strobe_edit.html",
        strobe=strobe,
        scenes=scene_manager.scenes,
        fades=fade_manager.fades
    )


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
            "Strobe nicht gefunden",
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
        "Neuer Strobe"
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
        return (
            "Strobe oder Modus ungültig",
            400
        )

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
            "Strobe nicht gefunden",
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
            "Strobe nicht gefunden",
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
        return "Strobe nicht gefunden", 404

    strobe_manager.start(
        strobe
    )

    return "OK"


@app.route("/strobes/stop")
def stop_strobe():

    strobe_manager.stop()

    return "OK"