param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Notebook,

    [Parameter(Mandatory = $false, Position = 1)]
    [string]$OutputDir = ".\exports",

    [Parameter(Mandatory = $false, Position = 2)]
    [string]$ReportName
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

Write-Host "Exporting HTML (no code inputs)..."
jupyter nbconvert --to html $Notebook --no-input --output $ReportName --output-dir $OutputDirAbs

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
    --virtual-time-budget=15000 `
    --run-all-compositor-stages-before-draw `
    "--print-to-pdf=$PdfPath" `
    $HtmlUri

Write-Host "Done."
Write-Host "HTML: $HtmlPath"
Write-Host "PDF:  $PdfPath"
