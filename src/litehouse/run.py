"""
This module exists as a workaround for when the flask.exe is restricted from execution by Cognizant or client
policies on the local workstation where BillingKit is installed with the billingkit-start.bat script.

This script can also be executed from the virtual environment with 'python -m BillingKit.run'.
"""
import sys

from .app import create_app

billingkit = create_app(*sys.argv[1:])

if __name__ == '__main__':
    billingkit.run()
