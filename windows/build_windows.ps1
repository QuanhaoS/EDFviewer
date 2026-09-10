$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python samples\build_phantom_edf.py
python -m pytest tests
python -m PyInstaller --clean --noconfirm EDFViewer-windows.spec

Write-Host "Built dist\EDFViewer\EDFViewer.exe"
