"""Diagnostika oken pro ladění zobrazení Ditto nad ukotvenými okny.

Použití:
    1) Otevři v Dittu okno pro výběr vkládané položky (necháš ho otevřené).
    2) Spusť tento skript:  python ditto_probe.py
    3) Výstup (zvlášť řádky obsahující "ditto") pošli zpět.

Skript nic nemění – jen vypíše viditelná top-level okna: HWND, TOPMOST příznak,
třídu okna, název procesu a titulek. Podle toho ověříme, na co má cílit
anchor_overlay_classes / anchor_overlay_processes v config.txt.
"""
import ctypes
import os
import sys

# Konzole bývá cp1250 – ať nepadáme na exotických znacích v titulcích.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

User32 = ctypes.windll.user32
Kernel32 = ctypes.windll.kernel32

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
User32.EnumWindows.argtypes = [WNDENUMPROC, ctypes.c_void_p]
User32.IsWindowVisible.argtypes = [ctypes.c_void_p]
User32.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
User32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
User32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
User32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
User32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
Kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
Kernel32.OpenProcess.restype = ctypes.c_void_p
Kernel32.QueryFullProcessImageNameW.argtypes = [
    ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
Kernel32.QueryFullProcessImageNameW.restype = ctypes.c_bool
Kernel32.CloseHandle.argtypes = [ctypes.c_void_p]

GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008


def proc_name(hwnd):
    pid = ctypes.c_ulong(0)
    User32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = Kernel32.OpenProcess(0x1000, False, pid.value)  # QUERY_LIMITED_INFORMATION
    if not h:
        return "?"
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = ctypes.c_ulong(1024)
        if Kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value)
    finally:
        Kernel32.CloseHandle(h)
    return "?"


def class_name(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    User32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def title(hwnd):
    n = User32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    User32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


rows = []


def _cb(hwnd, lparam):
    if not User32.IsWindowVisible(hwnd):
        return True
    topmost = bool(User32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOPMOST)
    rows.append((hwnd, topmost, class_name(hwnd), proc_name(hwnd), title(hwnd)))
    return True


User32.EnumWindows(WNDENUMPROC(_cb), 0)

print(f"{'HWND':>10}  {'TOP':>3}  {'CLASS':<24}  {'PROCESS':<18}  TITLE")
print("-" * 100)
for hwnd, topmost, cls, proc, ttl in rows:
    mark = "  *" if "ditto" in (cls + proc + ttl).lower() else "   "
    print(f"{hwnd:>10}  {'yes' if topmost else 'no':>3}  {cls:<24}  {proc:<18}  {ttl}{mark}")
print("\nŘádky označené * pravděpodobně patří Dittu – pošli je zpět.")
