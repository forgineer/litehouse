@echo off
echo Checking for virtual environment...
if exist .venv (
    echo Virtual environment already exists. Enabling and starting BillingKit...

    REM Activate virtual environment
    call .\.venv\Scripts\activate

    REM Start BillingKit
    REM The 'flask' CLI tool is not used for restricted use of 3rd party executables
    REM The run module allows for additinoal arguments to be passed
    REM Argument 1 is the log level and can be set to DEBUG, INFO, WARNING, ERROR, or CRITICAL
    python -m BillingKit.run "INFO"
    echo BillingKit started. Close the Terminal window to end the BillingKit service
) else (
    echo Virtual environment does not exist! Run billingkit-install.bat to create the virtual environment and install.
    pause
)