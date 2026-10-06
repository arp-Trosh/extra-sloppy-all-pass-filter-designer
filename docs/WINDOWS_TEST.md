# Windows test checklist (Windows 10 / Windows 11)

Thank you for testing! This takes about 10 minutes. Please note the Windows version
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
| 12 | Click **Exit** | An *About* box appears (credits and GPL licence). After OK the program closes. |

## 3. Please report

- Windows version, and whether each check passed. A screenshot after step 6 would be great
  (Win + Shift + S).
- Any warnings, crashes or slow starts, plus how many seconds the first start took.
