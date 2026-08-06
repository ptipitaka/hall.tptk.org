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
  python scripts/sync_volume_data.py --volume $Volume
}
if (-not $SkipGenerate) {
  python scripts/generate_cs_roman_tex.py --volume $Volume --mode $Mode
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
& latexmk -lualatex "-outdir=$auxDir" "-auxdir=$auxDir" $main
if ($LASTEXITCODE -ne 0) {
  throw "latexmk failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path $built)) {
  throw "Expected PDF not found: $built"
}
Copy-Item $built $dest -Force
Write-Host "PDF → $dest"
