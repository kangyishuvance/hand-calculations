param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Notebook,

    [Parameter(Mandatory = $false, Position = 1)]
    [string]$OutputDir = ".\exports",

    [Parameter(Mandatory = $false, Position = 2)]
    [string]$ReportName,

    [Parameter(Mandatory = $false)]
    [switch]$KeepHtml
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Notebook)) {
    throw "Notebook not found: $Notebook"
}

if (-not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

if ([string]::IsNullOrWhiteSpace($ReportName)) {
    $ReportName = [System.IO.Path]::GetFileNameWithoutExtension($Notebook) + "_report"
}

$OutputDirAbs = (Resolve-Path -LiteralPath $OutputDir).Path
$HtmlPath = Join-Path $OutputDirAbs ($ReportName + ".html")
$PdfPath = Join-Path $OutputDirAbs ($ReportName + ".pdf")
$CssPath = Join-Path $OutputDirAbs "_nbconvert_print_fix.css"

Write-Host "Exporting HTML (no code inputs)..."
jupyter nbconvert --to html $Notebook --no-input --output $ReportName --output-dir $OutputDirAbs

$PrintFixCss = @'
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
'@

Set-Content -LiteralPath $CssPath -Value $PrintFixCss -Encoding UTF8

$CssLinkTag = '<link rel="stylesheet" href="./_nbconvert_print_fix.css"/>'
$HtmlContent = Get-Content -LiteralPath $HtmlPath -Raw
if ($HtmlContent -notmatch [Regex]::Escape("_nbconvert_print_fix.css")) {
    if ($HtmlContent -match "(?i)</head>") {
        $HtmlContent = $HtmlContent -replace "(?i)</head>", "$CssLinkTag`n</head>"
    } else {
        $HtmlContent += "`n$CssLinkTag`n"
    }
    Set-Content -LiteralPath $HtmlPath -Value $HtmlContent -Encoding UTF8
}

$BrowserCandidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe",
    "$env:LocalAppData\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles(x86)\Microsoft\Edge\Application\msedge.exe"
)

$BrowserPath = $null
foreach ($Candidate in $BrowserCandidates) {
    if (Test-Path -LiteralPath $Candidate) {
        $BrowserPath = $Candidate
        break
    }
}

if (-not $BrowserPath) {
    throw "No Chrome/Edge executable found. HTML created at: $HtmlPath"
}

$HtmlUri = (New-Object System.Uri((Resolve-Path -LiteralPath $HtmlPath).Path)).AbsoluteUri

Write-Host "Printing PDF with: $BrowserPath"
& $BrowserPath `
    --headless=new `
    --disable-gpu `
    --allow-file-access-from-files `
    --print-to-pdf-no-header `
    --virtual-time-budget=15000 `
    --run-all-compositor-stages-before-draw `
    "--print-to-pdf=$PdfPath" `
    $HtmlUri

Write-Host "Done."
Write-Host "HTML: $HtmlPath"
Write-Host "PDF:  $PdfPath"

if (-not $KeepHtml) {
    Remove-Item -LiteralPath $HtmlPath -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $CssPath -ErrorAction SilentlyContinue
    Write-Host "Removed intermediate HTML/CSS."
}
