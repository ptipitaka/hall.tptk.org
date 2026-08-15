<#
.SYNOPSIS
  Build a cs-roman Thai TeX volume (LuaLaTeX).

.EXAMPLE
  .\build.ps1
  .\build.ps1 -Volume 01Vin01
  .\build.ps1 -Volume 01Vin01 -Mode printing
  .\build.ps1 -Volume 01Vin01 -SkipGenerate
#>
param(
  [string]$Volume = "01Vin01",
  [ValidateSet("sync", "printing")]
  [string]$Mode = "sync",
  [switch]$SkipGenerate,
  [switch]$SkipSync
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $SkipSync) {
  # sync may write progress to stderr; do not treat as terminating under Stop.
  $prevEap = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  & python scripts/sync_volume_data.py --volume $Volume 2>&1 | Out-Host
  $syncExit = $LASTEXITCODE
  $ErrorActionPreference = $prevEap
  if ($syncExit -ne 0) {
    throw "sync_volume_data.py failed (exit $syncExit)"
  }
}
if (-not $SkipGenerate) {
  # generate prints footnote warnings to stderr; under Stop that becomes
  # NativeCommandError and aborts before latexmk.
  $prevEap = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  & python scripts/generate_cs_roman_tex.py --volume $Volume --mode $Mode 2>&1 | Out-Host
  $genExit = $LASTEXITCODE
  $ErrorActionPreference = $prevEap
  if ($genExit -ne 0) {
    throw "generate_cs_roman_tex.py failed (exit $genExit)"
  }
}

if ($Mode -eq "printing") {
  $main = "volumes/$Volume/tex/main.printing.tex"
  $auxDir = "build/aux/printing/$Volume"
  $built = "$auxDir/main.printing.pdf"
  $dest = "volumes/$Volume/out/$Volume.printing.pdf"
  if (-not (Test-Path $main)) {
    python scripts/batch_prepare_volumes.py --volume $Volume --mode printing
  }
} else {
  $main = "volumes/$Volume/tex/main.tex"
  $auxDir = "build/aux/$Volume"
  $built = "$auxDir/main.pdf"
  $dest = "volumes/$Volume/out/$Volume.pdf"
  if (-not (Test-Path $main)) {
    python scripts/batch_prepare_volumes.py --volume $Volume --mode sync
  }
}

if (-not (Test-Path $main)) {
  throw "Missing $main after prepare"
}

New-Item -ItemType Directory -Force -Path $auxDir | Out-Null
New-Item -ItemType Directory -Force -Path "volumes/$Volume/out" | Out-Null

# Avoid -jobname=$Name — latexmk treats $Name as its own variable.
# Quote -outdir/-auxdir so PowerShell expands $auxDir before latexmk sees it.
# Per-volume aux dirs keep TOC .aux from one book from corrupting another.
# latexmk writes benign first-pass messages (e.g. missing .toc) to stderr;
# with $ErrorActionPreference Stop that becomes a terminating NativeCommandError.
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& latexmk -lualatex -f "-outdir=$auxDir" "-auxdir=$auxDir" $main 2>&1 | Out-Host
$latexmkExit = $LASTEXITCODE
$ErrorActionPreference = $prevEap

if (-not (Test-Path $built)) {
  throw "Expected PDF not found: $built (latexmk exit $latexmkExit)"
}
if ($latexmkExit -ne 0) {
  Write-Host "WARN latexmk exit $latexmkExit but PDF exists - copying anyway"
}
Copy-Item $built $dest -Force
Write-Host "PDF → $dest"
