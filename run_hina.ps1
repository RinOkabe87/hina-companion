Set-Location -LiteralPath $PSScriptRoot
$env:COQUI_TTS_HOME = Join-Path $PSScriptRoot "models"
$env:TTS_HOME = Join-Path $PSScriptRoot "models"
$env:LOCALAPPDATA = Join-Path $PSScriptRoot "appdata"
$env:HF_HOME = Join-Path $PSScriptRoot "models\huggingface"
$env:TORCH_HOME = Join-Path $PSScriptRoot "models\torch"
$env:PYTHONIOENCODING = "utf-8"
New-Item -ItemType Directory -Force -Path $env:LOCALAPPDATA, $env:HF_HOME, $env:TORCH_HOME | Out-Null
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment not found. Create .venv and install requirements.txt first."
}
& $python (Join-Path $PSScriptRoot "hina.py")
exit $LASTEXITCODE