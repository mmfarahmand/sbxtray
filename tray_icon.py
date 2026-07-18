import os

import wx
import wx.adv

from core_manager import CoreManager


def create_status_icon(color_rgb: tuple[int, int, int]) -> wx.Icon:
    """Generates a beautiful 3D glossy sphere icon dynamically for the system tray."""
    bmp = wx.Bitmap(16, 16, 32)
    bmp.UseAlpha(True)
    dc = wx.MemoryDC(bmp)
    gc = wx.GraphicsContext.Create(dc)
    if gc:
        # Clear with transparency
        gc.SetCompositionMode(wx.COMPOSITION_SOURCE)
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        gc.DrawRectangle(0, 0, 16, 16)
        gc.SetCompositionMode(wx.COMPOSITION_OVER)

        r, g, b = color_rgb
        # Base spherical gradient
        grad_brush = gc.CreateRadialGradientBrush(
            5.0,
            5.0,
            8.0,
            8.0,
            10.0,
            wx.Colour(r, g, b, 255),
            wx.Colour(max(0, r - 120), max(0, g - 120), max(0, b - 120), 255),
        )
        gc.SetBrush(grad_brush)
        gc.SetPen(gc.CreatePen(wx.Pen(wx.Colour(40, 40, 40, 180), 1)))
        gc.DrawEllipse(2.0, 2.0, 12.0, 12.0)

        # Highlighting top glare to give it depth
        glow_brush = gc.CreateLinearGradientBrush(
            4.0,
            3.0,
            4.0,
            7.0,
            wx.Colour(255, 255, 255, 220),
            wx.Colour(255, 255, 255, 20),
        )
        gc.SetBrush(glow_brush)
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.DrawEllipse(4.0, 3.0, 8.0, 3.5)

    dc.SelectObject(wx.NullBitmap)
    icon = wx.Icon()
    icon.CopyFromBitmap(bmp)
    return icon


class TrayIcon(wx.adv.TaskBarIcon):
    def __init__(
        self, app, manager: CoreManager, log_window, config_editor, status_window
    ):
        super().__init__()
        self.app = app
        self.manager = manager
        self.log_window = log_window
        self.config_editor = config_editor
        self.status_window = status_window

        # Generate state icons dynamically
        self.icon_running = create_status_icon((46, 204, 113))  # Emerald Green
        self.icon_stopped = create_status_icon((180, 180, 180))  # Slate Gray
        self.icon_crashed = create_status_icon((231, 76, 60))  # Alizarin Red
        self.icon_warning = create_status_icon((241, 196, 15))  # Warning Orange

        # Initialize status updates
        self.manager.register_status_callback(self.OnStatusChanged)
        self.update_tray(self.manager.status)

        # Bindings
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.OnDoubleLeftClick)

    def update_tray(self, status: str) -> None:
        """Updates the tray icon and its tooltip depending on the service status."""
        tooltip_prefix = "SBXTray"
        core_display = "Xray" if self.manager.active_core == "xray" else "Sing-Box"
        binary_name = self.manager.get_binary_name()

        if status == "running":
            icon = self.icon_running
            tooltip = (
                f"{tooltip_prefix} ({core_display}): Running (PID: {self.manager.pid})"
            )
        elif status == "stopped":
            icon = self.icon_stopped
            tooltip = f"{tooltip_prefix} ({core_display}): Stopped"
        elif status == "crashed":
            icon = self.icon_crashed
            tooltip = f"{tooltip_prefix} ({core_display}): Crashed / Unexpected Exit"
        elif status == "missing_binary":
            icon = self.icon_warning
            tooltip = (
                f"{tooltip_prefix}: Missing {binary_name} (Click Start to download)"
            )
        elif status == "invalid_config":
            icon = self.icon_crashed
            tooltip = f"{tooltip_prefix} ({core_display}): Invalid configuration file"
        else:
            icon = self.icon_warning
            tooltip = f"{tooltip_prefix} ({core_display}): {status.capitalize()}"

        self.RemoveIcon()
        self.SetIcon(icon, tooltip)

    def OnStatusChanged(self, status: str) -> None:
        self.update_tray(status)

    def OnDoubleLeftClick(self, event):
        # Default action: View logs
        if self.log_window:
            if not self.log_window.IsShown():
                self.log_window.Show()
            self.log_window.Raise()

    def CreatePopupMenu(self) -> wx.Menu:
        menu = wx.Menu()
        core_short = "Xray" if self.manager.active_core == "xray" else "Sing-Box"

        # Service Controls
        start_item = menu.Append(wx.ID_ANY, f"Start {core_short}")
        self.Bind(wx.EVT_MENU, self.OnStart, start_item)

        stop_item = menu.Append(wx.ID_ANY, f"Stop {core_short}")
        self.Bind(wx.EVT_MENU, self.OnStop, stop_item)

        restart_item = menu.Append(wx.ID_ANY, f"Restart {core_short}")
        self.Bind(wx.EVT_MENU, self.OnRestart, restart_item)

        menu.AppendSeparator()

        # Select Active Core Submenu
        core_menu = wx.Menu()
        xray_item = core_menu.AppendRadioItem(wx.ID_ANY, "Xray-core")
        singbox_item = core_menu.AppendRadioItem(wx.ID_ANY, "Sing-Box")

        if self.manager.active_core == "xray":
            xray_item.Check(True)
        else:
            singbox_item.Check(True)

        self.Bind(wx.EVT_MENU, self.OnSelectXray, xray_item)
        self.Bind(wx.EVT_MENU, self.OnSelectSingbox, singbox_item)
        menu.AppendSubMenu(core_menu, "Select Active Core")

        menu.AppendSeparator()

        # Configuration and Status
        status_item = menu.Append(wx.ID_ANY, "View Status")
        self.Bind(wx.EVT_MENU, self.OnViewStatus, status_item)

        edit_item = menu.Append(wx.ID_ANY, "Edit Configuration")
        self.Bind(wx.EVT_MENU, self.OnEditConfig, edit_item)

        logs_item = menu.Append(wx.ID_ANY, "View Logs")
        self.Bind(wx.EVT_MENU, self.OnViewLogs, logs_item)

        folder_item = menu.Append(wx.ID_ANY, "Open Configuration Folder")
        self.Bind(wx.EVT_MENU, self.OnOpenFolder, folder_item)

        menu.AppendSeparator()

        # About Box
        about_item = menu.Append(wx.ID_ANY, "About SBXTray")
        self.Bind(wx.EVT_MENU, self.OnAbout, about_item)

        # Shutdown Manager
        exit_item = menu.Append(wx.ID_ANY, "Exit")
        self.Bind(wx.EVT_MENU, self.OnExit, exit_item)

        # Context-sensitive enabling/disabling of menu items
        status = self.manager.status
        if status == "running":
            start_item.Enable(False)
            stop_item.Enable(True)
            restart_item.Enable(True)
        else:
            start_item.Enable(True)
            stop_item.Enable(False)
            restart_item.Enable(False)

        return menu

    def OnStart(self, event):
        self.app.start_core_service()

    def OnStop(self, event):
        self.manager.stop_service()

    def OnRestart(self, event):
        self.manager.restart_service()

    def OnSelectXray(self, event):
        self.app.switch_core("xray")

    def OnSelectSingbox(self, event):
        self.app.switch_core("singbox")

    def OnViewStatus(self, event):
        if self.status_window:
            if not self.status_window.IsShown():
                self.status_window.Show()
            self.status_window.Raise()

    def OnEditConfig(self, event):
        if self.config_editor:
            if not self.config_editor.IsShown():
                self.config_editor.Show()
            self.config_editor.Raise()

    def OnViewLogs(self, event):
        if self.log_window:
            if not self.log_window.IsShown():
                self.log_window.Show()
            self.log_window.Raise()

    def OnOpenFolder(self, event):
        try:
            os.startfile(self.manager.base_dir)
        except Exception as e:
            wx.MessageBox(
                f"Failed to open configuration folder:\n{e}",
                "Error",
                wx.OK | wx.ICON_ERROR,
            )

    def OnAbout(self, event):
        info = wx.adv.AboutDialogInfo()
        info.SetName("SBXTray")
        info.SetVersion("1.0.0")
        info.SetDescription(
            "A lightweight Windows system tray manager for Xray-core and Sing-Box.\n"
            "Designed for power users who want to maintain their own hand-written JSON configurations."
        )
        info.SetCopyright("(c) 2026 mmfarahmand")
        info.SetWebSite(
            "https://github.com/mmfarahmand/sbxtray", "SBXTray GitHub Project"
        )
        wx.adv.AboutBox(info)

    def OnExit(self, event):
        self.app.OnExitApp()
