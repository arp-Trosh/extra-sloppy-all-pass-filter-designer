# Windows test checklist (Windows 10 / Windows 11)

Thank you for testing! This takes about 15 minutes. Please note the Windows version
(Settings → System → About: Windows 10 or 11 and the version number, e.g. 23H2) and report
anything that differs from the expected results below.

## 1. Get the program

Download `esapf-gui-<version>-windows-x64.exe`. It is a single file and needs no installation.

> **Windows will probably warn you.** The executable is not code-signed (signing costs money),
> so SmartScreen may say *"Windows protected your PC"*. Click **More info → Run anyway**.
> Some antivirus programs also distrust new unsigned executables built with PyInstaller.
> If yours deletes the file, please tell us the antivirus name.

The first start takes a few seconds, because the program unpacks itself to a temporary folder.

## 2. Checks

| # | Do this | Expected result |
|---|---|---|
| 1 | Start the program | A window titled *Extra Sloppy All Pass Filter Designer* opens. It has a light-cyan background, F1 = 270, F2 = 3600, C = 10, button **3** is yellow and scale **1** is yellow. The graph shows only the grid. |
| 2 | Hover over **Design** | Tooltip: *Calculate values and display graph* |
| 3 | Click **Design** | The table fills 3 rows. Row (1) shows F1 = **91**, R1 = **174.456750**, C1 = 10, F2 = **10654**, R2 = **1.493779**. A blue curve wiggles around 0 and red curves sit between 60 and 80. |
| 4 | Click scale **0.2** | The left labels change to **+0.2** / **-0.2** and the blue curve gets taller. |
| 5 | Click filter button **5** | The table and graph clear, and rows (4) and (5) turn white. |
| 6 | Click **Design** | 5 rows are filled. Row (1): F1 = **54**, R1 = **294.198247**. |
| 7 | In row (1), change C1 to `10.1`, then click **Phase** | F1 of row (1) changes from 54 to **53**, and the graph changes slightly. |
| 8 | Change F1 (top left) to `5`, then click **Design** | A message box titled **ERROR**: *F1 should not be below 10 Hz*. Click OK. |
| 9 | Clear the R1 value of row (2), then click **Phase** | ERROR: *All Component Values MUST be Specified and Greater than Zero* |
| 10 | Click **Clear** | The table and graph are empty, and F1/F2/C are unchanged. |
| 11 | Display scaling: Settings → Display → Scale 150 % (if possible), then restart the program | The window is larger, but the layout is the same and the text is not cut off. |
| 12 | Set F1 back to `270`, click filter button **3**, then click **Bill Mode** (top right, next to Design) | A second, resizable window titled *… Bill Mode* replaces the classic one. F1 = 270, F2 = 3600, C = 10, section button **6** (3 per path) and series **E24** are selected. |
| 13 | Click **Design** | Row (1): F1 = **91.23**, R1 = **174456.79**, R1 E24 = **180000.00**, C1 = **10 nF**. Below the graph: *270–3600 Hz: max error 0.1335°, min suppression 58.7 dB*. |
| 14 | Click **Pair (sum)**, then **E-series R** | Row (1) of R1 E24 pair shows **150000.00 + 24000.00**. The curve changes, and the line below the graph says max error **0.3241°**. |
| 15 | Click **Perfect R** and **Single**. Open the C1 drop-down of row (1) and pick **22 nF** | R1 of row (1) changes to **79298.54**, and F1 stays at 91.23. |
| 16 | Type `20` in X axis **Min** and `20000` in **Max**, then click **Set axis** | The graph's frequency axis now runs from 20 to 20k. |
| 17 | Click section button **7**, then **Design** | Path 1 fills 4 rows (row (1): R1 = **204525.61**) and path 2 fills 3. The line below the graph says max error **0.0386°**. |
| 18 | Resize the Bill Mode window | The table and graph stretch, and nothing is cut off. |
| 19 | Click **Classic Mode** (or press Ctrl+B) | The classic window returns, with filter button **4** selected (7 sections round up to 4 per path). |
| 20 | Click **Exit** | An *About* box appears (credits and GPL licence). After OK the program closes. |

## 3. Please report

- Windows version, and whether each check passed. Screenshots after steps 6 and 17 would be
  great (Win + Shift + S).
- Any warnings, crashes or slow starts, plus how many seconds the first start took.
