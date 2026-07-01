# Rychlý přepínač oken pro Windows (Quick Window Switcher)

Tato aplikace vylepšuje a zrychluje přepínání mezi okny v systému Windows. Umožňuje
**textově vyhledávat** mezi spuštěnými okny, definovat **vlastní zkratky** pro přepnutí
(např. do editoru poznámek) nebo spuštění programu, pokud okno ještě není otevřené, a
organizovat okna do **pojmenovaných skupin** s živými náhledy, ukotvenými okny a ukládáním
rozložení.

Aplikace běží na pozadí (ikona v oznamovací oblasti) a vyvolává se globální klávesovou
zkratkou. Využívá nativní rozhraní Windows API (přes `ctypes`) pro maximální rychlost a
spolehlivost.

---

## 📑 Obsah

- [Požadavky a instalace](#-požadavky-a-instalace)
- [Jak aplikaci spustit](#-jak-aplikaci-spustit)
- [Globální klávesová zkratka](#-globální-klávesová-zkratka)
- [Základní použití](#-základní-použití)
- [Ovládání klávesnicí](#-ovládání-klávesnicí)
- [Konfigurace (`config.txt`)](#️-konfigurace-configtxt)
  - [Přehled všech voleb](#přehled-všech-voleb)
  - [Zkratky pro přepnutí / spuštění](#zkratky-pro-přepnutí--spuštění)
- [Skupiny oken](#-skupiny-oken)
- [Speciální příkazy ve vyhledávacím poli](#-speciální-příkazy-ve-vyhledávacím-poli)
- [Chování při vzniku nového okna](#-chování-při-vzniku-nového-okna)
- [Skrývání ikon na hlavním panelu a v Alt+Tab](#-skrývání-ikon-na-hlavním-panelu-a-v-alttab)
- [Náhledy oken](#-náhledy-oken)
- [OSD a ikona v oznamovací oblasti](#-osd-a-ikona-v-oznamovací-oblasti)
- [Parametry příkazové řádky](#-parametry-příkazové-řádky)
- [Soubory aplikace](#-soubory-aplikace)

---

## 📦 Požadavky a instalace

Aplikace je napsaná v Pythonu pro Windows a používá tyto knihovny:

| Knihovna | Účel |
|----------|------|
| **Python 3.x** (Windows) | běhové prostředí |
| `pystray` | ikona v oznamovací oblasti (tray) |
| `Pillow` (`PIL`) | vykreslování ikony a textu náhledů |

Vestavěné moduly (`tkinter`, `ctypes`, `re`, `json`, `subprocess` …) jsou součástí Pythonu.

Instalace závislostí:

```powershell
pip install pystray pillow
```

---

## 🚀 Jak aplikaci spustit

Spusťte aplikaci na pozadí (bez černého okna příkazové řádky) pomocí `pythonw.exe` na
souboru s příponou `.pyw`:

```powershell
pythonw.exe win_switcher.pyw
```

Případně použijte přiložený dávkový soubor **`start_switcher.bat`**, který nejprve ukončí
případnou předchozí instanci a poté přepínač znovu spustí:

```powershell
start_switcher.bat
```

Aplikace zůstane běžet na pozadí a čeká na stisk globální klávesové zkratky. V oznamovací
oblasti se objeví ikona přepínače.

---

## ⌨️ Globální klávesová zkratka

Přepínač se vyvolává **globální klávesovou zkratkou**, kterou si nastavíte v `config.txt`
pomocí voleb `hotkey_modifier` a `hotkey_key` (viz [Konfigurace](#️-konfigurace-configtxt)).

Pokud se zvolenou zkratku nepodaří zaregistrovat (je obsazená jiným programem nebo
rezervovaná systémem, např. `Win+Tab` pro Task View), aplikace automaticky zkusí v tomto
pořadí **záložní zkratky**:

1. `Alt + Caps Lock`
2. `Alt + Ctrl + Mezerník`

> 💡 Doporučená stabilní kombinace je `alt + caps` (Alt + Caps Lock).

---

## 🔍 Základní použití

1. **Vyvolejte přepínač** globální zkratkou.
2. **Začněte psát** část názvu okna (titulek prohlížeče, složky, VS Code…) nebo název
   procesu. Seznam se okamžitě filtruje (bez ohledu na velikost písmen).
3. **Vyberte** položku šipkami a stiskněte **Enter** pro přepnutí na okno.
4. **Zkratky a vzory:** napíšete-li definovanou zkratku (např. `vn`):
   - aplikace vyhledá okno odpovídající regulárnímu výrazu (např. `.*notes.*`);
   - pokud okno **existuje**, nabídne `⭐ [Aktivní okno] -> …`;
   - pokud **neexistuje**, nabídne `🚀 [Spustit] -> code -n c:/notes`.

---

## 🎹 Ovládání klávesnicí

Uvnitř okna přepínače:

| Klávesa | Akce |
|---------|------|
| **psaní textu** | filtruje okna podle titulku i názvu procesu |
| **Šipka ↑ / ↓** | pohyb v seznamu oken / příkazů |
| **Šipka ← / →** | přepínání mezi skupinami (a „všechna okna") |
| **Enter** | přepnout na okno, spustit příkaz nebo potvrdit akci |
| **Insert** | v režimu `aaa`/`aai` označit/odznačit položku a posunout kurzor dolů |
| **Shift + ↑ / ↓** | v režimu `aaa`/`aai` označovat položky při pohybu |
| **Delete** | zavřít okno (mimo skupinu) nebo zavřít/vyjmout okno ze skupiny |
| **Ctrl + R** | znovu načíst `config.txt` bez restartu aplikace |
| **Esc** | skrýt okno přepínače |
| **Ctrl + Q** | kompletně ukončit aplikaci běžící na pozadí |
| **kliknutí mimo okno** | přepínač se automaticky skryje |

---

## ⚙️ Konfigurace (`config.txt`)

Veškeré nastavení i zkratky jsou v textovém souboru `config.txt` ve složce aplikace.
Pokud soubor neexistuje, vytvoří se při prvním spuštění se základním obsahem. Změny lze
za běhu načíst klávesou **Ctrl + R**.

- Řádky začínající `#` jsou **komentáře**.
- Každá volba je na samostatném řádku ve tvaru `klíč hodnota`.
- Logické hodnoty přijímají `true` / `1` / `yes` (jinak `false`).

### Přehled všech voleb

| Volba | Hodnota | Výchozí | Popis |
|-------|---------|---------|-------|
| `hotkey_modifier` | `win`, `ctrl`, `alt`, `shift` (lze kombinovat `+`) | `win` | Modifikátor globální zkratky. Příklady: `alt`, `ctrl+shift`. |
| `hotkey_key` | `tab`, `space`, `caps`, `f1`–`f24`, jedno písmeno/číslice nebo hex kód | `tab` | Hlavní klávesa globální zkratky. |
| `show_thumbnails` | `true` / `false` | `false` | Velký **boční živý náhled** vybraného okna (DWM). |
| `show_list_thumbnails` | `true` / `false` | `true` | Malé **živé náhledy přímo v řádcích** seznamu. |
| `list_thumbnail_scale` | desetinné číslo | `5.0` | Měřítko malých náhledů (základ 48×30 px × měřítko). |
| `window_height` | celé číslo (px) | `680` | Výška okna přepínače. |
| `new_window_action` | `never`, `ask`, `always`, `leave` | `never` | Co se stane s nově vzniklým oknem, je-li aktivní skupina. |
| `new_window_auto_yes` | regulární výraz | – | **Ano** – okno se automaticky přidá do skupiny (natrvalo). |
| `new_window_auto_yes_temp` | regulární výraz | – | **Ano dočasně** – okno je ve skupině jen dokud je aktivní (neukládá se). |
| `new_window_auto_no` | regulární výraz | – | **Ne - zůstat** – okno se vynechá, skupina zůstane aktivní. |
| `auto_close_windows` | regulární výraz | – | **Zavřít** – nově vzniklé okno se automaticky zavře. |
| `new_window_auto_no_leave` | regulární výraz | – | **Ne - opustit skupinu** – okno se vynechá a opustí se skupina. |
| `hide_taskbar_icons` | `true` / `false` | `false` | Skrýt na hlavním panelu ikony oken **mimo** aktivní skupinu. |
| `hide_alttab_icons` | `true` / `false` | `false` | Skrýt okna mimo aktivní skupinu i z přepínání **Alt+Tab**. |

> Auto-pravidla (`new_window_auto_*`, `auto_close_windows`) jsou regulární výrazy hledané
> v řetězci **„proces titulek"** (např. `chrome.exe Nová zpráva – Gmail`), takže lze mířit
> na název aplikace i titulek. Vyhodnocují se **bez ohledu na velikost písmen**, více vzorů
> spojíte svislítkem `|`. Mají **přednost** před volbou `new_window_action` a vyhodnocují se
> v pořadí: **Ano → Ano dočasně → Ne - zůstat → Zavřít → Ne - opustit skupinu** (první shoda
> vyhraje).

**Příklad `hotkey_*`:**
```text
hotkey_modifier alt
hotkey_key f12
```

### Zkratky pro přepnutí / spuštění

Kromě voleb obsahuje `config.txt` i **zkratky** ve formátu:

```text
<zkratka> <regulární_výraz_titulku> <příkaz_pro_spuštění>
```

Po zadání zkratky a stisku **Enter**:

1. nejdříve se hledá okno odpovídající regulárnímu výrazu;
2. pokud okno existuje → aktivuje se;
3. pokud neexistuje → spustí se zadaný příkaz.

**Příklady:**
```text
vn .*notes.* code -n c:/notes
gc .*chrome.* "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

*(`.*` v regulárním výrazu odpovídá libovolné části titulku. Vyhodnocuje se bez ohledu na
velikost písmen.)*

---

## 🗂️ Skupiny oken

Skupina je pojmenovaná kolekce oken, kterou lze rychle aktivovat. Když je skupina aktivní:

- na všech monitorech se zobrazí **OSD nápis** s názvem skupiny;
- volitelně se **skryjí ikony oken mimo skupinu** na hlavním panelu i v Alt+Tab
  (viz `hide_taskbar_icons`, `hide_alttab_icons`);
- nová okna se zpracují podle `new_window_action` a auto-pravidel.

Názvy skupin začínají prefixem **`gg`** (např. `gga`, `ggwork`). Speciální skupina **`_`**
představuje „okna, která nejsou v žádné skupině". Skupiny a uložená rozložení se ukládají do
souboru `groups.json`.

> ⚠️ Ve výchozím stavu se **skupiny při každém startu vymažou**. Chcete-li je zachovat mezi
> spuštěními, spusťte aplikaci s parametrem `--keep-groups` (viz níže).

**Přepínání mezi skupinami:** šipkami **← / →** ve vyhledávacím poli procházíte abecedně
seřazené skupiny i stav „všechna okna". Aktuální pozice se zobrazuje ve stavovém řádku.

---

## 🧩 Speciální příkazy ve vyhledávacím poli

Tyto příkazy se píší přímo do vyhledávacího pole přepínače. `gg<x>` zastupuje název skupiny
(např. `gga`).

| Co napíšete | Význam |
|-------------|--------|
| `gg<x>` | Zobrazí okna ve skupině `gg<x>` (a umožní ji aktivovat). |
| `gg<x> <text>` | Vyhledá okno podle textu a po Enter ho **přidá do skupiny** `gg<x>`. |
| `_` | Zobrazí okna, která nejsou v žádné skupině. |
| `gg<x> aaa [filtr]` | **Hromadné přidání** – vypíše okna mimo skupinu; označená okna (Insert / Shift+šipky) se přidají do skupiny. |
| `gg<x> aai [filtr]` | **Výhradní přidání** – jako `aaa`, ale označená okna se zároveň odeberou ze všech ostatních skupin. |
| `gg<x> kkk` | **Ukotvit / odkotvit** předchozí aktivní okno ve skupině (drží okno navrchu). |
| `gg<x> rrr` | **Odebrat** aktuální (předchozí aktivní) okno ze skupiny. |
| `gg<x> ddd` | **Smazat skupinu** `gg<x>` (potvrdí se Enterem; `_` nelze smazat). |
| `gg<x> sv <název>` | **Uložit rozložení** (pozice oken) skupiny pod daným názvem. |
| `gg<x> lv <název>` | **Načíst rozložení** skupiny a rozmístit okna podle něj. |
| `kkk` | Ukotvit / odkotvit předchozí aktivní okno (bez vazby na skupinu). |
| `kka` | Ukotvit / odkotvit předchozí aktivní okno **globálně**. |
| `sv <název>` | Uložit **celkové** rozložení všech oken. |
| `lv <název>` | Načíst **celkové** rozložení všech oken. |

**Hromadný výběr (`aaa` / `aai`):** v tomto režimu klávesa **Insert** označí položku a posune
kurzor dolů, **Shift + ↑/↓** označuje při pohybu. Po **Enter** se přidají všechna označená
okna; pokud nic neoznačíte, přidá se okno pod kurzorem. Aktivuje se první označené okno
odshora.

**Ukotvení (`kkk` / `kka`):** ukotvené okno se nastaví „vždy navrchu" (TOPMOST) a maximalizovaná
okna ho nepřekryjí (rezervuje se odpovídající okraj pracovní plochy). Opakovaným příkazem se
okno odkotví. Ukotvení přežije i pád aplikace – při dalším startu se neplatné kotvy uklidí.

Kotvy se navíc **aktivně udržují**: na pozadí běží hlídač (~1× za 0,8 s), který ukotvenému
oknu obnoví příznak „vždy navrchu" a vrátí ho na rezervované místo, pokud ho něco odsune nebo
překryje (typicky po **návratu z celoobrazovkové VDI/Citrix relace** nebo po změně rozlišení).
Rezervovaný pruh work area tak nezůstane prázdný.

**Poloha ukotveného okna je pevná.** Okno **můžeš maximalizovat** (roztáhne se přes celý
monitor – rezervace pruhu se po dobu maximalizace uvolní). Jakmile ho ale **minimalizuješ,
zmenšíš nebo přesuneš**, vrátí se zpět do ukotvené polohy a velikosti. Chceš-li kotvu umístit
jinam, okno odkotvi (`gg<x> kkk` / `kkk`), přesuň a ukotvi znovu.

Rezervace okraje se automaticky uvolní, když:
- ukotvené okno **zavřeš** (nezůstane po něm prázdný pruh);
- u kotvy vázané na skupinu (`gg<x> kkk`) **opustíš nebo přepneš skupinu**. Kotva se ale jen
  „uspí" – po **návratu do skupiny se okno znovu automaticky ukotví**. Trvale ji zrušíš
  opětovným `gg<x> kkk` (odkotvení), zavřením okna nebo smazáním skupiny.

Globální kotvy (`kka`) a kotvy bez skupiny (samotné `kkk`) zůstávají aktivní stále, dokud je
ručně neodkotvíš nebo okno nezavřeš.

---

## 🆕 Chování při vzniku nového okna

Je-li aktivní nějaká skupina a objeví se nové okno, řídí se chování volbou
`new_window_action`:

| Hodnota | Chování |
|---------|---------|
| `never` | Nové okno se ignoruje. |
| `ask` | Zobrazí se dotaz s tlačítky:<br>**Ano** (přidat natrvalo) · **Ano dočasně** (ve skupině jen dokud je okno aktivní) · **Vždy** (přidávat bez ptaní) · **Vždy do přepnutí** (přidávat do změny skupiny) · **Ne – zůstat** (vynechat, zůstat ve skupině) · **Ne – opustit skupinu** (vynechat a opustit) · **Zavřít okno** (rovnou zavřít). |
| `always` | Nové okno se vždy přidá bez ptaní. |
| `leave` | Při novém okně se opustí skupina. |

**Ano dočasně** přidá okno do skupiny jen do runtime (neuloží se do `groups.json`) a okno je
členem skupiny **jen dokud je aktivní** – jakmile přepneš na jiné okno, ze skupiny vypadne
(a při návratu na něj se zase vrátí). Při opuštění skupiny se dočasní členové zapomenou.

Auto-pravidla podle regulárního výrazu (`new_window_auto_yes`, `new_window_auto_yes_temp`,
`new_window_auto_no`, `auto_close_windows`, `new_window_auto_no_leave`) mají **přednost** před
`new_window_action`. Hledají se v řetězci „proces titulek" a vyhodnocují se v pořadí
**Ano → Ano dočasně → Ne - zůstat → Zavřít → Ne - opustit skupinu**.

---

## 🙈 Skrývání ikon na hlavním panelu a v Alt+Tab

Při aktivní skupině lze „uklidit" plochu skrytím oken, která do skupiny nepatří:

- **`hide_taskbar_icons true`** – odebere tlačítka oken mimo skupinu z hlavního panelu
  (přes COM rozhraní `ITaskbarList`).
- **`hide_alttab_icons true`** – skryje okna mimo skupinu i z přepínání **Alt+Tab**
  (nastavením stylu `WS_EX_TOOLWINDOW`).

Po opuštění skupiny nebo ukončení aplikace se viditelnost ikon obnoví. Aplikace si původní
styly ukládá do vlastností oken, takže obnovení proběhne i po případném pádu (úklid při
příštím startu).

---

## 🖼️ Náhledy oken

- **Boční živý náhled** (`show_thumbnails`) – velký DWM náhled vybraného okna vedle seznamu.
- **Řádkové náhledy** (`show_list_thumbnails`) – malé živé náhledy přímo u každého řádku;
  jejich velikost řídí `list_thumbnail_scale` (základ 48×30 px násobený měřítkem).

Šířka okna přepínače se přizpůsobuje: nejširší je s bočním náhledem, užší při větším měřítku
řádkových náhledů, nejužší bez náhledů.

---

## 📟 OSD a ikona v oznamovací oblasti

- **OSD nápis skupiny** se při aktivní skupině zobrazuje na **všech monitorech**. Trvalý
  watchdog hlídá, aby nápis nezmizel, a reaguje na změnu rozložení monitorů.
- **Ikona v oznamovací oblasti (tray)** zobrazuje aktuální skupinu (popisek
  „Win Switcher | skupina: …") a nabízí položku **Ukončit**.

---

## 🏳️ Parametry příkazové řádky

| Parametr | Popis |
|----------|-------|
| `--keep-groups` | Nezmaže skupiny při startu – zachová skupiny a rozložení z předchozího běhu. |

Příklad:
```powershell
pythonw.exe win_switcher.pyw --keep-groups
```

---

## 📁 Soubory aplikace

| Soubor | Popis |
|--------|-------|
| `win_switcher.pyw` | Hlavní program. |
| `config.txt` | Nastavení a zkratky (vytvoří se automaticky, nečte-li se). |
| `groups.json` | Uložené skupiny a rozložení (pohledy). Při poškození se zazálohuje do `groups.json.bak`. |
| `start_switcher.bat` | Pohodlné spuštění / restart přepínače na pozadí. |
