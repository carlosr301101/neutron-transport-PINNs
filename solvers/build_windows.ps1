# Build the five 2D C solvers for Windows with MSYS2/MinGW-w64.
#
# Usage from an "MSYS2 UCRT64" shell (gcc already on PATH):
#   pwsh -File solvers/build_windows.ps1
#
# From PowerShell, point at the compiler explicitly:
#   pwsh -File solvers/build_windows.ps1 -Gcc "C:\msys64\ucrt64\bin\gcc.exe"
#   pwsh -File solvers/build_windows.ps1 -Gcc (cygpath -w (which gcc))
#
# If -Gcc is omitted the script looks for gcc on PATH and, as a fallback, in
# $env:MSYS2_LOCATION or the standard C:\msys64 installation.
#
# -static links the MinGW runtime so the .exe files do not need
# libgcc_s_seh-1.dll or libwinpthread-1.dll next to them.

param(
    [string]$Gcc = "",
    [string[]]$CFlags = @("-O2", "-static")
)

$ErrorActionPreference = "Stop"

function Resolve-Gcc([string]$Candidate) {
    if ($Candidate) {
        if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $Candidate).Path
        }
        $withExtension = "$Candidate.exe"
        if (Test-Path -LiteralPath $withExtension -PathType Leaf) {
            return (Resolve-Path -LiteralPath $withExtension).Path
        }
        $command = Get-Command $Candidate -ErrorAction SilentlyContinue
        if ($command) {
            return $command.Source
        }
        throw "gcc not found: $Candidate"
    }

    $command = Get-Command gcc -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    foreach ($root in @($env:MSYS2_LOCATION, "C:\msys64")) {
        if (-not $root) {
            continue
        }
        foreach ($environment in @("ucrt64", "mingw64")) {
            $path = Join-Path $root "$environment\bin\gcc.exe"
            if (Test-Path -LiteralPath $path -PathType Leaf) {
                return $path
            }
        }
    }

    throw "gcc not found. Run this script from the 'MSYS2 UCRT64' shell, or pass -Gcc <path-to-gcc.exe>."
}

$gccPath = Resolve-Gcc $Gcc
$runnersDir = Join-Path $PSScriptRoot "runners"
$solvers = @("NTS_DD", "NTS_LD", "NTS_STEP", "NTS_RM_CN", "NTS_RM_LLN")

Write-Host "Using gcc: $gccPath"

foreach ($solver in $solvers) {
    $source = Join-Path $runnersDir "$solver.c"
    $output = Join-Path $runnersDir "$solver.exe"
    Write-Host "Building $solver.exe"
    & $gccPath @CFlags -o $output $source -lm
    if ($LASTEXITCODE -ne 0) {
        throw "Build failed for $solver (exit code $LASTEXITCODE)"
    }
}

Write-Host "OK: $($solvers.Count) binaries written to $runnersDir"
