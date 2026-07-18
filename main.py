import os
import sys
from typing import Optional

import wx

from core_manager import CoreManager
from gui_download import DownloadDialog
from gui_editor import ConfigEditor
from gui_log import LogWindow
from gui_status import StatusWindow
from tray_icon import TrayIcon


class SBXTrayApp(wx.App):
    def __init__(self, *args, **kwargs):
        self.instance_checker: Optional[wx.SingleInstanceChecker] = None
        self.manager: Optional[CoreManager] = None
        self.log_window: Optional[LogWindow] = None
        self.config_editor: Optional[ConfigEditor] = None
        self.status_window: Optional[StatusWindow] = None
        self.tray_icon: Optional[TrayIcon] = None
        super().__init__(*args, **kwargs)

    def OnInit(self) -> bool:
        # Prevent running multiple instances of the tray manager app
        self.instance_checker = wx.SingleInstanceChecker(
            "SBXTraySingleInstanceChecker"
        )
        if self.instance_checker.IsAnotherRunning():
            wx.MessageBox(
                "Another instance of SBXTray is already running.",
                "SBXTray - Already Running",
                wx.OK | wx.ICON_WARNING,
            )
            return False

        # Prevent the application from exiting when secondary windows are closed
        self.SetExitOnFrameDelete(False)

        # Determine the base directory
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # Instantiate manager and windows
        self.manager = CoreManager(base_dir)

        self.log_window = LogWindow(None, self.manager)
        self.config_editor = ConfigEditor(None, self.manager)
        self.status_window = StatusWindow(None, self.manager)

        # Instantiate Tray Icon
        self.tray_icon = TrayIcon(
            self, self.manager, self.log_window, self.config_editor, self.status_window
        )

        # Auto-start service on startup
        wx.CallAfter(self.start_core_service)

        return True

    def start_core_service(self) -> None:
        """Starts the active core process. Prompts to download the core if missing."""
        if self.manager is None:
            return

        # Double check status
        self.manager.update_binary_status()
        core_display = "Xray-core" if self.manager.active_core == "xray" else "Sing-Box"
        binary_name = self.manager.get_binary_name()

        if self.manager.status == "missing_binary":
            # Prompt user to download
            res = wx.MessageBox(
                f"{binary_name} was not found in the application directory.\n\n"
                f"Would you like to download the latest {core_display} release package from GitHub?",
                f"{core_display} Missing",
                wx.YES_NO | wx.ICON_QUESTION,
            )
            if res == wx.YES:
                dlg = DownloadDialog(None, self.manager)
                dlg.StartDownload()
                result = dlg.ShowModal()
                dlg.Destroy()

                if result == wx.ID_OK:
                    # Update status and attempt start again
                    self.manager.update_binary_status()
                    self.start_core_service()
            else:
                self.manager.add_log(
                    f"[Manager] Startup aborted: {binary_name} is missing.\n"
                )
            return

        # If binary exists, try starting it
        started = self.manager.start_service()

        if not started:
            config_name = self.manager.get_config_name()
            if self.manager.status == "invalid_config":
                wx.MessageBox(
                    f"Startup failed: {config_name} contains invalid JSON.\n"
                    "Opening the configuration editor so you can fix it.",
                    "Invalid Configuration",
                    wx.OK | wx.ICON_ERROR,
                )
                if self.config_editor:
                    self.config_editor.Show()
                    self.config_editor.Raise()
            elif self.manager.status == "failed":
                wx.MessageBox(
                    f"Startup failed: Could not launch {core_display} process.\n"
                    "Check the logs for details.",
                    "Launch Failure",
                    wx.OK | wx.ICON_ERROR,
                )

    def switch_core(self, core: str) -> None:
        """Gracefully switches the active core type (Xray <-> Sing-Box)."""
        if self.manager is None:
            return
        if self.manager.active_core == core:
            return

        was_running = self.manager.is_running()
        if was_running:
            self.manager.add_log(
                "[Manager] Active core switched. Stopping running service first...\n"
            )
            self.manager.stop_service()

        # Update manager core
        self.manager.set_active_core(core)

        # Reload files and fields in open windows
        if self.config_editor:
            self.config_editor.reload_config_path()
        if self.status_window:
            self.status_window.UpdateFields()

        # Auto-restart if it was running before the switch
        if was_running:
            self.start_core_service()
        else:
            self.manager.add_log(f"[Manager] Switched active core to: {core.upper()}\n")

    def OnExitApp(self) -> None:
        """Gracefully terminates background processes and cleans up UI before exiting."""
        # Set exiting flags so sub-windows close rather than veto/hide
        if self.log_window:
            self.log_window.app_exiting = True
            self.log_window.Close()
        if self.config_editor:
            self.config_editor.app_exiting = True
            self.config_editor.Close()
        if self.status_window:
            self.status_window.app_exiting = True
            self.status_window.Close()

        # Stop active core service
        if self.manager:
            self.manager.stop_service()

        # Remove tray icon
        if self.tray_icon:
            self.tray_icon.RemoveIcon()
            self.tray_icon.Destroy()

        # Exit main loop
        self.ExitMainLoop()


if __name__ == "__main__":
    app = SBXTrayApp()
    app.MainLoop()
