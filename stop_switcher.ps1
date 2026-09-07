# Ukončí běžící přepínač oken (jen procesy python s win_switcher.pyw v příkazové řádce).
# Nejdřív pošle hlavnímu oknu WM_CLOSE, aby přepínač skončil čistě (odregistruje pruhy
# kotev, zruší TOPMOST ukotvených oken, obnoví ikony na hlavním panelu, sundá tray ikonu).
# Pokud proces do 5 s neskončí, ukončí ho natvrdo. Volá se ze stop_switcher.bat.

Add-Type -Namespace WS -Name Win -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
public delegate bool EnumProc(IntPtr h, IntPtr l);
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);
'@

$procs = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python' -and $_.CommandLine -match 'win_switcher\.pyw'
})
if ($procs.Count -eq 0) {
    Write-Host 'Prepinac nebezi.'
    exit 0
}
$ids = @($procs | ForEach-Object { [uint32]$_.ProcessId })

$WM_CLOSE = 0x10
$cb = [WS.Win+EnumProc] {
    param($h, $l)
    $owner = [uint32]0
    [void][WS.Win]::GetWindowThreadProcessId($h, [ref]$owner)
    if ($ids -contains $owner) {
        $sb = New-Object System.Text.StringBuilder 256
        [void][WS.Win]::GetWindowText($h, $sb, 256)
        if ($sb.ToString() -eq 'Quick Window Switcher') {
            [void][WS.Win]::PostMessage($h, $WM_CLOSE, [IntPtr]::Zero, [IntPtr]::Zero)
        }
    }
    return $true
}
[void][WS.Win]::EnumWindows($cb, [IntPtr]::Zero)

$deadline = (Get-Date).AddSeconds(5)
while ((Get-Date) -lt $deadline -and (Get-Process -Id $ids -ErrorAction SilentlyContinue)) {
    Start-Sleep -Milliseconds 200
}
$left = @(Get-Process -Id $ids -ErrorAction SilentlyContinue)
if ($left.Count -gt 0) {
    $left | Stop-Process -Force
    Write-Host 'Prepinac neodpovidal, ukoncen natvrdo.'
} else {
    Write-Host 'Prepinac ukoncen.'
}
