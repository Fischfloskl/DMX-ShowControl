<p align="center">
  <img src="assets/logo.jpg" alt="DMX-ShowControl Logo" style="max-width: 100%; height: auto;">
</p>

# DMX-ShowControl

**Open-source show control software for live music and DMX lighting.**

DMX-ShowControl is a Python-based show control application designed to synchronize DMX lighting with music and live performances.

It combines **scenes, sequences, triggers, timing and DMX control** in one application, with the goal of making synchronized light shows easier to create and operate.

> [!WARNING]
> **Early Development**
>
> DMX-ShowControl is currently under active development. Features, interfaces and configuration formats may change.

---

## ✨ Features

* 🎛️ **DMX lighting control**
* 🎬 **Scenes** for predefined lighting states
* 🔀 **Sequences** for automated scene playback
* ⌨️ **Keyboard triggers**
* ⏱️ **Timing tools** for synchronizing events with music
* 🎵 **Song-based show control**
* 🔌 **Serial DMX hardware support**
* 🌐 **Web-based control interface**
* 🎹 **MIDI support** *(in development)*
* 📱 **Remote/mobile control** *(in development)*

---

## 🖥️ Current Status

DMX-ShowControl is currently under active development and is not yet considered a stable release.

Some parts of the application may still contain **German text** or untranslated interface elements. The user interface is currently being translated to English.

---

## 🚀 Installation

### Development Version

Clone or download the repository:

```bash
git clone https://github.com/Fischfloskl/DMX-ShowControl.git
cd DMX-ShowControl
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Start the application:

```bash
python main.py
```

### Windows Release

A standalone Windows `.exe` release is available through the **GitHub Releases** section.

The standalone version includes the required Python runtime and dependencies, so **Python does not need to be installed separately**.

---

## 💡 Concept

DMX-ShowControl is designed around the idea of connecting music and lighting into one show workflow.

A typical setup looks like this:

```text
        Music / Backing Track
                 │
                 ▼
          DMX-ShowControl
                 │
       ┌─────────┼─────────┐
       │         │         │
    Triggers   Timing   Sequences
       │         │         │
       └─────────┼─────────┘
                 │
                 ▼
               Scenes
                 │
                 ▼
             DMX Output
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
      Wash     Spot     Strobe
```

The goal is not to replace large professional lighting systems.

Instead, DMX-ShowControl aims to provide a **simple and flexible show-control solution**, especially for smaller live setups, musicians and personal projects.

---

## 🔌 Hardware

DMX-ShowControl is designed with affordable and DIY-friendly hardware in mind.

The current development setup uses an **Arduino Nano / Leonardo-compatible board** as a serial communication bridge between the computer and an **M5Stack DMX module**.

The basic communication path is:

```text
DMX-ShowControl
       │
    USB / Serial
       │
       ▼
 Arduino Nano /
 Leonardo-compatible
       │
    DMX data
       │
       ▼
M5Stack DMX Module
       │
       ▼
  DMX Fixtures
```

The Arduino handles the communication between the computer and the DMX hardware, while the M5Stack DMX module is used for DMX output.

### Arduino Firmware

The Arduino firmware required for the current hardware setup is included in this repository.

The current `.ino` file is:

**[DMX_arduino_Buzz_updated-DMX-protocol.ino](https://github.com/Fischfloskl/DMX-ShowControl/blob/main/DMX_arduino_Buzz_updated-DMX-protocol/DMX_arduino_Buzz_updated-DMX-protocol.ino)**

This firmware was originally developed as part of the **Buzz project** and currently also contains keyboard-related functionality.

The firmware is being adapted for use with DMX-ShowControl. A simplified version without the keyboard functionality may be provided separately in the future.

> **Note:** The current Arduino firmware is intended for the hardware and communication setup used during development. Compatibility with other Arduino boards or DMX hardware may require modifications.

Additional DMX interfaces and hardware may be supported in the future.

---

## 🛠️ Technology

* **Python**
* **Flask**
* **HTML / CSS / JavaScript**
* **Socket.IO**
* **Arduino**
* **Serial communication**
* **DMX**
* **MIDI** *(in development)*

---

## 🗺️ Roadmap

* [ ] Finish English UI translation
* [x] Release standalone Windows `.exe`
* [ ] Improve MIDI integration
* [ ] Add MIDI Learn
* [ ] Improve DMX fixture support
* [ ] Improve the song/show workflow
* [ ] Improve mobile-friendly remote control
* [ ] Add documentation
* [ ] Add example shows and configurations

---

## 🤝 Contributing

Contributions, ideas, bug reports and feature requests are welcome.

If you find a bug or have an idea for improving DMX-ShowControl, feel free to open an **Issue**.

Pull requests are also welcome.

---

## 📄 License

DMX-ShowControl is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

See [`LICENSE`](LICENSE) for the full license text.

---

<p align="center">
  <strong>DMX-ShowControl</strong><br>
  Control your lights. Synchronize your show.
</p>
