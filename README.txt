DMX-ShowControl
===============

Open-source show control software for live music and DMX lighting.

DMX-ShowControl is a Python-based show control application designed to
synchronize DMX lighting with music and live performances.

It combines scenes, sequences, triggers, timing and DMX control in one
application, with the goal of making synchronized light shows easier to
create and operate.


FEATURES
--------

- DMX lighting control
- Scenes for predefined lighting states
- Sequences for automated scene playback
- Keyboard triggers
- Timing tools for synchronizing events with music
- Song-based show control
- Serial DMX hardware support
- Web-based control interface
- MIDI support (in development)
- Remote/mobile control (in development)


CURRENT STATUS
--------------

DMX-ShowControl is currently under active development.

The project is not yet considered a stable release. Features, interfaces
and configuration formats may change during development.

Some parts of the application may still contain German text or untranslated
interface elements. The user interface is currently being translated to
English.

A standalone Windows .EXE release is coming soon.

The goal is to make DMX-ShowControl usable without requiring users to
install Python or configure the development environment manually.


INSTALLATION
------------

DEVELOPMENT VERSION

1. Install Python 3.

2. Clone or download the repository.

3. Open a terminal in the project directory.

4. Install the required packages:

   pip install -r requirements.txt

5. Start the application:

   python main.py


WINDOWS RELEASE

A standalone Windows .EXE version will be released soon.

The planned release will include the required Python runtime and
dependencies, so users will not need to install Python separately.


CONCEPT
-------

DMX-ShowControl is designed around the idea of connecting music and
lighting into one show workflow.

A typical setup looks like this:

    Music / Backing Track
             |
             v
      DMX-ShowControl
             |
      +------+------+------+
      |      |      |      |
   Triggers Timing Sequences
      |      |      |
      +------+------+------+
             |
             v
           Scenes
             |
             v
         DMX Output
             |
       +-----+-----+
       |     |     |
      Wash  Spot  Strobe


The goal is not to replace large professional lighting systems.

Instead, DMX-ShowControl aims to provide a simple and flexible
show-control solution, especially for smaller live setups, musicians
and personal projects.


HARDWARE
--------

DMX-ShowControl is being developed with affordable and DIY-friendly
hardware in mind.

The current development setup uses serial communication with external
hardware for DMX output.

The exact hardware setup may change as development continues.


TECHNOLOGY
----------

- Python
- Flask
- HTML / CSS / JavaScript
- Socket.IO
- Arduino
- Serial communication
- DMX
- MIDI (in development)


ROADMAP
-------

- Finish English UI translation
- Release standalone Windows .EXE
- ADD MIDI integration
- Add MIDI Learn
- Improve DMX fixture support
- Improve the song/show workflow
- Improve mobile-friendly remote control
- Add documentation
- Add example shows and configurations


HARDWARE
--------

DMX-ShowControl is designed to work with affordable and DIY-friendly
hardware.

The current setup uses an Arduino as a serial communication bridge
between the computer and an M5Stack DMX module.

The basic communication path is:

    DMX-ShowControl
          |
       USB/Serial
          |
          v
       Arduino
          |
       DMX data
          |
          v
    M5Stack DMX Module
          |
          v
      DMX fixtures


The Arduino handles the communication between the computer and the
DMX hardware. The M5Stack DMX module is used for DMX output.

This setup allows DMX-ShowControl to be used with relatively inexpensive
hardware instead of requiring a dedicated professional DMX interface.

Additional DMX interfaces and hardware may be supported in the future.


CONTRIBUTING
------------

Contributions, ideas, bug reports and feature requests are welcome.

If you find a bug or have an idea for improving DMX-ShowControl, please
open an Issue on GitHub.

Pull requests are also welcome.


LICENSE
-------

DMX-ShowControl is licensed under the GNU General Public License v3.0
(GPL-3.0).

See the LICENSE file for the complete license text.


DMX-ShowControl
Control your lights. Synchronize your show.