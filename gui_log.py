import wx

from core_manager import CoreManager


class LogWindow(wx.Frame):
    def __init__(self, parent, manager: CoreManager):
        super().__init__(
            parent,
            title="SBXTray - Live Logs",
            size=(750, 480),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self.manager = manager
        self.app_exiting = False
        self.autoscroll = True

        self.InitUI()
        self.manager.register_log_callback(self.OnLogReceived)

    def InitUI(self):
        # Create a root panel to host all controls for correct tab traversal on Windows
        root_panel = wx.Panel(self)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Monospace Text Control for logs
        self.text_ctrl = wx.TextCtrl(
            root_panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
        )
        self.text_ctrl.SetName("Xray Live Logs Viewer")

        # Configure Monospace Font
        font = wx.Font(
            10,
            wx.FONTFAMILY_TELETYPE,
            wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL,
            faceName="Consolas",
        )
        if not font.IsOk():
            font = wx.Font(
                10, wx.FONTFAMILY_MONOSPACE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
            )
        self.text_ctrl.SetFont(font)

        main_sizer.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        # Controls Panel (Clear, Save, Auto-scroll)
        ctrl_panel = wx.Panel(root_panel)
        ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Clear Button
        self.clear_btn = wx.Button(ctrl_panel, label="C&lear Logs")
        self.clear_btn.Bind(wx.EVT_BUTTON, self.OnClearLogs)
        ctrl_sizer.Add(self.clear_btn, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)

        # Save Button
        self.save_btn = wx.Button(ctrl_panel, label="&Save to File...")
        self.save_btn.Bind(wx.EVT_BUTTON, self.OnSaveLogs)
        ctrl_sizer.Add(self.save_btn, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)

        # Auto Scroll Checkbox
        self.scroll_cb = wx.CheckBox(ctrl_panel, label="&Auto-scroll")
        self.scroll_cb.SetValue(self.autoscroll)
        self.scroll_cb.Bind(wx.EVT_CHECKBOX, self.OnToggleScroll)
        ctrl_sizer.Add(self.scroll_cb, 0, wx.ALIGN_CENTER_VERTICAL)

        ctrl_sizer.AddStretchSpacer(1)

        # Close Button
        self.close_btn = wx.Button(ctrl_panel, label="&Close")
        self.close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Hide())
        ctrl_sizer.Add(self.close_btn, 0, wx.ALIGN_CENTER_VERTICAL)

        ctrl_panel.SetSizer(ctrl_sizer)
        main_sizer.Add(ctrl_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        root_panel.SetSizer(main_sizer)

        # Frame level sizer to fit root panel
        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(root_panel, 1, wx.EXPAND)
        self.SetSizer(frame_sizer)

        # Bindings
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_SHOW, self.OnShow)

        self.Center()

    def repopulate_logs(self):
        """Reloads all logs currently cached in the manager."""
        self.text_ctrl.Clear()
        # Copy logs to prevent size-mutation exceptions from thread racing
        logs_snapshot = list(self.manager.logs)
        self.text_ctrl.SetValue("".join(logs_snapshot))
        if self.autoscroll:
            self.text_ctrl.SetInsertionPointEnd()

    def OnLogReceived(self, line: str):
        """Called (via wx.CallAfter) when a new log line is emitted by the manager."""
        if self.IsShown():
            self.text_ctrl.AppendText(line)
            # Limit display to avoid UI slowing down with massive buffers
            num_lines = self.text_ctrl.GetNumberOfLines()
            if num_lines > 11000:
                self.repopulate_logs()
            elif self.autoscroll:
                self.text_ctrl.SetInsertionPointEnd()

    def OnClearLogs(self, event):
        self.manager.logs.clear()
        self.text_ctrl.Clear()

    def OnSaveLogs(self, event):
        with wx.FileDialog(
            self,
            "Save logs to file",
            wildcard="Text files (*.txt)|*.txt|Log files (*.log)|*.log|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as file_dialog:
            if file_dialog.ShowModal() == wx.ID_CANCEL:
                return

            path = file_dialog.GetPath()
            try:
                # Thread-safe read
                logs_content = "".join(list(self.manager.logs))
                with open(path, "w", encoding="utf-8") as f:
                    f.write(logs_content)
                wx.MessageBox(
                    "Logs successfully saved!", "Info", wx.OK | wx.ICON_INFORMATION
                )
            except Exception as e:
                wx.MessageBox(
                    f"Failed to save logs to file:\n{e}", "Error", wx.OK | wx.ICON_ERROR
                )

    def OnToggleScroll(self, event):
        self.autoscroll = self.scroll_cb.GetValue()
        if self.autoscroll:
            self.text_ctrl.SetInsertionPointEnd()

    def OnShow(self, event):
        if event.IsShown():
            self.repopulate_logs()
        event.Skip()

    def OnClose(self, event):
        if self.app_exiting:
            event.Skip()
        else:
            self.Hide()
