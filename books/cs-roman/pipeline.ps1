<#
.SYNOPSIS
  Extract + headings + prepare TeX for cs-roman volumes (Docker web service).

  Prepares both sync and printing drivers/bodies by default. Build PDFs with
  .\scripts\batch_build_volumes.ps1 (-Mode sync|printing|both).

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

  # Re-bind orphan footnotes left in older artifacts / edge shapes the extract
  # pass should cover going forward. Never rely on one-off JSON patches --
  # those vanish on the next extract (see scripts/scratch/_fix_01vin01_orphans.py).
  if ($Volume) {
    foreach ($id in $Volume) {
      Invoke-WebPython @(
        "books/cs-roman/scripts/fixup_orphan_footnote_callouts.py",
        "--volume", $id
      )
    }
  } else {
    Invoke-WebPython @(
      "books/cs-roman/scripts/fixup_orphan_footnote_callouts.py",
      "--all"
    )
  }

  # PDF U+23AF → en-dash (Sarabun has no glyph). Newer extract normalizes;
  # repair any leftover in stored JSON.
  if ($Volume) {
    foreach ($id in $Volume) {
      Invoke-WebPython @(
        "books/cs-roman/scripts/fixup_printable_dashes.py",
        "--volume", $id
      )
    }
  } else {
    Invoke-WebPython @(
      "books/cs-roman/scripts/fixup_printable_dashes.py",
      "--all"
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