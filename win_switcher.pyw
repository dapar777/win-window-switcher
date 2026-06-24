import os
import re
import argparse
import ctypes
import ctypes.wintypes
import threading
import subprocess
import json
import shutil
import tkinter as tk
from tkinter import messagebox
import pystray
from PIL import Image, ImageDraw, ImageFont, ImageTk

# --- Windows API Constants & DLLs ---
User32 = ctypes.windll.user32
Kernel32 = ctypes.windll.kernel32
DwmApi = ctypes.windll.dwmapi

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

# Win32 Function Signatures
User32.EnumWindows.argtypes = [WNDENUMPROC, ctypes.c_void_p]
User32.IsWindowVisible.argtypes = [ctypes.c_void_p]
User32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
User32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
User32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
User32.GetWindow.argtypes = [ctypes.c_void_p, ctypes.c_uint]
User32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
User32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
User32.BringWindowToTop.argtypes = [ctypes.c_void_p]
User32.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
User32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
User32.keybd_event.argtypes = [ctypes.c_byte, ctypes.c_byte, ctypes.c_ulong, ctypes.c_void_p]
User32.IsIconic.argtypes = [ctypes.c_void_p]
User32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
User32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
User32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
User32.SetPropW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_void_p]
User32.SetPropW.restype = ctypes.c_bool
User32.GetPropW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
User32.GetPropW.restype = ctypes.c_void_p
User32.RemovePropW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
User32.RemovePropW.restype = ctypes.c_void_p
User32.SetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
User32.SetWindowTextW.restype = ctypes.c_bool
User32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
User32.PostMessageW.restype = ctypes.c_bool

Kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
Kernel32.OpenProcess.restype = ctypes.c_void_p
Kernel32.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
Kernel32.QueryFullProcessImageNameW.restype = ctypes.c_bool
User32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
User32.SetWindowPos.restype = ctypes.c_bool
User32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
User32.SetWindowLongW.restype = ctypes.c_long
Kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
Kernel32.CloseHandle.restype = ctypes.c_bool
User32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
User32.GetWindowRect.restype = ctypes.c_bool
User32.SetWinEventHook.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_uint]
User32.SetWinEventHook.restype = ctypes.c_void_p
User32.UnhookWinEvent.argtypes = [ctypes.c_void_p]
User32.UnhookWinEvent.restype = ctypes.c_bool
User32.GetMessageW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
User32.GetMessageW.restype = ctypes.c_int
User32.TranslateMessage.argtypes = [ctypes.c_void_p]
User32.TranslateMessage.restype = ctypes.c_bool
User32.DispatchMessageW.argtypes = [ctypes.c_void_p]
User32.DispatchMessageW.restype = ctypes.c_void_p
User32.SystemParametersInfoW.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
User32.SystemParametersInfoW.restype = ctypes.c_bool
User32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
User32.GetMonitorInfoW.restype = ctypes.c_bool

Shell32 = ctypes.windll.shell32
Shell32.SHAppBarMessage.argtypes = [ctypes.c_uint, ctypes.c_void_p]
Shell32.SHAppBarMessage.restype = ctypes.c_ulong

# AppBar constants
ABM_NEW      = 0x00000000
ABM_REMOVE   = 0x00000001
ABM_QUERYPOS = 0x00000002
ABM_SETPOS   = 0x00000003
ABE_LEFT     = 0
ABE_TOP      = 1
ABE_RIGHT    = 2
ABE_BOTTOM   = 3

# Rect structure for DWM
class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

class APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize",           ctypes.c_uint),
        ("hWnd",             ctypes.c_void_p),
        ("uCallbackMessage", ctypes.c_uint),
        ("uEdge",            ctypes.c_uint),
        ("rc",               RECT),
        ("lParam",           ctypes.c_ssize_t),
    ]

# DWM Thumbnail Structure and definitions
class DWM_THUMBNAIL_PROPERTIES(ctypes.Structure):
    _fields_ = [
        ("dwFlags", ctypes.wintypes.DWORD),
        ("rcDestination", RECT),
        ("rcSource", RECT),
        ("opacity", ctypes.c_byte),
        ("fVisible", ctypes.wintypes.BOOL),
        ("fSourceClientAreaOnly", ctypes.wintypes.BOOL)
    ]

DWM_TNP_RECTDESTINATION = 0x00000001
DWM_TNP_OPACITY = 0x00000004
DWM_TNP_VISIBLE = 0x00000008
DWM_TNP_SOURCECLIENTAREAONLY = 0x00000010

# --- ITaskbarList COM (for hiding/showing taskbar buttons per group) ---
class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]

def _make_guid(d1, d2, d3, d4):
    g = _GUID()
    g.Data1 = d1
    g.Data2 = d2
    g.Data3 = d3
    g.Data4 = (ctypes.c_ubyte * 8)(*d4)
    return g

# CLSID_TaskbarList  = {56FDF344-FD6D-11D0-958A-006097C9A090}
# IID_ITaskbarList   = {56FDF342-FD6D-11D0-958A-006097C9A090}
_CLSID_TaskbarList = _make_guid(0x56FDF344, 0xFD6D, 0x11D0, [0x95, 0x8A, 0x00, 0x60, 0x97, 0xC9, 0xA0, 0x90])
_IID_ITaskbarList  = _make_guid(0x56FDF342, 0xFD6D, 0x11D0, [0x95, 0x8A, 0x00, 0x60, 0x97, 0xC9, 0xA0, 0x90])

# Configure DWM argument signatures
DwmApi.DwmRegisterThumbnail.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
DwmApi.DwmUpdateThumbnailProperties.argtypes = [ctypes.c_void_p, ctypes.POINTER(DWM_THUMBNAIL_PROPERTIES)]
DwmApi.DwmUnregisterThumbnail.argtypes = [ctypes.c_void_p]

GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
GW_OWNER = 4
SW_RESTORE = 9
SW_SHOW = 5
WM_HOTKEY = 0x0312
HWND_TOPMOST   = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE     = 0x0002
SWP_NOSIZE_FLAG = 0x0001
SWP_NOZORDER_FLAG = 0x0004
EVENT_SYSTEM_MOVESIZEEND = 0x000B
WINEVENT_OUTOFCONTEXT    = 0x0000

# --- Application Configuration ---
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.txt")

class WindowSwitcherApp:
    def __init__(self, root, keep_groups=False):
        self.root = root
        self.root.title("Quick Window Switcher")
        
        # Window properties
        self.root.overrideredirect(True)  # Frameless window
        self.root.attributes("-topmost", True)
        
        # Modern Dark Theme Colors
        self.bg_color = "#1e1e24"
        self.fg_color = "#e2e2e7"
        self.accent_color = "#007acc"
        self.list_bg = "#25252d"
        self.list_sel_bg = "#2a5a8a"
        self.list_sel_fg = "#ffffff"
        self.footer_color = "#8a8a93"
        
        self.root.configure(bg=self.bg_color)
        
        # State variables
        self.is_visible = False
        self.shortcuts = []
        self.show_thumbnails = True  # Side preview
        self.show_list_thumbnails = True  # Inline small previews
        self.current_thumbnail_handle = None
        self.all_windows = []
        self.filtered_items = []  # Matches current search filter
        
        # Row-specific inline DWM thumbnail handles
        self.row_thumbnail_handles = []
        self.selected_index = 0
        
        # Runtime session group tracking (mapping hwnd -> set of group_names)
        self.runtime_hwnd_to_groups = {}
        
        # Groups persistence
        self.groups_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "groups.json")
        self.groups = {}
        self.views = {}
        self.last_group = ""
        self.last_activated_group = ""
        self.activated_windows_hwnds = set()  # HWNDs seen when group was last activated
        self.declined_new_windows = set()    # HWNDs user declined to add (reset on group switch)
        self._pending_ask_hwnds = set()       # HWNDs for which ask-dialog is currently open
        self.pending_new_windows = []  # New windows not yet in any group (for 'ask' mode)
        self.new_window_action = "never"  # Config: never | ask | always | leave
        self.new_window_auto_yes      = None  # compiled regex: auto-add matching titles
        self.new_window_auto_no       = None  # compiled regex: auto-skip matching titles (stay in group)
        self.new_window_auto_no_leave = None  # compiled regex: auto-skip + leave group
        self.auto_close_windows = None  # compiled regex: auto-close matching new windows
        self.prev_active_hwnd = None
        self.prev_active_title = ""
        # Taskbar icon hiding via ITaskbarList COM
        self.hide_taskbar_icons = False
        self.hide_alttab_icons = False
        self._taskbar_hidden_hwnds = set()
        self._taskbar_hidden_ex_styles = {}  # hwnd -> original EXSTYLE
        self._taskbar_com_obj = None
        self._taskbar_vtable = None
        # Multi-select state (aaa / aai mode)
        self.multi_selected = set()        # set of indices in filtered_items
        self.multi_sel_bg = "#1e3e5e"      # bg for multi-selected (not cursor) rows
        # Window anchoring (kkk / kka)
        self.anchored_hwnds = {}           # hwnd -> {"group_ctx": str|None, "global_anchor": bool}
        self._anchor_hook_handle = None
        self._anchor_proc_ref = None       # Keep WinEventProc from GC
        self._anchor_hook_thread = None
        self._original_workareas = {}      # kept for compat but unused
        self._appbar_windows = {}          # key -> (helper_toplevel, hwnd)
        # Foreground-change group exit detection
        self._fg_hook_thread = None
        self._fg_proc_ref = None
        self._fg_hook_handle = None
        self.load_groups()
        # Promazání skupin při každém startu – řízeno přepínačem --keep-groups
        if not keep_groups:
            self.groups = {"_": []}
            self.views = {}
            self.save_groups()
        
        # Load config
        self.load_config()
        self._init_taskbar_com()
        
        # Setup modern GUI layout
        self.setup_ui()
        
        # Bind virtual events
        self.root.bind("<<ShowSwitcher>>", lambda e: self.on_hotkey_pressed())
        self.root.bind("<FocusOut>", lambda e: self.hide_switcher_on_focus_loss())
        
        # Hide initially
        self.root.withdraw()
        
        # Start hotkey thread
        self.hotkey_running = True
        self.hotkey_thread = threading.Thread(target=self.listen_global_hotkey, daemon=True)
        self.hotkey_thread.start()

        # Tray icon
        self.tray_icon = None
        self.tray_thread = threading.Thread(target=self._run_tray, daemon=True)
        self.tray_thread.start()

        # Foreground window tracking – auto-exit group when user switches outside it
        self._fg_hook_thread = threading.Thread(target=self._run_foreground_hook, daemon=True)
        self._fg_hook_thread.start()

        # OSD overlay - trvalé zobrazení názvu skupiny na všech monitorech
        self.osd_windows = []  # seznam OSD oken pro každý monitor
        self._setup_osd()

        # Background hlídání nových oken (ask/always mode)
        self._watch_new_windows_scheduled = False
        self._watch_timer_id = None
        self.root.after(3000, self._watch_new_windows)

    def _get_monitors(self):
        """Vrátí seznam monitorů jako (x, y, w, h)."""
        MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(RECT), ctypes.c_void_p)
        monitors = []
        def cb(hMon, hDC, lpRect, lParam):
            r = lpRect.contents
            monitors.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
            return True
        User32.EnumDisplayMonitors(None, None, MonitorEnumProc(cb), 0)
        if not monitors:
            monitors = [(0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())]
        return monitors

    def _get_active_window_monitor(self):
        """Vrátí (x, y, w, h) monitoru, na kterém je aktivní okno."""
        hwnd = User32.GetForegroundWindow()
        monitors = self._get_monitors()
        if hwnd:
            rect = RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            win_cx = (rect.left + rect.right) // 2
            win_cy = (rect.top + rect.bottom) // 2
            for mx, my, mw, mh in monitors:
                if mx <= win_cx < mx + mw and my <= win_cy < my + mh:
                    return (mx, my, mw, mh)
        return monitors[0]

    def _setup_osd(self):
        """Vytvoří OSD okno pro každý monitor."""
        for osd in self.osd_windows:
            try:
                osd["win"].destroy()
            except Exception:
                pass
        self.osd_windows = []
        for mx, my, mw, mh in self._get_monitors():
            win = tk.Toplevel(self.root)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            win.attributes("-transparentcolor", "#010101")
            win.configure(bg="#010101")
            lbl = tk.Label(
                win,
                text="",
                font=("Times New Roman", 24, "bold"),
                bg="#010101",
                fg="#a0a0a0",
                bd=0,
                relief="flat",
                highlightthickness=0,
                padx=18,
                pady=10
            )
            lbl.pack()
            self.osd_windows.append({"win": win, "label": lbl, "mx": mx, "my": my, "mw": mw, "mh": mh})
            win.withdraw()

    def _osd_reposition_one(self, osd_entry, text):
        win = osd_entry["win"]
        lbl = osd_entry["label"]
        mx, my, mw, mh = osd_entry["mx"], osd_entry["my"], osd_entry["mw"], osd_entry["mh"]
        lbl.config(text=text)
        win.update_idletasks()
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()
        x = mx + int(mw * 0.75) - w // 2
        y = my + mh - h - 4
        win.geometry(f"+{x}+{y}")

    def _update_osd(self, group_name, _reassert=False):
        label = group_name if group_name else ""
        if label:
            for osd_entry in self.osd_windows:
                self._osd_reposition_one(osd_entry, label)
                osd_entry["win"].deiconify()
                osd_entry["win"].lift()
                osd_entry["win"].attributes("-topmost", True)
                # WinAPI HWND_TOPMOST – spolehlivější než Tkinter na multi-monitoru
                try:
                    hwnd_osd = User32.GetAncestor(osd_entry["win"].winfo_id(), 3)
                    User32.SetWindowPos(hwnd_osd, HWND_TOPMOST, 0, 0, 0, 0,
                                        SWP_NOMOVE | SWP_NOSIZE_FLAG)
                except Exception:
                    pass
            if not _reassert:
                # Tři vlny re-assertů pro různě pomalé compositor/display stack situace
                for delay in (300, 1000, 3000):
                    def _deferred_reassert(g=group_name):
                        if self.last_activated_group == g:
                            self._update_osd(g, _reassert=True)
                    self.root.after(delay, _deferred_reassert)
        else:
            for osd_entry in self.osd_windows:
                osd_entry["win"].withdraw()

    def _make_tray_image(self, group_name):
        """Vygeneruje 64x64 ikonku s názvem skupiny."""
        img = Image.new("RGBA", (64, 64), (30, 30, 36, 255))
        draw = ImageDraw.Draw(img)
        label = group_name[2:].upper() if group_name.startswith("gg") else ("~" if not group_name else group_name[:4].upper())
        if not label:
            label = "≡"
        try:
            font = ImageFont.truetype("arialbd.ttf", 22)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((64 - tw) / 2 - bbox[0], (64 - th) / 2 - bbox[1]), label, font=font, fill=(0, 172, 255, 255))
        return img

    def _run_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("Ukončit", lambda icon, item: self.root.after(0, self.quit_app))
        )
        self.tray_icon = pystray.Icon(
            "WinSwitcher",
            self._make_tray_image(""),
            title="Win Switcher | skupina: žádná",
            menu=menu
        )
        self.tray_icon.run()

    def _update_tray(self, group_name):
        if self.tray_icon is None:
            return
        label = group_name if group_name else "žádná"
        self.tray_icon.title = f"Win Switcher | skupina: {label}"
        self.tray_icon.icon = self._make_tray_image(group_name)

    def load_config(self):
        self.shortcuts = []
        self.show_thumbnails = False # Side preview defaulted to False as we scale inline
        self.show_list_thumbnails = True
        self.list_thumbnail_scale = 5.0 # default scale factor
        self.window_height = 680 # default height
        self.hotkey_modifier = 0x0008 # MOD_WIN (Win key)
        self.hotkey_vk = 0x09 # VK_TAB (Tab key)
        
        if not os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    f.write(
                        "# Konfigurační soubor pro přepínání oken\n"
                        "# Formát: <zkratka> <vzor_regulárního_výrazu> <příkaz_na_spuštění>\n"
                        "vn .*notes.* code -n c:/notes\n"
                        "gc .*chrome.* \"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\"\n"
                        "\n"
                        "# Nastavení zobrazování bočního živého náhledu (true / false)\n"
                        "show_thumbnails false\n"
                        "\n"
                        "# Nastavení zobrazování malých náhledů přímo v seznamu oken (true / false)\n"
                        "show_list_thumbnails true\n"
                        "\n"
                        "# Měřítko zvětšení malých náhledů (např. 5 pro pětinásobné zvětšení z původních 48x30)\n"
                        "list_thumbnail_scale 5.0\n"
                        "\n"
                        "# Výška okna přepínače\n"
                        "window_height 680\n"
                        "\n"
                        "# Globální aktivační klávesová zkratka (např. win+tab nebo win+caps)\n"
                        "# Parametr hotkey_modifier podporuje: win, ctrl, alt, shift\n"
                        "hotkey_modifier win\n"
                        "hotkey_key tab\n"
                    )
            except Exception:
                pass
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                            
                        if line.startswith("show_thumbnails "):
                            val = line.split(None, 1)[1].lower()
                            self.show_thumbnails = (val == "true" or val == "1" or val == "yes")
                            continue
                            
                        if line.startswith("show_list_thumbnails "):
                            val = line.split(None, 1)[1].lower()
                            self.show_list_thumbnails = (val == "true" or val == "1" or val == "yes")
                            continue
                            
                        if line.startswith("list_thumbnail_scale "):
                            try:
                                self.list_thumbnail_scale = float(line.split(None, 1)[1])
                            except Exception:
                                self.list_thumbnail_scale = 5.0
                            continue

                        if line.startswith("window_height "):
                            try:
                                self.window_height = int(line.split(None, 1)[1])
                            except Exception:
                                self.window_height = 680
                            continue

                        if line.startswith("hotkey_modifier "):
                            mod = line.split(None, 1)[1].lower()
                            flags = 0
                            for token in re.split(r"[+\s]+", mod):
                                if token in ("win", "lwin", "rwin", "meta", "super"):
                                    flags |= 0x0008
                                elif token in ("alt", "menu"):
                                    flags |= 0x0001
                                elif token in ("ctrl", "control"):
                                    flags |= 0x0002
                                elif token == "shift":
                                    flags |= 0x0004
                            if flags:
                                self.hotkey_modifier = flags
                            continue

                        if line.startswith("hotkey_key "):
                            kv = line.split(None, 1)[1].lower()
                            if kv == "tab":
                                self.hotkey_vk = 0x09
                            elif kv in ("caps", "capslock", "caps_lock"):
                                self.hotkey_vk = 0x14
                            elif kv == "space":
                                self.hotkey_vk = 0x20
                            elif len(kv) == 1 and kv.isalpha():
                                self.hotkey_vk = ord(kv.upper())
                            elif len(kv) == 1 and kv.isdigit():
                                self.hotkey_vk = ord(kv)
                            elif kv.startswith("f") and kv[1:].isdigit():
                                fn = int(kv[1:])
                                if 1 <= fn <= 24:
                                    self.hotkey_vk = 0x6F + fn  # F1=0x70, F12=0x7B, ...
                            else:
                                try:
                                    self.hotkey_vk = int(kv, 16)
                                except Exception:
                                    self.hotkey_vk = 0x09 # Fallback tab
                            continue

                        if line.startswith("new_window_action "):
                            val = line.split(None, 1)[1].lower()
                            if val in ("never", "ask", "always", "leave"):
                                self.new_window_action = val
                            continue

                        if line.startswith("new_window_auto_yes "):
                            pattern = line.split(None, 1)[1].strip()
                            try:
                                self.new_window_auto_yes = re.compile(pattern, re.IGNORECASE)
                            except re.error:
                                self.new_window_auto_yes = None
                            continue

                        if line.startswith("new_window_auto_no "):
                            pattern = line.split(None, 1)[1].strip()
                            try:
                                self.new_window_auto_no = re.compile(pattern, re.IGNORECASE)
                            except re.error:
                                self.new_window_auto_no = None
                            continue

                        if line.startswith("new_window_auto_no_leave "):
                            pattern = line.split(None, 1)[1].strip()
                            try:
                                self.new_window_auto_no_leave = re.compile(pattern, re.IGNORECASE)
                            except re.error:
                                self.new_window_auto_no_leave = None
                            continue

                        if line.startswith("auto_close_windows "):
                            pattern = line.split(None, 1)[1].strip()
                            try:
                                self.auto_close_windows = re.compile(pattern, re.IGNORECASE)
                            except re.error:
                                self.auto_close_windows = None
                            continue

                        if line.startswith("hide_taskbar_icons "):
                            val = line.split(None, 1)[1].lower()
                            self.hide_taskbar_icons = val in ("true", "1", "yes")
                            continue

                        if line.startswith("hide_alttab_icons "):
                            val = line.split(None, 1)[1].lower()
                            self.hide_alttab_icons = val in ("true", "1", "yes")
                            continue
                            
                        parts = line.split(maxsplit=2)
                        if len(parts) == 3:
                            self.shortcuts.append({
                                "shortcut": parts[0],
                                "pattern": parts[1],
                                "command": parts[2]
                            })
            except Exception as e:
                print(f"Chyba při načítání configu: {e}")

    def load_groups(self):
        if os.path.exists(self.groups_file):
            try:
                with open(self.groups_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "groups" in data:
                        self.groups = data.get("groups", {})
                        self.views = data.get("views", {})
                    else:
                        self.groups = data
                        self.views = {}
            except Exception as e:
                print(f"Chyba při načítání skupin: {e}")
                try:
                    shutil.copy2(self.groups_file, self.groups_file + ".bak")
                    print("Záloha poškozených skupin vytvořena.")
                except Exception:
                    pass
                self.groups = {}
                self.views = {}
        else:
            self.groups = {}
            self.views = {}
        self.ensure_default_group()

    def save_groups(self):
        self.ensure_default_group()
        try:
            tmp_file = self.groups_file + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump({"groups": self.groups, "views": self.views}, f, ensure_ascii=False, indent=4)
            os.replace(tmp_file, self.groups_file)
        except Exception as e:
            print(f"Chyba při ukládání skupin: {e}")

    def ensure_default_group(self):
        if "_" not in self.groups:
            self.groups = {"_": [] , **self.groups}
        elif list(self.groups.keys())[0] != "_":
            default_items = self.groups.get("_", [])
            other_groups = {k: v for k, v in self.groups.items() if k != "_"}
            self.groups = {"_": default_items, **other_groups}

    def get_window_rect(self, hwnd):
        rect = RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return {
            "left": rect.left,
            "top": rect.top,
            "right": rect.right,
            "bottom": rect.bottom,
            "width": rect.right - rect.left,
            "height": rect.bottom - rect.top
        }

    def set_window_position(self, hwnd, x, y, width, height):
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        return User32.SetWindowPos(hwnd, None, x, y, width, height, SWP_NOZORDER | SWP_NOACTIVATE)

    def _window_matches_saved_entry(self, win, entry):
        os_prop_id = User32.GetPropW(win["hwnd"], "WinSwitcherID")
        if os_prop_id and entry.get("id") and int(os_prop_id) == int(entry.get("id")):
            return True

        if entry.get("process") and entry.get("class") and entry.get("title"):
            return (
                entry["process"].lower() == win["process"].lower() and
                entry["class"] == win["class"] and
                entry["title"] == win["title"]
            )

        if entry.get("title") and entry["title"] in win["title"]:
            return True

        return False

    def save_group_view(self, group_name, view_name):
        if group_name not in self.views:
            self.views[group_name] = {}

        view_items = []
        for win in self.all_windows:
            if group_name == "" or self.is_window_in_group(win, group_name):
                rect = self.get_window_rect(win["hwnd"])
                view_items.append({
                    "id": int(User32.GetPropW(win["hwnd"], "WinSwitcherID")) if User32.GetPropW(win["hwnd"], "WinSwitcherID") else None,
                    "process": win.get("process", ""),
                    "class": win.get("class", ""),
                    "title": win.get("title", ""),
                    "rect": rect
                })

        self.views[group_name][view_name] = view_items
        self.save_groups()
        return len(view_items) > 0

    def load_group_view(self, group_name, view_name):
        group_views = self.views.get(group_name, {})
        saved_view = group_views.get(view_name)
        if not saved_view:
            return False

        loaded_any = False
        for entry in saved_view:
            for win in self.all_windows:
                if self._window_matches_saved_entry(win, entry):
                    rect = entry.get("rect")
                    if rect:
                        hwnd = win["hwnd"]
                        if User32.IsIconic(hwnd):
                            User32.ShowWindow(hwnd, SW_RESTORE)
                        self.set_window_position(hwnd, rect["left"], rect["top"], rect["width"], rect["height"])
                        loaded_any = True
                        break
        return loaded_any

    def is_window_in_group(self, win, group_name):
        # 1. Použij cachovaný WinSwitcherID z win dict (nastaven v get_open_windows, bez WinAPI volání)
        os_prop_id = win.get("win_switcher_id")
        
        # 2. Default group '_' means "all windows not in any other named group"
        if group_name == "_":
            other_groups = [g for g in self.groups.keys() if g != "_"]
            if not other_groups:
                return True
            return not self.is_window_in_any_group(win)

        # 2. Check runtime session HWND mapping as well
        if group_name in self.runtime_hwnd_to_groups:
            if win["hwnd"] in self.runtime_hwnd_to_groups[group_name]:
                return True
                
        saved_entries = self.groups.get(group_name, [])
        for entry in saved_entries:
            if isinstance(entry, dict):
                st_id = entry.get("id")
                st_title = entry.get("title", "")
                st_class = entry.get("class", "")
                st_proc = entry.get("process", "")
                
                # Perfect match if the window properties match the saved UUID/ID
                if os_prop_id and st_id and int(os_prop_id) == int(st_id):
                    if group_name not in self.runtime_hwnd_to_groups:
                        self.runtime_hwnd_to_groups[group_name] = set()
                    self.runtime_hwnd_to_groups[group_name].add(win["hwnd"])
                    return True

                # Fallback: match only starší záznamy bez ID, ne nové uložené položky
                if not st_id and st_class and st_proc and win["class"] == st_class and win["process"].lower() == st_proc.lower():
                    if group_name not in self.runtime_hwnd_to_groups:
                        self.runtime_hwnd_to_groups[group_name] = set()
                    self.runtime_hwnd_to_groups[group_name].add(win["hwnd"])
                    return True
            else:
                # Legacy string support
                title = win["title"]
                if entry == title or entry in title or title in entry:
                    if group_name not in self.runtime_hwnd_to_groups:
                        self.runtime_hwnd_to_groups[group_name] = set()
                    self.runtime_hwnd_to_groups[group_name].add(win["hwnd"])
                    return True
        return False

    def is_window_in_any_group(self, win):
        for g_name in self.groups:
            if g_name == "_":
                continue
            if self.is_window_in_group(win, g_name):
                return True
        return False

    def reload_config(self, event=None):
        self.load_config()
        self.clear_all_row_thumbnails()
        self.clear_thumbnail()
        
        # Grid layout adjustments
        if not self.show_thumbnails:
            self.preview_canvas.pack_forget()
        else:
            self.preview_canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            
        self.center_on_screen()
        self.on_text_changed()
        
        status_text = f"Načteno (zkratky: {len(self.shortcuts)}, náhledy: {'ANO' if self.show_thumbnails else 'NE'}, řádkové: {'ANO' if self.show_list_thumbnails else 'NE'})"
        self.status_label.config(text=status_text)
        self.root.after(2000, lambda: self.status_label.config(text="Ctrl+R: Načíst config | Ctrl+Q: Ukončit | Esc: Zavřít"))

    def setup_ui(self):
        # Outer border frame
        self.main_frame = tk.Frame(self.root, bg=self.bg_color, bd=2, highlightbackground=self.accent_color, highlightthickness=1)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Search Entry Container
        entry_container = tk.Frame(self.main_frame, bg=self.bg_color, padx=10, pady=10)
        entry_container.pack(fill=tk.X)
        
        # Search Entry
        self.entry_var = tk.StringVar()
        self.entry_var.trace_add("write", lambda *args: self.on_text_changed())
        
        self.entry = tk.Entry(
            entry_container,
            textvariable=self.entry_var,
            font=("Segoe UI", 14),
            bg=self.list_bg,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            bd=0,
            highlightthickness=1,
            highlightbackground="#3e3e4a",
            highlightcolor=self.accent_color
        )
        self.entry.pack(fill=tk.X, ipady=8, pady=2)
        
        # Main content layout (Left side scrollable frame, Right side big preview)
        self.content_frame = tk.Frame(self.main_frame, bg=self.bg_color)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Custom Scrollable List Container (replaces Tkinter's Listbox)
        self.list_cnt = tk.Frame(self.content_frame, bg=self.bg_color, padx=10, pady=5)
        self.list_cnt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.list_scrollbar = tk.Scrollbar(self.list_cnt, orient=tk.VERTICAL)
        self.list_canvas = tk.Canvas(
            self.list_cnt,
            bg=self.list_bg,
            bd=0,
            highlightthickness=0,
            yscrollcommand=self.on_canvas_scroll
        )
        self.list_scrollbar.config(command=self.list_canvas.yview)
        
        self.scroll_rows_frame = tk.Frame(self.list_canvas, bg=self.list_bg)
        self.scroll_window_id = self.list_canvas.create_window((0, 0), window=self.scroll_rows_frame, anchor="nw")
        
        self.scroll_rows_frame.bind("<Configure>", lambda e: self.list_canvas.config(scrollregion=self.list_canvas.bbox("all")))
        self.list_canvas.bind("<Configure>", lambda e: [self.list_canvas.itemconfig(self.scroll_window_id, width=e.width), self.update_all_row_thumbnails()])
        
        self.list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Live Windows DWM Preview Canvas (Right side)
        self.preview_canvas = tk.Canvas(
            self.content_frame,
            bg=self.list_bg,
            bd=1,
            highlightthickness=0
        )
        if self.show_thumbnails:
            self.preview_canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            
        # Footer Help Text
        self.status_label = tk.Label(
            self.main_frame,
            text="Ctrl+R: Načíst config | Ctrl+Q: Ukončit | Esc: Zavřít",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.footer_color,
            anchor="w",
            padx=10,
            pady=5
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.root.bind("<Escape>", lambda e: self.hide_switcher())
        self.root.bind("<Control-q>", lambda e: self.quit_app())
        self.root.bind("<Control-r>", lambda e: self.reload_config())
        
        self.entry.bind("<Down>", self.move_selection_down)
        self.entry.bind("<Up>", self.move_selection_up)
        self.entry.bind("<Left>", self.navigate_group_left)
        self.entry.bind("<Right>", self.navigate_group_right)
        self.entry.bind("<Return>", self.on_item_activated)
        # Intercept Insert via generic KeyPress + Windows keycode (VK_INSERT=45).
        # This works regardless of keysym name, keyboard layout, or Tk version.
        self.entry.bind("<KeyPress>", self._on_entry_keypress, add=True)

    def center_on_screen(self):
        self.root.update_idletasks()
        w = 950 if self.show_thumbnails else (850 if self.list_thumbnail_scale >= 3.0 else 650)
        h = getattr(self, "window_height", 680)
        # Zobrazení na monitoru aktivního okna
        mx, my, mw, mh = self._get_active_window_monitor()
        x = mx + (mw - w) // 2
        y = my + (mh - h) // 2
        self.root.geometry(f"{w}x{h}+{int(x)}+{int(y)}")

    def get_open_windows(self):
        windows = []
        def callback(hwnd, lParam):
            if User32.IsWindowVisible(hwnd):
                length = User32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    User32.GetWindowTextW(hwnd, buffer, length + 1)
                    title = buffer.value
                    
                    if title == "Quick Window Switcher":
                        return True

                    # Přeskoč všechna okna vlastního procesu (dialogy, OSD, tray…)
                    _own_pid = ctypes.c_ulong()
                    User32.GetWindowThreadProcessId(hwnd, ctypes.byref(_own_pid))
                    if _own_pid.value == os.getpid():
                        return True

                    ex_style = User32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    hidden_by_switcher = bool(User32.GetPropW(hwnd, "WinSwitcherExStyle"))
                    if not (ex_style & WS_EX_TOOLWINDOW) or hidden_by_switcher:
                        owner = User32.GetWindow(hwnd, GW_OWNER)
                        if not owner:
                            # Retrieve class name and process executable name
                            class_buf = ctypes.create_unicode_buffer(512)
                            User32.GetClassNameW(hwnd, class_buf, 512)
                            class_name = class_buf.value
                            
                            pid = ctypes.c_ulong()
                            User32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                            process_name = ""
                            h_process = Kernel32.OpenProcess(0x1000, False, pid)
                            if h_process:
                                path_buf = ctypes.create_unicode_buffer(1024)
                                p_size = ctypes.c_ulong(1024)
                                if Kernel32.QueryFullProcessImageNameW(h_process, 0, path_buf, ctypes.byref(p_size)):
                                    process_name = os.path.basename(path_buf.value)
                                Kernel32.CloseHandle(h_process)
                                
                            # Cache WinSwitcherID hned při enumeraci – GetPropW je drahé volání
                            win_switcher_id = User32.GetPropW(hwnd, "WinSwitcherID")
                            windows.append({
                                "hwnd": hwnd,
                                "title": title,
                                "class": class_name,
                                "process": process_name,
                                "win_switcher_id": int(win_switcher_id) if win_switcher_id else None
                            })
            return True
            
        User32.EnumWindows(WNDENUMPROC(callback), 0)

        # Deduplikace: pokud více oken má stejný WinSwitcherID (kontaminace starým fallbackem),
        # zachovej ID jen u prvního, u ostatních odstraň (RemovePropW) a vynuluj cache.
        seen_ids = {}
        for w in windows:
            wid = w["win_switcher_id"]
            if wid is None:
                continue
            if wid not in seen_ids:
                seen_ids[wid] = w["hwnd"]
            else:
                # Duplicitní ID – odstraň z OS okna i z cache
                User32.RemovePropW(w["hwnd"], "WinSwitcherID")
                w["win_switcher_id"] = None

        return windows

    def on_hotkey_pressed(self):
        if self.is_visible:
            # If the switcher is already visible, pressing the hotkey acts as Enter to select currently selected window
            self.on_item_activated()
        else:
            self.show_switcher()

    def show_switcher(self):
        self.is_visible = True
        # Capture previous active window
        prev_hwnd = User32.GetForegroundWindow()
        self.prev_active_hwnd = prev_hwnd
        self.prev_active_title = ""
        if prev_hwnd:
            length = User32.GetWindowTextLengthW(prev_hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                User32.GetWindowTextW(prev_hwnd, buffer, length + 1)
                if buffer.value != "Quick Window Switcher":
                    self.prev_active_title = buffer.value
                else:
                    self.prev_active_title = ""

        self.all_windows = self.get_open_windows()
        self._refresh_window_group_titles()

        self.entry_var.set(self.last_group + " " if self.last_group else "")
        self.center_on_screen()
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        
        try:
            hwnd_tk = self.root.winfo_id()
            hwnd_host = User32.GetAncestor(hwnd_tk, 3)
            User32.ShowWindow(hwnd_host, SW_SHOW)
            
            User32.keybd_event(0x12, 0, 0, 0)
            User32.keybd_event(0x12, 0, 2, 0)
            
            User32.SetForegroundWindow(hwnd_host)
            User32.BringWindowToTop(hwnd_host)
        except Exception as e:
            print(f"Chyba v popředí: {e}")
            
        self.root.focus_force()
        self.entry.focus_set()
        
        self.on_text_changed()

    def hide_switcher(self):
        self.is_visible = False
        self.clear_all_row_thumbnails()
        self.clear_thumbnail()
        self.root.withdraw()
        # root.withdraw() skryje i vlastněná OSD okna (Win32 owned windows) –
        # pokud jsme stále ve skupině, znovu je zobrazíme s malým zpožděním.
        if self.last_activated_group:
            g = self.last_activated_group
            self.root.after(50, lambda: self._update_osd(g, _reassert=True) if self.last_activated_group == g else None)

    def hide_switcher_on_focus_loss(self):
        self.root.after(100, self._check_focus_and_hide)

    def _check_focus_and_hide(self):
        focused_widget = self.root.focus_get()
        if focused_widget is None:
            self.hide_switcher()

    def on_text_changed(self):
        # Debounce – čeká 60ms po posledním stisku klávesy, pak teprve renderuje
        if hasattr(self, '_text_changed_after_id') and self._text_changed_after_id:
            self.root.after_cancel(self._text_changed_after_id)
        self._text_changed_after_id = self.root.after(60, self._do_text_changed)

    def _do_text_changed(self):
        self._text_changed_after_id = None
        self.clear_all_row_thumbnails()
        search_text = self.entry_var.get().strip()
        self.multi_selected = set()  # Reset multi-select on any text change
        
        for r_widget in self.scroll_rows_frame.winfo_children():
            r_widget.destroy()
            
        self.filtered_items = []
        
        # Check if the search text starts with a group pattern "gg..." or the default group "_"
        first_token = ""
        tokens = search_text.split()
        if tokens:
            first_token = tokens[0]
            
        if (first_token.lower().startswith("gg") and len(first_token) > 2) or first_token == "_":
            group_name = first_token.lower()
            remaining = search_text[len(first_token):].strip()
            self.last_group = group_name  # Keep the group prefilled

            if group_name == "_":
                other_groups = [g for g in self.groups.keys() if g != "_"]
                if not other_groups:
                    for win in self.all_windows:
                        if not remaining or remaining.lower() in win["title"].lower() or remaining.lower() in win["process"].lower():
                            self.filtered_items.append({
                                "type": "window",
                                "hwnd": win["hwnd"],
                                "title": win["title"]
                            })
                else:
                    for win in self.all_windows:
                        if not self.is_window_in_any_group(win):
                            if not remaining or remaining.lower() in win["title"].lower() or remaining.lower() in win["process"].lower():
                                self.filtered_items.append({
                                    "type": "window",
                                    "hwnd": win["hwnd"],
                                    "title": win["title"]
                                })
            elif remaining.lower() == "aaa" or remaining.lower().startswith("aaa "):
                filter_text = remaining[3:].strip()
                # Multi-select: list all windows NOT in this group
                self.multi_selected = set()
                for win in self.all_windows:
                    if not self.is_window_in_group(win, group_name):
                        if not filter_text or filter_text.lower() in win["title"].lower() or filter_text.lower() in win["process"].lower():
                            self.filtered_items.append({
                                "type": "window",
                                "hwnd": win["hwnd"],
                                "title": win["title"],
                                "add_to_group": group_name,
                                "aaa_mode": True,
                            })
            elif remaining.lower() == "aai" or remaining.lower().startswith("aai "):
                filter_text = remaining[3:].strip()
                # Exclusive add: list non-group windows; on activate remove from other groups too
                self.multi_selected = set()
                for win in self.all_windows:
                    if not self.is_window_in_group(win, group_name):
                        if not filter_text or filter_text.lower() in win["title"].lower() or filter_text.lower() in win["process"].lower():
                            self.filtered_items.append({
                                "type": "window",
                                "hwnd": win["hwnd"],
                                "title": win["title"],
                                "add_to_group": group_name,
                                "aai_mode": True,
                            })
            elif remaining.lower() == "kkk":
                cur_hwnd = self.prev_active_hwnd
                cur_title = self.prev_active_title or "Neznámé"
                is_anchored = cur_hwnd and cur_hwnd in self.anchored_hwnds
                label = "📌 [Odkotvit okno]" if is_anchored else "📌 [Ukotvit okno]"
                self.filtered_items.append({
                    "type": "anchor_window",
                    "group_ctx": group_name,
                    "global_anchor": False,
                    "title": f"{label} '{cur_title}' ve skupině {group_name}",
                })
            elif remaining.lower() == "rrr":
                self.filtered_items.append({
                    "type": "remove_current_window",
                    "group_name": group_name,
                    "title": f"➖ [Odebrat aktuální okno] -> '{self.prev_active_title if self.prev_active_title else 'Neznámé'}' ze skupiny {group_name}"
                })
            elif remaining.lower() == "ddd":
                if group_name != "_":
                    self.filtered_items.append({
                        "type": "delete_group",
                        "group_name": group_name,
                        "title": f"🗑️ [Smazat skupinu '{group_name}'] – Potvrďte Enterem"
                    })
                else:
                    self.filtered_items.append({
                        "type": "window",
                        "hwnd": 0,
                        "title": "⚠️ Výchozí skupinu '_' nelze smazat"
                    })
            elif remaining.lower().startswith("sv "):
                view_name = remaining[3:].strip()
                self.filtered_items.append({
                    "type": "save_view",
                    "group_name": group_name,
                    "view_name": view_name,
                    "title": f"💾 [Uložit rozložení] {group_name} -> {view_name}" if view_name else f"💾 Zadej název pohledu pro {group_name}"
                })
            elif remaining.lower().startswith("lv "):
                view_name = remaining[3:].strip()
                self.filtered_items.append({
                    "type": "load_view",
                    "group_name": group_name,
                    "view_name": view_name,
                    "title": f"📐 [Načíst rozložení] {group_name} -> {view_name}" if view_name else f"📐 Zadej název pohledu pro {group_name}"
                })
            elif remaining:
                for win in self.all_windows:
                    if remaining.lower() in win["title"].lower() or remaining.lower() in win["process"].lower():
                        self.filtered_items.append({
                            "type": "window",
                            "hwnd": win["hwnd"],
                            "title": win["title"],
                            "add_to_group": group_name
                        })
            else:
                for win in self.all_windows:
                    if self.is_window_in_group(win, group_name):
                        self.filtered_items.append({
                            "type": "window",
                            "hwnd": win["hwnd"],
                            "title": win["title"]
                        })

        elif search_text.lower().startswith("sv "):
            view_name = search_text[3:].strip()
            self.filtered_items.append({
                "type": "save_view",
                "group_name": "",
                "view_name": view_name,
                "title": f"💾 [Uložit celkové rozložení] -> {view_name}" if view_name else f"💾 Zadej název pohledu"
            })
        elif search_text.lower().startswith("lv "):
            view_name = search_text[3:].strip()
            self.filtered_items.append({
                "type": "load_view",
                "group_name": "",
                "view_name": view_name,
                "title": f"📐 [Načíst celkové rozložení] -> {view_name}" if view_name else f"📐 Zadej název pohledu"
            })
        elif search_text.lower() == "kkk":
            cur_hwnd = self.prev_active_hwnd
            cur_title = self.prev_active_title or "Neznámé"
            is_anchored = cur_hwnd and cur_hwnd in self.anchored_hwnds
            label = "📌 [Odkotvit okno]" if is_anchored else "📌 [Ukotvit okno]"
            self.filtered_items.append({
                "type": "anchor_window",
                "group_ctx": "",
                "global_anchor": False,
                "title": f"{label} '{cur_title}' (bez skupiny)",
            })
        elif search_text.lower() == "kka":
            cur_hwnd = self.prev_active_hwnd
            cur_title = self.prev_active_title or "Neznámé"
            is_anchored = cur_hwnd and cur_hwnd in self.anchored_hwnds
            label = "📌 [Odkotvit okno]" if is_anchored else "📌 [Ukotvit okno (globálně)]"
            self.filtered_items.append({
                "type": "anchor_window",
                "group_ctx": None,
                "global_anchor": True,
                "title": f"{label} '{cur_title}' (globálně)",
            })
        else:
            cleared_group = self.last_group
            self.last_group = ""

            matched_shortcut = None
            for s in self.shortcuts:
                if s["shortcut"].lower() == search_text.lower():
                    matched_shortcut = s
                    break

            if matched_shortcut:
                pattern = matched_shortcut["pattern"]
                command = matched_shortcut["command"]

                pattern_matches = []
                regex = None
                try:
                    regex = re.compile(pattern, re.IGNORECASE)
                except Exception:
                    pass

                for win in self.all_windows:
                    if regex and regex.search(win["title"]):
                        pattern_matches.append(win)

                if pattern_matches:
                    for win in pattern_matches:
                        self.filtered_items.append({
                            "type": "window",
                            "hwnd": win["hwnd"],
                            "title": f"⭐ [Aktivní okno] -> {win['title']}"
                        })
                else:
                    self.filtered_items.append({
                        "type": "command",
                        "command": command,
                        "title": f"🚀 [Spustit] -> {command}"
                    })
            else:
                windows_not_in_any_group = []
                windows_in_cleared_group = []
                windows_in_other_groups = []

                for win in self.all_windows:
                    if not search_text or search_text.lower() in win["title"].lower() or search_text.lower() in win["process"].lower():
                        item_obj = {
                            "type": "window",
                            "hwnd": win["hwnd"],
                            "title": win["title"]
                        }
                        if cleared_group and self.is_window_in_group(win, cleared_group):
                            windows_in_cleared_group.append(item_obj)
                        elif self.is_window_in_any_group(win):
                            windows_in_other_groups.append(item_obj)
                        else:
                            windows_not_in_any_group.append(item_obj)

                self.filtered_items = windows_not_in_any_group + windows_in_other_groups + windows_in_cleared_group
                        
        # Určení výchozího vybraného řádku na základě kontextu skupiny:
        # - Ve stejné skupině jako naposledy → kurzor na předchozí okno (index 1)
        # - Přechod do jiné skupiny → kurzor na nejnovější okno v ní (index 0)
        # - Při vyhledávání s filtrem vždy index 0
        current_group_ctx = ""
        if search_text:
            _t = search_text.split()
            if _t and (( _t[0].lower().startswith("gg") and len(_t[0]) > 2) or _t[0] == "_"):
                if not search_text[len(_t[0]):].strip():
                    current_group_ctx = _t[0].lower()

        is_pure_view = not search_text or current_group_ctx != ""

        if is_pure_view:
            if current_group_ctx == self.last_activated_group:
                # Stejná skupina jako naposledy → kurzor na předchozí okno
                self.selected_index = 1 if len(self.filtered_items) > 1 else 0
            else:
                # Přechod do jiné skupiny → kurzor na nejnovější okno
                self.selected_index = 0
        else:
            self.selected_index = 0
        self.render_rows()

    def render_rows(self):
        self.clear_all_row_thumbnails()
        for widget in self.scroll_rows_frame.winfo_children():
            widget.destroy()
            
        if not self.filtered_items:
            lbl = tk.Label(
                self.scroll_rows_frame,
                text="Žádná okna nenalezena",
                font=("Segoe UI", 11),
                bg=self.list_bg,
                fg=self.footer_color,
                pady=20
            )
            lbl.pack(fill=tk.X)
            self.clear_thumbnail()
            return
            
        for idx, item in enumerate(self.filtered_items):
            is_selected = (idx == self.selected_index)
            is_multi = (idx in self.multi_selected)
            if is_selected:
                bg = self.list_sel_bg
                fg = self.list_sel_fg
            elif is_multi:
                bg = self.multi_sel_bg
                fg = "#cce4ff"
            else:
                bg = self.list_bg
                fg = self.fg_color
            
            row_frame = tk.Frame(self.scroll_rows_frame, bg=bg, bd=0, padx=5, pady=4)
            row_frame.pack(fill=tk.X, expand=True)
            
            row_frame.bind("<Button-1>", lambda e, idx=idx: self._on_row_click(idx))
            
            if self.show_list_thumbnails and item["type"] == "window":
                # Create a mini dynamic live DWM Thumbnail container on the left, scaled dynamically via list_thumbnail_scale config (default 48x30, multiplied by list_thumbnail_scale)
                scale_val = getattr(self, "list_thumbnail_scale", 5.0)
                thumb_w = int(48 * scale_val)
                thumb_h = int(30 * scale_val)
                
                mini_canvas = tk.Canvas(
                    row_frame,
                    width=thumb_w,
                    height=thumb_h,
                    bg="#000000",
                    bd=1,
                    highlightthickness=1,
                    highlightbackground="#4e4e5a"
                )
                mini_canvas.pack(side=tk.LEFT, padx=(5, 10))
                mini_canvas.bind("<Button-1>", lambda e, idx=idx: self._on_row_click(idx))
                
                # Thumbnaily renderuj až 150ms po zastavení psaní (přeskočí zbytečné registrace DWM při psaní)
                self.root.after(150, lambda mc=mini_canvas, hwnd=item["hwnd"]: self.render_row_thumbnail(mc, hwnd))
            else:
                if item["type"] == "command":
                    icon_text = "🚀"
                elif item.get("aaa_mode") or item.get("aai_mode"):
                    icon_text = "+" if not is_multi else "✓"
                elif item["type"] == "anchor_window":
                    icon_text = "📌"
                else:
                    icon_text = "🪟"
                icon_lbl = tk.Label(
                    row_frame,
                    text=icon_text,
                    font=("Segoe UI", 11),
                    bg=bg,
                    fg=fg,
                    width=4
                )
                icon_lbl.pack(side=tk.LEFT, padx=(5, 10))
                icon_lbl.bind("<Button-1>", lambda e, idx=idx: self._on_row_click(idx))

            # Build display title (prepend 📌 for anchored windows in normal mode)
            display_title = item["title"]
            if item["type"] == "window" and item.get("hwnd") and item["hwnd"] in self.anchored_hwnds:
                if not item.get("aaa_mode") and not item.get("aai_mode"):
                    display_title = "📌 " + display_title
                
            title_lbl = tk.Label(
                row_frame,
                text=display_title,
                font=("Segoe UI", 11, "bold" if is_selected else "normal"),
                bg=bg,
                fg=fg,
                anchor="w",
                justify="left"
            )
            title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            title_lbl.bind("<Button-1>", lambda e, idx=idx: self._on_row_click(idx))
            
        self.render_side_preview()
        self.scroll_into_view()

    def select_row_by_index(self, idx):
        self.selected_index = idx
        self.render_rows()

    def _on_row_click(self, idx):
        """Jednoklik na řádek: vybere + aktivuje (v aaa/aai módu jen vybere)."""
        self.selected_index = idx
        self.render_rows()
        if self.filtered_items and idx < len(self.filtered_items):
            item = self.filtered_items[idx]
            if item.get("aaa_mode") or item.get("aai_mode"):
                return  # v módu přidávání klik jen pozicuje kurzor
        self.on_item_activated()

    def on_canvas_scroll(self, *args):
        self.list_scrollbar.set(*args)
        self.update_all_row_thumbnails()

    def update_all_row_thumbnails(self):
        try:
            if not self.list_canvas.winfo_exists():
                return
            canvas_limit_top = self.list_canvas.winfo_rooty() - self.root.winfo_rooty()
            canvas_limit_bottom = canvas_limit_top + self.list_canvas.winfo_height()
            
            for item in self.row_thumbnail_handles:
                try:
                    canvas = item["canvas"]
                    thumb_handle = item["handle"]
                    
                    if not canvas.winfo_exists():
                        continue
                        
                    canvas_x = canvas.winfo_rootx() - self.root.winfo_rootx()
                    canvas_y = canvas.winfo_rooty() - self.root.winfo_rooty()
                    
                    canvas_w = canvas.winfo_width()
                    canvas_h = canvas.winfo_height()
                    if canvas_w <= 1 or canvas_h <= 1:
                        scale_val = getattr(self, "list_thumbnail_scale", 5.0)
                        canvas_w = int(48 * scale_val)
                        canvas_h = int(30 * scale_val)
                        
                    thumb_top = canvas_y
                    thumb_bottom = canvas_y + canvas_h
                    
                    # Clip with viewport bounds to prevent drawing on the search field or footer
                    c_top = max(thumb_top, canvas_limit_top)
                    c_bottom = min(thumb_bottom, canvas_limit_bottom)
                    
                    is_visible = True
                    if c_top >= c_bottom or thumb_bottom <= canvas_limit_top or thumb_top >= canvas_limit_bottom:
                        is_visible = False
                        
                    props = DWM_THUMBNAIL_PROPERTIES()
                    props.dwFlags = DWM_TNP_RECTDESTINATION | DWM_TNP_VISIBLE | DWM_TNP_OPACITY | DWM_TNP_SOURCECLIENTAREAONLY
                    props.opacity = 255
                    props.fVisible = is_visible
                    props.fSourceClientAreaOnly = True
                    
                    props.rcDestination = RECT(
                        canvas_x,
                        c_top,
                        canvas_x + canvas_w,
                        c_bottom
                    )
                    DwmApi.DwmUpdateThumbnailProperties(thumb_handle, ctypes.byref(props))
                except Exception:
                    pass
        except Exception:
            pass

    def render_row_thumbnail(self, canvas, hwnd_target):
        try:
            if not canvas.winfo_exists():
                return
            self.root.update_idletasks()
            if not canvas.winfo_exists():
                return
            hwnd_tk = canvas.winfo_id()
            hwnd_host = User32.GetAncestor(hwnd_tk, 3)
            
            canvas_x = canvas.winfo_rootx() - self.root.winfo_rootx()
            canvas_y = canvas.winfo_rooty() - self.root.winfo_rooty()
            
            canvas_w = canvas.winfo_width()
            canvas_h = canvas.winfo_height()
            
            if canvas_w <= 1 or canvas_h <= 1:
                scale_val = getattr(self, "list_thumbnail_scale", 5.0)
                canvas_w = int(48 * scale_val)
                canvas_h = int(30 * scale_val)
                
            canvas_limit_top = self.list_canvas.winfo_rooty() - self.root.winfo_rooty()
            canvas_limit_bottom = canvas_limit_top + self.list_canvas.winfo_height()
            
            thumb_top = canvas_y
            thumb_bottom = canvas_y + canvas_h
            
            c_top = max(thumb_top, canvas_limit_top)
            c_bottom = min(thumb_bottom, canvas_limit_bottom)
            
            is_visible = True
            if c_top >= c_bottom or thumb_bottom <= canvas_limit_top or thumb_top >= canvas_limit_bottom:
                is_visible = False
                
            thumb_handle = ctypes.c_void_p()
            hr = DwmApi.DwmRegisterThumbnail(hwnd_host, hwnd_target, ctypes.byref(thumb_handle))
            
            if hr == 0 and thumb_handle:
                self.row_thumbnail_handles.append({
                    "handle": thumb_handle,
                    "canvas": canvas,
                    "hwnd": hwnd_target
                })
                
                props = DWM_THUMBNAIL_PROPERTIES()
                props.dwFlags = DWM_TNP_RECTDESTINATION | DWM_TNP_VISIBLE | DWM_TNP_OPACITY | DWM_TNP_SOURCECLIENTAREAONLY
                props.opacity = 255
                props.fVisible = is_visible
                props.fSourceClientAreaOnly = True
                
                props.rcDestination = RECT(
                    canvas_x,
                    c_top,
                    canvas_x + canvas_w,
                    c_bottom
                )
                
                DwmApi.DwmUpdateThumbnailProperties(thumb_handle, ctypes.byref(props))
            else:
                canvas.config(bg="#31313a")
        except Exception as e:
            print(f"Chyba vykreslení řádkového náhledu: {e}")

    def clear_all_row_thumbnails(self):
        for thumb in self.row_thumbnail_handles:
            try:
                DwmApi.DwmUnregisterThumbnail(thumb["handle"])
            except Exception:
                pass
        self.row_thumbnail_handles = []

    def clear_thumbnail(self):
        if self.current_thumbnail_handle is not None:
            try:
                DwmApi.DwmUnregisterThumbnail(self.current_thumbnail_handle)
            except Exception:
                pass
            self.current_thumbnail_handle = None
        self.preview_canvas.delete("all")

    def render_side_preview(self):
        if not self.show_thumbnails:
            self.clear_thumbnail()
            return
            
        if not self.filtered_items or self.selected_index >= len(self.filtered_items):
            self.clear_thumbnail()
            return
            
        item = self.filtered_items[self.selected_index]
        
        if item["type"] != "window":
            self.clear_thumbnail()
            self.preview_canvas.create_text(
                150, 150,
                text="🚀 Příkaz ke spuštění\n(Nemá náhled)",
                fill=self.footer_color,
                font=("Segoe UI", 11),
                justify="center"
            )
            return

        hwnd_target = item["hwnd"]
        hwnd_tk = self.root.winfo_id()
        hwnd_host = User32.GetAncestor(hwnd_tk, 3)
        
        self.clear_thumbnail()
        
        try:
            self.root.update_idletasks()
            
            canvas_x = self.preview_canvas.winfo_x()
            canvas_y = self.preview_canvas.winfo_y()
            canvas_w = self.preview_canvas.winfo_width()
            canvas_h = self.preview_canvas.winfo_height()
            
            parent = self.preview_canvas.winfo_parent()
            while parent and parent != ".":
                p_widget = self.root.nametowidget(parent)
                canvas_x += p_widget.winfo_x()
                canvas_y += p_widget.winfo_y()
                parent = p_widget.winfo_parent()
            
            if canvas_w <= 1 or canvas_h <= 1:
                canvas_w = 280
                canvas_h = 240
            
            thumb_handle = ctypes.c_void_p()
            hr = DwmApi.DwmRegisterThumbnail(hwnd_host, hwnd_target, ctypes.byref(thumb_handle))
            
            if hr == 0 and thumb_handle:
                self.current_thumbnail_handle = thumb_handle
                
                props = DWM_THUMBNAIL_PROPERTIES()
                props.dwFlags = DWM_TNP_RECTDESTINATION | DWM_TNP_VISIBLE | DWM_TNP_OPACITY | DWM_TNP_SOURCECLIENTAREAONLY
                props.opacity = 255
                props.fVisible = True
                props.fSourceClientAreaOnly = False
                
                margin = 8
                props.rcDestination = RECT(
                    canvas_x + margin,
                    canvas_y + margin,
                    canvas_x + canvas_w - margin,
                    canvas_y + canvas_h - margin
                )
                
                DwmApi.DwmUpdateThumbnailProperties(thumb_handle, ctypes.byref(props))
            else:
                self.preview_canvas.create_text(
                    150, 150,
                    text="❌ Náhled nedostupný",
                    fill=self.footer_color,
                    font=("Segoe UI", 11)
                )
        except Exception as e:
            print(f"Chyba vykreslení bočního náhledu: {e}")

    def scroll_into_view(self):
        self.root.update_idletasks()
        rows_widgets = self.scroll_rows_frame.winfo_children()
        if self.selected_index < len(rows_widgets):
            target_widget = rows_widgets[self.selected_index]
            
            canvas_h = self.list_canvas.winfo_height()
            if canvas_h <= 1:
                canvas_h = 260
                
            y_top = target_widget.winfo_y()
            y_bottom = y_top + target_widget.winfo_height()
            
            scroll_region_h = self.scroll_rows_frame.winfo_height()
            
            if scroll_region_h > canvas_h:
                current_scroll_start = self.list_canvas.yview()[0] * scroll_region_h
                current_scroll_end = self.list_canvas.yview()[1] * scroll_region_h
                
                if y_top < current_scroll_start:
                    self.list_canvas.yview_moveto(y_top / scroll_region_h)
                elif y_bottom > current_scroll_end:
                    self.list_canvas.yview_moveto((y_bottom - canvas_h) / scroll_region_h)

    def move_selection_down(self, event):
        if self.filtered_items:
            in_multi_mode = any(item.get("aaa_mode") or item.get("aai_mode") for item in self.filtered_items)
            if in_multi_mode and (event.state & 0x1):  # Shift held – toggle current
                self.multi_selected ^= {self.selected_index}
            elif not in_multi_mode:  # mimo multi-mód: reset výběru
                self.multi_selected.clear()
            # plain arrow v multi-módu (bez Shift): jen posun kurzoru, výběr se nemění
            self.selected_index = (self.selected_index + 1) % len(self.filtered_items)
            if in_multi_mode and (event.state & 0x1):  # Shift – toggle novou pozici
                self.multi_selected ^= {self.selected_index}
            self.render_rows()
        return "break"

    def move_selection_up(self, event):
        if self.filtered_items:
            in_multi_mode = any(item.get("aaa_mode") or item.get("aai_mode") for item in self.filtered_items)
            if in_multi_mode and (event.state & 0x1):  # Shift held – toggle current
                self.multi_selected ^= {self.selected_index}
            elif not in_multi_mode:  # mimo multi-mód: reset výběru
                self.multi_selected.clear()
            # plain arrow v multi-módu (bez Shift): jen posun kurzoru, výběr se nemění
            self.selected_index = (self.selected_index - 1) % len(self.filtered_items)
            if in_multi_mode and (event.state & 0x1):  # Shift – toggle novou pozici
                self.multi_selected ^= {self.selected_index}
            self.render_rows()
        return "break"

    def _on_entry_keypress(self, event):
        """Generický handler kláves na entry – chytá Insert přes keycode (VK_INSERT=45)."""
        # keycode 45 = VK_INSERT na Windows, funguje bez ohledu na keysym/rozložení klávesnice
        if event.keycode == 45 or event.keysym in ('Insert', 'KP_Insert'):
            return self.on_insert_toggle_select(event)
        # keycode 46 = VK_DELETE – zavřít / vyjmout okno ze skupiny
        if event.keycode == 46 or event.keysym == 'Delete':
            return self._on_delete_window(event)
        # Všechny ostatní klávesy: nevrací "break", normální zpracování pokračuje

    def on_insert_toggle_select(self, event=None):
        """Označí / odznačí aktuální položku v aaa/aai režimu a posune kurzor dolů."""
        if not self.filtered_items:
            return "break"
        in_multi_mode = any(item.get("aaa_mode") or item.get("aai_mode") for item in self.filtered_items)
        if in_multi_mode:
            self.multi_selected ^= {self.selected_index}
            self.selected_index = (self.selected_index + 1) % len(self.filtered_items)
            self.render_rows()
        return "break"

    def _on_delete_window(self, event=None):
        """Delete klávesa: zavře nebo vyjme okno ze skupiny podle kontextu."""
        if not self.filtered_items or self.selected_index >= len(self.filtered_items):
            return "break"
        item = self.filtered_items[self.selected_index]
        if item["type"] != "window" or not item.get("hwnd"):
            return "break"

        hwnd = item["hwnd"]
        win_title = item["title"]
        win_obj = next((w for w in self.all_windows if w["hwnd"] == hwnd), None)

        # Detect group context from entry text
        _cur_tokens = self.entry_var.get().strip().split()
        current_group = ""
        if _cur_tokens:
            first_token = _cur_tokens[0].lower()
            if (first_token.startswith("gg") and len(first_token) > 2) or first_token == "_":
                current_group = first_token

        # Check if the window is actually IN the current group
        in_group = False
        if current_group and current_group != "_" and win_obj:
            in_group = self.is_window_in_group(win_obj, current_group)

        WM_CLOSE = 0x0010
        if in_group:
            answer = self._ask_delete_in_group_dialog(win_title, current_group)
            if answer == "close":
                User32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
                self.root.after(400, self._refresh_after_window_change)
            elif answer == "remove":
                if win_obj:
                    self._remove_win_from_group(win_obj, current_group)
                self._refresh_after_window_change()
        else:
            if self._ask_close_window_dialog(win_title):
                User32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
                self.root.after(400, self._refresh_after_window_change)
        return "break"

    def _refresh_after_window_change(self):
        """Obnoví seznam oken a přefiltruje zobrazení."""
        self.all_windows = self.get_open_windows()
        self._refresh_window_group_titles()
        self._do_text_changed()

    def _ask_close_window_dialog(self, win_title):
        """Dialog: potvrdit zavření okna mimo skupinu. Vrací True/False."""
        result = [False]
        dlg = tk.Toplevel(self.root)
        dlg.title("Zavřít okno")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.attributes("-topmost", True)

        short_title = (win_title[:80] + "…") if len(win_title) > 80 else win_title
        tk.Label(dlg, text=f"Opravdu zavřít okno?\n\n{short_title}",
                 justify="left", padx=16, pady=12, wraplength=420).pack()

        btn_frame = tk.Frame(dlg, padx=12, pady=8)
        btn_frame.pack()

        def pick(val):
            result[0] = val
            dlg.destroy()

        btn_yes = tk.Button(btn_frame, text="Zavřít", width=14, command=lambda: pick(True))
        btn_no  = tk.Button(btn_frame, text="Zrušit", width=14, command=lambda: pick(False))
        btn_yes.grid(row=0, column=0, padx=4, pady=2)
        btn_no.grid (row=0, column=1, padx=4, pady=2)

        for btn, other in [(btn_yes, btn_no), (btn_no, btn_yes)]:
            btn.bind("<Left>",   lambda e, o=other: (o.focus_set(), "break")[1])
            btn.bind("<Right>",  lambda e, o=other: (o.focus_set(), "break")[1])
            btn.bind("<Return>", lambda e, b=btn: b.invoke())
            btn.bind("<space>",  lambda e, b=btn: b.invoke())

        dlg.update_idletasks()
        x = self.root.winfo_screenwidth() // 2 - dlg.winfo_width() // 2
        y = self.root.winfo_screenheight() // 2 - dlg.winfo_height() // 2
        dlg.geometry(f"+{x}+{y}")

        dlg.lift()
        dlg.focus_force()
        btn_yes.focus_set()

        dlg.wait_window()
        return result[0]

    def _ask_delete_in_group_dialog(self, win_title, group_name):
        """Dialog pro okno VE skupině: Zavřít / Vyjmout ze skupiny / Zrušit.
        Vrací: 'close' | 'remove' | 'cancel'
        """
        result = ["cancel"]
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Okno ve skupině '{group_name}'")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.attributes("-topmost", True)

        short_title = (win_title[:80] + "…") if len(win_title) > 80 else win_title
        tk.Label(dlg, text=short_title, justify="left", padx=16, pady=12, wraplength=420).pack()

        btn_frame = tk.Frame(dlg, padx=12, pady=8)
        btn_frame.pack()

        def pick(val):
            result[0] = val
            dlg.destroy()

        btn_close  = tk.Button(btn_frame, text="Zavřít okno",        width=22, command=lambda: pick("close"))
        btn_remove = tk.Button(btn_frame, text="Vyjmout ze skupiny", width=22, command=lambda: pick("remove"))
        btn_cancel = tk.Button(btn_frame, text="Zrušit",              width=22, command=lambda: pick("cancel"))
        btn_close.grid (row=0, column=0, padx=4, pady=2)
        btn_remove.grid(row=1, column=0, padx=4, pady=2)
        btn_cancel.grid(row=2, column=0, padx=4, pady=2)

        btns = [btn_close, btn_remove, btn_cancel]
        for i, btn in enumerate(btns):
            up_btn = btns[(i - 1) % len(btns)]
            dn_btn = btns[(i + 1) % len(btns)]
            btn.bind("<Up>",     lambda e, b=up_btn: (b.focus_set(), "break")[1])
            btn.bind("<Down>",   lambda e, b=dn_btn: (b.focus_set(), "break")[1])
            btn.bind("<Return>", lambda e, b=btn: b.invoke())
            btn.bind("<space>",  lambda e, b=btn: b.invoke())

        dlg.update_idletasks()
        x = self.root.winfo_screenwidth() // 2 - dlg.winfo_width() // 2
        y = self.root.winfo_screenheight() // 2 - dlg.winfo_height() // 2
        dlg.geometry(f"+{x}+{y}")

        dlg.lift()
        dlg.focus_force()
        btn_close.focus_set()

        dlg.wait_window()
        return result[0]

    def navigate_group_left(self, event):
        # Gather all groups, sort them alphabetically
        all_group_names = sorted(list(self.groups.keys()))
        current_val = self.entry_var.get().strip().split(maxsplit=1)
        current_g = ""
        if current_val:
            first_token = current_val[0].lower()
            if first_token == "_" or (first_token.startswith("gg") and len(first_token) > 2):
                current_g = first_token
        
        if not current_g:
            # We are currently in "all windows" (no group). Going left wraps to the last group.
            if all_group_names:
                new_g = all_group_names[-1]
            else:
                return "break"
        else:
            if current_g in all_group_names:
                idx = all_group_names.index(current_g)
                if idx == 0:
                    new_g = "" # Switch to "all windows"
                else:
                    new_g = all_group_names[idx - 1]
            else:
                new_g = ""
                
        # Preserving the search text after group name if any
        remaining = ""
        current_text = self.entry_var.get().strip()
        if current_g and current_text.lower().startswith(current_g):
            remaining = current_text[len(current_g):].strip()
            
        new_text = f"{new_g} {remaining.strip()}" if new_g else remaining
        self.entry_var.set(new_text)
        self.entry.icursor(tk.END)
        # Show navigation hint in status bar
        all_names = sorted(list(self.groups.keys()))
        if new_g:
            pos = all_names.index(new_g) + 1 if new_g in all_names else "?"
            self.status_label.config(text=f"← Skupina {pos}/{len(all_names)}: {new_g}  |  ← → pro přepínání skupin")
        else:
            self.status_label.config(text=f"← Všechna okna ({len(all_names)} skupin)  |  ← → pro přepínání skupin")
        return "break"

    def navigate_group_right(self, event):
        # Gather all groups, sort them alphabetically
        all_group_names = sorted(list(self.groups.keys()))
        current_val = self.entry_var.get().strip().split(maxsplit=1)
        current_g = ""
        if current_val:
            first_token = current_val[0].lower()
            if first_token == "_" or (first_token.startswith("gg") and len(first_token) > 2):
                current_g = first_token
        
        if not current_g:
            # We are currently in "all windows" (no group). Going right wraps to the first group.
            if all_group_names:
                new_g = all_group_names[0]
            else:
                return "break"
        else:
            if current_g in all_group_names:
                idx = all_group_names.index(current_g)
                if idx == len(all_group_names) - 1:
                    new_g = "" # Switch to "all windows"
                else:
                    new_g = all_group_names[idx + 1]
            else:
                new_g = ""
                
        # Preserving the search text after group name if any
        remaining = ""
        current_text = self.entry_var.get().strip()
        if current_g and current_text.lower().startswith(current_g):
            remaining = current_text[len(current_g):].strip()
            
        new_text = f"{new_g} {remaining.strip()}" if new_g else remaining
        self.entry_var.set(new_text)
        self.entry.icursor(tk.END)
        # Show navigation hint in status bar
        all_names = sorted(list(self.groups.keys()))
        if new_g:
            pos = all_names.index(new_g) + 1 if new_g in all_names else "?"
            self.status_label.config(text=f"Skupina {pos}/{len(all_names)}: {new_g} →  |  ← → pro přepínání skupin")
        else:
            self.status_label.config(text=f"Všechna okna ({len(all_names)} skupin) →  |  ← → pro přepínání skupin")
        return "break"

    def _ask_new_window_dialog(self, title, message):
        """Vlastní dialog s tlačítky: Zavřít okno / Ano / Vždy / Vždy do přepnutí / Ne - zůstat / Ne - opustit skupinu.
        Vrací: 'close' | 'yes' | 'always' | 'always_until_switch' | 'no' | 'no_leave'
        """
        result = ["no"]
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.attributes("-topmost", True)

        tk.Label(dlg, text=message, justify="left", padx=16, pady=12, wraplength=420).pack()

        btn_frame = tk.Frame(dlg, padx=12, pady=8)
        btn_frame.pack()

        def pick(val):
            result[0] = val
            dlg.destroy()

        # Layout:
        #   Row 0: [Zavřít okno] (colspan 2)  ← šipkou nahoru z Ano
        #   Row 1: [Ano] (colspan 2)
        #   Row 2: [Vždy] [Vždy do přepnutí]
        #   Row 3: [Ne - zůstat] [Ne - opustit skupinu]
        btn_zavrit = tk.Button(btn_frame, text="Zavřít okno",           width=18, command=lambda: pick("close"))
        btn_ano    = tk.Button(btn_frame, text="Ano",                    width=18, command=lambda: pick("yes"))
        btn_vzdy   = tk.Button(btn_frame, text="Vždy",                   width=18, command=lambda: pick("always"))
        btn_vpre   = tk.Button(btn_frame, text="Vždy do přepnutí",       width=18, command=lambda: pick("always_until_switch"))
        btn_nz     = tk.Button(btn_frame, text="Ne - zůstat",             width=18, command=lambda: pick("no"))
        btn_nl     = tk.Button(btn_frame, text="Ne - opustit skupinu",    width=18, command=lambda: pick("no_leave"))

        btn_zavrit.grid(row=0, column=0, columnspan=2, padx=4, pady=2)
        btn_ano.grid   (row=1, column=0, columnspan=2, padx=4, pady=2)
        btn_vzdy.grid  (row=2, column=0,               padx=4, pady=2)
        btn_vpre.grid  (row=2, column=1,               padx=4, pady=2)
        btn_nz.grid    (row=3, column=0,               padx=4, pady=2)
        btn_nl.grid    (row=3, column=1,               padx=4, pady=2)

        btns = [btn_zavrit, btn_ano, btn_vzdy, btn_vpre, btn_nz, btn_nl]
        positions = [(0, 0), (1, 0), (2, 0), (2, 1), (3, 0), (3, 1)]

        # Navigace šipkami mezi tlačítky
        nav = {
            (0, 0): {"Down": (1, 0)},
            (1, 0): {"Up": (0, 0), "Down": (2, 0)},
            (2, 0): {"Up": (1, 0), "Right": (2, 1), "Down": (3, 0)},
            (2, 1): {"Up": (1, 0), "Left":  (2, 0), "Down": (3, 1)},
            (3, 0): {"Up": (2, 0), "Right": (3, 1)},
            (3, 1): {"Up": (2, 1), "Left":  (3, 0)},
        }
        pos_map = {pos: btn for btn, pos in zip(btns, positions)}

        def bind_nav(btn, pos):
            def on_key(e, p=pos):
                target = nav.get(p, {}).get(e.keysym)
                if target:
                    pos_map[target].focus_set()
                return "break"
            btn.bind("<Left>",  on_key)
            btn.bind("<Right>", on_key)
            btn.bind("<Up>",    on_key)
            btn.bind("<Down>",  on_key)
            btn.bind("<Return>", lambda e: btn.invoke())
            btn.bind("<space>",  lambda e: btn.invoke())

        for btn, pos in zip(btns, positions):
            bind_nav(btn, pos)

        dlg.update_idletasks()
        x = self.root.winfo_screenwidth() // 2 - dlg.winfo_width() // 2
        y = self.root.winfo_screenheight() // 2 - dlg.winfo_height() // 2
        dlg.geometry(f"+{x}+{y}")

        # Vynutit focus na dialog přes WinAPI (funguje i když je jiné okno v popředí)
        hwnd_dlg = User32.GetAncestor(dlg.winfo_id(), 3)
        User32.ShowWindow(hwnd_dlg, SW_SHOW)
        User32.keybd_event(0x12, 0, 0, 0)   # ALT down – trik pro SetForegroundWindow
        User32.SetForegroundWindow(hwnd_dlg)
        User32.keybd_event(0x12, 0, 2, 0)   # ALT up
        dlg.lift()
        dlg.focus_force()
        btns[1].focus_set()  # Focus na Ano; šipkou nahoru → Zavřít okno

        dlg.wait_window()
        return result[0]

    def _watch_new_windows(self):
        """Periodicky hlídá nová okna na pozadí a ptá se uživatele (ask mode) nebo rovnou přidá (always)."""
        try:
            if self.new_window_action != "never" and self.last_activated_group and self.activated_windows_hwnds:
                current_windows = self.get_open_windows()
                current_hwnds = {w["hwnd"] for w in current_windows}
                new_hwnds = current_hwnds - self.activated_windows_hwnds - self.declined_new_windows
                for w in current_windows:
                    if w["hwnd"] in new_hwnds and not self.is_window_in_any_group(w):
                        title = w["title"]
                        # Regex výjimky z configu mají prioritu před new_window_action
                        if self.auto_close_windows and self.auto_close_windows.search(title):
                            WM_CLOSE = 0x0010
                            User32.PostMessageW(w["hwnd"], WM_CLOSE, 0, 0)
                            self.declined_new_windows.add(w["hwnd"])
                            continue
                        if self.new_window_auto_no_leave and self.new_window_auto_no_leave.search(title):
                            self._leave_active_group()
                            break
                        if self.new_window_auto_no and self.new_window_auto_no.search(title):
                            self.declined_new_windows.add(w["hwnd"])
                            continue
                        if self.new_window_auto_yes and self.new_window_auto_yes.search(title):
                            self._add_win_to_group(w, self.last_activated_group)
                            self.activated_windows_hwnds.add(w["hwnd"])
                            continue
                        if self.new_window_action in ("always", "always_until_switch"):
                            self._add_win_to_group(w, self.last_activated_group)
                            self.activated_windows_hwnds.add(w["hwnd"])
                        elif self.new_window_action == "leave":
                            self._leave_active_group()
                            break
                        else:  # ask
                            if w["hwnd"] in self._pending_ask_hwnds:
                                continue  # dialog pro toto okno je již otevřen
                            self._pending_ask_hwnds.add(w["hwnd"])
                            answer = self._ask_new_window_dialog(
                                "Nové okno",
                                f"Přidat do skupiny '{self.last_activated_group}'?\n\n{w['title']}",
                            )
                            self._pending_ask_hwnds.discard(w["hwnd"])
                            if answer == "yes":
                                self._add_win_to_group(w, self.last_activated_group)
                                self.activated_windows_hwnds.add(w["hwnd"])
                            elif answer == "always":
                                self.new_window_action = "always"
                                self._add_win_to_group(w, self.last_activated_group)
                                self.activated_windows_hwnds.add(w["hwnd"])
                            elif answer == "always_until_switch":
                                self.new_window_action = "always_until_switch"
                                self._add_win_to_group(w, self.last_activated_group)
                                self.activated_windows_hwnds.add(w["hwnd"])
                            elif answer == "close":
                                WM_CLOSE = 0x0010
                                User32.PostMessageW(w["hwnd"], WM_CLOSE, 0, 0)
                                self.declined_new_windows.add(w["hwnd"])
                            elif answer == "no_leave":  # opustit skupinu
                                self.declined_new_windows.add(w["hwnd"])
                                self._leave_active_group()
                                break
                            else:  # "no" – přeskoč toto okno, příště (jiné okno) se zeptá
                                self.declined_new_windows.add(w["hwnd"])
        finally:
            self._watch_timer_id = self.root.after(2000, self._watch_new_windows)

    def _window_title_base(self, hwnd):
        length = User32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buffer = ctypes.create_unicode_buffer(length + 1)
        User32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value
        marker = " [WinSwitcher: "
        if title.endswith("]") and marker in title:
            idx = title.rfind(marker)
            if idx != -1:
                return title[:idx]
        return title

    def _window_group_suffix(self, groups):
        if not groups:
            return ""
        return f" [WinSwitcher: {', '.join(groups)}]"

    def get_groups_for_window(self, win):
        groups = []
        for gname in self.groups:
            if gname == "_":
                continue
            if self.is_window_in_group(win, gname):
                groups.append(gname)
        return groups

    def _update_window_title_groups(self, win):
        title = self._window_title_base(win["hwnd"])
        groups = self.get_groups_for_window(win)
        suffix = self._window_group_suffix(groups)
        new_title = title + suffix
        if new_title != self._window_title_base(win["hwnd"]):
            User32.SetWindowTextW(win["hwnd"], new_title)
        win["title"] = title
        win["groups"] = groups

    def _refresh_window_group_titles(self):
        for win in self.all_windows:
            self._update_window_title_groups(win)

    def _add_win_to_group(self, win, gname):
        """Přidá okno do skupiny (ukládá do groups, runtime cache i groups.json)."""
        if gname not in self.groups:
            self.groups[gname] = []
        prop_id = win.get("win_switcher_id") or User32.GetPropW(win["hwnd"], "WinSwitcherID")
        if not prop_id:
            import random
            prop_id = random.randint(1000000, 99999999)
            User32.SetPropW(win["hwnd"], "WinSwitcherID", prop_id)
        else:
            prop_id = int(prop_id)
        # Aktualizuj cache v all_windows dict (aby is_window_in_group nepotřebovalo WinAPI)
        win["win_switcher_id"] = prop_id
        for existing in self.groups[gname]:
            if isinstance(existing, dict) and existing.get("id") == prop_id:
                return  # Duplicit
        self.groups[gname].append({
            "id": prop_id,
            "process": win.get("process", ""),
            "class": win.get("class", ""),
            "title": win.get("title", "")
        })
        if gname not in self.runtime_hwnd_to_groups:
            self.runtime_hwnd_to_groups[gname] = set()
        self.runtime_hwnd_to_groups[gname].add(win["hwnd"])
        self.save_groups()
        self._refresh_window_group_titles()

    def _minimize_non_group_windows(self, group_name):
        """Minimalizuje všechna okna, která nepatří do zadané skupiny."""
        SW_MINIMIZE = 6
        for win in self.all_windows:
            if not self.is_window_in_group(win, group_name):
                User32.ShowWindow(win["hwnd"], SW_MINIMIZE)

    def _remove_win_from_group(self, win, gname):
        """Odebere okno ze skupiny (groups dict + runtime cache)."""
        if gname not in self.groups:
            return
        prop_id = win.get("win_switcher_id") or User32.GetPropW(win["hwnd"], "WinSwitcherID")
        if prop_id:
            prop_id = int(prop_id)
        to_remove = []
        for entry in self.groups[gname]:
            if isinstance(entry, dict):
                if prop_id and entry.get("id") == prop_id:
                    to_remove.append(entry)
                elif entry.get("process") == win.get("process") and entry.get("class") == win.get("class"):
                    to_remove.append(entry)
            else:
                if entry == win.get("title"):
                    to_remove.append(entry)
        for e in to_remove:
            self.groups[gname].remove(e)
        if gname in self.runtime_hwnd_to_groups:
            self.runtime_hwnd_to_groups[gname].discard(win["hwnd"])
        if not self.groups[gname] and gname != "_":
            del self.groups[gname]
            self.runtime_hwnd_to_groups.pop(gname, None)
        self.save_groups()
        self._refresh_window_group_titles()

    # --------------- Window anchoring (kkk / kka) ---------------

    def _anchor_window(self, hwnd, group_ctx, global_anchor=False):
        """Ukotvit okno: nastaví HWND_TOPMOST a omezí work area monitorů."""
        if not hwnd:
            return
        User32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE_FLAG)
        # Persist anchor flag so startup cleanup can find stale topmost windows after crash/kill
        User32.SetPropW(hwnd, "WinSwitcherAnchored", ctypes.c_void_p(1))
        rect = RECT()
        User32.GetWindowRect(hwnd, ctypes.byref(rect))
        self.anchored_hwnds[hwnd] = {
            "group_ctx": group_ctx,
            "global_anchor": global_anchor,
            "rect": (rect.left, rect.top, rect.right, rect.bottom),
        }
        self._apply_anchor_workarea()
        self._ensure_anchor_hook_running()

    def _unanchor_window(self, hwnd):
        """Odkotvit okno: vrátí HWND_NOTOPMOST a obnoví work area."""
        if hwnd in self.anchored_hwnds:
            User32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE_FLAG)
            User32.RemovePropW(hwnd, "WinSwitcherAnchored")
            del self.anchored_hwnds[hwnd]
        self._apply_anchor_workarea()  # Recompute with remaining anchors (or full restore)

    def _apply_anchor_workarea(self):
        """Registruje AppBar okna pro každou ukotvenu stranu monitoru, aby
        maximalizovaná okna nepřekrývala kotvy. Používá SHAppBarMessage –
        stejný mechanismus jako taskbar, takže Explorer jej nepřepisuje."""
        self._remove_appbar_windows()
        if not self.anchored_hwnds:
            return

        MonitorEnumProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.POINTER(RECT), ctypes.c_void_p
        )
        monitor_rects = []
        def _mon_cb(hMon, hDC, lpRect, lParam):
            r = lpRect.contents
            monitor_rects.append((hMon, r.left, r.top, r.right, r.bottom))
            return True
        User32.EnumDisplayMonitors(None, None, MonitorEnumProc(_mon_cb), 0)

        for hMon, mx1, my1, mx2, my2 in monitor_rects:
            # For each edge, track the maximum intrusion of anchors on that edge.
            # edge_extent[ABE_LEFT]   = max x2 of anchors closest to left edge
            # edge_extent[ABE_RIGHT]  = min x1 of anchors closest to right edge
            # edge_extent[ABE_TOP]    = max y2 of anchors closest to top edge
            # edge_extent[ABE_BOTTOM] = min y1 of anchors closest to bottom edge
            edge_extent = {}

            for hwnd_a, anc_data in self.anchored_hwnds.items():
                ax1, ay1, ax2, ay2 = anc_data["rect"]
                if ax2 <= mx1 or ax1 >= mx2 or ay2 <= my1 or ay1 >= my2:
                    continue
                dist_left   = ax1 - mx1
                dist_right  = mx2 - ax2
                dist_top    = ay1 - my1
                dist_bottom = my2 - ay2
                min_dist = min(dist_left, dist_right, dist_top, dist_bottom)
                if min_dist == dist_left:
                    edge_extent[ABE_LEFT]   = max(edge_extent.get(ABE_LEFT,   ax2), ax2)
                elif min_dist == dist_right:
                    edge_extent[ABE_RIGHT]  = min(edge_extent.get(ABE_RIGHT,  ax1), ax1)
                elif min_dist == dist_top:
                    edge_extent[ABE_TOP]    = max(edge_extent.get(ABE_TOP,    ay2), ay2)
                else:
                    edge_extent[ABE_BOTTOM] = min(edge_extent.get(ABE_BOTTOM, ay1), ay1)

            for edge, extent in edge_extent.items():
                if edge == ABE_LEFT:
                    appbar_rect = (mx1, my1, extent, my2)
                elif edge == ABE_RIGHT:
                    appbar_rect = (extent, my1, mx2, my2)
                elif edge == ABE_TOP:
                    appbar_rect = (mx1, my1, mx2, extent)
                else:  # ABE_BOTTOM
                    appbar_rect = (mx1, extent, mx2, my2)
                key = f"{hMon}_{edge}"
                self._create_appbar_win(key, edge, appbar_rect)

        # AppBar registration broadcasts WM_SETTINGCHANGE asynchronously;
        # the anchored window processes it later and reflows.  Re-assert its
        # position at a few increasing delays to cover varying system speeds.
        self._reassert_anchor_positions()
        self.root.after(150, self._reassert_anchor_positions)
        self.root.after(400, self._reassert_anchor_positions)

    def _reassert_anchor_positions(self):
        """Vrátí každé ukotvené okno na uloženou pozici (po změně work area)."""
        WS_MAXIMIZE    = 0x01000000
        GWL_STYLE      = -16
        SWP_NOZORDER   = 0x0004
        SWP_NOACTIVATE = 0x0010
        for hwnd_a, anc_data in list(self.anchored_hwnds.items()):
            ax1, ay1, ax2, ay2 = anc_data["rect"]
            try:
                style = User32.GetWindowLongW(hwnd_a, GWL_STYLE)
                if style & WS_MAXIMIZE:
                    User32.SetWindowLongW(hwnd_a, GWL_STYLE, style & ~WS_MAXIMIZE)
                User32.SetWindowPos(hwnd_a, None, ax1, ay1,
                                    ax2 - ax1, ay2 - ay1,
                                    SWP_NOZORDER | SWP_NOACTIVATE)
            except Exception:
                pass

    def _create_appbar_win(self, key, edge, appbar_rect):
        """Vytvoří skryté pomocné okno a zaregistruje ho jako AppBar."""
        helper = tk.Toplevel(self.root)
        helper.overrideredirect(True)
        helper.geometry("1x1+-32000+-32000")   # mimo obrazovku
        helper.update_idletasks()
        ab_hwnd = int(helper.winfo_id())

        GWL_EXSTYLE      = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TRANSPARENT = 0x00000020
        old_ex = User32.GetWindowLongW(ab_hwnd, GWL_EXSTYLE)
        User32.SetWindowLongW(ab_hwnd, GWL_EXSTYLE,
            old_ex | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT)

        abd = APPBARDATA()
        abd.cbSize = ctypes.sizeof(APPBARDATA)
        abd.hWnd = ab_hwnd
        abd.uCallbackMessage = 0x8001   # WM_APP+1, callbacks ignorovány
        abd.uEdge = edge
        abd.rc.left   = appbar_rect[0]
        abd.rc.top    = appbar_rect[1]
        abd.rc.right  = appbar_rect[2]
        abd.rc.bottom = appbar_rect[3]
        abd.lParam = 0

        Shell32.SHAppBarMessage(ABM_NEW,      ctypes.byref(abd))
        Shell32.SHAppBarMessage(ABM_QUERYPOS, ctypes.byref(abd))
        Shell32.SHAppBarMessage(ABM_SETPOS,   ctypes.byref(abd))

        self._appbar_windows[key] = (helper, ab_hwnd)

    def _remove_appbar_windows(self):
        """Odregistruje a zničí všechna pomocná AppBar okna."""
        for key, (helper, ab_hwnd) in list(self._appbar_windows.items()):
            try:
                abd = APPBARDATA()
                abd.cbSize = ctypes.sizeof(APPBARDATA)
                abd.hWnd = ab_hwnd
                Shell32.SHAppBarMessage(ABM_REMOVE, ctypes.byref(abd))
                helper.destroy()
            except Exception:
                pass
        self._appbar_windows.clear()

    def _restore_all_workareas(self):
        """Obnoví pracovní plochu odregistrováním všech AppBar oken.
        Také odstraňuje TOPMOST ze všech dosud ukotvených oken."""
        for hwnd in list(self.anchored_hwnds.keys()):
            try:
                User32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE_FLAG)
                User32.RemovePropW(hwnd, "WinSwitcherAnchored")
            except Exception:
                pass
        self.anchored_hwnds.clear()
        self._remove_appbar_windows()

    def _ensure_anchor_hook_running(self):
        if self._anchor_hook_handle:
            return
        self._anchor_hook_thread = threading.Thread(target=self._run_anchor_hook, daemon=True)
        self._anchor_hook_thread.start()

    def _run_foreground_hook(self):
        """Vlákno s WinEvent hookem pro EVENT_SYSTEM_FOREGROUND.
        Pokud uživatel přepne na okno mimo aktivní skupinu (mimo switcher),
        automaticky odchází ze skupiny."""
        import ctypes.wintypes
        EVENT_SYSTEM_FOREGROUND = 0x0003
        my_pid = os.getpid()

        WinEventProcType = ctypes.WINFUNCTYPE(
            None,
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p,
            ctypes.c_long, ctypes.c_long, ctypes.c_ulong, ctypes.c_ulong,
        )

        def _cb(hHook, event, hwnd, idObject, idChild, dwThread, dwTime):
            if not hwnd:
                return
            if not self.last_activated_group:
                return
            # Ignoruj okna našeho vlastního procesu (switcher, dialogy, tray)
            pid = ctypes.c_ulong(0)
            User32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == my_pid:
                return
            # Plánuj kontrolu na hlavním vlákně (thread-safe přístup k tk a all_windows)
            self.root.after(0, lambda h=hwnd: self._check_fg_for_group_exit(h))

        proc = WinEventProcType(_cb)
        self._fg_proc_ref = proc
        hook = User32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND,
            None, proc, 0, 0, WINEVENT_OUTOFCONTEXT,
        )
        self._fg_hook_handle = hook

        msg = ctypes.wintypes.MSG()
        while True:
            ret = User32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == 0 or ret == -1:
                break
            User32.TranslateMessage(ctypes.byref(msg))
            User32.DispatchMessageW(ctypes.byref(msg))

        if hook:
            User32.UnhookWinEvent(hook)
        self._fg_hook_handle = None

    def _check_fg_for_group_exit(self, hwnd):
        """Spouští se na hlavním vlákně po změně foreground okna.
        Pokud okno není v aktivní skupině, vyjde ze skupiny."""
        if not self.last_activated_group:
            return
        # Pokud fokus mezitím přešel jinam, event byl přechodný – ignoruj ho.
        current_fg = User32.GetForegroundWindow()
        if current_fg != hwnd:
            return
        # Aplikuj stejný filtr jako get_open_windows: okna, která by se v switcheru
        # ani neobjevila (bez titulku, tool windows, owned dialogy, …), jsou systémové
        # overlaye (Alt+Tab, Task View, notifikace…) – nepoužíváme výpis tříd,
        # protože ten je verzově specifický.
        title_len = User32.GetWindowTextLengthW(hwnd)
        if title_len == 0:
            return  # žádný titulek = systémové/pozadí okno
        ex_style = User32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        hidden_by_switcher = bool(User32.GetPropW(hwnd, "WinSwitcherExStyle"))
        if (ex_style & WS_EX_TOOLWINDOW) and not hidden_by_switcher:
            return  # tool window (ne naše) = systémový overlay
        owner = User32.GetWindow(hwnd, GW_OWNER)
        if owner:
            return  # owned window = dialog nebo child
        # Hledáme okno v kešovaném seznamu
        win_obj = next((w for w in self.all_windows if w.get("hwnd") == hwnd), None)
        if win_obj is None:
            # Okno není v naší cache – bylo otevřeno po posledním refreshi switcheru.
            # Skupinu neopouštíme: _watch_new_windows se postará o ask/add logiku.
            # Spustíme check okamžitě místo čekání na příští polling interval.
            if self.last_activated_group:
                if self._watch_timer_id is not None:
                    try:
                        self.root.after_cancel(self._watch_timer_id)
                    except Exception:
                        pass
                    self._watch_timer_id = None
                self.root.after(150, self._watch_new_windows)
            return
        # Primární kontrola: runtime HWND cache (nejrychlejší a nejspolehlivější).
        # Brání falešnému odchodu ze skupiny u oken se změněným HWND (PL/SQL, atd.)
        if hwnd in self.runtime_hwnd_to_groups.get(self.last_activated_group, set()):
            return  # okno je ve skupině dle runtime cache – nijak nereagujeme
        # Sekundární kontrola přes is_window_in_group (může také update runtime cache)
        if not self.is_window_in_group(win_obj, self.last_activated_group):
            self._leave_active_group()

    def _leave_active_group(self):
        """Opustí aktivní skupinu: obnoví taskbar, tray a OSD."""
        self.last_activated_group = ""
        self.last_group = ""  # aby switcher příště otevřel na všech oknech
        self._restore_all_taskbar_icons()
        self.root.after(0, lambda: self._update_tray(""))
        self.root.after(0, lambda: self._update_osd(""))

    def _run_anchor_hook(self):
        """Vlákno s WinEvent hookem – přizpůsobuje okna přes kotvy."""
        import ctypes.wintypes

        WinEventProcType = ctypes.WINFUNCTYPE(
            None,
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p,
            ctypes.c_long, ctypes.c_long, ctypes.c_ulong, ctypes.c_ulong,
        )
        _in_callback = [False]

        def _cb(hHook, event, hwnd, idObject, idChild, dwThread, dwTime):
            if _in_callback[0] or not hwnd or idObject != 0:
                return
            if hwnd in self.anchored_hwnds:
                # Update stored rect of the anchor itself when it moves
                rect = RECT()
                if User32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    if hwnd in self.anchored_hwnds:
                        self.anchored_hwnds[hwnd]["rect"] = (rect.left, rect.top, rect.right, rect.bottom)
                return
            if not self.anchored_hwnds:
                return
            moved = RECT()
            if not User32.GetWindowRect(hwnd, ctypes.byref(moved)):
                return
            bx1, by1, bx2, by2 = moved.left, moved.top, moved.right, moved.bottom
            for anc_hwnd, anc_data in list(self.anchored_hwnds.items()):
                ax1, ay1, ax2, ay2 = anc_data["rect"]
                ox1 = max(ax1, bx1)
                oy1 = max(ay1, by1)
                ox2 = min(ax2, bx2)
                oy2 = min(ay2, by2)
                if ox1 >= ox2 or oy1 >= oy2:
                    continue  # No overlap
                ow, oh = ox2 - ox1, oy2 - oy1
                new_x, new_y, new_w, new_h = bx1, by1, bx2 - bx1, by2 - by1
                if ow >= oh:
                    # Clip horizontally
                    if bx1 < ax2 and bx2 > ax2:
                        # B overlaps from the left into A → push B right edge to ax1 or left edge to ax2
                        if bx1 < ax1:
                            new_w = ax1 - bx1  # Clip B's right side
                        else:
                            new_x = ax2       # Clip B's left side
                            new_w = bx2 - ax2
                    elif bx2 > ax1 and bx1 < ax1:
                        new_w = ax1 - bx1
                else:
                    # Clip vertically
                    if by1 < ay2 and by2 > ay2:
                        if by1 < ay1:
                            new_h = ay1 - by1
                        else:
                            new_y = ay2
                            new_h = by2 - ay2
                    elif by2 > ay1 and by1 < ay1:
                        new_h = ay1 - by1
                if new_w > 100 and new_h > 60 and (new_x != bx1 or new_y != by1 or new_w != bx2-bx1 or new_h != by2-by1):
                    _in_callback[0] = True
                    try:
                        User32.SetWindowPos(hwnd, None, new_x, new_y, new_w, new_h, SWP_NOZORDER_FLAG)
                    finally:
                        _in_callback[0] = False
                break  # Apply one anchor clip per event

        proc = WinEventProcType(_cb)
        self._anchor_proc_ref = proc
        hook = User32.SetWinEventHook(
            EVENT_SYSTEM_MOVESIZEEND, EVENT_SYSTEM_MOVESIZEEND,
            None, proc, 0, 0, WINEVENT_OUTOFCONTEXT,
        )
        self._anchor_hook_handle = hook

        msg = ctypes.wintypes.MSG()
        while True:
            ret = User32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == 0 or ret == -1:
                break
            User32.TranslateMessage(ctypes.byref(msg))
            User32.DispatchMessageW(ctypes.byref(msg))

        if hook:
            User32.UnhookWinEvent(hook)
        self._anchor_hook_handle = None

    def on_item_activated(self, event=None):
        if not self.filtered_items:
            return

        # Zachycení kontextu skupiny před schováním přepínače
        _cur_text = self.entry_var.get().strip()
        _cur_tokens = _cur_text.split()
        activated_group = ""
        if _cur_tokens:
            first_token = _cur_tokens[0].lower()
            if first_token.startswith("gg") and len(first_token) > 2:
                activated_group = first_token

        item = self.filtered_items[self.selected_index]
        self.hide_switcher()
        
        if item["type"] == "window":
            # --- aaa / aai multi-select handling ---
            if item.get("aaa_mode") or item.get("aai_mode"):
                gname = item.get("add_to_group", "")
                is_exclusive = bool(item.get("aai_mode"))
                # Determine which items to add:
                #   - označená okna (Insert) → aktivuje se první označené odshora
                #   - žádné označení → přidá a aktivuje okno pod kurzorem
                if self.multi_selected:
                    indices_to_add = set(self.multi_selected)
                    first_idx = min(self.multi_selected)
                else:
                    indices_to_add = {self.selected_index}
                    first_idx = self.selected_index
                self.multi_selected = set()
                for add_idx in indices_to_add:
                    if add_idx >= len(self.filtered_items):
                        continue
                    add_item = self.filtered_items[add_idx]
                    if add_item.get("hwnd"):
                        win_obj = next((w for w in self.all_windows if w["hwnd"] == add_item["hwnd"]), None)
                        if win_obj:
                            self._add_win_to_group(win_obj, gname)
                            if is_exclusive:
                                # Remove from all other groups
                                for other_g in list(self.groups.keys()):
                                    if other_g != gname and other_g != "_":
                                        self._remove_win_from_group(win_obj, other_g)
                # Aktivuj první označené okno (nebo okno pod kurzorem pokud bez výběru)
                activate_item = self.filtered_items[first_idx] if first_idx < len(self.filtered_items) else item
                hwnd = activate_item["hwnd"]
            else:
                # Add to group if specified (single window, normal mode)
                if "add_to_group" in item:
                    gname = item["add_to_group"]
                    if gname not in self.groups:
                        self.groups[gname] = []
                        
                    # To get info about item window
                    resolved_win = None
                    for w in self.all_windows:
                        if w["hwnd"] == item["hwnd"]:
                            resolved_win = w
                            break
                    if not resolved_win:
                        resolved_win = item
                    
                    # Retrieve or set a permanent random 32-bit WinSwitcherID
                    prop_id = User32.GetPropW(item["hwnd"], "WinSwitcherID")
                    if not prop_id:
                        import random
                        prop_id = random.randint(1000000, 99999999)
                        User32.SetPropW(item["hwnd"], "WinSwitcherID", prop_id)
                    else:
                        prop_id = int(prop_id)
                    
                    # Check for duplicates by WinSwitcherID (unique per window handle)
                    exists = False
                    for existing in self.groups[gname]:
                        if isinstance(existing, dict):
                            if existing.get("id") and prop_id and existing.get("id") == prop_id:
                                exists = True
                                break
                        else:
                            if existing == resolved_win.get("title"):
                                exists = True
                                break
                    
                    if not exists:
                        self.groups[gname].append({
                            "id": prop_id,
                            "process": resolved_win.get("process", ""),
                            "class": resolved_win.get("class", ""),
                            "title": resolved_win.get("title", "")
                        })
                        self.save_groups()
                        
                    # Register to runtime cache
                    if gname not in self.runtime_hwnd_to_groups:
                        self.runtime_hwnd_to_groups[gname] = set()
                    self.runtime_hwnd_to_groups[gname].add(item["hwnd"])
                hwnd = item["hwnd"]
                    
            if User32.IsIconic(hwnd):
                User32.ShowWindow(hwnd, SW_RESTORE)
            else:
                User32.ShowWindow(hwnd, SW_SHOW)

            # Pokud přepínáme do skupiny, minimalizujeme všechna okna mimo ni
            # V aaa/aai módu filtered_items obsahuje okna MIMO skupinu (kandidáti k přidání),
            # takže group_hwnds musíme vzít z runtime cache skupiny, ne z filtered_items.
            if item.get("aaa_mode") or item.get("aai_mode"):
                aaa_gname = item.get("add_to_group", "")
                group_hwnds = (
                    set(self.runtime_hwnd_to_groups.get(aaa_gname, set()))
                    if activated_group else None
                )
            else:
                group_hwnds = (
                    {it["hwnd"] for it in self.filtered_items if it.get("hwnd") and it["type"] == "window"}
                    if activated_group else None
                )

            if activated_group and group_hwnds is not None:
                for w in self.all_windows:
                    if w["hwnd"] != hwnd and w["hwnd"] not in group_hwnds:
                        User32.ShowWindow(w["hwnd"], 6)  # SW_MINIMIZE

            User32.SetForegroundWindow(hwnd)
            User32.BringWindowToTop(hwnd)
            if activated_group != self.last_activated_group and self.new_window_action == "always_until_switch":
                self.new_window_action = "ask"
            if activated_group != self.last_activated_group:
                self.declined_new_windows.clear()
            self.last_activated_group = activated_group
            self._update_taskbar_visibility(activated_group, explicit_hwnds=group_hwnds)
            self.activated_windows_hwnds = set(w["hwnd"] for w in self.all_windows)
            self.root.after(0, lambda g=activated_group: self._update_tray(g))
            self.root.after(0, lambda g=activated_group: self._update_osd(g))
            
        elif item["type"] == "save_view":
            if item.get("view_name"):
                saved = self.save_group_view(item["group_name"], item["view_name"])
                if not saved:
                    self.status_label.config(text=f"Žádná okna ve skupině {item['group_name']} k uložení")
                else:
                    self.status_label.config(text=f"Rozložení uloženo: {item['view_name']}")
            else:
                self.status_label.config(text=f"Zadej název pohledu pro {item['group_name']}")
        elif item["type"] == "load_view":
            if item.get("view_name"):
                loaded = self.load_group_view(item["group_name"], item["view_name"])
                if loaded:
                    self.status_label.config(text=f"Rozložení načteno: {item['view_name']}")
                else:
                    self.status_label.config(text=f"Nenalezeny okna pro načtení {item['view_name']}")
            else:
                self.status_label.config(text=f"Zadej název pohledu pro {item['group_name']}")
        elif item["type"] == "add_current_window":
            if self.prev_active_hwnd:
                gname = item["group_name"]
                if gname not in self.groups:
                    self.groups[gname] = []
                
                # Get details of prev window
                class_buf = ctypes.create_unicode_buffer(512)
                User32.GetClassNameW(self.prev_active_hwnd, class_buf, 512)
                class_name = class_buf.value
                
                pid = ctypes.c_ulong()
                User32.GetWindowThreadProcessId(self.prev_active_hwnd, ctypes.byref(pid))
                process_name = ""
                h_process = Kernel32.OpenProcess(0x1000, False, pid)
                if h_process:
                    path_buf = ctypes.create_unicode_buffer(1024)
                    p_size = ctypes.c_ulong(1024)
                    if Kernel32.QueryFullProcessImageNameW(h_process, 0, path_buf, ctypes.byref(p_size)):
                        process_name = os.path.basename(path_buf.value)
                    Kernel32.CloseHandle(h_process)
                
                # Retrieve or set a permanent random 32-bit WinSwitcherID
                prop_id = User32.GetPropW(self.prev_active_hwnd, "WinSwitcherID")
                if not prop_id:
                    import random
                    prop_id = random.randint(1000000, 99999999)
                    User32.SetPropW(self.prev_active_hwnd, "WinSwitcherID", prop_id)
                else:
                    prop_id = int(prop_id)
                
                exists = False
                for existing in self.groups[gname]:
                    if isinstance(existing, dict):
                        if existing.get("id") and prop_id and existing.get("id") == prop_id:
                            exists = True
                            break
                    else:
                        if existing == self.prev_active_title:
                            exists = True
                            break
                            
                if not exists:
                    self.groups[gname].append({
                        "id": prop_id,
                        "process": process_name,
                        "class": class_name,
                        "title": self.prev_active_title
                    })
                    self.save_groups()
                    self._refresh_window_group_titles()
                    
                # Cache HWND
                if gname not in self.runtime_hwnd_to_groups:
                    self.runtime_hwnd_to_groups[gname] = set()
                self.runtime_hwnd_to_groups[gname].add(self.prev_active_hwnd)
            
            if self.prev_active_hwnd:
                if User32.IsIconic(self.prev_active_hwnd):
                    User32.ShowWindow(self.prev_active_hwnd, SW_RESTORE)
                else:
                    User32.ShowWindow(self.prev_active_hwnd, SW_SHOW)
                User32.SetForegroundWindow(self.prev_active_hwnd)
                User32.BringWindowToTop(self.prev_active_hwnd)
                if activated_group != self.last_activated_group and self.new_window_action == "always_until_switch":
                    self.new_window_action = "ask"
                if activated_group != self.last_activated_group:
                    self.declined_new_windows.clear()
                self.last_activated_group = activated_group
                self._update_taskbar_visibility(activated_group)
                self.activated_windows_hwnds = set(w["hwnd"] for w in self.all_windows)
                self.root.after(0, lambda g=activated_group: self._update_tray(g))
                self.root.after(0, lambda g=activated_group: self._update_osd(g))
                
        elif item["type"] == "remove_current_window":
            if self.prev_active_hwnd:
                gname = item["group_name"]
                
                class_buf = ctypes.create_unicode_buffer(512)
                User32.GetClassNameW(self.prev_active_hwnd, class_buf, 512)
                class_name = class_buf.value
                
                pid = ctypes.c_ulong()
                User32.GetWindowThreadProcessId(self.prev_active_hwnd, ctypes.byref(pid))
                process_name = ""
                h_process = Kernel32.OpenProcess(0x1000, False, pid)
                if h_process:
                    path_buf = ctypes.create_unicode_buffer(1024)
                    p_size = ctypes.c_ulong(1024)
                    if Kernel32.QueryFullProcessImageNameW(h_process, 0, path_buf, ctypes.byref(p_size)):
                        process_name = os.path.basename(path_buf.value)
                    Kernel32.CloseHandle(h_process)
                
                if gname in self.groups:
                    to_remove = []
                    for existing in self.groups[gname]:
                        if isinstance(existing, dict):
                            if (existing.get("process") == process_name and 
                                existing.get("class") == class_name):
                                to_remove.append(existing)
                        else:
                            if existing == self.prev_active_title:
                                to_remove.append(existing)
                    for tr in to_remove:
                        self.groups[gname].remove(tr)
                        
                    if not self.groups[gname] and gname != "_":
                        del self.groups[gname]
                    self.save_groups()
                    self._refresh_window_group_titles()
                # Cache HWND remove
                if gname in self.runtime_hwnd_to_groups:
                    self.runtime_hwnd_to_groups[gname].discard(self.prev_active_hwnd)
            
            if self.prev_active_hwnd:
                if User32.IsIconic(self.prev_active_hwnd):
                    User32.ShowWindow(self.prev_active_hwnd, SW_RESTORE)
                else:
                    User32.ShowWindow(self.prev_active_hwnd, SW_SHOW)
                User32.SetForegroundWindow(self.prev_active_hwnd)
                User32.BringWindowToTop(self.prev_active_hwnd)
                if activated_group != self.last_activated_group and self.new_window_action == "always_until_switch":
                    self.new_window_action = "ask"
                if activated_group != self.last_activated_group:
                    self.declined_new_windows.clear()
                self.last_activated_group = activated_group
                self._update_taskbar_visibility(activated_group)
                self.activated_windows_hwnds = set(w["hwnd"] for w in self.all_windows)
                self.root.after(0, lambda g=activated_group: self._update_tray(g))
                self.root.after(0, lambda g=activated_group: self._update_osd(g))
            
        elif item["type"] == "command":
            cmd = item["command"]
            try:
                subprocess.Popen(cmd, shell=True, start_new_session=True)
            except Exception as e:
                messagebox.showerror("Chyba spuštění", f"Nepodařilo se spustit příkaz:\n{cmd}\n\nChyba: {e}")

        elif item["type"] == "delete_group":
            gname = item["group_name"]
            if gname in self.groups and gname != "_":
                # Najdi okna, která jsou POUZE v této skupině (ne v žádné jiné)
                only_in_group = []
                for w in self.all_windows:
                    if self.is_window_in_group(w, gname):
                        in_other = any(
                            g2 != gname and g2 != "_" and self.is_window_in_group(w, g2)
                            for g2 in self.groups
                        )
                        if not in_other:
                            only_in_group.append(w)

                close_them = False
                if only_in_group:
                    titles = "\n".join(f"  • {w['title'][:70]}" for w in only_in_group[:5])
                    if len(only_in_group) > 5:
                        titles += f"\n  … a {len(only_in_group) - 5} dalších"
                    close_them = messagebox.askyesno(
                        f"Smazat skupinu '{gname}'",
                        f"Tato okna nejsou v žádné jiné skupině:\n{titles}\n\nZavřít je?",
                        parent=self.root
                    )

                if close_them:
                    WM_CLOSE = 0x0010
                    for w in only_in_group:
                        User32.PostMessageW(w["hwnd"], WM_CLOSE, 0, 0)

                del self.groups[gname]
                self.runtime_hwnd_to_groups.pop(gname, None)
                self.views.pop(gname, None)
                if self.last_group == gname:
                    self.last_group = "_"
                if self.last_activated_group == gname:
                    self.last_activated_group = ""
                self.save_groups()
                self._refresh_window_group_titles()
                self.status_label.config(text=f"Skupina '{gname}' smazána.")

        elif item["type"] == "ask_add_to_group":
            gname = item["group_name"]
            for w in self.all_windows:
                if w["hwnd"] == item["hwnd"]:
                    self._add_win_to_group(w, gname)
                    break
            self.pending_new_windows = [w for w in self.pending_new_windows if w["hwnd"] != item["hwnd"]]
            hwnd = item["hwnd"]
            if hwnd:
                if User32.IsIconic(hwnd):
                    User32.ShowWindow(hwnd, SW_RESTORE)
                User32.SetForegroundWindow(hwnd)
                User32.BringWindowToTop(hwnd)

        elif item["type"] == "anchor_window":
            target_hwnd = self.prev_active_hwnd
            if not target_hwnd:
                return
            if target_hwnd in self.anchored_hwnds:
                self._unanchor_window(target_hwnd)
            else:
                self._anchor_window(target_hwnd, item.get("group_ctx"), item.get("global_anchor", False))

    def listen_global_hotkey(self):
        HOTKEY_ID = 2411
        mod = getattr(self, "hotkey_modifier", 0x0008)
        vk = getattr(self, "hotkey_vk", 0x09)
        
        success = User32.RegisterHotKey(None, HOTKEY_ID, mod, vk)
        
        if not success:
            last_error = ctypes.GetLastError()
            print(f"Zvolená zkratka je blokována nebo selhala (kód chyby {last_error}). Zkouším registraci Alt+Caps Lock...")
            success = User32.RegisterHotKey(None, HOTKEY_ID, 0x0001, 0x14) # Alt + Caps Lock
            
            if not success:
                last_error = ctypes.GetLastError()
                print(f"Alt+Caps Lock selhalo (kód chyby {last_error}). Zkouším registraci Alt+Ctrl+Mezerník...")
                success = User32.RegisterHotKey(None, HOTKEY_ID, 0x0001 | 0x0002, 0x20) # Alt + Ctrl + Space
                
                if not success:
                    last_error = ctypes.GetLastError()
                    print(f"Nepodařilo se zaregistrovat žádnou klávesovou zkratku (kód chyby {last_error}).")
                    return

        try:
            msg = ctypes.wintypes.MSG()
            while self.hotkey_running:
                if User32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                    if msg.message == WM_HOTKEY:
                        self.root.event_generate("<<ShowSwitcher>>", when="tail")
                    User32.TranslateMessage(ctypes.byref(msg))
                    User32.DispatchMessageW(ctypes.byref(msg))
        except Exception as e:
            print(f"Chyba v hotkey loopu: {e}")
        finally:
            User32.UnregisterHotKey(None, HOTKEY_ID)

    # --- ITaskbarList COM helpers ---

    def _init_taskbar_com(self):
        try:
            Ole32 = ctypes.windll.ole32
            Ole32.CoInitialize(None)
            Ole32.CoCreateInstance.restype = ctypes.HRESULT
            p = ctypes.c_void_p()
            hr = Ole32.CoCreateInstance(
                ctypes.byref(_CLSID_TaskbarList), None, 1,
                ctypes.byref(_IID_ITaskbarList), ctypes.byref(p)
            )
            if hr == 0 and p:
                vtbl_ptr = ctypes.cast(p, ctypes.POINTER(ctypes.c_void_p))
                vtbl = ctypes.cast(vtbl_ptr[0], ctypes.POINTER(ctypes.c_void_p))
                HrInit = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p)(vtbl[3])
                HrInit(p)
                self._taskbar_com_obj = p
                self._taskbar_vtable = vtbl
        except Exception as e:
            print(f"Taskbar COM init failed: {e}")
        # Always restore windows hidden by a previous session
        self._restore_stale_hidden_windows()
        # Remove TOPMOST from windows anchored by a previous session (crash/kill cleanup)
        self._restore_stale_anchored_windows()
        # Safety net for legacy sessions: when app starts outside any group,
        # ensure all normal windows have taskbar buttons visible.
        self._force_show_all_taskbar_tabs()

    def _taskbar_delete_tab(self, hwnd):
        try:
            # Remove from taskbar via COM
            if self.hide_taskbar_icons and self._taskbar_com_obj and self._taskbar_vtable:
                fn = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.c_void_p)(self._taskbar_vtable[5])
                fn(self._taskbar_com_obj, hwnd)
                User32.SetPropW(hwnd, "WinSwitcherTaskbarHidden", ctypes.c_void_p(1))
            # Hide from Alt+Tab via WS_EX_TOOLWINDOW
            if self.hide_alttab_icons:
                ex = User32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                self._taskbar_hidden_ex_styles[hwnd] = ex
                # Persist original ex_style as a window property so it survives app restart
                User32.SetPropW(hwnd, "WinSwitcherExStyle", ctypes.c_void_p(ex & 0xFFFFFFFF))
                User32.SetWindowLongW(hwnd, GWL_EXSTYLE, (ex | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW)
                # Notify shell about the style change (SWP_NOSIZE|NOMOVE|NOZORDER|NOACTIVATE|FRAMECHANGED)
                # Without this Teams, Outlook and similar apps ignore the WS_EX_TOOLWINDOW change
                User32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0037)
        except Exception:
            pass

    def _taskbar_add_tab(self, hwnd):
        try:
            # Restore original extended style (removes WS_EX_TOOLWINDOW)
            if self.hide_alttab_icons:
                if hwnd in self._taskbar_hidden_ex_styles:
                    User32.SetWindowLongW(hwnd, GWL_EXSTYLE, self._taskbar_hidden_ex_styles.pop(hwnd))
                else:
                    saved = User32.GetPropW(hwnd, "WinSwitcherExStyle")
                    if saved is not None:
                        User32.SetWindowLongW(hwnd, GWL_EXSTYLE, int(saved) & 0xFFFFFFFF)
                User32.RemovePropW(hwnd, "WinSwitcherExStyle")
                # Notify shell about ex_style change
                User32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0037)  # NOSIZE|NOMOVE|NOZORDER|NOACTIVATE|FRAMECHANGED
            # Add back to taskbar via COM
            if self._taskbar_com_obj and self._taskbar_vtable:
                fn = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.c_void_p)(self._taskbar_vtable[4])
                fn(self._taskbar_com_obj, hwnd)
            User32.RemovePropW(hwnd, "WinSwitcherTaskbarHidden")
        except Exception:
            pass

    def _restore_stale_hidden_windows(self):
        """On startup: restore windows hidden by a previous session via persisted window properties."""
        # Collect hwnds first (safe inside EnumWindows), then process outside
        hwnds_to_restore = []
        def enum_cb(hwnd, _):
            try:
                saved_ex = User32.GetPropW(hwnd, "WinSwitcherExStyle")
                saved_tab = User32.GetPropW(hwnd, "WinSwitcherTaskbarHidden")
                if saved_ex or saved_tab:
                    original_ex = (int(saved_ex) & 0xFFFFFFFF) if saved_ex else None
                    hwnds_to_restore.append((hwnd, original_ex, bool(saved_tab)))
            except Exception:
                pass
            return True
        try:
            User32.EnumWindows(WNDENUMPROC(enum_cb), None)
        except Exception:
            pass
        for hwnd, original_ex, had_taskbar_hidden in hwnds_to_restore:
            try:
                if original_ex is not None:
                    User32.SetWindowLongW(hwnd, GWL_EXSTYLE, original_ex)
                    # SWP_NOSIZE|SWP_NOMOVE|SWP_NOZORDER|SWP_NOACTIVATE|SWP_FRAMECHANGED = 0x0037
                    User32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0037)
                User32.RemovePropW(hwnd, "WinSwitcherExStyle")
                if had_taskbar_hidden and self._taskbar_com_obj and self._taskbar_vtable:
                    fn = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.c_void_p)(self._taskbar_vtable[4])
                    fn(self._taskbar_com_obj, hwnd)
                User32.RemovePropW(hwnd, "WinSwitcherTaskbarHidden")
            except Exception:
                pass

    def _force_show_all_taskbar_tabs(self):
        """Startup safety net: force AddTab on normal top-level windows."""
        if not (self._taskbar_com_obj and self._taskbar_vtable):
            return
        try:
            fn = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.c_void_p)(self._taskbar_vtable[4])
            for win in self.get_open_windows():
                hwnd = win.get("hwnd")
                if hwnd:
                    fn(self._taskbar_com_obj, hwnd)
        except Exception:
            pass

    def _restore_stale_anchored_windows(self):
        """Startup cleanup: odstraňuje TOPMOST z oken ukotvených předešlou sessioní
        (přežila restart/kill switcheru bez čistého ukončení)."""
        hwnds_to_fix = []
        def enum_cb(hwnd, _):
            try:
                if User32.GetPropW(hwnd, "WinSwitcherAnchored"):
                    hwnds_to_fix.append(hwnd)
            except Exception:
                pass
            return True
        try:
            User32.EnumWindows(WNDENUMPROC(enum_cb), None)
        except Exception:
            pass
        for hwnd in hwnds_to_fix:
            try:
                User32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE_FLAG)
                User32.RemovePropW(hwnd, "WinSwitcherAnchored")
            except Exception:
                pass

    def _update_taskbar_visibility(self, group_name, explicit_hwnds=None):
        """Show taskbar icons for windows in group_name, hide all others.
        explicit_hwnds: pokud je zadána, použije se tato přesná množina místo is_window_in_group.
        """
        if not (self.hide_taskbar_icons or self.hide_alttab_icons):
            return
        show_all = not group_name or group_name == "_"
        if show_all:
            self._restore_all_taskbar_icons()
            return
        for win in self.all_windows:
            hwnd = win.get("hwnd")
            if not hwnd:
                continue
            in_group = (hwnd in explicit_hwnds) if explicit_hwnds is not None else self.is_window_in_group(win, group_name)
            if in_group:
                if hwnd in self._taskbar_hidden_hwnds:
                    self._taskbar_add_tab(hwnd)
                    self._taskbar_hidden_hwnds.discard(hwnd)
            else:
                if hwnd not in self._taskbar_hidden_hwnds:
                    self._taskbar_delete_tab(hwnd)
                    self._taskbar_hidden_hwnds.add(hwnd)

    def _restore_all_taskbar_icons(self):
        for hwnd in list(self._taskbar_hidden_hwnds):
            self._taskbar_add_tab(hwnd)
        self._taskbar_hidden_hwnds.clear()

    def quit_app(self):
        self.hotkey_running = False
        self.clear_all_row_thumbnails()
        self.clear_thumbnail()
        self._restore_all_taskbar_icons()
        self._restore_all_workareas()
        if self.tray_icon:
            self.tray_icon.stop()
        User32.PostQuitMessage(0)
        self.root.destroy()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quick Window Switcher")
    parser.add_argument(
        "--keep-groups",
        action="store_true",
        help="Nezmazat skupiny při startu (zachovat skupiny z předchozí session)"
    )
    args = parser.parse_args()

    root = tk.Tk()
    app = WindowSwitcherApp(root, keep_groups=args.keep_groups)
    root.mainloop()
