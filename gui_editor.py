import json
import os
from typing import Optional

import wx

from core_manager import CoreManager


class ConfigEditor(wx.Frame):
    def __init__(self, parent, manager: CoreManager):
        super().__init__(
            parent,
            title="SBXTray - Edit Configuration",
            size=(700, 550),
            style=wx.DEFAULT_FRAME_STYLE,
        )
        self.manager = manager
        self.config_path = self.manager.get_config_path()
        self.app_exiting = False
        self.dirty = False
        self.loading = False
        self.original_content = ""

        self.InitUI()
        self.load_file()

    def InitUI(self):
        # Create a single root panel to host all controls for correct tab traversal on Windows
        root_panel = wx.Panel(self)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Monospace Text Control with Tab processing
        self.text_ctrl = wx.TextCtrl(root_panel, style=wx.TE_MULTILINE | wx.TE_RICH2)
        self.text_ctrl.SetName("JSON Configuration Editor")

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

        # Controls Panel (Save, Format, Close)
        ctrl_panel = wx.Panel(root_panel)
        ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Save Button
        self.save_btn = wx.Button(ctrl_panel, label="&Save")
        self.save_btn.Bind(wx.EVT_BUTTON, self.OnSave)
        ctrl_sizer.Add(self.save_btn, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)

        # Format JSON Button
        self.format_btn = wx.Button(ctrl_panel, label="Format &JSON")
        self.format_btn.Bind(wx.EVT_BUTTON, self.OnFormatJSON)
        ctrl_sizer.Add(self.format_btn, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)

        # Status indicator for unsaved changes
        self.status_label = wx.StaticText(ctrl_panel, label="")
        ctrl_sizer.Add(self.status_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        ctrl_sizer.AddStretchSpacer(1)

        # Close Button
        self.close_btn = wx.Button(ctrl_panel, label="&Close")
        self.close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        ctrl_sizer.Add(self.close_btn, 0, wx.ALIGN_CENTER_VERTICAL)

        ctrl_panel.SetSizer(ctrl_sizer)
        main_sizer.Add(ctrl_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        root_panel.SetSizer(main_sizer)

        # Frame level sizer to fit root panel
        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(root_panel, 1, wx.EXPAND)
        self.SetSizer(frame_sizer)

        # Event Bindings
        self.text_ctrl.Bind(wx.EVT_TEXT, self.OnTextChange)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_SHOW, self.OnShow)

        self.Center()

    def load_file(self) -> None:
        self.loading = True
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                content = "{}"
                # Save empty file initially
                with open(self.config_path, "w", encoding="utf-8") as f:
                    f.write(content)

            self.text_ctrl.SetValue(content)
            self.original_content = content
            self.set_dirty(False)
        except Exception as e:
            wx.MessageBox(
                f"Failed to load configuration file:\n{e}",
                "Error",
                wx.OK | wx.ICON_ERROR,
            )
        finally:
            self.loading = False

    def reload_config_path(self) -> None:
        """Dynamically reloads the configuration path and file when active core changes."""
        self.config_path = self.manager.get_config_path()
        self.load_file()

    def set_dirty(self, is_dirty: bool) -> None:
        self.dirty = is_dirty
        if is_dirty:
            self.status_label.SetLabel("* Unsaved changes")
        else:
            self.status_label.SetLabel("Saved")

    def validate_json(self) -> Optional[dict]:
        content = self.text_ctrl.GetValue()
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            err_line = e.lineno
            err_col = e.colno
            err_msg = e.msg
            wx.MessageBox(
                f"JSON Validation Failed!\n\nError: {err_msg}\nLine: {err_line}, Column: {err_col}",
                "Invalid JSON Configuration",
                wx.OK | wx.ICON_ERROR,
            )
            return None

    def save_config(self) -> bool:
        """Validates JSON and saves the configuration to file. Returns True if saved successfully."""
        parsed_json = self.validate_json()
        if parsed_json is None:
            return False  # Validation failed, don't save

        try:
            content = self.text_ctrl.GetValue()
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.original_content = content
            self.set_dirty(False)
            return True
        except Exception as e:
            wx.MessageBox(
                f"Failed to write configuration file:\n{e}",
                "Error",
                wx.OK | wx.ICON_ERROR,
            )
            return False

    def OnSave(self, event):
        if self.save_config():
            wx.MessageBox(
                "Configuration saved successfully!", "Info", wx.OK | wx.ICON_INFORMATION
            )

    def OnFormatJSON(self, event):
        parsed_json = self.validate_json()
        if parsed_json is not None:
            # Reformat content
            formatted_content = json.dumps(parsed_json, indent=2, ensure_ascii=False)
            self.loading = True
            self.text_ctrl.SetValue(formatted_content)
            self.loading = False
            self.set_dirty(formatted_content != self.original_content)

    def OnTextChange(self, event):
        if not self.loading:
            self.set_dirty(self.text_ctrl.GetValue() != self.original_content)
        event.Skip()

    def OnShow(self, event):
        if event.IsShown():
            # Only reload config if there are no unsaved edits
            if not self.dirty:
                self.load_file()
        event.Skip()

    def OnClose(self, event):
        if self.app_exiting:
            event.Skip()
            return

        if self.dirty:
            dlg = wx.MessageDialog(
                self,
                "You have unsaved changes to config.json.\nDo you want to save them before closing?",
                "Save Changes?",
                wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
            )
            res = dlg.ShowModal()
            dlg.Destroy()

            if res == wx.ID_YES:
                if self.save_config():
                    self.Hide()
                else:
                    event.Veto()  # Save failed/invalid JSON, keep editor open
            elif res == wx.ID_NO:
                # Discard and reload the original file contents
                self.load_file()
                self.Hide()
            else:
                event.Veto()  # Cancel close
        else:
            self.Hide()
