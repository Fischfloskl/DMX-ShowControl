# DMX-ShowControl Installer

This directory contains the **Windows installer** for DMX-ShowControl.

The installer is created using **Inno Setup** and packages the standalone DMX-ShowControl application for Windows.

## 📦 What does the installer include?

The installer contains:

* DMX-ShowControl
* Required application files
* Required Python runtime and dependencies
* Application assets
* Configuration files required by the application

Users do **not** need to install Python separately when using the standalone version.

## 🚀 Installation

Run the installer:

```text
DMX-ShowControl-Setup.exe
```

Follow the installation wizard to select the installation location and create the desired shortcuts.

After installation, DMX-ShowControl can be started from the Start Menu or the created desktop shortcut.

## ⚠️ Development Status

This is an **early development version** of DMX-ShowControl.

The application and installer are still being tested. Features, configuration formats and the installation process may change in future versions.

Some parts of the application may still contain German text or untranslated interface elements.

## 🔧 Building the Installer

The installer is built using **Inno Setup**.

The Inno Setup script is included in this directory.

Open the `.iss` file with Inno Setup and compile it to create a new installer.

The resulting installer can then be distributed as a Windows executable.

## 📁 Project Structure

A typical setup looks like:

```text
Installer/
├── README.md
├── DMX-ShowControl.iss
└── ...
```

The actual application source code is maintained in the main DMX-ShowControl repository.

## 📄 License

DMX-ShowControl is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

See the main repository for the complete license text.

---

**DMX-ShowControl**
*Control your lights. Synchronize your show.*
