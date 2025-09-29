@echo off
REM Create virtual environment
echo Checking for virtual environment...
if exist .venv (
    echo Virtual environment already exists. Enabling...
) else (
    echo Creating virtual environment...
    python -m venv .venv
    echo Virtual environment created!
    pause
)

REM Activate virtual environment
echo Activating virtual environment...
call .\.venv\Scripts\activate

REM Install BillingKit package with dependencies
echo Installing BillingKit...
pip install .

echo BillingKit install complete. Run billingkit-start.bat to start BillingKit.