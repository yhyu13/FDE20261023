$ErrorActionPreference = 'Stop'
$Py = 'C:\Users\24717\AppData\Local\Programs\Python\Python310\python.exe'
& $Py -B "$PSScriptRoot\produce.py" --input-dir "$PSScriptRoot\inputs" --engine-dir "$PSScriptRoot\engine" --stage all
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
