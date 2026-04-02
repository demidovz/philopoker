$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

if ($args.Count -eq 0) {
    python .\play_match.py --mode openrouter --rounds 2 --thesis-id free_will
} else {
    python .\play_match.py @args
}
