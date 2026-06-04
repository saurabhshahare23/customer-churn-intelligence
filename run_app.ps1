$ErrorActionPreference = "Stop"

Write-Host "Starting Customer Churn Intelligence Platform..." -ForegroundColor Cyan

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "Python was not found on PATH. Please install Python and try again." -ForegroundColor Red
    exit 1
}

$requirementsPath = Join-Path $PSScriptRoot "requirements.txt"
$minimumPackages = @(
    "streamlit",
    "pandas",
    "numpy",
    "plotly",
    "joblib",
    "scikit-learn",
    "matplotlib"
)

if (Test-Path $requirementsPath) {
    $requirementsContent = Get-Content $requirementsPath | Where-Object { $_.Trim() -ne "" -and -not $_.Trim().StartsWith("#") }
    if ($requirementsContent.Count -gt 0) {
        Write-Host "Installing packages from requirements.txt..." -ForegroundColor Cyan
        python -m pip install -r $requirementsPath
    }
    else {
        Write-Host "requirements.txt is empty. Installing minimum app packages..." -ForegroundColor Yellow
        python -m pip install $minimumPackages
    }
}
else {
    Write-Host "requirements.txt not found. Installing minimum app packages..." -ForegroundColor Yellow
    python -m pip install $minimumPackages
}

Write-Host "Launching Streamlit app..." -ForegroundColor Green
python -m streamlit run "deployment/streamlit/app.py"
