param(
    [switch]$NoAuto
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Assistant = Join-Path $Root "terraform_assistant.py"

if (-not (Test-Path $Assistant)) {
    throw "terraform_assistant.py introuvable dans $Root"
}

function Test-PythonExe {
    param(
        [string]$Exe,
        [string[]]$PrefixArgs = @()
    )

    try {
        $output = & $Exe @PrefixArgs --version 2>&1
        return ($LASTEXITCODE -eq 0 -and (($output -join "`n") -match "^Python 3\."))
    } catch {
        return $false
    }
}

function Get-PythonCommand {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py -and (Test-PythonExe -Exe $py.Source -PrefixArgs @("-3"))) {
        return @($py.Source, "-3")
    }

    foreach ($name in @("python", "python3")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and (Test-PythonExe -Exe $cmd.Source)) {
            return @($cmd.Source)
        }
    }

    $candidateRoots = @(
        "$env:LOCALAPPDATA\Programs\Python",
        "$env:ProgramFiles\Python312",
        "$env:ProgramFiles\Python311",
        "${env:ProgramFiles(x86)}\Python312",
        "${env:ProgramFiles(x86)}\Python311"
    ) | Where-Object { $_ -and (Test-Path $_) }

    foreach ($rootPath in $candidateRoots) {
        $pythonExe = Get-ChildItem -Path $rootPath -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($pythonExe -and (Test-PythonExe -Exe $pythonExe.FullName)) {
            return @($pythonExe.FullName)
        }
    }

    return @()
}

function Install-Python {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "Python est absent et winget est introuvable. Installe Python 3 puis relance ce script."
    }

    Write-Host ""
    Write-Host "Installation de Python 3.12 via winget..."
    & $winget.Source install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Installation Python via winget echouee."
    }
}

$python = @(Get-PythonCommand)

if ($python.Count -eq 0) {
    Write-Host "Python 3 est introuvable ou pointe vers le raccourci Microsoft Store."
    $answer = Read-Host "Installer Python 3 automatiquement avec winget ? [Y/n]"
    if ($answer -and -not $answer.ToLower().StartsWith("y") -and -not $answer.ToLower().StartsWith("o")) {
        throw "Python 3 est requis pour lancer l'assistant."
    }

    Install-Python
    $python = @(Get-PythonCommand)

    if ($python.Count -eq 0) {
        throw "Python semble installe mais pas visible dans ce terminal. Ferme/reouvre PowerShell puis relance .\start-assistant.ps1"
    }
}

$pythonExe = $python[0]
$pythonPrefixArgs = @()
if ($python.Count -gt 1) {
    $pythonPrefixArgs = $python[1..($python.Count - 1)]
}

$assistantArgs = @($Assistant)
if (-not $NoAuto) {
    $assistantArgs += "--auto"
}

Set-Location $Root
$allPythonArgs = @()
$allPythonArgs += $pythonPrefixArgs
$allPythonArgs += $assistantArgs
& $pythonExe @allPythonArgs
exit $LASTEXITCODE
