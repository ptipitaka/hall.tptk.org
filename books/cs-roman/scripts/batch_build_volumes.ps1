<#
.SYNOPSIS
  latexmk every books/cs-roman/volumes/*/tex/main.tex into volumes/<id>/out/<id>.pdf

.EXAMPLE
  .\scripts\batch_build_volumes.ps1
  .\scripts\batch_build_volumes.ps1 -Volume 01Vin01,02Vin02
#>
param(
  [string[]]$Volume = @()
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$ids = @()
if ($Volume.Count -gt 0) {
  $ids = $Volume
} else {
  $ids = Get-ChildItem -Path "volumes" -Directory | ForEach-Object { $_.Name } | Sort-Object
}

$ok = 0
$failed = @()

foreach ($id in $ids) {
  $main = "volumes/$id/tex/main.tex"
  if (-not (Test-Path $main)) {
    Write-Host "SKIP $id (no main.tex)"
    continue
  }
  if (-not (Test-Path "volumes/$id/tex/body.generated.tex")) {
    Write-Host "SKIP $id (no body.generated.tex)"
    continue
  }

  Write-Host "=== Building $id ==="
  # Avoid the name $aux - latexmk/PowerShell can treat it oddly on -outdir=.
  $outDir = Join-Path "build/aux" $id
  if (Test-Path $outDir) {
    Remove-Item -Recurse -Force $outDir
  }
  New-Item -ItemType Directory -Force -Path $outDir | Out-Null
  New-Item -ItemType Directory -Force -Path "volumes/$id/out" | Out-Null

  # Per-volume dirs so TOC .aux from one book cannot corrupt the next.
  # Quote args so PowerShell expands $outDir before latexmk sees them.
  # -f: keep going when TOC/label passes do not stabilize (large volumes).
  & latexmk -lualatex -g -f "-outdir=$outDir" "-auxdir=$outDir" $main
  $built = Join-Path $outDir "main.pdf"
  $dest = "volumes/$id/out/$id.pdf"
  if (-not (Test-Path $built)) {
    Write-Host "FAIL $id (missing $built; latexmk exit $LASTEXITCODE)"
    $failed += $id
    continue
  }
  if ($LASTEXITCODE -ne 0) {
    Write-Host "WARN $id latexmk exit $LASTEXITCODE but PDF exists - copying anyway"
  }
  Copy-Item $built $dest -Force
  Write-Host "PDF -> $dest"
  $ok++
}

Write-Host "Done: $ok ok, $($failed.Count) failed"
if ($failed.Count -gt 0) {
  Write-Host ("Failed: " + ($failed -join ", "))
  exit 1
}
