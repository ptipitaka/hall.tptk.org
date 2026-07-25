<#
.SYNOPSIS
  Extract + headings + prepare TeX for cs-roman volumes (Docker web service).

.EXAMPLE
  .\pipeline.ps1
  .\pipeline.ps1 -Volume 01Vin01
  .\pipeline.ps1 -SkipExtract
#>
param(
  [string[]]$Volume,
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
        "books/cs-roman/source/$id.pdf",
        "--output-dir", "books/cs-roman/output"
      )
    }
  } else {
    Invoke-WebPython $extractArgs
  }
}

if (-not $SkipHeadings) {
  Invoke-WebPython @("books/cs-roman/scripts/batch_cs_roman_headings.py")
}

if (-not $SkipPrepare) {
  $prep = @("books/cs-roman/scripts/batch_prepare_volumes.py")
  if ($Volume) {
    foreach ($id in $Volume) {
      $prep += @("--volume", $id)
    }
  }
  Invoke-WebPython $prep
}

Write-Host "Pipeline done. Build PDFs with: .\scripts\batch_build_volumes.ps1"
