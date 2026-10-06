#!/usr/bin/env bash
# Download the third-party reference material used by this project.
# These files are copyright their respective authors and are NOT
# redistributed in this repository (see .gitignore).
#
#   original/   J-Tek Apf.exe + VB6 runtime (Lawrence Woolf, GJ3RAX)
#   web/        GJ3RAX program page, example pages and screenshots
#   *.pdf       VHF Communications 2/1987 (R. Oppelt, DB2NP, pp. 66-72)
#
# Usage: reference/fetch.sh   (safe to re-run; existing files are kept)
set -euo pipefail
cd "$(dirname "$0")"

UA='Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0'
GJ='https://www.gj3rax.com'

# dest | url | sha256 ("-" = not pinned, the page may legitimately change)
manifest=(
  "original/apf.exe|$GJ/files/apf.exe|b6bb568254990423cd845ec4be5125471739ee04424bf21303d69641616bb26c"
  "original/msvbvm60.dll|$GJ/files/msvbvm60.dll|-"
  "web/apf.htm|$GJ/apf.htm|-"
  "web/kk7b.htm|$GJ/kk7b.htm|-"
  "web/an1981.htm|$GJ/an1981.htm|-"
  "web/n4bcu.htm|$GJ/n4bcu.htm|-"
  "web/kk7b.jpg|$GJ/graphics/kk7b.jpg|b29583d677d3928b6f747eeeb1a9cb76f31a8682e7f7fcf46582e1af428a959f"
  "web/an1981.jpg|$GJ/graphics/an1981.jpg|6f25dca41f974deaa0f78ee967cee9518f8dfd75efcd5d6fa56cdf6d118a45d9"
  "web/n4bcu.jpg|$GJ/graphics/n4bcu.jpg|8f5dedf36f1b90a329cc50be9a8c1bbbb7ce632d553e928f7b83df57174e61a6"
  "VHF-COMM.1987.2.pdf|https://www.worldradiohistory.com/Archive-DX/VHF-Communications/VHF-COMM.1987.2.pdf|091fe4f4e8c8411cbd3ffdf3d3a04988f7d7768cde8d0bd0e6a388114bd97d64"
)

status=0
for entry in "${manifest[@]}"; do
  IFS='|' read -r dest url sha <<<"$entry"
  mkdir -p "$(dirname "$dest")"
  if [[ ! -s $dest ]]; then
    echo "fetch  $dest"
    curl -fsSL -A "$UA" -o "$dest" "$url" || { echo "FAILED $url" >&2; status=1; continue; }
  fi
  if [[ $sha != - ]]; then
    actual=$(sha256sum "$dest" | cut -d' ' -f1)
    if [[ $actual == "$sha" ]]; then echo "ok     $dest"
    else echo "MISMATCH $dest ($actual)" >&2; status=1; fi
  fi
done
exit $status
