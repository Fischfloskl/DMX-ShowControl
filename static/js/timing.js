// ============================================================
// timing.js
// ============================================================


// ============================================================
// LIVE TIMING
// ============================================================

let running = false;
let startTime = 0;
let elapsed = 0;
let animationFrame = null;

//let recordKey = null;

let recordingRecordKey = false;


// ------------------------------------------------------------
// Live Timer starten / stoppen
// ------------------------------------------------------------

function toggleTimer() {

    const button =
        document.getElementById("recordButton");

    if (!button)
        return;


    if (!running) {

        running = true;

        startTime =
            performance.now() - elapsed;

        button.textContent =
            "Stop";

        updateTimer();

    } else {

        running = false;

        elapsed =
            performance.now() - startTime;

        button.textContent =
            "Record";

        cancelAnimationFrame(
            animationFrame
        );

        updateDisplay();
    }
}


// ------------------------------------------------------------
// Live Timer Update
// ------------------------------------------------------------

function updateTimer() {

    if (!running)
        return;


    elapsed =
        performance.now() - startTime;

    updateDisplay();


    animationFrame =
        requestAnimationFrame(
            updateTimer
        );
}


// ------------------------------------------------------------
// Live Anzeige
// ------------------------------------------------------------

function updateDisplay() {

    const timer =
        document.getElementById("timer");

    const unit =
        document.getElementById("unitSelect");


    if (!timer || !unit)
        return;


    if (unit.value === "ms") {

        timer.textContent =
            elapsed.toFixed(0) + " ms";

    }

    else if (unit.value === "min") {

        timer.textContent =
            (elapsed / 60000)
                .toFixed(3)
            + " min";

    }

    else {

        timer.textContent =
            (elapsed / 1000)
                .toFixed(3)
            + " s";
    }
}


// ------------------------------------------------------------
// Live Reset
// ------------------------------------------------------------

function resetTimer() {

    running = false;

    elapsed = 0;

    cancelAnimationFrame(
        animationFrame
    );


    const button =
        document.getElementById("recordButton");

    if (button)
        button.textContent = "Record";


    updateDisplay();
}


// ------------------------------------------------------------
// Live Copy
// ------------------------------------------------------------

function copyTimer(btn) {

    const timer =
        document.getElementById("timer");

    if (!timer)
        return;


    const text =
        timer.textContent.trim();


    const temp =
        document.createElement("textarea");

    temp.value = text;

    document.body.appendChild(temp);

    temp.select();

    temp.setSelectionRange(
        0,
        99999
    );


    try {

        document.execCommand("copy");

    } catch (err) {

        console.log(
            "Copy failed",
            err
        );
    }


    document.body.removeChild(temp);


    if (btn) {

        const old =
            btn.innerHTML;

        btn.innerHTML =
            "✔";


        setTimeout(() => {

            btn.innerHTML =
                old;

        }, 1200);
    }
}





// ============================================================
// LIVE HOTKEY AUFNEHMEN
// ============================================================

function startLivePlayKeyRecording() {

    if (recordingRecordKey)
        return;


    recordingRecordKey = true;


    const button =
        document.getElementById(
            "hotkeyButtonLive"
        );

    const display =
        document.getElementById(
            "hotkeyDisplayLive"
        );


    if (button)
        button.textContent =
            "Taste drücken...";


    if (display)
        display.textContent =
            "Drücke jetzt die gewünschte Taste";


    function keyHandler(event) {

        event.preventDefault();


        recordKey =
            event.key.toLowerCase();


        if (display) {

            display.textContent =
                "Aktuelle Taste: " +
                event.key;
        }


        if (button)
            button.textContent =
                "Taste aufnehmen";


        recordingRecordKey = false;


        document.removeEventListener(
            "keydown",
            keyHandler
        );


        fetch(
            "/timing/live/save-key",
            {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    key: recordKey
                })
            }
        );
    }


    document.addEventListener(
        "keydown",
        keyHandler
    );
}


// ============================================================
// LIVE HOTKEY
// ============================================================

document.addEventListener(
    "keydown",
    function(event) {

        if (timingMode === "global")
            return;


        if (recordingRecordKey)
            return;


        if (!recordKey)
            return;


        if (!keysEqual(
            event.key,
            recordKey
        ))
            return;


        event.preventDefault();

        toggleTimer();
    }
);


// ============================================================
// KEY NORMALISIERUNG
// ============================================================

function normalizeKey(key) {

    key =
        String(key);


    if (key === " ")
        return "space";


    return key
        .toLowerCase()
        .replace(
            /[\s_\/-]/g,
            ""
        );
}


const KEY_NAMES = {

    "mediaplaypause":
        "MediaPlayPause",

    "mediatracknext":
        "MediaTrackNext",

    "mediatrackprevious":
        "MediaTrackPrevious",

    "mediastop":
        "MediaStop",

    "audiovolumeup":
        "AudioVolumeUp",

    "audiovolumedown":
        "AudioVolumeDown",

    "audiovolumemute":
        "AudioVolumeMute",

    "control":
        "Control",

    "ctrl":
        "Control",

    "shift":
        "Shift",

    "alt":
        "Alt",

    "meta":
        "Meta",

    "windows":
        "Meta",

    "enter":
        "Enter",

    "escape":
        "Escape",

    "esc":
        "Escape",

    "arrowup":
        "ArrowUp",

    "up":
        "ArrowUp",

    "arrowdown":
        "ArrowDown",

    "down":
        "ArrowDown",

    "arrowleft":
        "ArrowLeft",

    "left":
        "ArrowLeft",

    "arrowright":
        "ArrowRight",

    "right":
        "ArrowRight",

    "backspace":
        "Backspace",

    "tab":
        "Tab",

    "space":
        " "
};


function getJSKey(key) {

    const normalized =
        normalizeKey(key);


    return (
        KEY_NAMES[normalized]
        || key
    );
}


function keysEqual(a, b) {

    return (
        normalizeKey(a)
        ===
        normalizeKey(b)
    );
}


// ============================================================
// GLOBAL TRIGGER TIMING
// ============================================================

let globalTimerElapsed = 0;


// ------------------------------------------------------------
// Socket.IO
// ------------------------------------------------------------

const socket = io();


// ------------------------------------------------------------
// NEUE GEMESSENE ZEIT
// ------------------------------------------------------------
//
// Python sendet:
//
// timing_update
// {
//     elapsed: 1.234
// }
//
// Diese Zeit ist immer die zuletzt
// vollständig abgeschlossene Zeit.
// ------------------------------------------------------------

socket.on(
    "timing_update",
    function(data) {

        globalTimerElapsed =
            Number(data.elapsed) || 0;


        updateDisplayglobal();
    }
);


// ------------------------------------------------------------
// RESET
// ------------------------------------------------------------

socket.on(
    "timing_reset",
    function() {

        global_time = 0;

        location.reload();
        updateDisplayglobal();
        
    }
);


// ------------------------------------------------------------
// GLOBAL ANZEIGE
// ------------------------------------------------------------

function updateDisplayglobal() {

    const timer =
        document.getElementById(
            "timer-global"
        );

    const unit =
        document.getElementById(
            "unitSelect"
        );


    if (!timer || !unit)
        return;


    if (unit.value === "ms") {

        timer.textContent =
            (global_time * 1000)
                .toFixed(0)
            + " ms";

    }

    else if (
        unit.value === "min"
    ) {

        timer.textContent =
            (global_time / 60)
                .toFixed(3)
            + " min";

    }

    else {

        timer.textContent =
            global_time
                .toFixed(3)
            + " s";
    }
}

// ------------------------------------------------------------
// GLOBAL RESET
// ------------------------------------------------------------

function resetTimerglobal() {

    global_time = 0;
    
    updateDisplayglobal();

    fetch("/timing/reset", {
        method: "POST"
    });
}


// ------------------------------------------------------------
// GLOBAL COPY
// ------------------------------------------------------------

function copyTimerglobal(btn) {

    const timer =
        document.getElementById(
            "timer-global"
        );


    if (
        global_time === null ||
        global_time === undefined
    )
        return;


    const text = global_time.toFixed(3);

    const temp =
        document.createElement(
            "textarea"
        );


    temp.value =
        text;

    document.body.appendChild(
        temp
    );


    temp.select();

    temp.setSelectionRange(
        0,
        99999
    );


    try {

        document.execCommand(
            "copy"
        );

    } catch (err) {

        console.log(
            "Copy failed",
            err
        );
    }


    document.body.removeChild(
        temp
    );


    if (btn) {

        const old =
            btn.innerHTML;


        btn.innerHTML =
            "✔";


        setTimeout(() => {

            btn.innerHTML =
                old;

        }, 1200);
    }
}


// ============================================================
// INITIALISIERUNG
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        updateDisplayglobal();
    }
);