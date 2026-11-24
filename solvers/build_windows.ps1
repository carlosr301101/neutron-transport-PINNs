# Build the five 2D C solvers for Windows with MSYS2/MinGW-w64.
#
# Usage (from a PowerShell prompt with gcc in PATH, or with -Gcc):
#   pwsh -File solvers/build_windows.ps1
#   pwsh -File solvers/build_windows.ps1 -Gcc "C:\msys64\ucrt64\bin\gcc.exe"
#
# -static links the MinGW runtime so the .exe files do not need
# libgcc_s_seh-1.dll or libwinpthread-1.dll next to them.

param(
    [string]$Gcc = "gcc",
    [string[]]$CFlags = @("-O2", "-static")
)

$ErrorActionPreference = "Stop"

$runnersDir = Join-Path $PSScriptRoot "runners"
$solvers = @("NTS_DD", "NTS_LD", "NTS_STEP", "NTS_RM_CN", "NTS_RM_LLN")

foreach ($solver in $solvers) {
    $source = Join-Path $runnersDir "$solver.c"
    $output = Join-Path $runnersDir "$solver.exe"
    Write-Host "Building $solver.exe"
    & $Gcc @CFlags -o $output $source -lm
    if ($LASTEXITCODE -ne 0) {
        throw "Build failed for $solver (exit code $LASTEXITCODE)"
    }
}

Write-Host "OK: $($solvers.Count) binaries written to $runnersDir"
