import functools
import requests

from . import (
    billingplatform as bp, 
    utils
)
from flask import (
    Blueprint, current_app, flash, redirect, render_template, request, Response, url_for
)
from typing import Any


# Declare blueprint (as 'bk' for BillingKit)
# This blueprint houses organization management page for BillingKit.
# Create and maintain BillingPlatform connections (credentials) and
# other configurations for BillingKit per org.
bk = Blueprint('orgs', __name__, url_prefix='/orgs')


def verify_enabled_connection(view) -> Any:
    """
    Decorator for verifying that the "enabled" connection is set and valid (still exists).
    If there is no connection enabled or no longer exists as an organization, the user is routed back to the Orgs view.
    Otherwise, continue to the desired route/view.
    """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        _config_data: dict = current_app.config['CONFIG']
        _connections: dict = _config_data['CONNECTIONS']
        _enabled_connection: str = _config_data['ENABLED_CONNECTION']

        if _enabled_connection == '':
            flash('There is no connection enabled. Please create and enable a connection.', 'error')
            return redirect(url_for('orgs.index'))

        if _enabled_connection not in _connections:
            flash(f'The current enabled connection ({_enabled_connection}) no longer exists. Please enable a valid connection.', 'error')
            return redirect(url_for('orgs.index'))

        return view(**kwargs)

    return wrapped_view


@bk.route("/")
def index() -> Response | str:
    """
    This route should be the initial page for displaying current BillingPlatform orgs or configured connections.

    :return: The main Orgs view with list of connections and the current enabled connection per config.
    """
    # Get current config data
    config_data: dict = current_app.config['CONFIG']

    return render_template('orgs.jinja',
                           connections=config_data['CONNECTIONS'],
                           enabled_connection=config_data['ENABLED_CONNECTION'])


@bk.route("/refresh-connections")
def refresh_connections() -> Response | str:
    """
    This route is used to refreshing the list of connections listed in the MAIN view.

    :return: The list of connections with the current enabled connection.
    """
    # Get current config data
    config_data: dict = current_app.config['CONFIG']

    return render_template('orgs_refresh_connections.jinja',
                           connections=config_data['CONNECTIONS'],
                           enabled_connection=config_data['ENABLED_CONNECTION'])


@bk.route("/create-connection", methods=["POST"])
def create_connection() -> Response | str:
    """
    This route is for creating new BillingPlatform org connections by filling out a modal form in the UI.
    This org is verified not to already exist before adding to the user's list of existing connections.

    :return: The new org is added to the list of connections if it passes verification then redirects back to Org view.
    """
    current_app.logger.debug(request.form)

    # Get current config data and path to config file for saving back
    config_data: dict = current_app.config['CONFIG']
    config_file_path: str = current_app.config['CONFIG_FILE']

    try:
        connection_id: str = str(hash(request.form['name'])) # Generic hash of the name for 'unique' Id
        connection_name: str = request.form['name']
        connection_url: str = request.form['url']
        connection_username: str = request.form['username']
        connection_password: str = request.form['password']
        connection_client_id: str = request.form['client_id']
        connection_client_secret: str = request.form['client_secret']
        connection_auth_mode: str = request.form['auth_mode']
        connection_auth_version: str = request.form['auth_version']
        connection_rest_version: str = request.form['rest_version']

        # Arguments for requests.Session (verify, cert, etc.)
        connection_request_args: dict = {}
        
        if 'cert_path' in request.form and request.form['cert_path'] != '':
            connection_request_args['verify'] = request.form['cert_path']

        # Build connection record if it does not already exist
        if connection_id in config_data['CONNECTIONS']:
            flash(f'This connection ({connection_name}) already exists and cannot be added.', 'error')
        else:
            connection_record: dict = {
                'id': connection_id,
                'name': connection_name,
                'url': connection_url,
                'username': connection_username,
                'password': connection_password,
                'client_id': connection_client_id,
                'client_secret': connection_client_secret,
                'auth_mode': connection_auth_mode,
                'auth_version': connection_auth_version or "1.0",
                'rest_version': connection_rest_version or "2.0",
                'request_args': connection_request_args
            }

            # Save connection record
            config_data['CONNECTIONS'].update({connection_id: connection_record})
            config_data['ENABLED_CONNECTION'] = connection_id

            # Save global app config (session)
            current_app.config['CONFIG'] = config_data

            # Save app config to file
            utils.save_config(config_file_path, current_app.config['CONFIG'])

            flash(f'The connection ({connection_name}) was successfully created.', 'info')
    except Exception as e:
        flash(f'The connection failed to be created: {e}', 'error')

    return redirect(url_for('orgs.refresh_connections'))


@bk.route("/update_modal/<string:method>/<string:connection_id>")
def update_modal(method: str, connection_id: str) -> str:
    """
    This route returns an 'update' or 'delete' HTML template response for a dynamic modal form.
    HTMX is leveraged to make this request based on the button click for Update or Delete.

    :param method: The method to be performed on the org connection. Is 'update' or 'delete'.
    :param connection_id: The unique Id of the connection.
    :return: An HTML template for rendering the requested method in a modal form.
    """
    # Get current config data
    config_data: dict = current_app.config['CONFIG']
    connection: dict = config_data['CONNECTIONS'][connection_id]

    # Return modal HTML based on method (update or delete)
    if method == 'delete':
        return render_template('orgs_delete_connection.jinja', connection=connection)
    else: # Update
        return render_template('orgs_update_connection.jinja', connection=connection)


@bk.route("/update-connection", methods=["POST"])
def update_connection() -> Response | str:
    """
    This route is for updated and existing BillingPlatform org connections from a modal in the UI.

    :return: The org connection settings are successfully saved and the user is then redirected back to Org view.
    """
    current_app.logger.debug(request.form)
    
    # Get current config data
    config_data: dict = current_app.config['CONFIG']
    config_file_path: str = current_app.config['CONFIG_FILE']

    try:
        connection_id: str = request.form['id']
        connection_name: str = request.form['name']
        connection_url: str = request.form['url']
        connection_username: str = request.form['username']
        connection_password: str = request.form['password']
        connection_client_id: str = request.form['client_id']
        connection_client_secret: str = request.form['client_secret']
        connection_auth_mode: str = request.form['auth_mode']
        connection_auth_version: str = request.form['auth_version']
        connection_rest_version: str = request.form['rest_version']
        
        # Arguments for requests.Session (verify, cert, etc.)
        connection_request_args: dict = {}
        
        if 'cert_path' in request.form and request.form['cert_path'] != '':
            connection_request_args['verify'] = request.form['cert_path']

        # Build connection record
        connection_record: dict = {
            'id': connection_id,
            'name': connection_name,
            'url': connection_url,
            'username': connection_username,
            'password': connection_password,
            'client_id': connection_client_id,
            'client_secret': connection_client_secret,
            'auth_mode': connection_auth_mode,
            'auth_version': connection_auth_version,
            'rest_version': connection_rest_version,
            'request_args': connection_request_args
        }

        # Save connection record
        config_data['CONNECTIONS'].update({connection_id: connection_record})

        # Save global app config
        current_app.config['CONFIG'] = config_data

        # Save app config to file
        utils.save_config(config_file_path, current_app.config['CONFIG'])

        flash(f'The connection ({connection_name}) was successfully updated.', 'info')
    except Exception as e:
        flash(f'The connection ({request.form["name"]}) failed to update: {e}', 'error')

    return redirect(url_for('orgs.refresh_connections'))


@bk.route("/delete-connection", methods=["POST"])
def delete_connection() -> Response | str:
    """
    This route is for deleting and existing BillingPlatform org connections from a modal in the UI.

    :return: The org connection successfully deleted and the user is then redirected back to Org view.
    """
    current_app.logger.debug(request.form)

    # Get current config data
    config_data: dict = current_app.config['CONFIG']
    config_file_path: str = current_app.config['CONFIG_FILE']
    connection_name: str = ''

    try:
        connection_id: str = request.form['id']
        connection_name: str = config_data['CONNECTIONS'][connection_id]['name']
        del config_data['CONNECTIONS'][connection_id]

        # If the connection that was deleted is the current enabled connection, enable the first connection
        if config_data['ENABLED_CONNECTION'] == connection_id:
            # Check to make sure there are any connections left...
            if len(config_data['CONNECTIONS']) > 0:
                first_connection: dict = next(iter(config_data['CONNECTIONS'].values()))
                first_connection_id: str = first_connection['id']
                config_data['ENABLED_CONNECTION'] = first_connection_id

        # Save global app config
        current_app.config['CONFIG'] = config_data

        # Save app config to file
        utils.save_config(config_file_path, current_app.config['CONFIG'])

        flash(f'The connection ({connection_name}) was successfully deleted.', 'info')
    except Exception as e:
        flash(f'The connection ({connection_name}) failed to delete: {e}', 'error')

    return redirect(url_for('orgs.refresh_connections'))


@bk.route("/test-connection/<string:connection_id>")
def test_connection(connection_id: str) -> Response | str:
    """
    This route is for testing a BillingPlatform org connection from the UI.

    :return: The org connection is tested and then redirected back to Org view with a 'success' or 'error' flash.
    """
    # Get current config data
    config_data: dict = current_app.config['CONFIG']
    connection: dict = {}
    connection_name: str = ''

    try:
        # Get unique connection ID
        connection: dict = config_data['CONNECTIONS'][connection_id]
        connection_name: str = connection['name']

        current_app.logger.debug('Testing connection...')

        session: requests.Session = bp.get_session(connection=connection)

        bp.logout(session=session)
        
        flash(f'The connection ({connection_name}) was successfully tested!', 'info')
    except requests.ConnectTimeout:
        flash(f'The connection ({connection_name}) timed out. The API may be temporarily down. Please check the status of your org.', 'error')
    except Exception as e:
        flash(f'The connection ({connection_name}) failed: {e}', 'error')

    return render_template('flash_messages.jinja')


@bk.route("/enable-connection/<string:connection_id>", methods=["POST"])
def enable_connection(connection_id: str) -> Response | str:
    """
    This route is for enabling a BillingPlatform org connection from the UI.

    :return: The org connection is set as the 'ENABLED_CONNECTION' and reflected as such when returned to the UI.
    """
    current_app.logger.debug(request.form)

    # Get current config data
    config_data: dict = current_app.config['CONFIG']
    config_file_path: str = current_app.config['CONFIG_FILE']

    try:
        config_data['ENABLED_CONNECTION'] = connection_id

         # Save global app config
        current_app.config['CONFIG'] = config_data

        # Save app config to file
        utils.save_config(config_file_path, current_app.config['CONFIG'])

    except Exception as e:
        flash(f'The connection failed to activate: {e}', 'error')

    return redirect(url_for('orgs.refresh_connections'))
