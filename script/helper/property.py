import logging
import os

from .jiraclient import JiraClient

## JIRA config
JIRA_TOKEN = os.getenv('JIRA_TOKEN')
JIRA_DOMAIN = os.getenv('JIRA_DOMAIN')
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY')

jira_client = JiraClient(JIRA_DOMAIN, JIRA_TOKEN)

## Flow config
JIRA_SHOULD_CHECK_DEPLOYMENT_NOTE: bool = (os.getenv('JIRA_SHOULD_CHECK_DEPLOYMENT_NOTE', '').lower()
                                           in ('true', '1', 'yes'))
LOGGER_LEVEL = logging.getLevelNamesMapping()[os.getenv('LOGGER_LEVEL', 'INFO').upper()]
