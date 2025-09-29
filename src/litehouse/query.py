import os
import numpy as np
import pandas as pd
import re
import requests

from . import (
    billingplatform as bp, 
    utils
)
from .orgs import verify_enabled_connection
from datetime import datetime
from flask import (
    current_app, 
    Blueprint, 
    flash, 
    redirect, 
    render_template, 
    request, 
    Response, 
    send_file, 
    session, 
    url_for
)


# Declare blueprint (as 'bk' for BillingKit)
# This blueprint houses all endpoints related to querying data.
# Query BillingPlatform entities using (BP)SQL supported statements or
# retrieve data in bulk via the Bulk Data Backup view.
bk = Blueprint('query', __name__, url_prefix='/query')


def get_data(session: requests.Session, sql: str, limit: int, offset: int) -> list[dict]:
    """
    Retrieves the data based on the user's input of the query form. This depends on the entry of a
    'Limit' and/or 'Offset' in the query that will determine the REST call made to BillingPlatform.

    :param session: The user session object used in authentication of the REST service(s).
    :param sql: A SQL statement string from the query input form.
    :param limit: A numerical limit of returned rows from the SQL query results.
    :param offset: A numerical offset for where the SQL query should begin retrieving results.
    :return: A list of dictionaries (records) based on the query results from BillingPlatform.
    """
    _data: list[dict] = []

    # If using the Limit or Offset inputs, use the lower level 'query' method
    # Otherwise, use the 'bulk_query' method for ALL query results.
    if limit > 0 or offset > 0:
        # using the 'query' method limits all query results to 10,000 rows
        # This is a BillingPlatform limitation
        _data = bp.query(session=session, sql=sql, offset_start=offset, offset_end=limit)
    else:
        _data = bp.bulk_query(session=session, sql=sql)

    return _data


def get_query_entity(query: str) -> str:
    """
    Parses the SQL query string to determine the root entity in the FROM clause.

    :param query: The SQL query string to parse.
    :return: The root entity in the FROM clause of the query, or "(complex query)" if a driver table is detected.
    """
    # Remove comments to avoid confusion with subqueries that might be inside comments.
    query = re.sub(r'--.*?(\n|$)', '', query)  # Remove single-line comments.
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)  # Remove multi-line comments.

    # Find the FROM clause.
    from_match = re.search(r'FROM\s+(.+?)(?:\s+WHERE|\s+GROUP BY|\s+ORDER BY|\s+LIMIT|\s+FOR UPDATE|\s+;|$)', query, flags=re.IGNORECASE | re.DOTALL)

    complex_query_value: str = '(complex query)'

    if from_match:
        from_clause = from_match.group(1).strip()

        # Check for nested SELECT within the FROM clause.
        if from_clause.startswith('('):
            if re.search(r'^\(SELECT', from_clause, flags=re.IGNORECASE):
                return complex_query_value

        # Extract the table name if it's a simple table.
        table_match = re.search(r'^(\w+)', from_clause, flags=re.IGNORECASE)
        if table_match:
            return table_match.group(1).upper()

    return complex_query_value


@bk.route("/")
@verify_enabled_connection
def index() -> Response | str:
    """
    This route should be the page for displaying the initial BillingPlatform query form.
    The listed entities are based on the current enabled connection.

    :return: The main Entities view with the list of BillingPlatform objects.
    """
    # Get current config data and enabled connection
    _config_data: dict = current_app.config['CONFIG']
    _enabled_connection: str = _config_data['ENABLED_CONNECTION']
    _connection: dict = _config_data['CONNECTIONS'][_enabled_connection]
    _current_query: str = session.get('CURRENT_QUERY', '')
    _current_query_limit: int = session.get('CURRENT_QUERY_LIMIT', 0)
    _current_query_offset: int = session.get('CURRENT_QUERY_OFFSET', 0)
    _session: requests.Session = requests.Session()
    _data: list[dict] = []

    # Verify/get session
    try:
        _session = bp.get_session(connection=_connection)
    except requests.ConnectTimeout:
        flash('The connection timed out. The API may be temporarily down. Please check the status of your org.', 'error')
        return render_template('flash_messages.jinja')
    except Exception as e:
        flash('Unable to authenticate (create session). Please verify connection settings.', 'error')
        return redirect(url_for('orgs.index'))

    # Query entities
    try:
        _sql: str = 'SELECT Id, EntityLabel, EntityName, SystemFlag FROM ENTITY ORDER BY EntityLabel'
        _data = bp.query(session=_session, sql=_sql)
    except Exception as e:
        flash(f'Unable to get entities list. Please verify connection or org API settings. {e}', 'error')
        return redirect(url_for('orgs.index'))
    
    # Logout and/or close the session
    bp.logout(session=_session)

    # Return the initial entities template, the enabled connection, the entity data.
    return render_template('query.jinja', connection=_connection, entities=_data, current_query=_current_query, 
                           current_query_limit=_current_query_limit, current_query_offset=_current_query_offset)


@bk.route("/entities")
def entities() -> Response | str:
    """
    This route is for returning (or swapping) the current list of entities within a BillingPlatform org.

    :return: A hypermedia response containing the list of BillingPlatform entities with additional detail.
    """
    # Get current config data and enabled connection
    _config_data: dict = current_app.config['CONFIG']
    _enabled_connection: str = _config_data['ENABLED_CONNECTION']
    _connection: dict = _config_data['CONNECTIONS'][_enabled_connection]
    _session: requests.Session = requests.Session()
    _data: list[dict] = []

    # Verify/get session
    try:
        _session = bp.get_session(connection=_connection)
    except requests.ConnectTimeout:
        flash('The connection timed out. The API may be temporarily down. Please check the status of your org.', 'error')
        return render_template('flash_messages.jinja')
    except:
        flash('Unable to authenticate (create session). Please verify connection settings.', 'error')
        return redirect(url_for('orgs.index'))

    # Query entities
    try:
        _sql: str = 'SELECT Id, EntityLabel, EntityName, SystemFlag FROM ENTITY ORDER BY EntityLabel'
        _data = bp.query(session=_session, sql=_sql)
    except:
        flash('Unable to get entities list. Please verify connection or org API settings.', 'error')
        return redirect(url_for('orgs.index'))

    # Logout and/or close the session
    bp.logout(session=_session)

    # Return the initial entities template, the enabled connection, the entity data.
    return render_template('query_entities.jinja', connection=_connection, entities=_data)


@bk.route("/entity-fields/<int:entity_id>/<string:entity_name>/<string:entity_label>")
def entity_fields(entity_id: int, entity_name: str, entity_label: str) -> Response | str:
    """
    This route is for returning (swapping) a list of entity fields from a selected entity on the initial Entities view.

    :param entity_id: The unique entity Id (key).
    :param entity_name: The name of the entity.
    :param entity_label: The entity label (human-readable)
    :return: A hypermedia response containing the list of BillingPlatform entity fields with additional detail.
    """
    # Get current config data and enabled connection
    _config_data: dict = current_app.config['CONFIG']
    _enabled_connection: str = _config_data['ENABLED_CONNECTION']
    _connection: dict = _config_data['CONNECTIONS'][_enabled_connection]
    _session: requests.Session = requests.Session()
    _data: list[dict] = []

    # Verify/get session
    try:
        _session = bp.get_session(connection=_connection)
    except requests.ConnectTimeout:
        flash('The connection timed out. The API may be temporarily down. Please check the status of your org.', 'error')
        return render_template('flash_messages.jinja')
    except:
        flash('Unable to authenticate (create session). Please verify connection settings.', 'error')
        return redirect(request.referrer)

    # Query entity fields
    try:
        _entity_fields_sql: str = f"""
            SELECT
                Id
                , FieldLabel
                , FieldName
                , DataType
                , DataLength
                , DefaultValue
                , ExternalKeyFlag
                , SystemFlag
                , UniqueField
                , RequiredFlag
                , ReferencedEntityIdObj.EntityName
                , (SELECT ListValue FROM ENTITY_FIELD_PICK_LIST.EntityFieldIdObj)
            FROM ENTITY_FIELD WHERE EntityId = {entity_id}
            AND DataType NOT IN ('DIVIDER', 'EMBEDDED_LIST', 'EMBEDDED_LIST_ADD',
            'EXTENSION_WIDGET', 'LABEL', 'LISTFORM', 'QUICK_LINK', 'RELATED_LIST')
            AND Status = 'ACTIVE' ORDER BY FieldLabel
        """

        _data = bp.query(session=_session, sql=_entity_fields_sql)
    except:
        flash('Unable to get entity fields list. Please verify connection or org API settings.', 'error')
        return render_template('flash_messages.jinja')

    # Logout and/or close the session
    bp.logout(session=_session)

    # Return the HTML rendered list of entities, entity name, entity label, and the fields (metadata).
    return render_template('query_entity_fields.jinja', connection=_connection, entity_name=entity_name, 
                           entity_label=entity_label, entity_fields=_data)


@bk.route("/query-data", methods=["POST"])
def query_data():
    """
    This route is for submitting the SQL query form and returning the BillingPlatform data in a table view.

    :return: A view of the returned BillingPlatform data from the submitted SQL.
    """
    current_app.logger.debug(request.form)

    # Get current config data and enabled connection
    _config_data: dict = current_app.config['CONFIG']
    _enabled_connection: str = _config_data['ENABLED_CONNECTION']
    _connection: dict = _config_data['CONNECTIONS'][_enabled_connection]
    _session: requests.Session = requests.Session()
    _data: list[dict] = []
    _data_df: pd.DataFrame | None = None

    # Setup key inputs and
    _limit: int = 0
    _offset: int = 0
    _query_text: str = ''
    _saved_query: bool = False

    for key, value in request.form.items():
        # The limit and offset will come in as string values when the form is submitted
        # They are converted to an integer here if given a value.
        if key.startswith('limit'):
            _limit = 0 if value == '' else int(value)

        if key.startswith('offset'):
            _offset = 0 if value == '' else int(value)

        if key.startswith('query_text'):
            _query_text = value

        if key.startswith('query_name'):
            _saved_query = True

    # Save current query attributes in the gloabl session object
    session['CURRENT_QUERY'] = _query_text
    session['CURRENT_QUERY_LIMIT'] = _limit
    session['CURRENT_QUERY_OFFSET'] = _offset

    # Retrieve the query (FROM) entity
    _query_entity: str = get_query_entity(query=_query_text)

    # Verify/get session
    try:
        _session = bp.get_session(connection=_connection)
    except requests.ConnectTimeout:
        flash('The connection timed out. The API may be temporarily down. Please check the status of your org.', 'error')
        return render_template('flash_messages.jinja')
    except:
        flash('Unable to authenticate (create session). Please verify connection settings.', 'error')
        return redirect(url_for('orgs.index'))

    # Perform the query
    try:
        _data = get_data(session=_session, sql=_query_text, limit=_limit, offset=_offset)
        _data_df = pd.DataFrame(_data)
    except Exception as e:
        if 'No data found for query.' in str(e):
            flash(f'{e}', 'warning')
        else:
            flash(f'Unable to query data. {e}', 'error')

        return render_template('flash_messages.jinja')

    # Replace any None values with NaN.
    # When the JSON response is converted to a dict, the null values are converted to a None value
    # This None value will be preserved in the HTML table if not changed
    _data_df.replace({None: np.nan}, inplace=True)

    # Convert data to HTML table
    _html_data: str = _data_df.to_html(index=False,
                                       na_rep='',
                                       justify='left',
                                       border=0,
                                       table_id='data_table',
                                       classes=['cell-border', 'table', 'table-bordered', 'table-hover', 'table-striped'])

    # Logout and/or close the session
    bp.logout(session=_session)

    # Return query data view with the current connection, original SQL query text, and the HTML table data.
    return render_template('query_data.jinja', connection=_connection, query_entity=_query_entity, query_text=_query_text, 
                           query_limit=_limit, query_offset=_offset, saved_query=_saved_query, data=_html_data)


@bk.route("/refresh-data")
def refresh_data():
    """
    This route is for refreshes the query data to display any new or changed records.

    :return: An updated HTML table of the returned BillingPlatform data from the submitted SQL.
    """
    # Get current config data and enabled connection
    _config_data: dict = current_app.config['CONFIG']
    _enabled_connection: str = _config_data['ENABLED_CONNECTION']
    _connection: dict = _config_data['CONNECTIONS'][_enabled_connection]
    _session: requests.Session = requests.Session()
    _data: list[dict] = []
    _data_df: pd.DataFrame | None = None

    # Capture the current query text, limit, and offset from the session
    _current_query: str = session['CURRENT_QUERY']
    _current_query_limit: int = session['CURRENT_QUERY_LIMIT']
    _current_query_offset: int = session['CURRENT_QUERY_OFFSET']

    # Retrieve the query (FROM) entity
    _query_entity: str = get_query_entity(query=_current_query)

    # Verify/get session
    try:
        _session = bp.get_session(connection=_connection)
    except requests.ConnectTimeout:
        flash('The connection timed out. The API may be temporarily down. Please check the status of your org.', 'error')
        return render_template('flash_messages.jinja')
    except:
        flash('Unable to authenticate (create session). Please verify connection settings.', 'error')
        return redirect(url_for('orgs.index'))

    # Perform the query
    try:
        _data = get_data(session=_session, sql=_current_query, limit=_current_query_limit, offset=_current_query_offset)
        _data_df = pd.DataFrame(_data)
    except Exception as e:
        if 'No data found for query.' in str(e):
            flash(f'{e}', 'warning')
        else:
            flash(f'Unable to query data. {e}', 'error')

        return render_template('flash_messages.jinja')

    # Replace any None values with NaN.
    # When the JSON response is converted to a dict, the null values are converted to a None value
    # This None value will be preserved in the HTML table if not changed
    _data_df.replace({None: np.nan}, inplace=True)

    # Convert data to HTML table
    _html_data: str = _data_df.to_html(index=False, 
                                       na_rep='', 
                                       justify='left', 
                                       border=0, 
                                       table_id='data_table', 
                                       classes=['cell-border', 'table', 'table-bordered', 'table-hover', 'table-striped'])

    # Logout and/or close the session
    bp.logout(session=_session)

    # Return query data view with the current connection, original SQL query text, and the HTML table data.
    return render_template('query_data_refresh.jinja', connection=_connection, data=_html_data)


@bk.route("/download-query-data/<string:file_type>")
def download_query_data(file_type: str):
    """
    This route is called to retrieve the data and export it as one of three file types - CSV, Excel (xlsx), or JSON.

    :return: Returns a CSV, Excel (xlsx) or JSON formatted file back to the user.
    """
    # Check file type before executing anything
    if file_type not in ['csv', 'xlsx', 'json']:
        flash('Unsupported file format for download of query data.', 'error')
        return redirect(url_for('query.index'))

    # Get current config data and enabled connection
    _config_data: dict = current_app.config['CONFIG']
    _enabled_connection: str = _config_data['ENABLED_CONNECTION']
    _connection: dict = _config_data['CONNECTIONS'][_enabled_connection]
    _session: requests.Session = requests.Session()
    _data: list[dict] = []
    _data_df: pd.DataFrame | None = None

    # Capture the current query text, limit, and offset from the session
    _current_query: str = session['CURRENT_QUERY']
    _current_query_limit: int = session['CURRENT_QUERY_LIMIT']
    _current_query_offset: int = session['CURRENT_QUERY_OFFSET']


    # Verify/get session
    try:
        _session = bp.get_session(connection=_connection)
    except requests.ConnectTimeout:
        flash('The connection timed out. The API may be temporarily down. Please check the status of your org.', 'error')
        return redirect(url_for('orgs.index'))
    except:
        flash('Unable to authenticate (create session). Please verify connection settings.', 'error')
        return redirect(url_for('orgs.index'))

    # Query the data
    try:
        _data = get_data(session=_session, sql=_current_query, limit=_current_query_limit, offset=_current_query_offset)
        _data_df = pd.DataFrame(_data)
    except Exception as e:
        flash(f'Unable to query data. {e}', 'error')
        return redirect(url_for('orgs.index'))

    # Logout and/or close the session
    bp.logout(session=_session)

    # Generate filename with date/time stamp
    _now = datetime.now()
    _file_name: str = f'billingkit_query_{_now.strftime("%Y%m%d%H%M%S")}.{file_type}'
    _download_file_path: str = os.path.join(current_app.instance_path, 'downloads', _file_name)

    if file_type == 'csv':
        # Generate the CSV file
        _data_df.to_csv(path_or_buf=_download_file_path, index=False)

    elif file_type == 'xlsx':
        # Generate the Excel (xlsx) file
        with pd.ExcelWriter(_download_file_path) as writer:
            _data_df.to_excel(excel_writer=writer, index=False)

    elif file_type == 'json':
        # Generate the JSON file
        _data_df.to_json(path_or_buf=_download_file_path, index=False, orient='records', indent=4)

    return send_file(path_or_file=_download_file_path, as_attachment=True)


@bk.route("/save-query", methods=["POST"])
def save_query():
    """
    This route is for saving queries for later use. Saved queries are indexed by their name value. If this name value
    already exists, the query will not be saved.

    :return: The query is successfully saved if it passes verification then redirects back to main Query view.
    """
    current_app.logger.debug(request.form)

    # Get current config data and path to config file for saving back
    _config_data: dict = current_app.config['CONFIG']
    _config_file_path: str = current_app.config['CONFIG_FILE']

    try:
        query_id: str = str(hash(request.form['query_name'])) # Generic hash of the name for 'unique' Id
        query_name: str = request.form['query_name']
        query_text: str = request.form['query_text']
        query_limit: int = int(request.form['query_limit'])
        query_offset: int = int(request.form['query_offset'])
        query_entity: str = request.form['query_entity']

        if query_id in _config_data['SAVED_QUERIES']:
            flash(f'This query ({query_name}) already exists and cannot be added.', 'error')
        else:
            # Build connection record
            query_record: dict = {
                'id': query_id,
                'name': query_name,
                'text': query_text,
                'limit': query_limit,
                'offset': query_offset,
                'entity': query_entity,
                'save_date': datetime.now().isoformat(),
                # key/values for modal hypermedia
                'name_id': 'query_name' + query_id,
                'text_id': 'query_text' + query_id,
                'limit_id': 'limit' + query_id,
                'offset_id': 'offset' + query_id,
            }

            # Save connection record
            _config_data['SAVED_QUERIES'].update({query_id: query_record})

            # Save global app config (session)
            current_app.config['CONFIG'] = _config_data

            # Save app config to file
            utils.save_config(_config_file_path, current_app.config['CONFIG'])

            flash(f'The query ({query_name}) was successfully saved.', 'info')
    except Exception as e:
        flash(f'The query failed to be saved: {e}', 'error')
        return render_template('flash_messages.jinja')

    return render_template('query_successful_save.jinja')


@bk.route("/saved_queries")
def saved_queries():
    """
    Retrieves all saved queries for the Modal.

    :return: Returns hypermedia containing all saved queries for the user.
    """
    # Get current config data and path to config file for saving back
    _config_data: dict = current_app.config['CONFIG']

    return render_template('query_saved_queries.jinja', saved_queries=_config_data['SAVED_QUERIES'])


@bk.route("/delete-query/<string:query_id>", methods=["POST"])
def delete_query(query_id: str):
    """
    Deletes a saved query in the user's profile.

    :return: Returns hypermedia containing all saved queries for the user.
    """
    # Get current config data and path to config file for saving back
    _config_data: dict = current_app.config['CONFIG']
    _config_file_path: str = current_app.config['CONFIG_FILE']

    # Delete connection record
    del _config_data['SAVED_QUERIES'][query_id]

    # Save global app config (session)
    current_app.config['CONFIG'] = _config_data

    # Save app config to file
    utils.save_config(_config_file_path, current_app.config['CONFIG'])

    return render_template('query_saved_queries.jinja', saved_queries=_config_data['SAVED_QUERIES'])
