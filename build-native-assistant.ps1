$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Csc = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"

if (-not (Test-Path $Csc)) {
    throw "csc.exe introuvable. Impossible de compiler l'application native Windows."
}

$Source = Join-Path $Root "NativeAssistant\Program.cs"
$Output = Join-Path $Root "IaC-Assistant.exe"

if (-not (Test-Path $Source)) {
    throw "Source introuvable: $Source"
}

& $Csc `
    /nologo `
    /target:winexe `
    /platform:anycpu `
    /out:$Output `
    /reference:System.dll `
    /reference:System.Core.dll `
    /reference:System.Drawing.dll `
    /reference:System.Windows.Forms.dll `
    $Source

if ($LASTEXITCODE -ne 0) {
    throw "Compilation echouee."
}

Write-Host "Application compilee: $Output"
