import logging
import os

## JIRA config
JIRA_TOKEN = os.getenv('JIRA_TOKEN')
JIRA_DOMAIN = os.getenv('JIRA_DOMAIN')
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY')

## Flow config
JIRA_SHOULD_CHECK_DEPLOYMENT_NOTE: bool = (os.getenv('JIRA_SHOULD_CHECK_DEPLOYMENT_NOTE', '').lower()
                                           in ('true', '1', 'yes'))
JIRA_SHOULD_CHECK_LINKED_DEPENDENCY: bool = (os.getenv('JIRA_SHOULD_CHECK_LINKED_DEPENDENCY', '').lower()
                                             in ('true', '1', 'yes'))
JIRA_SHOULD_CHECK_GITHUB: bool = (os.getenv('JIRA_SHOULD_CHECK_GITHUB', '').lower() in ('true', '1', 'yes'))
LOGGER_LEVEL = logging.getLevelNamesMapping()[os.getenv('LOGGER_LEVEL', 'INFO').upper()]

#### Export ####
__all__ = [
    'JIRA_TOKEN',
    'JIRA_DOMAIN',
    'JIRA_PROJECT_KEY',

    'JIRA_SHOULD_CHECK_DEPLOYMENT_NOTE',
    'JIRA_SHOULD_CHECK_LINKED_DEPENDENCY',
    'JIRA_SHOULD_CHECK_GITHUB',
    'LOGGER_LEVEL',
]
