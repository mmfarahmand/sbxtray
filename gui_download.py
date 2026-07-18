import json
import os
import re
import threading
import urllib.request
import zipfile
from typing import Optional

import wx

from core_manager import CoreManager


class DownloadDialog(wx.Dialog):
    def __init__(self, parent, manager: CoreManager):
        self.manager = manager
        core_display = "Xray-core" if self.manager.active_core == "xray" else "Sing-Box"

        super().__init__(
            parent,
            title=f"SBXTray - Download {core_display}",
            size=(420, 190),
            style=wx.DEFAULT_DIALOG_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX),
        )

        self.thread: Optional[threading.Thread] = None
        self.cancelled = False

        self.InitUI()

    def InitUI(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Primary status label
        self.status_label = wx.StaticText(
            panel, label="Querying GitHub API for latest release..."
        )
        self.status_label.SetFont(
            wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        )
        sizer.Add(self.status_label, 0, wx.ALL | wx.EXPAND, 15)

        # Progress gauge
        self.gauge = wx.Gauge(panel, range=100, style=wx.GA_HORIZONTAL)
        self.gauge.SetName("Download Progress Gauge")
        sizer.Add(self.gauge, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 15)

        # Detail / speed label
        self.progress_label = wx.StaticText(panel, label="")
        self.progress_label.SetFont(
            wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        )
        sizer.Add(self.progress_label, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 10)

        # Cancel Button
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.cancel_btn = wx.Button(panel, label="&Cancel")
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.OnCancel)
        btn_sizer.Add(self.cancel_btn, 0, wx.ALL, 10)

        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT)
        panel.SetSizer(sizer)

        # Dialog level sizer to fit panel
        dialog_sizer = wx.BoxSizer(wx.VERTICAL)
        dialog_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(dialog_sizer)

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.CenterOnParent()

    def StartDownload(self) -> None:
        self.thread = threading.Thread(target=self.RunDownload, daemon=True)
        self.thread.start()

    def RunDownload(self) -> None:
        try:
            active_core = self.manager.active_core
            if active_core == "xray":
                repo = "XTLS/Xray-core"
                pattern = r"^xray-(?!.*legacy).*windows-64\.zip$"
                core_display = "Xray-core"
            else:
                repo = "SagerNet/sing-box"
                pattern = r"^sing-box-(?!.*legacy).*windows-amd64\.zip$"
                core_display = "Sing-Box"

            wx.CallAfter(
                self.status_label.SetLabel,
                f"Connecting to GitHub API for {core_display}...",
            )

            req = urllib.request.Request(
                f"https://api.github.com/repos/{repo}/releases/latest",
                headers={"User-Agent": "sbxtray-manager/1.0"},
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8"))

            if self.cancelled:
                return

            # Parse assets for suitable Windows zip
            asset_url = None
            asset_name = None
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if re.match(pattern, name, re.IGNORECASE):
                    asset_url = asset.get("browser_download_url")
                    asset_name = name
                    break

            if not asset_url:
                raise Exception(
                    f"Could not find a suitable Windows 64-bit release asset in {repo} releases."
                )

            wx.CallAfter(self.status_label.SetLabel, f"Downloading {asset_name}...")

            # Stream the file to memory with progress updates
            req_asset = urllib.request.Request(
                asset_url, headers={"User-Agent": "sbxtray-manager/1.0"}
            )
            with urllib.request.urlopen(req_asset, timeout=15) as response:
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                chunk_size = 32768
                zip_data = bytearray()

                while not self.cancelled:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    zip_data.extend(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                        wx.CallAfter(
                            self.UpdateProgress,
                            percent,
                            f"Downloaded {downloaded // 1024} KB / {total_size // 1024} KB ({percent}%)",
                        )
                    else:
                        wx.CallAfter(
                            self.UpdateProgress,
                            -1,
                            f"Downloaded {downloaded // 1024} KB (size unknown)",
                        )

            if self.cancelled:
                return

            # Save downloaded file
            wx.CallAfter(self.status_label.SetLabel, "Saving file to disk...")
            wx.CallAfter(self.gauge.SetValue, 95)

            zip_path = os.path.join(self.manager.base_dir, asset_name)
            with open(zip_path, "wb") as f:
                f.write(zip_data)

            # Extract zip package
            wx.CallAfter(
                self.status_label.SetLabel, f"Extracting {core_display} ZIP package..."
            )
            wx.CallAfter(self.gauge.SetValue, 98)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                allowed_filenames = {
                    "xray.exe",
                    "sing-box.exe",
                    "wintun.dll",
                    "libcronet.dll",
                    "geoip.dat",
                    "geosite.dat",
                }
                for member in zip_ref.infolist():
                    basename = os.path.basename(member.filename)
                    if basename.lower() in allowed_filenames:
                        member.filename = basename
                        zip_ref.extract(member, self.manager.base_dir)

            # Clean up ZIP download
            os.remove(zip_path)

            wx.CallAfter(self.OnSuccess)

        except Exception as e:
            if not self.cancelled:
                wx.CallAfter(self.OnFailure, str(e))

    def UpdateProgress(self, percent: int, text: str) -> None:
        if percent >= 0:
            self.gauge.SetValue(percent)
        else:
            self.gauge.Pulse()
        self.progress_label.SetLabel(text)

    def OnCancel(self, event):
        self.cancelled = True
        self.EndModal(wx.ID_CANCEL)

    def OnClose(self, event):
        self.cancelled = True
        self.EndModal(wx.ID_CANCEL)

    def OnSuccess(self) -> None:
        core_display = "Xray-core" if self.manager.active_core == "xray" else "Sing-Box"
        wx.MessageBox(
            f"{core_display} downloaded and extracted successfully!",
            "Success",
            wx.OK | wx.ICON_INFORMATION,
        )
        self.EndModal(wx.ID_OK)

    def OnFailure(self, err_msg: str) -> None:
        core_display = "Xray-core" if self.manager.active_core == "xray" else "Sing-Box"
        wx.MessageBox(
            f"Failed to download {core_display} from GitHub:\n\n{err_msg}",
            "Download Error",
            wx.OK | wx.ICON_ERROR,
        )
        self.EndModal(wx.ID_CANCEL)
