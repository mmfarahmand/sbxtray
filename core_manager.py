import collections
import json
import os
import subprocess
import threading
import time
from typing import Callable, Deque, List, Optional


class CoreManager:
    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)
        self.process: Optional[subprocess.Popen] = None
        self.status = "stopped"  # running, stopped, crashed, failed, missing_binary, invalid_config
        self.pid: Optional[int] = None
        self.start_time: Optional[float] = None
        self.logs: Deque[str] = collections.deque(maxlen=10000)

        self.status_callbacks: List[Callable[[str], None]] = []
        self.log_callbacks: List[Callable[[str], None]] = []

        self._monitor_thread: Optional[threading.Thread] = None
        self._stdout_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None

        # Core type: "xray" or "singbox"
        self.active_core = "xray"
        self.load_settings()
        self.update_binary_status()

    def get_settings_path(self) -> str:
        return os.path.join(self.base_dir, "settings.json")

    def load_settings(self) -> None:
        path = self.get_settings_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.active_core = data.get("active_core", "xray")
                    if self.active_core not in ["xray", "singbox"]:
                        self.active_core = "xray"
            except Exception:
                self.active_core = "xray"

    def save_settings(self) -> None:
        path = self.get_settings_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"active_core": self.active_core}, f, indent=2)
        except Exception:
            pass

    def get_binary_name(self) -> str:
        return "xray.exe" if self.active_core == "xray" else "sing-box.exe"

    def get_binary_path(self) -> str:
        return os.path.join(self.base_dir, self.get_binary_name())

    def get_config_name(self) -> str:
        return "xray.json" if self.active_core == "xray" else "singbox.json"

    def get_config_path(self) -> str:
        return os.path.join(self.base_dir, self.get_config_name())

    def update_binary_status(self) -> None:
        """Updates the status based on whether the active binary exists."""
        if not os.path.exists(self.get_binary_path()):
            self.status = "missing_binary"
        elif self.status == "missing_binary":
            self.status = "stopped"

    def set_active_core(self, core: str) -> None:
        """Changes the active core, saving settings and updating state."""
        if core not in ["xray", "singbox"]:
            return
        if self.active_core == core:
            return

        self.active_core = core
        self.save_settings()
        self.update_binary_status()
        self.notify_status_changed()

    def register_status_callback(self, callback: Callable[[str], None]) -> None:
        self.status_callbacks.append(callback)

    def register_log_callback(self, callback: Callable[[str], None]) -> None:
        self.log_callbacks.append(callback)

    def notify_status_changed(self) -> None:
        import wx

        for cb in self.status_callbacks:
            wx.CallAfter(cb, self.status)

    def add_log(self, line: str) -> None:
        self.logs.append(line)
        import wx

        for cb in self.log_callbacks:
            wx.CallAfter(cb, line)

    def is_running(self) -> bool:
        if self.process is not None:
            return self.process.poll() is None
        return False

    def start_service(self) -> bool:
        if self.is_running():
            return True

        binary_path = self.get_binary_path()
        config_path = self.get_config_path()

        if not os.path.exists(binary_path):
            self.status = "missing_binary"
            self.notify_status_changed()
            return False

        # Create empty JSON config if it doesn't exist
        if not os.path.exists(config_path):
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write("{}")
                self.add_log(
                    f"[Manager] Created empty configuration file at {self.get_config_name()}\n"
                )
            except Exception as e:
                self.status = "failed"
                self.add_log(f"[Manager Error] Failed to create config file: {e}\n")
                self.notify_status_changed()
                return False

        # Validate JSON before starting
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                json.load(f)
        except Exception as e:
            self.status = "invalid_config"
            self.add_log(
                f"[Manager Error] Failed to start: {self.get_config_name()} contains invalid JSON: {e}\n"
            )
            self.notify_status_changed()
            return False

        try:
            core_display = "Xray-core" if self.active_core == "xray" else "Sing-Box"
            self.add_log(f"[Manager] Starting {core_display}...\n")

            # Setup startupinfo to hide CMD window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            self.process = subprocess.Popen(
                [binary_path, "run", "-c", config_path],
                cwd=self.base_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            self.start_time = time.time()
            self.status = "running"
            self.pid = self.process.pid

            self._start_threads()
            self.notify_status_changed()
            self.add_log(f"[Manager] {core_display} started (PID: {self.pid})\n")
            return True
        except Exception as e:
            self.status = "failed"
            self.add_log(f"[Manager Error] Failed to start core process: {e}\n")
            self.notify_status_changed()
            return False

    def stop_service(self) -> None:
        if self.process is None:
            self.status = "stopped"
            self.notify_status_changed()
            return

        core_display = "Xray-core" if self.active_core == "xray" else "Sing-Box"
        self.add_log(f"[Manager] Stopping {core_display}...\n")
        self.status = "stopped"

        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.add_log(
                    "[Manager Warning] Process did not terminate gracefully, force-killing...\n"
                )
                self.process.kill()
                self.process.wait()
        except Exception as e:
            self.add_log(f"[Manager Error] Exception while terminating process: {e}\n")
        finally:
            self.process = None
            self.pid = None
            self.start_time = None
            self.notify_status_changed()
            self.add_log(f"[Manager] {core_display} stopped\n")

    def restart_service(self) -> bool:
        self.stop_service()
        return self.start_service()

    def get_uptime(self) -> float:
        if self.status == "running" and self.start_time is not None:
            return time.time() - self.start_time
        return 0.0

    def _start_threads(self) -> None:
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._monitor_thread = threading.Thread(
            target=self._monitor_process, daemon=True
        )

        self._stdout_thread.start()
        self._stderr_thread.start()
        self._monitor_thread.start()

    def _read_stdout(self) -> None:
        if self.process is None or self.process.stdout is None:
            return
        for line in iter(self.process.stdout.readline, ""):
            self.add_log(line)
        self.process.stdout.close()

    def _read_stderr(self) -> None:
        if self.process is None or self.process.stderr is None:
            return
        for line in iter(self.process.stderr.readline, ""):
            self.add_log(line)
        self.process.stderr.close()

    def _monitor_process(self) -> None:
        if self.process is None:
            return
        self.process.wait()
        if self.status == "running":
            exit_code = self.process.poll()
            self.status = "crashed"
            self.pid = None
            self.start_time = None
            self.process = None
            core_display = "Xray-core" if self.active_core == "xray" else "Sing-Box"
            self.add_log(
                f"[Manager Warning] {core_display} exited unexpectedly with code {exit_code}\n"
            )
            self.notify_status_changed()
