param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Notebook,

    [Parameter(Mandatory = $false, Position = 1)]
    [string]$OutputDir,

    [Parameter(Mandatory = $false, Position = 2)]
    [string]$ReportName,

    [Parameter(Mandatory = $false)]
    [switch]$DeleteHtml,

    [Parameter(Mandatory = $false)]
    [string]$Orientation = "portrait"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Notebook)) {
    throw "Path not found: $Notebook"
}

# Resolve list of notebooks to process
$IsDirectory = (Get-Item -LiteralPath $Notebook).PSIsContainer
if ($IsDirectory) {
    $Notebooks = Get-ChildItem -LiteralPath $Notebook -Filter "*.ipynb" | Select-Object -ExpandProperty FullName
    if ($Notebooks.Count -eq 0) {
        throw "No .ipynb files found in: $Notebook"
    }
    Write-Host "Found $($Notebooks.Count) notebook(s) in directory."
} else {
    $Notebooks = @($Notebook)
}

$PrintFixCss = @"
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
    size: A4 $Orientation;
    margin: 12mm;
}
"@

# Default output: PDF_outputs folder inside the source directory
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $SourceDir = if ($IsDirectory) { $Notebook } else { Split-Path $Notebook -Parent }
    $OutputDir = Join-Path $SourceDir "PDF_outputs"
}

if (-not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
    Write-Host "Created output folder: $OutputDir"
}

$OutputDirAbs = (Resolve-Path -LiteralPath $OutputDir).ProviderPath
$CssPath = Join-Path $OutputDirAbs "_nbconvert_print_fix.css"
Set-Content -LiteralPath $CssPath -Value $PrintFixCss -Encoding UTF8

foreach ($nb in $Notebooks) {
    $name = if ($IsDirectory -or [string]::IsNullOrWhiteSpace($ReportName)) {
        [System.IO.Path]::GetFileNameWithoutExtension($nb) + "_report"
    } else {
        $ReportName
    }

    $HtmlPath = Join-Path $OutputDirAbs ($name + ".html")
    $PdfPath  = Join-Path $OutputDirAbs ($name + ".pdf")

    Write-Host "`nExporting: $nb"

    # Generate HTML (kept for reference)
    jupyter nbconvert --to html $nb --no-input --output $name --output-dir $OutputDirAbs

    # Inject print CSS into HTML (inline to avoid file:// URI issues with network paths)
    $CssStyle = "<style type=`"text/css`">`n$PrintFixCss`n</style>"
    $HtmlContent = Get-Content -LiteralPath $HtmlPath -Raw
    if ($HtmlContent -notmatch "nbconvert_print_fix") {
        if ($HtmlContent -match "(?i)</head>") {
            $HtmlContent = $HtmlContent -replace "(?i)</head>", "$CssStyle`n</head>"
        } else {
            $HtmlContent += "`n$CssStyle`n"
        }
        Set-Content -LiteralPath $HtmlPath -Value $HtmlContent -Encoding UTF8
    }

    # Generate PDF via webpdf (uses Playwright — waits for MathJax before printing)
    Write-Host "Printing PDF (webpdf)..."
    $ScriptDir = Split-Path $PSCommandPath -Parent
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonExe -or $PythonExe -like "*WindowsApps*") {
        $PythonExe = "C:\Users\vance\.conda\envs\jupyter_sandbox\python.exe"
    }
    if ($Orientation -eq "landscape") {
        & $PythonExe "$ScriptDir\webpdf_landscape.py" $nb $name $OutputDirAbs
    } else {
        jupyter nbconvert --to webpdf $nb --no-input --output $name --output-dir $OutputDirAbs --allow-chromium-download
    }

    if (-not (Test-Path -LiteralPath $PdfPath)) {
        throw "PDF was not created for: $nb"
    }

    Write-Host "PDF: $PdfPath"

    if ($DeleteHtml) {
        Remove-Item -LiteralPath $HtmlPath -ErrorAction SilentlyContinue
    }
}

if ($DeleteHtml) {
    Remove-Item -LiteralPath $CssPath -ErrorAction SilentlyContinue
}

Write-Host "`nDone. Output dir: $OutputDirAbs"
