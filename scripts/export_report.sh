#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 4 ]]; then
  echo "Usage: $0 <notebook.ipynb> [output_dir] [report_name_without_ext] [--keep-html]"
  exit 1
fi

NOTEBOOK="$1"
OUTPUT_DIR="${2:-./exports}"
KEEP_HTML=0

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

if [[ $# -eq 4 ]]; then
  if [[ "$4" == "--keep-html" ]]; then
    KEEP_HTML=1
  else
    echo "Unknown option: $4"
    echo "Usage: $0 <notebook.ipynb> [output_dir] [report_name_without_ext] [--keep-html]"
    exit 1
  fi
fi

HTML_PATH="$OUTPUT_DIR/$REPORT_BASE.html"
PDF_PATH="$OUTPUT_DIR/$REPORT_BASE.pdf"
CSS_PATH="$OUTPUT_DIR/_nbconvert_print_fix.css"

echo "Exporting HTML (no code inputs)..."
jupyter nbconvert --to html "$NOTEBOOK" --no-input --output "$REPORT_BASE" --output-dir "$OUTPUT_DIR"

cat > "$CSS_PATH" <<'CSS'
/* Make wide notebook outputs printable without horizontal scrollbars. */
.jp-OutputArea,
.jp-OutputArea-child,
.jp-OutputArea-output,
.jp-RenderedHTMLCommon,
.jp-RenderedLatex {
  overflow: visible !important;
  max-width: 100% !important;
}

.jp-OutputArea-output pre,
pre {
  white-space: pre-wrap !important;
  word-break: break-word !important;
}

img,
svg,
canvas {
  max-width: 100% !important;
  height: auto !important;
}

@page {
  size: A4 portrait;
  margin: 12mm;
}
CSS

if ! grep -q "_nbconvert_print_fix.css" "$HTML_PATH"; then
  TMP_HTML="${HTML_PATH}.tmp"
  awk '
    BEGIN { inserted = 0 }
    /<\/head>/ && !inserted {
      print "<link rel=\"stylesheet\" href=\"./_nbconvert_print_fix.css\"/>"
      inserted = 1
    }
    { print }
    END {
      if (!inserted) {
        print "<link rel=\"stylesheet\" href=\"./_nbconvert_print_fix.css\"/>"
      }
    }
  ' "$HTML_PATH" > "$TMP_HTML"
  mv "$TMP_HTML" "$HTML_PATH"
fi

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
  --print-to-pdf-no-header \
  --virtual-time-budget=15000 \
  --run-all-compositor-stages-before-draw \
  --print-to-pdf="$(cd "$OUTPUT_DIR" && pwd)/$(basename "$PDF_PATH")" \
  "$HTML_URI"

echo "Done."
echo "HTML: $HTML_PATH"
echo "PDF:  $PDF_PATH"

if [[ $KEEP_HTML -eq 0 ]]; then
  rm -f "$HTML_PATH" "$CSS_PATH"
  echo "Removed intermediate HTML/CSS."
fi
