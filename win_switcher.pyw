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

Kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
Kernel32.OpenProcess.restype = ctypes.c_void_p
Kernel32.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
Kernel32.QueryFullProcessImageNameW.restype = ctypes.c_bool
Kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
Kernel32.CloseHandle.restype = ctypes.c_bool

# Rect structure for DWM
class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
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

# Configure DWM argument signatures
DwmApi.DwmRegisterThumbnail.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
DwmApi.DwmUpdateThumbnailProperties.argtypes = [ctypes.c_void_p, ctypes.POINTER(DWM_THUMBNAIL_PROPERTIES)]
DwmApi.DwmUnregisterThumbnail.argtypes = [ctypes.c_void_p]

GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
GW_OWNER = 4
SW_RESTORE = 9
SW_SHOW = 5
WM_HOTKEY = 0x0312

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
        self.last_group = ""
        self.last_activated_group = ""
        self.prev_active_hwnd = None
        self.prev_active_title = ""
        self.load_groups()
        # Promazání skupin při každém startu – řízeno přepínačem --keep-groups
        if not keep_groups:
            self.groups = {}
            self.save_groups()
        
        # Load config
        self.load_config()
        
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

        # OSD overlay - trvalé zobrazení názvu skupiny na všech monitorech
        self.osd_windows = []  # seznam OSD oken pro každý monitor
        self._setup_osd()

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

    def _update_osd(self, group_name):
        label = group_name if group_name else ""
        if label:
            for osd_entry in self.osd_windows:
                self._osd_reposition_one(osd_entry, label)
                osd_entry["win"].deiconify()
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
                            if "win" in mod:
                                self.hotkey_modifier = 0x0008
                            elif "alt" in mod:
                                self.hotkey_modifier = 0x0001
                            elif "ctrl" in mod or "control" in mod:
                                self.hotkey_modifier = 0x0002
                            elif "shift" in mod:
                                self.hotkey_modifier = 0x0004
                            continue

                        if line.startswith("hotkey_key "):
                            kv = line.split(None, 1)[1].lower()
                            if kv == "tab":
                                self.hotkey_vk = 0x09
                            elif kv == "caps" or kv == "capslock" or kv == "caps_lock":
                                self.hotkey_vk = 0x14
                            elif kv == "space":
                                self.hotkey_vk = 0x20
                            else:
                                try:
                                    self.hotkey_vk = int(kv, 16)
                                except Exception:
                                    self.hotkey_vk = 0x09 # Fallback tab
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
                    self.groups = json.load(f)
            except Exception as e:
                print(f"Chyba při načítání skupin: {e}")
                try:
                    shutil.copy2(self.groups_file, self.groups_file + ".bak")
                    print("Záloha poškozených skupin vytvořena.")
                except Exception:
                    pass
                self.groups = {}
        else:
            self.groups = {}

    def save_groups(self):
        try:
            tmp_file = self.groups_file + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self.groups, f, ensure_ascii=False, indent=4)
            os.replace(tmp_file, self.groups_file)
        except Exception as e:
            print(f"Chyba při ukládání skupin: {e}")

    def is_window_in_group(self, win, group_name):
        # 1. Check exact WinSwitcherID window property set directly on the OS window (absolute precision!)
        os_prop_id = User32.GetPropW(win["hwnd"], "WinSwitcherID")
        
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
                    
                is_web_browser = any(b in (st_proc or "").lower() for b in ["chrome", "opera", "msedge", "firefox", "brave", "vivaldi", "iexplore"])
                win_title = win["title"]
                
                if is_web_browser:
                    # Web browsers get flexible matching across title changes
                    if st_class and st_proc and win["class"] == st_class and win["process"] == st_proc:
                        if st_id:
                            # Re-tag the window property so it is uniquely tracked henceforce
                            User32.SetPropW(win["hwnd"], "WinSwitcherID", int(st_id))
                        if group_name not in self.runtime_hwnd_to_groups:
                            self.runtime_hwnd_to_groups[group_name] = set()
                        self.runtime_hwnd_to_groups[group_name].add(win["hwnd"])
                        return True
                else:
                    # Precise title match for multiple-window apps (like Total Commander)
                    if st_title and (st_title == win_title or st_title in win_title or win_title in st_title):
                        if st_id:
                            User32.SetPropW(win["hwnd"], "WinSwitcherID", int(st_id))
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
                        
                    ex_style = User32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    if not (ex_style & WS_EX_TOOLWINDOW):
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
                                
                            windows.append({
                                "hwnd": hwnd, 
                                "title": title,
                                "class": class_name,
                                "process": process_name
                            })
            return True
            
        User32.EnumWindows(WNDENUMPROC(callback), 0)
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
        self.entry_var.set(self.last_group)
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

    def hide_switcher_on_focus_loss(self):
        self.root.after(100, self._check_focus_and_hide)

    def _check_focus_and_hide(self):
        focused_widget = self.root.focus_get()
        if focused_widget is None:
            self.hide_switcher()

    def on_text_changed(self):
        self.clear_all_row_thumbnails()
        search_text = self.entry_var.get().strip()
        
        for r_widget in self.scroll_rows_frame.winfo_children():
            r_widget.destroy()
            
        self.filtered_items = []
        
        # Check if the search text starts with a group pattern "gg..."
        first_token = ""
        tokens = search_text.split()
        if tokens:
            first_token = tokens[0]
            
        if first_token.lower().startswith("gg") and len(first_token) > 2:
            group_name = first_token.lower()
            remaining = search_text[len(first_token):].strip()
            self.last_group = group_name  # Keep the group prefilled
            
            if remaining.lower() == "aaa":
                self.filtered_items.append({
                    "type": "add_current_window",
                    "group_name": group_name,
                    "title": f"➕ [Přidat aktuální okno] -> '{self.prev_active_title if self.prev_active_title else 'Neznámé'}' do skupiny {group_name}"
                })
            elif remaining.lower() == "rrr":
                self.filtered_items.append({
                    "type": "remove_current_window",
                    "group_name": group_name,
                    "title": f"➖ [Odebrat aktuální okno] -> '{self.prev_active_title if self.prev_active_title else 'Neznámé'}' ze skupiny {group_name}"
                })
            elif remaining:
                # gga aa mode -> offer all windows filtered by remaining, with action to add to group_name
                for win in self.all_windows:
                    if remaining.lower() in win["title"].lower():
                        self.filtered_items.append({
                            "type": "window",
                            "hwnd": win["hwnd"],
                            "title": win["title"],
                            "add_to_group": group_name
                        })
            else:
                # gga mode -> offer ONLY windows currently in group_name
                for win in self.all_windows:
                    if self.is_window_in_group(win, group_name):
                        self.filtered_items.append({
                            "type": "window",
                            "hwnd": win["hwnd"],
                            "title": win["title"]
                        })
        else:
            # If the user has erased or typed something else, reset the prefilled group
            # Also, if we had a prefilled group but just cleared it, prioritize ordering
            # so that windows NOT in that cleared group appear first.
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
                # Sort order:
                # if a group was cleared (or generally on empty search), windows NOT belonging to ANY group are prioritized at the top of the list.
                # then windows in the cleared group are put at the very end.
                # other windows in groups are in between.
                windows_not_in_any_group = []
                windows_in_cleared_group = []
                windows_in_other_groups = []
                
                for win in self.all_windows:
                    if not search_text or search_text.lower() in win["title"].lower():
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
            if _t and _t[0].lower().startswith("gg") and len(_t[0]) > 2:
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
            bg = self.list_sel_bg if is_selected else self.list_bg
            fg = self.list_sel_fg if is_selected else self.fg_color
            
            row_frame = tk.Frame(self.scroll_rows_frame, bg=bg, bd=0, padx=5, pady=4)
            row_frame.pack(fill=tk.X, expand=True)
            
            row_frame.bind("<Button-1>", lambda e, idx=idx: self.select_row_by_index(idx))
            row_frame.bind("<Double-Button-1>", lambda e: self.on_item_activated())
            
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
                mini_canvas.bind("<Button-1>", lambda e, idx=idx: self.select_row_by_index(idx))
                mini_canvas.bind("<Double-Button-1>", lambda e: self.on_item_activated())
                
                # Setup render delayed slightly so geometry configuration initializes correctly
                self.root.after(10, lambda mc=mini_canvas, hwnd=item["hwnd"]: self.render_row_thumbnail(mc, hwnd))
            else:
                icon_lbl = tk.Label(
                    row_frame,
                    text="🚀" if item["type"] == "command" else "🪟",
                    font=("Segoe UI", 11),
                    bg=bg,
                    fg=fg,
                    width=4
                )
                icon_lbl.pack(side=tk.LEFT, padx=(5, 10))
                icon_lbl.bind("<Button-1>", lambda e, idx=idx: self.select_row_by_index(idx))
                
            title_lbl = tk.Label(
                row_frame,
                text=item["title"],
                font=("Segoe UI", 11, "bold" if is_selected else "normal"),
                bg=bg,
                fg=fg,
                anchor="w",
                justify="left"
            )
            title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            title_lbl.bind("<Button-1>", lambda e, idx=idx: self.select_row_by_index(idx))
            title_lbl.bind("<Double-Button-1>", lambda e: self.on_item_activated())
            
        self.render_side_preview()
        self.scroll_into_view()

    def select_row_by_index(self, idx):
        self.selected_index = idx
        self.render_rows()

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
            self.selected_index = (self.selected_index + 1) % len(self.filtered_items)
            self.render_rows()
        return "break"

    def move_selection_up(self, event):
        if self.filtered_items:
            self.selected_index = (self.selected_index - 1) % len(self.filtered_items)
            self.render_rows()
        return "break"

    def navigate_group_left(self, event):
        # Gather all groups, sort them alphabetically
        all_group_names = sorted(list(self.groups.keys()))
        current_val = self.entry_var.get().strip().split(maxsplit=1)
        current_g = current_val[0].lower() if current_val and current_val[0].lower().startswith("gg") else ""
        
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
            
        new_text = f"{new_g} {remaining}".strip() if new_g else remaining
        self.entry_var.set(new_text)
        self.entry.icursor(tk.END)
        return "break"

    def navigate_group_right(self, event):
        # Gather all groups, sort them alphabetically
        all_group_names = sorted(list(self.groups.keys()))
        current_val = self.entry_var.get().strip().split(maxsplit=1)
        current_g = current_val[0].lower() if current_val and current_val[0].lower().startswith("gg") else ""
        
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
            
        new_text = f"{new_g} {remaining}".strip() if new_g else remaining
        self.entry_var.set(new_text)
        self.entry.icursor(tk.END)
        return "break"

    def _minimize_non_group_windows(self, group_name):
        """Minimalizuje všechna okna, která nepatří do zadané skupiny."""
        SW_MINIMIZE = 6
        for win in self.all_windows:
            if not self.is_window_in_group(win, group_name):
                User32.ShowWindow(win["hwnd"], SW_MINIMIZE)

    def on_item_activated(self, event=None):
        if not self.filtered_items:
            return

        # Zachycení kontextu skupiny před schováním přepínače
        _cur_text = self.entry_var.get().strip()
        _cur_tokens = _cur_text.split()
        activated_group = (
            _cur_tokens[0].lower()
            if _cur_tokens and _cur_tokens[0].lower().startswith("gg") and len(_cur_tokens[0]) > 2
            else ""
        )

        item = self.filtered_items[self.selected_index]
        self.hide_switcher()
        
        if item["type"] == "window":
            # Add to group if specified
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
            if activated_group:
                for w in self.all_windows:
                    if w["hwnd"] != hwnd and not self.is_window_in_group(w, activated_group):
                        User32.ShowWindow(w["hwnd"], 6)  # SW_MINIMIZE

            User32.SetForegroundWindow(hwnd)
            User32.BringWindowToTop(hwnd)
            self.last_activated_group = activated_group
            self.root.after(0, lambda g=activated_group: self._update_tray(g))
            self.root.after(0, lambda g=activated_group: self._update_osd(g))
            
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
                self.last_activated_group = activated_group
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
                        
                    if not self.groups[gname]:
                        del self.groups[gname]
                    self.save_groups()
                    
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
                self.last_activated_group = activated_group
                self.root.after(0, lambda g=activated_group: self._update_tray(g))
                self.root.after(0, lambda g=activated_group: self._update_osd(g))
            
        elif item["type"] == "command":
            cmd = item["command"]
            try:
                subprocess.Popen(cmd, shell=True, start_new_session=True)
            except Exception as e:
                messagebox.showerror("Chyba spuštění", f"Nepodařilo se spustit příkaz:\n{cmd}\n\nChyba: {e}")

    def listen_global_hotkey(self):
        HOTKEY_ID = 2411
        mod = getattr(self, "hotkey_modifier", 0x0008)
        vk = getattr(self, "hotkey_vk", 0x09)
        
        success = User32.RegisterHotKey(None, HOTKEY_ID, mod, vk)
        
        if not success:
            # Win+Tab is standard system shortcut and Windows prevents registering it. Let's fallback to Alt+Caps Lock or Alt+Space cleanly
            print("Zvolená zkratka je blokována systémem. Zkouším registraci Alt+Caps Lock...")
            success = User32.RegisterHotKey(None, HOTKEY_ID, 0x0001, 0x14) # Alt + Caps Lock
            
            if not success:
                print("Zkouším registraci Alt+Ctrl+Mezerník...")
                success = User32.RegisterHotKey(None, HOTKEY_ID, 0x0001 | 0x0002, 0x20) # Alt + Ctrl + Space
                
                if not success:
                    print("Nepodařilo se zaregistrovat klávesovou zkratku.")
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

    def quit_app(self):
        self.hotkey_running = False
        self.clear_all_row_thumbnails()
        self.clear_thumbnail()
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
