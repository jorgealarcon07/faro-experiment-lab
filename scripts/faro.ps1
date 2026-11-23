$ErrorActionPreference = "Stop"
python -m faro_exp.cli @args
exit $LASTEXITCODE
