<#
.SYNOPSIS
  Run CS Roman (and optional pali_script) unit tests via Docker.

.EXAMPLE
  .\books\cs-roman\scripts\run_tests.ps1
  .\books\cs-roman\scripts\run_tests.ps1 -Module test_cs_roman_transforms
  .\books\cs-roman\scripts\run_tests.ps1 -PaliScript
#>
param(
  [string]$Module,
  [switch]$PaliScript
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Set-Location $RepoRoot

function Invoke-WebPython([string[]]$PyArgs) {
  docker compose exec -T web python @PyArgs
  if ($LASTEXITCODE -ne 0) {
    throw "docker compose exec failed: python $($PyArgs -join ' ')"
  }
}

Write-Host "latexmk / source PDF / DPD tests skip inside the container."

if ($Module) {
  $pattern = if ($Module.EndsWith(".py")) { $Module } else { "$Module.py" }
  Invoke-WebPython @(
    "-m", "unittest", "discover",
    "-s", "books/cs-roman/scripts",
    "-p", $pattern,
    "-v"
  )
} else {
  Invoke-WebPython @(
    "-m", "unittest", "discover",
    "-s", "books/cs-roman/scripts",
    "-p", "test_*.py",
    "-v"
  )
}

if ($PaliScript) {
  Invoke-WebPython @(
    "-m", "unittest", "discover",
    "-s", "packages/pali_script/tests",
    "-v"
  )
}
