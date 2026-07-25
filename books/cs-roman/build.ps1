<#
.SYNOPSIS
  Build a cs-roman Thai TeX volume (LuaLaTeX).

.EXAMPLE
  .\build.ps1
  .\build.ps1 -Volume 01Vin01
  .\build.ps1 -Volume 01Vin01 -SkipGenerate
#>
param(
  [string]$Volume = "01Vin01",
  [switch]$SkipGenerate,
  [switch]$SkipSync
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $SkipSync) {
  python scripts/sync_volume_data.py --volume $Volume
}
if (-not $SkipGenerate) {
  python scripts/generate_cs_roman_tex.py --volume $Volume
}

$main = "volumes/$Volume/tex/main.tex"
if (-not (Test-Path $main)) {
  throw "Missing $main"
}

New-Item -ItemType Directory -Force -Path "build/aux" | Out-Null
New-Item -ItemType Directory -Force -Path "volumes/$Volume/out" | Out-Null

# Avoid -jobname=$Name — latexmk treats $Name as its own variable.
& latexmk -lualatex $main
if ($LASTEXITCODE -ne 0) {
  throw "latexmk failed with exit code $LASTEXITCODE"
}

$built = "build/aux/main.pdf"
$dest = "volumes/$Volume/out/$Volume.pdf"
if (-not (Test-Path $built)) {
  throw "Expected PDF not found: $built"
}
Copy-Item $built $dest -Force
Write-Host "PDF → $dest"
