<#
.SYNOPSIS
  Sequentially regenerate matika.json/segments (headings) + rebuild sync+printing
  PDFs for a list of cs-roman volumes, in order. Continues past per-volume
  failures and writes a running log.
#>
param(
  [string[]]$Volumes,
  [string]$VolumesFile = "",
  [string]$LogPath = "C:/tmp/run_all_volumes.log"
)

if ($VolumesFile -ne "") {
  $Volumes = Get-Content $VolumesFile | Where-Object { $_.Trim() -ne "" }
}

$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = "utf-8"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Log($msg) {
  $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $msg
  Write-Host $line
  Add-Content -Path $LogPath -Value $line -Encoding utf8
}

Log "=== Starting run for $($Volumes.Count) volumes: $($Volumes -join ', ') ==="

foreach ($vol in $Volumes) {
  Log "--- $vol : headings/matika ---"
  python scripts/assign_cs_roman_heading_levels.py "output/$vol.segments.json" *>> $LogPath
  if ($LASTEXITCODE -ne 0) {
    Log "FAIL $vol : assign_cs_roman_heading_levels.py exit $LASTEXITCODE"
    continue
  }

  Log "--- $vol : build sync ---"
  powershell -File .\build.ps1 -Volume $vol *>> $LogPath
  if ($LASTEXITCODE -ne 0) {
    Log "FAIL $vol : build sync exit $LASTEXITCODE"
  } else {
    Log "OK $vol : sync PDF built"
  }

  Log "--- $vol : build printing ---"
  powershell -File .\build.ps1 -Volume $vol -Mode printing *>> $LogPath
  if ($LASTEXITCODE -ne 0) {
    Log "FAIL $vol : build printing exit $LASTEXITCODE"
  } else {
    Log "OK $vol : printing PDF built"
  }

  Log "=== DONE $vol ==="
}

Log "=== ALL VOLUMES COMPLETE ==="
