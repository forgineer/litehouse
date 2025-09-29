import os
import secrets

from . import utils
from flask import Flask


def create_app(log_level: str = 'INFO') -> Flask:
    """
    The main function (app factory) for BillingKit.

    :return: A Flask app (BillingKit)
    """
    # Configure logging
    # This will set the logging format and handlers for the application
    utils.configure_logging(level=log_level)

    # Create and configure the app
    app: Flask = Flask(__name__)

    # Define a default config template for when the app starts up and one is not found on the initial installation
    CONFIG_DATA: dict = {
        'SECRET_KEY': 'dev', # Temporary value
        'CONNECTIONS': {},
        'ENABLED_CONNECTION': '',
        'SAVED_QUERIES': {},
    }

    # Define config file name
    # All configuration for the app will be stored in a local JSON file until when/if the app is eventually hosted.
    CONFIG_FILE_NAME: str = 'config.json'

    # Use the instance path to contain the config (data) file
    CONFIG_FILE_PATH: str = os.path.join(app.instance_path, CONFIG_FILE_NAME)
    app.logger.info(f'Config file path: {CONFIG_FILE_PATH}')

    # Verify if the config file exists. If not, create it based on the template
    if os.path.exists(CONFIG_FILE_PATH):
        app.logger.info('Found config file! Loading...')

        # Read the config file and load the data
        CONFIG_DATA = utils.read_config(CONFIG_FILE_PATH)
        app.logger.info('Config Loaded!')
        app.logger.debug(f'CONFIG_DATA: {CONFIG_DATA}')
    else:
        app.logger.info('Config file not found. Creating...')
        # Generate a random secret key if no configuration file is found
        CONFIG_DATA['SECRET_KEY'] = secrets.token_urlsafe(32)

        # Create the directory if it does not already exist
        # For simplicity, we will use the instance path as defined by Flask
        # This instance path should be created in the 'var' directory of the virtual environment (venv)
        try:
            os.makedirs(app.instance_path)
        except OSError as e:
            app.logger.error(e)

        # Write the config file based on the template and generated secret key
        utils.save_config(CONFIG_FILE_PATH, CONFIG_DATA)
        app.logger.info('Config created!')
        app.logger.debug(f'CONFIG_DATA: {CONFIG_DATA}')
    
    # Define downloads path in instance path
    # The downloads folder will contain all exported data files (CSV, Excel, JSON) as a temporary location
    # before being pushed back to the user's local OS' Downloads directory
    DOWNLOADS_FILE_PATH: str = os.path.join(app.instance_path, 'downloads')
    app.logger.info(f'Downloads file path: {DOWNLOADS_FILE_PATH}')

    # If the downloads directory exists, delete all files within (reset), else create the folder.
    if os.path.exists(DOWNLOADS_FILE_PATH):
        # Loop through and delete all files in the directory
        for filename in os.listdir(DOWNLOADS_FILE_PATH):
            downloads_file: str = os.path.join(DOWNLOADS_FILE_PATH, filename)

            try:
                os.remove(downloads_file)
                app.logger.info(f'Deleting file: {downloads_file}')
            except OSError as e:
                app.logger.warning(f'Error deleting files: {downloads_file} - {e}')
    else:
        # Create the 'downloads' directory if not already exists in the instance path
        try:
            os.makedirs(DOWNLOADS_FILE_PATH)
            app.logger.info("The 'downloads' path has been created!")
        except OSError as e:
            app.logger.error(e)

    # Map application config for Flask so that it can be accessed between blueprints/views
    app.config.from_mapping(
        SECRET_KEY=CONFIG_DATA['SECRET_KEY'],
        CONFIG=CONFIG_DATA,
        CONFIG_FILE=CONFIG_FILE_PATH
    )

    # Import BillingKit blueprint modules
    from . import orgs, query

    # Register blueprints
    app.register_blueprint(orgs.bk) # BillingPlatform org connections
    app.register_blueprint(query.bk) # Make Ad-hoc queries to BillingPlatform

    # Define the index entry point (default page): The BillingKit Org Connections page
    app.add_url_rule('/', endpoint='orgs.index')

    return app
