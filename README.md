# SBXTray

SBXTray is a lightweight, premium Windows system tray companion application for Xray-core and Sing-Box. It is built specifically for **power users** who want to maintain their own hand-written configuration files directly, without dealing with heavy, over-engineered proxy clients.

## Features

- **Dual-Core Support**: Switch between **Xray-core** and **Sing-Box** dynamically from the system tray menu. Settings are saved automatically to `settings.json`.
- **Zero Console Window Clutter**: Runs directly into the system tray without popping up any CMD or console windows.
- **Dynamic 3D Sphere Indicators**: Programmatically renders high-quality glossy status icons (Green for Running, Gray for Stopped, Red for Crashed, Orange for Missing Executable).
- **Asynchronous GitHub Releases Downloader**: Automatically offers to download and extract the latest release package for the active core from GitHub (XTLS/Xray-core or SagerNet/sing-box) if the executable is missing.
- **Rich Live Log Streamer**: Displays stdout and stderr in real-time within a sleek GUI log viewer. Retains up to 10,000 log lines in memory and supports auto-scroll toggles, clearing, and exporting logs to file.
- **Advanced Configuration Editor**: Edit your configurations directly in the app. Dynamically loads `xray.json` when Xray is active, and `singbox.json` when Sing-Box is active. Features JSON syntax formatting and active JSON validation (preventing corrupted saves).
- **Real-time Status Dashboard**: Tracks active core type, process state, Process ID (PID), exact startup timestamp, uptime counter, and paths.

## Setup & Running

### Running from Pre-built Binaries
If you do not want to run from source, you can download the latest pre-compiled build directly from the [GitHub Releases](https://github.com/mmfarahmand/sbxtray/releases) page. The release contains a single, standalone executable that launches directly without any other dependencies.

### Running from Source Code
1. **Prerequisites**: Windows OS, Python 3.12+ (Python 3.13 is fully supported).
2. **Dependencies**: **`wxPython`** is the only external dependency. You can install it via pip:
   ```cmd
   pip install wxPython
   ```
3. **Running the App**: Launch the application from source by running:
   ```cmd
   python main.py
   ```
   *(To run the application silently in the background without opening a CMD console window, use `pythonw main.py`)*
4. **Core Installation**: If the executable for the active core (`xray.exe` or `sing-box.exe`) is missing, the application will prompt you to download the latest core on startup. Click **Yes** to automatically fetch and extract it from the official GitHub repository (along with GeoIP and GeoSite assets).
5. **Configuration**: If no configuration file is present, the application will automatically initialize an empty `{}` JSON configuration (`xray.json` for Xray, `singbox.json` for Sing-Box). You can edit configuration files inside the app.

## Context Menu Actions

- **Start [Core]**: Launches the active core background process using `xray.exe run -c xray.json` or `sing-box.exe run -c singbox.json` (disabled if already running).
- **Stop [Core]**: Gracefully terminates the running process (disabled if stopped).
- **Restart [Core]**: Sequence-stops then starts the active core process again.
- **Select Active Core**: Submenu to switch between **Xray-core** and **Sing-Box**. If the service is running, it gracefully stops the old core, switches config edit buffers, and restarts with the new core.
- **View Status**: Displays detailed diagnostics (Active Core, PID, Uptime, executable/config paths).
- **Edit Configuration**: Built-in editor with validation and formatting. Automatically loads the config file corresponding to the active core.
- **View Logs**: Monitor live stdout and stderr in real-time.
- **Open Configuration Folder**: Opens the project directory in Windows File Explorer.
- **About SBXTray**: Displays version details, copyright, and a clickable link to the GitHub project.
- **Exit**: Terminates the running core and exits the tray manager.
