""" Load CSV as Entity Data Module

Part of a set of helper functions to allow Watson Conversation Developers
perform tasks around managing WCS workspaces.

Included in this module are:

load_csv_as_entity_data: Loads entity data from a CSV
"""

from datetime import datetime
import pandas as pd
from watson_developer_cloud import ConversationV1
from ..util.get_and_backup_workspace import get_and_backup_workspace
from ._util import _load_entity_data
from .._constants import _DEFAULT_BACKUP_FILE

# Right now this doesn't support patterns. This should be
# updated when the APIs for managing patterns are made available
# Alternatively, this can be updated with the values API to move
# beyond this limitation or an alternative function could be developed
# to specifically handle patterns


def load_csv_as_entity_data(
        conversation_username: str = None,
        conversation_password: str = None,
        version: str = None,
        workspace: str = None,
        csv_file: str = None,
        clear_existing: bool = False,
        target_backup_file: str = _DEFAULT_BACKUP_FILE) -> None:

    """ Load entity data from a CSV file

    Currently can only handle synonym values

    CSV file will be of the following structure:
    action,entity,value,synonym

    valid actions are "ADD" or "REMOVE"

    remove statments will be executed first, then adds will be grouped
    and executed as a single statement. adds are additive with existing
    data and will not replace existing data unless the 'clear_existing'
    option is True

    parameters:
    conversation_username: username for WCS instance
    conversation_password: password for WCS instance
    version: version of WCS API
    workspace: workspace_id for WCS instance
    csv_file: CSV file containing data
    clear_existing: if true, any specified intents that exist will be cleared
    target_backup_file: backup workspace to this file before making changes
    """

    # validate that values are provided
    args = locals()
    for key in [
            'conversation_username',
            'conversation_password',
            'version',
            'workspace',
            'csv_file']:
        if args[key] is None:
            raise ValueError("Argument '{}' requires a value".format(key))

    # setup conversation class
    conversation = ConversationV1(
        username=conversation_username,
        password=conversation_password,
        version=version
    )

    # build backup file if not specified
    # otherwise just call it the POSIX timestamp
    if target_backup_file == _DEFAULT_BACKUP_FILE:
        target_backup_file = _DEFAULT_BACKUP_FILE.format(
            str(datetime.now().timestamp()))

    # backup our target instance
    _ = get_and_backup_workspace(
        username=conversation_username,
        password=conversation_password,
        workspace=workspace,
        version=version,
        export_path=target_backup_file
    )

    # load data
    entity_data = pd.read_csv(
        csv_file,
        dtype='str',
        keep_default_na=False)

    # default values
    config_data = {
        "clear_existing": clear_existing
    }

    # call the function
    _load_entity_data(conversation=conversation,
                      workspace_id=workspace,
                      entity_data=entity_data,
                      config_data=config_data)
    print(("load_csv_as_entity_data "
           "for '{}' complete.").format(csv_file))
