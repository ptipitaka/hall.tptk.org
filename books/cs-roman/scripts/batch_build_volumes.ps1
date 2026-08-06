<#
.SYNOPSIS
  latexmk every cs-roman volume into volumes/<id>/out/.

.EXAMPLE
  .\scripts\batch_build_volumes.ps1
  .\scripts\batch_build_volumes.ps1 -Volume 01Vin01,02Vin02
  .\scripts\batch_build_volumes.ps1 -Mode printing -Volume 01Vin01
  .\scripts\batch_build_volumes.ps1 -Mode both -Volume 01Vin01,02Vin02
#>
param(
  [string[]]$Volume = @(),
  [ValidateSet("sync", "printing", "both")]
  [string]$Mode = "sync"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$ids = @()
if ($Volume.Count -gt 0) {
  $ids = $Volume
} else {
  $ids = Get-ChildItem -Path "volumes" -Directory |
    Where-Object { $_.Name -notlike "_*" } |
    ForEach-Object { $_.Name } |
    Sort-Object
}

$modes = @()
if ($Mode -eq "both") {
  $modes = @("sync", "printing")
} else {
  $modes = @($Mode)
}

$ok = 0
$failed = @()

foreach ($id in $ids) {
  foreach ($buildMode in $modes) {
    if ($buildMode -eq "printing") {
      $main = "volumes/$id/tex/main.printing.tex"
      $body = "volumes/$id/tex/body.printing.generated.tex"
      $outDir = Join-Path "build/aux/printing" $id
      $builtName = "main.printing.pdf"
      $dest = "volumes/$id/out/$id.printing.pdf"
    } else {
      $main = "volumes/$id/tex/main.tex"
      $body = "volumes/$id/tex/body.generated.tex"
      $outDir = Join-Path "build/aux" $id
      $builtName = "main.pdf"
      $dest = "volumes/$id/out/$id.pdf"
    }

    if (-not (Test-Path $main)) {
      Write-Host "SKIP $id/$buildMode (no $(Split-Path $main -Leaf))"
      continue
    }
    if (-not (Test-Path $body)) {
      Write-Host "SKIP $id/$buildMode (no $(Split-Path $body -Leaf))"
      continue
    }

    Write-Host "=== Building $id ($buildMode) ==="
    if (Test-Path $outDir) {
      Remove-Item -Recurse -Force $outDir
    }
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    New-Item -ItemType Directory -Force -Path "volumes/$id/out" | Out-Null

    # Per-volume dirs so TOC .aux from one book cannot corrupt the next.
    # Quote args so PowerShell expands $outDir before latexmk sees them.
    # -f: keep going when TOC/label passes do not stabilize (large volumes).
    & latexmk -lualatex -g -f "-outdir=$outDir" "-auxdir=$outDir" $main
    $built = Join-Path $outDir $builtName
    if (-not (Test-Path $built)) {
      Write-Host "FAIL $id/$buildMode (missing $built; latexmk exit $LASTEXITCODE)"
      $failed += "$id/$buildMode"
      continue
    }
    if ($LASTEXITCODE -ne 0) {
      Write-Host "WARN $id/$buildMode latexmk exit $LASTEXITCODE but PDF exists - copying anyway"
    }
    Copy-Item $built $dest -Force
    Write-Host "PDF -> $dest"
    $ok++
  }
}

Write-Host "Done: $ok ok, $($failed.Count) failed"
if ($failed.Count -gt 0) {
  Write-Host ("Failed: " + ($failed -join ", "))
  exit 1
}
