(() => {
    "use strict";

    const config = window.LIVE_FADERS_CONFIG || {};
    const endpoint = config.endpoint || "/api/dmx/live-values";

    const liveButton = document.getElementById("lf-live");
    const blackoutButton = document.getElementById("lf-blackout");
    const statusElement = document.getElementById("lf-status");
    const tabsElement = document.getElementById("lf-device-tabs");
    const devicesElement = document.getElementById("lf-devices");

    let liveEnabled = false;
    let blackoutEnabled = false;
    let selectedDevice = 0;
    let requestInProgress = false;
    let pendingValues = {};
    let sendTimer = null;
    let abortController = null;

    function setStatus(message, type = "") {
        statusElement.textContent = message;
        statusElement.classList.toggle("is-active", type === "active");
        statusElement.classList.toggle("is-error", type === "error");
    }

    function getDeviceList(raw) {
        if (Array.isArray(raw)) {
            return raw;
        }

        if (raw && Array.isArray(raw.devices)) {
            return raw.devices;
        }

        if (raw && typeof raw === "object") {
            return Object.entries(raw).map(([key, value]) => ({
                id: value?.id ?? key,
                ...(value || {})
            }));
        }

        return [];
    }

    function getChannelDefinitions(device) {
        const raw = device.channels ?? device.channel_names;

        if (Array.isArray(raw)) {
            return raw.map((channel, index) => {
                if (typeof channel === "string") {
                    return {
                        number: index + 1,
                        name: channel
                    };
                }

                return {
                    number: index + 1,
                    name: channel?.name
                        ?? channel?.label
                        ?? `Kanal ${index + 1}`
                };
            });
        }

        const count = Number(
            device.channel_count
            ?? device.channelCount
            ?? device.num_channels
            ?? device.channel_amount
            ?? device.channels
            ?? 0
        );

        if (Number.isInteger(count) && count > 0 && count <= 512) {
            return Array.from({ length: count }, (_, index) => ({
                number: index + 1,
                name: `CH ${index + 1}`
            }));
        }

        return [];
    }

    const devices = getDeviceList(config.devices).map((device, index) => {
        const channels = getChannelDefinitions(device);

        return {
            id: String(device.id ?? device.device_id ?? index),
            name: String(
                device.name
                ?? device.label
                ?? device.model
                ?? `Gerät ${index + 1}`
            ),
            startChannel: Number(
                device.start_channel
                ?? device.start_address
                ?? device.dmx_address
                ?? device.address
                ?? 1
            ),
            channels,
            values: channels.map(() => 0),
            element: null
        };
    }).filter(device => device.channels.length > 0);

    function validStartChannel(value, channelCount) {
        const start = Number(value);

        if (!Number.isInteger(start) || start < 1 || start > 512) {
            return false;
        }

        return start + channelCount - 1 <= 512;
    }

    function getOutputValues(forceBlackout = false) {
        const values = {};

        devices.forEach(device => {
            if (!validStartChannel(device.startChannel, device.channels.length)) {
                return;
            }

            device.values.forEach((value, index) => {
                const channel = device.startChannel + index;
                values[channel] = forceBlackout ? 0 : value;
            });
        });

        return values;
    }

    function queueOutput(values) {
        if (!liveEnabled) {
            return;
        }

        Object.assign(pendingValues, values);

        if (sendTimer !== null) {
            clearTimeout(sendTimer);
        }

        sendTimer = setTimeout(flushOutput, 25);
    }

    async function flushOutput() {
        sendTimer = null;

        if (!liveEnabled || requestInProgress) {
            return;
        }

        const values = pendingValues;
        pendingValues = {};

        if (!Object.keys(values).length) {
            return;
        }

        requestInProgress = true;
        abortController = new AbortController();

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ values }),
                signal: abortController.signal
            });

            const result = await response.json().catch(() => ({}));

            if (!response.ok || result.success === false) {
                throw new Error(
                    result.error || `HTTP ${response.status}`
                );
            }

            setStatus(
                blackoutEnabled
                    ? "Live aktiv – Blackout ausgegeben"
                    : "Live-Ausgabe aktiv",
                "active"
            );
        } catch (error) {
            if (error.name !== "AbortError") {
                console.error("Live-DMX-Ausgabe fehlgeschlagen:", error);
                setStatus(`DMX-Ausgabe fehlgeschlagen: ${error.message}`, "error");
            }
        } finally {
            requestInProgress = false;
            abortController = null;

            if (liveEnabled && Object.keys(pendingValues).length) {
                flushOutput();
            }
        }
    }

    function renderTabs() {
        tabsElement.replaceChildren();

        devices.forEach((device, index) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "lf-tab";
            button.textContent = device.name;
            button.classList.toggle("is-selected", index === selectedDevice);

            button.addEventListener("click", () => {
                selectedDevice = index;
                updateSelectedDevice();
            });

            tabsElement.appendChild(button);
        });
    }

    function updateSelectedDevice() {
        devices.forEach((device, index) => {
            device.element?.classList.toggle(
                "is-selected",
                index === selectedDevice
            );
        });

        [...tabsElement.children].forEach((tab, index) => {
            tab.classList.toggle("is-selected", index === selectedDevice);
        });
    }

    function renderDevices() {
        devicesElement.replaceChildren();

        if (!devices.length) {
            const message = document.createElement("p");
            message.className = "lf-loading";
            message.textContent =
                "Keine Geräte mit Kanälen gefunden. Bitte prüfe data/devices.json und das Geräteformat.";
            devicesElement.appendChild(message);
            return;
        }

        devices.forEach((device, deviceIndex) => {
            const card = document.createElement("section");
            card.className = "lf-device";

            const header = document.createElement("div");
            header.className = "lf-device-header";

            const title = document.createElement("h2");
            title.textContent = device.name;
            header.appendChild(title);

            const addressLabel = document.createElement("label");
            addressLabel.className = "lf-address";
            addressLabel.textContent = "Startkanal";

            const addressInput = document.createElement("input");
            addressInput.type = "number";
            addressInput.min = "1";
            addressInput.max = "512";
            addressInput.step = "1";
            addressInput.value = String(device.startChannel);
            addressInput.setAttribute("aria-label", `Startkanal für ${device.name}`);

            addressInput.addEventListener("change", () => {
                const nextAddress = Number(addressInput.value);

                if (!validStartChannel(nextAddress, device.channels.length)) {
                    addressInput.value = String(device.startChannel);
                    setStatus(
                        `Ungültiger Startkanal für ${device.name}. Das Gerät muss vollständig in DMX 1–512 liegen.`,
                        "error"
                    );
                    return;
                }

                device.startChannel = nextAddress;

                if (liveEnabled) {
                    queueOutput(getOutputValues(blackoutEnabled));
                }
            });

            addressLabel.appendChild(addressInput);
            header.appendChild(addressLabel);
            card.appendChild(header);

            const faders = document.createElement("div");
            faders.className = "lf-faders";

            device.channels.forEach((channel, channelIndex) => {
                const fader = document.createElement("div");
                fader.className = "lf-fader";

                const label = document.createElement("label");
                label.className = "lf-fader-label";
                label.textContent = channel.name;
                label.title = channel.name;

                const sliderWrap = document.createElement("div");
                sliderWrap.className = "lf-slider-wrap";

                const slider = document.createElement("input");
                slider.type = "range";
                slider.className = "lf-slider";
                slider.min = "0";
                slider.max = "255";
                slider.step = "1";
                slider.value = String(device.values[channelIndex]);
                slider.setAttribute(
                    "aria-label",
                    `${device.name}, ${channel.name}`
                );

                const valueInput = document.createElement("input");
                valueInput.type = "number";
                valueInput.className = "lf-value";
                valueInput.min = "0";
                valueInput.max = "255";
                valueInput.step = "1";
                valueInput.value = String(device.values[channelIndex]);
                valueInput.setAttribute(
                    "aria-label",
                    `DMX-Wert ${channel.name}`
                );

                function updateValue(rawValue) {
                    const value = Math.max(
                        0,
                        Math.min(255, Math.round(Number(rawValue) || 0))
                    );

                    device.values[channelIndex] = value;
                    slider.value = String(value);
                    valueInput.value = String(value);

                    if (liveEnabled) {
                        const absoluteChannel =
                            device.startChannel + channelIndex;

                        queueOutput({
                            [absoluteChannel]: blackoutEnabled ? 0 : value
                        });
                    }
                }

                slider.addEventListener("input", () => {
                    updateValue(slider.value);
                });

                valueInput.addEventListener("change", () => {
                    updateValue(valueInput.value);
                });

                sliderWrap.appendChild(slider);
                fader.appendChild(label);
                fader.appendChild(sliderWrap);
                fader.appendChild(valueInput);
                faders.appendChild(fader);
            });

            card.appendChild(faders);
            devicesElement.appendChild(card);
            device.element = card;

            if (deviceIndex === selectedDevice) {
                card.classList.add("is-selected");
            }
        });

        updateSelectedDevice();
    }

    function setLive(enabled) {
        liveEnabled = enabled;

        liveButton.classList.toggle("is-active", enabled);
        liveButton.textContent = enabled
            ? "Live deaktivieren"
            : "Live aktivieren";

        blackoutButton.disabled = !enabled;
        blackoutButton.textContent = blackoutEnabled
            ? "Blackout aufheben"
            : "Blackout";

        if (enabled) {
            setStatus("Live-Ausgabe wird aktiviert …");

            queueOutput(getOutputValues(blackoutEnabled));
        } else {
            if (sendTimer !== null) {
                clearTimeout(sendTimer);
                sendTimer = null;
            }

            pendingValues = {};

            if (abortController) {
                abortController.abort();
            }

            setStatus("Live-Ausgabe deaktiviert");
        }
    }

    liveButton.addEventListener("click", () => {
        if (liveEnabled) {
            setLive(false);
            return;
        }

        if (!devices.length) {
            setStatus("Keine geeigneten Geräte verfügbar.", "error");
            return;
        }

        const accepted = true;
        /*const accepted = window.confirm(
            "Live-DMX-Ausgabe aktivieren? Die aktuellen Faderwerte werden an die DMX-Ausgabe gesendet."
        );*/

        if (accepted) {
            setLive(true);
        }
    });

    blackoutButton.addEventListener("click", () => {
        if (!liveEnabled) {
            return;
        }

        blackoutEnabled = !blackoutEnabled;

        blackoutButton.textContent = blackoutEnabled
            ? "Blackout aufheben"
            : "Blackout";

        queueOutput(getOutputValues(blackoutEnabled));

        setStatus(
            blackoutEnabled
                ? "Blackout wird ausgegeben – Faderwerte bleiben gespeichert"
                : "Blackout aufgehoben – Faderwerte werden wieder ausgegeben",
            "active"
        );
    });

    renderTabs();
    renderDevices();
})();