from environment import *
from . import jiramodel
from .jiraclient import JiraClient

## Initialize the JIRA client with environment configuration
jira_client = JiraClient(JIRA_DOMAIN, JIRA_TOKEN)

## Define what gets exported when using "from jira import *"
__all__ = [
    # Client
    'jira_client',

    # Core Models
    'jiramodel'
]
