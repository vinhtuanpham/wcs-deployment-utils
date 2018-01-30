import requests
from queue import Queue
from watson_developer_cloud import ConversationV1, WatsonException

def copy_dialog_data(root_node=None,
                     target_node='root',
                     target_insert_as='sibling',
                     source_username=None,
                     source_password=None,
                     source_workspace=None,
                     target_username=None,
                     target_password=None,
                     target_workspace=None,
                     version=None):
    
    """ Copy a branch of dialog from a source workspace to a target workspace.

    Default insert is 'sibling' which inserts the branch as the immediate
    sibling of the target node. Alternatively, 'child' can be specified
    so that the branch is inserted as the first child of the node. If
    target_node is specified as 'root', the branch is inserted as the first
    child of the dialog root

    Parameters:
    root_node: ID or title of the root node in source
    target_node: ID or title of the root node in target
    target_insert_as: Default 'sibling'. Location of branch insertion, with 
        respect to the target root. Valid options are 'sibling' and 'child'
    source_username: Username for source WCS instance
    source_password: Password for source WCS instance
    source_workspace: Workspace ID for source WCS instance
    target_username: Username for target WCS instance
    target_password: Password for target WCS instance
    target_workspace: Workspace ID for target WCS instance
    version: WCS API version
    """
    base_api_url = 'https://gateway.watsonplatform.net/conversation/api/v1/'
    target_insert_as = target_insert_as.lower()
    
    # nodes to move to target
    to_import = []
    
    # queue to hold the ids that need to be located
    to_locate = Queue()
    
    # set up the SDK for both source and target
    target_conv = ConversationV1(
        username=target_username,
        password=target_password,
        version=version
    )
    
    source_conv = ConversationV1(
        username=source_username,
        password=source_password,
        version=version
    )
    
    # get export of workspace
    source_export = source_conv.get_workspace(
        workspace_id=source_workspace, 
        export=True)
    target_export = target_conv.get_workspace(
        workspace_id=target_workspace, 
        export=True)

    # locate the roots
    source_root = _find_node(root_node, source_export['dialog_nodes'])
    target_root = _find_node(target_node, target_export['dialog_nodes'])
    # Check that we found the root
    if source_root is None:
        raise ValueError('Specified root node not found')
    
    # remove digression information if the target is not a root
    if (target_insert_as != 'sibling' or
            target_root is None or
            target_root['parent'] is not None):
        source_root['digress_out_slots'] = None
        source_root['digress_out'] = None
        source_root['digress_in'] = None
    
    # set the parent/sibling based on insert type and target root
    if target_root is None:
        print('inserting as first child of dialog root')
        source_root['parent'] = None
        source_root['previous_sibling'] = None
    elif target_insert_as == 'sibling':
        print('inserting as first sibling of target root')
        source_root['parent'] = target_root['parent'] 
        source_root['previous_sibling'] = target_root['dialog_node'] 
    elif target_insert_as == 'child':
        print('inserting as first child of target root')
        source_root['parent'] = target_root['dialog_node'] 
        source_root['previous_sibling'] = None
    
    
    # first thing to add is the root node
    to_import.append(source_root)
    to_locate.put(source_root['dialog_node'])
    
    # Iterate through all the parents starting with the root
    while to_locate.empty() == False:
        id_to_locate = to_locate.get()
        
        # Check for nodes that list this as the parent
        for node in source_export['dialog_nodes']:
            if node['parent'] == id_to_locate:
                to_import.append(node)
                to_locate.put(node['dialog_node'])

    # ensure that target space is clear of collisions
    for node in to_import:
        try:
            target_conv.delete_dialog_node(workspace_id=target_workspace,
                                           dialog_node=node['dialog_node'])
        except WatsonException as e:
            # ultimately, if something fails to delete,
            # it will throw an error on the update
            pass
    r = requests.request(
        "POST",
        base_api_url + "workspaces/{}".format(target_workspace),
        params={
            "version": "2017-05-26",
            "append": "true"},
         json={
             "dialog_nodes": to_import},
         auth=(target_username, target_password))
    
    if r.ok == False:
        print(r.text)
        raise Exception('Dialog update failed')
    print('Dialog update success')

def _find_node(node_id, dialog_nodes):
    """ Find a specific node in an list of dialog node JSON representations

    Parameters:
    node_id: The ID or title of the dialog node
    dialog_nodes: The list of dialog nodes to search on

    Returns:
    target_node: The Dialog Node object for the specified ID or title
    """
    if node_id == 'root':
        return None
    
    target_node = None

    for node in dialog_nodes:
        # It will match either the node title or the id
        if (str(node['title']).lower() == node_id.lower() or
                str(node['dialog_node']).lower() == node_id.lower()):
            target_node = node
            break

    return target_node
