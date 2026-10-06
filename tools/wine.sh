#!/usr/bin/env bash
# Run the original J-Tek Apf.exe (and the VBDec P-code disassembler) under Wine,
# in a project-local prefix (.wine/, git-ignored) so the user's ~/.wine is untouched.
#
#   tools/wine.sh setup [--vbdec] [--oracle]
#                            create prefix, install VB6 runtime; optionally VBDec and the
#                            Windows embeddable Python used by tools/oracle (Phase 1 capture)
#   tools/wine.sh original   run the original Apf.exe
#   tools/wine.sh vbdec      open Apf.exe in VBDec
#   tools/wine.sh kill       close everything running in the prefix
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
export WINEPREFIX=$ROOT/.wine WINEDEBUG=${WINEDEBUG:--all}
REF=$ROOT/reference/original
VBDEC_URL=https://sandsprite.com/vbdec/VBDEC_Setup.exe
PYEMBED_URL=https://www.python.org/ftp/python/3.13.16/python-3.13.16-embed-win32.zip
VBDEC_EXE='C:\Sandsprite\vbdec\vbdec.exe'

need_ref() { [[ -s $REF/apf.exe && -s $REF/msvbvm60.dll ]] || "$ROOT/reference/fetch.sh"; }

setup() {
  need_ref
  wineboot -i >/dev/null 2>&1
  # VB6 runtime must be system-wide (syswow64) and preferred over Wine's builtin stub,
  # otherwise VB6 ActiveX components (VBDec) fail to register.
  cp "$REF/msvbvm60.dll" "$WINEPREFIX/drive_c/windows/syswow64/msvbvm60.dll"
  wine reg add 'HKCU\Software\Wine\DllOverrides' /v msvbvm60 /t REG_SZ /d native /f >/dev/null
  echo "prefix ready: $WINEPREFIX"
  mkdir -p "$ROOT/.tools"
  for opt in "$@"; do
    case $opt in
      --vbdec)
        [[ -s $ROOT/.tools/VBDEC_Setup.exe ]] || curl -fsSL -o "$ROOT/.tools/VBDEC_Setup.exe" "$VBDEC_URL"
        wine "$ROOT/.tools/VBDEC_Setup.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- 2>&1 | grep -i regsvr32 || true
        echo "VBDec installed" ;;
      --oracle)
        [[ -s $ROOT/.tools/pyembed.zip ]] || curl -fsSL -o "$ROOT/.tools/pyembed.zip" "$PYEMBED_URL"
        rm -rf "$ROOT/.tools/pywin" && mkdir -p "$ROOT/.tools/pywin"
        python3 -m zipfile -e "$ROOT/.tools/pyembed.zip" "$ROOT/.tools/pywin"
        echo "Windows embeddable Python installed in .tools/pywin" ;;
      *) echo "unknown option $opt" >&2; exit 1 ;;
    esac
  done
}

case ${1:-} in
  setup)    shift; setup "$@" ;;
  original) need_ref; cd "$REF" && exec wine apf.exe ;;
  vbdec)    need_ref; exec wine "$VBDEC_EXE" "$(winepath -w "$REF/apf.exe")" ;;
  kill)     wineserver -k ;;
  *)        sed -n '2,10p' "$0"; exit 1 ;;
esac
