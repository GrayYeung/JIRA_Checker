import logging

from jira import *


###
def check_open_git_pull_request() -> bool:
    """
    Ride on Git plugin in JIRA to check if there is any open PR for the issue.
    """
    
    issue_id = "997225"
    resp = jira_client.get_dev_summary_panel_one_click_urls(issue_id)
    logging.info(resp)

    return True
