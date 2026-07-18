import datetime

import wx

from core_manager import CoreManager


class StatusWindow(wx.Frame):
    def __init__(self, parent, manager: CoreManager):
        super().__init__(
            parent,
            title="SBXTray - Status Information",
            size=(520, 360),
            style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX),
        )
        self.manager = manager
        self.app_exiting = False

        # 1-second refresh timer for Uptime and PID tracking
        self.timer = wx.Timer(self)

        self.InitUI()
        self.manager.register_status_callback(self.OnStatusChangedExternal)

    def InitUI(self):
        # Create a single root panel to host all controls for correct tab traversal on Windows
        root_panel = wx.Panel(self)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Header / Title Block
        header_panel = wx.Panel(root_panel)
        header_sizer = wx.BoxSizer(wx.VERTICAL)

        self.title_lbl = wx.StaticText(
            header_panel, label="SBXTray - Service Manager"
        )
        title_font = wx.Font(
            12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
        )
        self.title_lbl.SetFont(title_font)
        header_sizer.Add(self.title_lbl, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 12)

        header_panel.SetSizer(header_sizer)
        main_sizer.Add(header_panel, 0, wx.EXPAND | wx.BOTTOM, 15)

        # FlexGridSizer for status details (2 columns: Key, Value)
        grid_sizer = wx.FlexGridSizer(rows=6, cols=2, vgap=12, hgap=15)
        grid_sizer.AddGrowableCol(1, 1)

        # Styling helper for key labels
        def add_key_label(label_text):
            lbl = wx.StaticText(root_panel, label=label_text)
            lbl.SetFont(
                wx.Font(
                    9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
                )
            )
            grid_sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 20)

        # Styling helper for selectable value labels
        def create_selectable_value():
            ctrl = wx.TextCtrl(
                root_panel,
                style=wx.TE_READONLY | wx.BORDER_NONE | wx.TE_NO_VSCROLL | wx.TE_RICH2,
            )
            ctrl.SetBackgroundColour(root_panel.GetBackgroundColour())
            ctrl.SetFont(
                wx.Font(
                    9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
                )
            )
            return ctrl

        # Status
        add_key_label("Service Status:")
        self.status_val = create_selectable_value()
        self.status_val.SetName("Service Status")
        self.status_val.SetFont(
            wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        )
        grid_sizer.Add(self.status_val, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        # PID
        add_key_label("Process ID (PID):")
        self.pid_val = create_selectable_value()
        self.pid_val.SetName("Process ID (PID)")
        grid_sizer.Add(self.pid_val, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        # Start Time
        add_key_label("Start Time:")
        self.start_time_val = create_selectable_value()
        self.start_time_val.SetName("Start Time")
        grid_sizer.Add(self.start_time_val, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        # Uptime
        add_key_label("Uptime:")
        self.uptime_val = create_selectable_value()
        self.uptime_val.SetName("Uptime")
        grid_sizer.Add(self.uptime_val, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        # Config Path
        add_key_label("Config File:")
        self.config_path_val = create_selectable_value()
        self.config_path_val.SetName("Config File Path")
        grid_sizer.Add(
            self.config_path_val, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 20
        )

        # Executable Path
        add_key_label("Executable Path:")
        self.core_path_val = create_selectable_value()
        self.core_path_val.SetName("Executable Path")
        grid_sizer.Add(
            self.core_path_val, 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 20
        )

        main_sizer.Add(grid_sizer, 1, wx.EXPAND)

        # Button Panel
        btn_panel = wx.Panel(root_panel)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.start_stop_btn = wx.Button(btn_panel, label="&Start")
        self.start_stop_btn.Bind(wx.EVT_BUTTON, self.OnToggleService)
        btn_sizer.Add(self.start_stop_btn, 0, wx.RIGHT, 10)

        self.restart_btn = wx.Button(btn_panel, label="&Restart")
        self.restart_btn.Bind(wx.EVT_BUTTON, self.OnRestartService)
        btn_sizer.Add(self.restart_btn, 0, wx.RIGHT, 10)

        btn_sizer.AddStretchSpacer(1)

        self.close_btn = wx.Button(btn_panel, label="&Close")
        self.close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Hide())
        btn_sizer.Add(self.close_btn, 0)

        btn_panel.SetSizer(btn_sizer)
        main_sizer.Add(btn_panel, 0, wx.EXPAND | wx.ALL, 15)

        root_panel.SetSizer(main_sizer)

        # Frame level sizer to fit root panel
        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(root_panel, 1, wx.EXPAND)
        self.SetSizer(frame_sizer)

        # Events
        self.Bind(wx.EVT_TIMER, self.OnTimerUpdate)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_SHOW, self.OnShow)

        self.Center()

    def UpdateFields(self) -> None:
        """Updates status values from CoreManager."""
        status = self.manager.status
        self.status_val.SetValue(status.upper())

        core_display = "Xray-core" if self.manager.active_core == "xray" else "Sing-Box"
        core_short = "Xray" if self.manager.active_core == "xray" else "Sing-Box"
        self.title_lbl.SetLabel(f"SBXTray - {core_display} Service Manager")

        # Color-code status labels
        if status == "running":
            self.status_val.SetForegroundColour(wx.Colour(0, 128, 0))  # Standard Green
            self.start_stop_btn.SetLabel(f"&Stop {core_short}")
            self.start_stop_btn.Enable(True)
            self.restart_btn.Enable(True)
        elif status in [
            "stopped",
            "crashed",
            "failed",
            "missing_binary",
            "invalid_config",
        ]:
            if status == "stopped":
                self.status_val.SetForegroundColour(
                    wx.Colour(128, 128, 128)
                )  # Standard Gray
            else:
                self.status_val.SetForegroundColour(
                    wx.Colour(200, 0, 0)
                )  # Standard Red

            self.start_stop_btn.SetLabel(f"&Start {core_short}")
            self.restart_btn.Enable(False)

            if status == "missing_binary":
                self.start_stop_btn.Enable(
                    True
                )  # Clicking Start triggers download offer
            else:
                self.start_stop_btn.Enable(True)

        # Update PID
        if self.manager.pid:
            self.pid_val.SetValue(str(self.manager.pid))
        else:
            self.pid_val.SetValue("N/A")

        # Update Start Time
        if self.manager.start_time:
            dt = datetime.datetime.fromtimestamp(self.manager.start_time)
            self.start_time_val.SetValue(dt.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            self.start_time_val.SetValue("N/A")

        # Update Paths
        self.config_path_val.SetValue(self.manager.get_config_path())
        self.core_path_val.SetValue(self.manager.get_binary_path())

        # Call layout to handle any label resizing
        self.Layout()

    def OnTimerUpdate(self, event):
        """Updates Uptime periodically."""
        if self.manager.status == "running":
            uptime_sec = self.manager.get_uptime()
            td = datetime.timedelta(seconds=int(uptime_sec))
            self.uptime_val.SetValue(str(td))

            # Double check PID consistency
            if str(self.manager.pid) != self.pid_val.GetValue():
                self.UpdateFields()
        else:
            self.uptime_val.SetValue("N/A")

    def OnStatusChangedExternal(self, status: str):
        """Updates status immediately if changed externally."""
        if self.IsShown():
            self.UpdateFields()

    def OnToggleService(self, event):
        status = self.manager.status
        if status == "running":
            self.manager.stop_service()
        else:
            app = wx.GetApp()
            if hasattr(app, "start_xray_service"):
                app.start_xray_service()
            else:
                self.manager.start_service()
        self.UpdateFields()

    def OnRestartService(self, event):
        self.manager.restart_service()
        self.UpdateFields()

    def OnShow(self, event):
        if event.IsShown():
            self.UpdateFields()
            self.timer.Start(1000)
        else:
            self.timer.Stop()
        event.Skip()

    def OnClose(self, event):
        if self.app_exiting:
            event.Skip()
        else:
            self.Hide()
