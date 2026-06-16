# Rychlý přepínač oken pro Windows (Quick Window Switcher)

Tato aplikace vylepšuje a zrychluje přepínání mezi okny v systému Windows. Umožňuje textově vyhledávat mezi spuštěnými okny a definovat vlastní zkratky pro přepnutí (např. do vašeho editoru poznámek) nebo spuštění příslušného programu, pokud okno ještě není otevřené.

Aplikace je napsána v čistém Pythonu bez externích závislostí a využívá nativní rozhraní Windows API pro maximální rychlost a spolehlivost.

---

## 🚀 Jak aplikaci spustit

Spusťte aplikaci na pozadí (bez zbytečného černého okna příkazové řádky) pomocí Pythonu na souboru s příponou `.pyw`:

```powershell
pythonw.exe win_switcher.pyw
```

Aplikace zůstane běžet na pozadí a čeká na stisk klávesové zkratky.

---

## ⌨️ Jak se aplikace používá

1. **Vyvolání přepínače:** Stiskněte klávesovou zkratku **`Ctrl + Shift + Space`** (případně `Alt + Space` jako záložní, pokud by byla první zkratka obsazená).
2. **Vyhledávání:** Okamžitě začněte psát název okna (např. část nadpisu webového prohlížeče, složky, VS Code, atd.).
3. **Zkratky a vzory paternu:**
   - Pokud napíšete např. zkratku `vn` (definovanou v konfiguraci):
     - Aplikace vyhledá okno odpovídající zadanému regulárnímu výrazu (např. `.*notes.*`).
     - Pokud **existuje**, nabídne vám přepnutí na toto okno.
     - Pokud **neexistuje**, nabídne možnost **`[Spustit] -> code -n c:/notes`**.
4. **Ovládání klávesnicí:**
   - **`Šipka Nahoru / Dolů`**: Pohyb v seznamu oken/příkazů přímo z vyhledávacího pole.
   - **`Enter`**: Přepnutí na vybrané okno, nebo spuštění příkazu/programu.
   - **`Ctrl + R`**: Znovu načíst konfigurační soubor `config.txt` (bez restartu aplikace).
   - **`Esc`**: Skrýt okno přepínače.
   - **`Ctrl + Q`**: Kompletně ukončit aplikaci na pozadí.
   - **Kliknutí mimo okno**: Okno se automaticky skryje.

---

## ⚙️ Konfigurace zkratek (`config.txt`)

Konfigurace se nachází v souboru `config.txt` s formátem:
```text
<zkratka> <vzor_regulárního_výrazu> <příkaz_na_spuštění>
```

> `hotkey_key` může být nastaveno jako `tab`, `space`, `caps`, `f1`–`f24`, nebo jako jednopísmenná/jednociferná klávesa (`x`, `1`, atd.).

**Příklady:**
```text
vn .*notes.* code -n c:/notes
gc .*chrome.* "C:\Program Files\Google\Chrome\Application\chrome.exe"
```
*(Znak `.*` v regulárním výrazu slouží k tomu, aby se hledala libovolná část titulu okna. Vzory se vyhodnocují bez ohledu na velikost písmen.)*
