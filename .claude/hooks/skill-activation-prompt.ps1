$ErrorActionPreference = "Stop"

Push-Location "$env:CLAUDE_PROJECT_DIR\.claude\hooks"
try {
    $stdinContent = [Console]::In.ReadToEnd()
    $stdinContent | npx tsx skill-activation-prompt.ts
} finally {
    Pop-Location
}
