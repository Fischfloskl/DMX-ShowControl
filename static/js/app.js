function reconnect(){

    //if(!confirm("Reconnect the DMX controller? This process may take 5 seconds.")){
    //return;
    //}
    let button = document.getElementById("reconnect-button")
    button.innerHTML = "Connecting...";


    fetch("/api/reconnect", {
        method: "POST"
    })
    .then(response => response.json())
    .then(data => {

        location.reload();

    });

}


function initCollapsibleCards() {
    const cardSelectors = ".card-collapsed, .card-uncolapsed";

    document.querySelectorAll(cardSelectors).forEach((card) => {
        const header = card.querySelector(".card-header");

        if (!header || card.dataset.collapseInitialized === "true") {
            return;
        }

        // card-collapsed starts closed; card-uncolapsed starts open.
        if (card.classList.contains("card-collapsed")) {
            card.classList.add("is-collapsed");
        }

        header.setAttribute("role", "button");
        header.setAttribute("tabindex", "0");
        header.setAttribute(
            "aria-expanded",
            String(!card.classList.contains("is-collapsed"))
        );

        function toggleCard() {
            const isCollapsed = card.classList.toggle("is-collapsed");

            header.setAttribute("aria-expanded", String(!isCollapsed));
        }

        header.addEventListener("click", toggleCard);

        header.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                toggleCard();
            }
        });

        card.dataset.collapseInitialized = "true";
    });
}

document.addEventListener("DOMContentLoaded", initCollapsibleCards);



document.addEventListener("keydown", function (event) {
    // Ctrl+S on Windows/Linux, Cmd+S on macOS
    if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "s") {
        return;
    }

    // Do not interfere with text editing fields.
    const target = event.target;
    if (
        target instanceof HTMLElement &&
        (
            target.isContentEditable ||
            ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
        )
    ) {
        return;
    }

    const saveButton = document.querySelector(
        ".save-button:not(:disabled)"
    );

    if (!saveButton) {
        return;
    }

    event.preventDefault();
    saveButton.click();
});



/* ============================================================
   DMX Color Picker
   Persistent HSV picker for RGB DMX zones
   ============================================================ */

function initDMXColorPickers() {
    document.querySelectorAll(".dmx-color-picker").forEach((picker) => {
        if (picker.dataset.initialized === "true") {
            return;
        }

        picker.dataset.initialized = "true";

        const wrapper = document.createElement("div");
        wrapper.className = "dmx-color-picker-wrapper";

        const canvas = document.createElement("canvas");
        canvas.width = 240;
        canvas.height = 160;
        canvas.className = "dmx-color-canvas";
        canvas.style.cssText =
            "display:block;width:100%;max-width:360px;height:auto;cursor:crosshair;border-radius:6px;touch-action:none;";

                
        const hueSlider = document.createElement("input");
        hueSlider.type = "range";
        hueSlider.min = "0";
        hueSlider.max = "360";
        hueSlider.value = "0";
        hueSlider.title = "Hue";
        hueSlider.style.cssText = "width:100%;max-width:360px;";

        const hueLabel = document.createElement("div");
        hueLabel.textContent = "Hue";
        hueLabel.style.cssText = "font-size:12px;color:#888;margin-top:8px;";

        const brightness = document.createElement("input");
        brightness.type = "range";
        brightness.min = "0";
        brightness.max = "100";
        brightness.value = "100";
        brightness.style.cssText = "width:100%;max-width:360px;";

        const brightnessLabel = document.createElement("div");
        brightnessLabel.textContent = "Brightness";
        brightnessLabel.style.cssText = "font-size:12px;color:#888;margin-top:8px;";


        const preview = document.createElement("div");
        preview.style.cssText =
            "height:24px;max-width:360px;border-radius:4px;margin-top:8px;border:1px solid #555;";

        wrapper.append(
            canvas,
            hueLabel,
            hueSlider,
            brightnessLabel,
            brightness,
            preview
        );
        picker.parentNode.insertBefore(wrapper, picker);
        picker.hidden = true;

        const ctx = canvas.getContext("2d");

        let hue = 0;
        let saturation = 1;
        let value = 1;

        function drawPalette() {
            const image = ctx.createImageData(canvas.width, canvas.height);

            for (let y = 0; y < canvas.height; y++) {
                for (let x = 0; x < canvas.width; x++) {
                    const sat = x / (canvas.width - 1);
                    const val = 1 - y / (canvas.height - 1);

                    const rgb = hsvToRgb(hue, sat, val);
                    const i = (y * canvas.width + x) * 4;

                    image.data[i] = rgb.r;
                    image.data[i + 1] = rgb.g;
                    image.data[i + 2] = rgb.b;
                    image.data[i + 3] = 255;
                }
            }

            ctx.putImageData(image, 0, 0);

            const markerX = saturation * (canvas.width - 1);
            const markerY = (1 - value) * (canvas.height - 1);

            ctx.beginPath();
            ctx.arc(markerX, markerY, 5, 0, Math.PI * 2);
            ctx.strokeStyle = value > 0.5 ? "#000" : "#fff";
            ctx.lineWidth = 2;
            ctx.stroke();

            updateOutput();
        }

        function hsvToRgb(h, s, v) {
            const f = (n, k = (n + h / 60) % 6) =>
                v - v * s * Math.max(Math.min(k, 4 - k, 1), 0);

            return {
                r: Math.round(f(5) * 255),
                g: Math.round(f(3) * 255),
                b: Math.round(f(1) * 255)
            };
        }

        function rgbToHsv(r, g, b) {
            r /= 255;
            g /= 255;
            b /= 255;

            const max = Math.max(r, g, b);
            const min = Math.min(r, g, b);
            const delta = max - min;

            let h = 0;

            if (delta !== 0) {
                if (max === r) h = 60 * (((g - b) / delta) % 6);
                else if (max === g) h = 60 * ((b - r) / delta + 2);
                else h = 60 * ((r - g) / delta + 4);
            }

            if (h < 0) h += 360;

            return {
                h,
                s: max === 0 ? 0 : delta / max,
                v: max
            };
        }

        function updateOutput() {
            const rgb = hsvToRgb(hue, saturation, value);

            const hex = "#" + [rgb.r, rgb.g, rgb.b]
                .map(n => n.toString(16).padStart(2, "0"))
                .join("");

            picker.value = hex;
            preview.style.backgroundColor = hex;

            
            const channels = {
                [picker.dataset.rChannel]: rgb.r,
                [picker.dataset.gChannel]: rgb.g,
                [picker.dataset.bChannel]: rgb.b
            };

            const prefix = picker.dataset.valuePrefix || "ch";

            Object.entries(channels).forEach(([channel, channelValue]) => {
                const input = document.querySelector(
                    `input[name="${prefix}_${channel}"]`
                );

                if (input) {
                    input.value = channelValue;
                }
            });

        }

        function selectPosition(event) {
            const rect = canvas.getBoundingClientRect();

            saturation = Math.max(
                0,
                Math.min(1, (event.clientX - rect.left) / rect.width)
            );

            value = 1 - Math.max(
                0,
                Math.min(1, (event.clientY - rect.top) / rect.height)
            );

            brightness.value = Math.round(value * 100);
            drawPalette();
        }

        canvas.addEventListener("pointerdown", (event) => {
            canvas.setPointerCapture(event.pointerId);
            selectPosition(event);
        });

        canvas.addEventListener("pointermove", (event) => {
            if (event.buttons === 1) {
                selectPosition(event);
            }
        });
                
        hueSlider.addEventListener("input", () => {
            hue = Number(hueSlider.value);
            drawPalette();
        });

        brightness.addEventListener("input", () => {
            value = Number(brightness.value) / 100;
            drawPalette();
        });

        // Restore the current RGB value from the scene.
        const initial = picker.value.match(
            /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i
        );

        if (initial) {
            const hsv = rgbToHsv(
                parseInt(initial[1], 16),
                parseInt(initial[2], 16),
                parseInt(initial[3], 16)
            );

            hue = hsv.h;
            hueSlider.value = Math.round(hue);
            saturation = hsv.s;
            value = hsv.v;
            brightness.value = Math.round(value * 100);
        }

        drawPalette();
    });
}

document.addEventListener("DOMContentLoaded", initDMXColorPickers);
