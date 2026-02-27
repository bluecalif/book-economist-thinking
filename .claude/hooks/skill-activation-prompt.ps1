$ErrorActionPreference = "SilentlyContinue"

Push-Location $PSScriptRoot
try {
    $projectDir = (Resolve-Path "$PSScriptRoot\..\..").Path
    $env:CLAUDE_PROJECT_DIR = $projectDir

    # Read stdin as UTF-8 bytes to preserve Korean characters
    $reader = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), [System.Text.Encoding]::UTF8)
    $stdinContent = $reader.ReadToEnd()
    $reader.Close()

    # Pipe to Node via temp file to avoid encoding corruption
    $tempFile = [System.IO.Path]::GetTempFileName()
    [System.IO.File]::WriteAllText($tempFile, $stdinContent, [System.Text.UTF8Encoding]::new($false))
    Get-Content -Path $tempFile -Encoding UTF8 -Raw | npx tsx skill-activation-prompt.ts
    Remove-Item $tempFile -ErrorAction SilentlyContinue
} finally {
    Pop-Location
}
