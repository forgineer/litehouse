import json

from logging.config import dictConfig

def configure_logging(level: str = 'INFO') -> None:
    """
    Configure the logging for the application.
    This sets up the logging format and handlers.
    """
    # Setup/modify logging here prior to app startup
    # Change to DEBUG when necessary and restart the application to trace reported issues
    dictConfig({
        'version': 1,
        'formatters': {
            'default': {
                'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
            }
        },
        'handlers': {
            'wsgi': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://flask.logging.wsgi_errors_stream',
                'formatter': 'default'
            }
        },
        'root': {
            'level': level,
            'handlers': ['wsgi']
        }
    })


def read_config(config_file_path: str) -> dict:
    """
    Read the configuration from a JSON file.

    :param config_file_path: The file path to the config file (instance folder).
    :return: The configuration data as a dictionary.
    """
    with open(config_file_path, 'r') as config_file:
        return json.load(config_file)


def save_config(config_file_path: str, config_data: dict) -> None:
    """
    Save the current config to a file (JSON) after a change.

    :param config_file_path: The file path to the config file (instance folder).
    :param config_data: The configuration data as a dictionary.
    :return: None
    """
    with open(config_file_path, 'w') as config_file:
        json.dump(config_data, config_file, indent=4)
