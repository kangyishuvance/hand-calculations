#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 3 ]]; then
  echo "Usage: $0 <notebook.ipynb> [output_dir] [report_name_without_ext]"
  exit 1
fi

NOTEBOOK="$1"
OUTPUT_DIR="${2:-./exports}"

if [[ ! -f "$NOTEBOOK" ]]; then
  echo "Notebook not found: $NOTEBOOK"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

if [[ $# -ge 3 ]]; then
  REPORT_BASE="$3"
else
  REPORT_BASE="$(basename "${NOTEBOOK%.*}")_report"
fi

HTML_PATH="$OUTPUT_DIR/$REPORT_BASE.html"
PDF_PATH="$OUTPUT_DIR/$REPORT_BASE.pdf"

echo "Exporting HTML (no code inputs)..."
jupyter nbconvert --to html "$NOTEBOOK" --no-input --output "$REPORT_BASE" --output-dir "$OUTPUT_DIR"

if command -v google-chrome >/dev/null 2>&1; then
  CHROME_BIN="google-chrome"
elif command -v chromium >/dev/null 2>&1; then
  CHROME_BIN="chromium"
elif [[ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]]; then
  CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
elif [[ -x "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" ]]; then
  CHROME_BIN="/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
else
  echo "No Chromium-based browser found."
  echo "Install Google Chrome/Chromium/Edge, then retry."
  echo "HTML export is ready at: $HTML_PATH"
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  HTML_URI="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve().as_uri())' "$HTML_PATH")"
else
  echo "python3 is required to build a file:// URI for browser PDF printing."
  exit 1
fi

echo "Printing PDF with: $CHROME_BIN"
"$CHROME_BIN" \
  --headless=new \
  --disable-gpu \
  --allow-file-access-from-files \
  --virtual-time-budget=15000 \
  --run-all-compositor-stages-before-draw \
  --print-to-pdf="$(cd "$OUTPUT_DIR" && pwd)/$(basename "$PDF_PATH")" \
  "$HTML_URI"

echo "Done."
echo "HTML: $HTML_PATH"
echo "PDF:  $PDF_PATH"
