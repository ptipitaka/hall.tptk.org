<#
.SYNOPSIS
  Extract + fixups + residual gate + headings + prepare TeX for cs-roman
  (Docker web service).

  Prepares both sync and printing drivers/bodies by default. Build PDFs with
  .\scripts\batch_build_volumes.ps1 (-Mode sync|printing|both).

  Fixups and the residual gate are driven by scripts/fixup_manifest.json —
  see docs/fixup_process.md. Do not hardcode new fixup blocks here.

.EXAMPLE
  .\pipeline.ps1
  .\pipeline.ps1 -Volume 01Vin01
  .\pipeline.ps1 -SkipExtract
  .\pipeline.ps1 -PrepareMode printing
#>
param(
  [string[]]$Volume,
  [ValidateSet("sync", "printing", "both")]
  [string]$PrepareMode = "both",
  [switch]$SkipExtract,
  [switch]$SkipFixups,
  [switch]$SkipFixupGate,
  [switch]$SkipHeadings,
  [switch]$SkipPrepare
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $RepoRoot

function Invoke-WebPython([string[]]$PyArgs) {
  docker compose exec -T web python @PyArgs
  if ($LASTEXITCODE -ne 0) {
    throw "docker compose exec failed: python $($PyArgs -join ' ')"
  }
}

if (-not $SkipExtract) {
  $extractArgs = @(
    "books/cs-roman/scripts/extract_cs_roman_pdf.py",
    "books/cs-roman/source",
    "--output-dir", "books/cs-roman/output"
  )
  if ($Volume) {
    foreach ($id in $Volume) {
      Invoke-WebPython @(
        "books/cs-roman/scripts/extract_cs_roman_pdf.py",
        "books/cs-roman/source/${id}.pdf",
        "--output-dir", "books/cs-roman/output"
      )
    }
  } else {
    Invoke-WebPython $extractArgs
  }
}

# JSON / layout fixups from fixup_manifest.json (even when SkipExtract).
if (-not $SkipFixups) {
  if ($Volume) {
    foreach ($id in $Volume) {
      Invoke-WebPython @(
        "books/cs-roman/scripts/run_cs_roman_fixups.py",
        "--pipeline",
        "--volume", $id
      )
    }
  } else {
    Invoke-WebPython @(
      "books/cs-roman/scripts/run_cs_roman_fixups.py",
      "--pipeline"
    )
  }
}

# Fail if gate=strict residuals remain (see docs/fixup_process.md).
if (-not $SkipFixupGate) {
  if ($Volume) {
    foreach ($id in $Volume) {
      Invoke-WebPython @(
        "books/cs-roman/scripts/scan_fixup_residuals.py",
        "--strict",
        "--volume", $id
      )
    }
  } else {
    Invoke-WebPython @(
      "books/cs-roman/scripts/scan_fixup_residuals.py",
      "--strict"
    )
  }
}

if (-not $SkipHeadings) {
  Invoke-WebPython @("books/cs-roman/scripts/batch_cs_roman_headings.py")
}

if (-not $SkipPrepare) {
  $prep = @(
    "books/cs-roman/scripts/batch_prepare_volumes.py",
    "--mode", $PrepareMode
  )
  if ($Volume) {
    foreach ($id in $Volume) {
      $prep += @("--volume", $id)
    }
  }
  Invoke-WebPython $prep
}

Write-Host "Pipeline done. Build PDFs with:"
Write-Host "  cd books/cs-roman"
Write-Host "  .\scripts\batch_build_volumes.ps1"  # sync (default)
Write-Host "  .\scripts\batch_build_volumes.ps1 -Mode printing"
Write-Host "  .\scripts\batch_build_volumes.ps1 -Mode both"
