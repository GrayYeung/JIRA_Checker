import logging

import requests

from .jiramodel import *


#### Client ####

class JiraClient:

    def __init__(self, jira_domain, jira_token):
        self.jira_domain = jira_domain
        self.jira_token = jira_token

    def __create_header(self) -> dict[str, str]:
        """
        Create headers for JIRA API requests.
        :return: Dictionary of headers
        """
        return {
            "Authorization": f"Basic {self.jira_token}",
            "Accept": "application/json"
        }

    def fetch_search(self, params: SearchTicketsParams) -> SearchTicketsResponse:
        url = f'https://{self.jira_domain}/rest/api/3/search'
        response = requests.get(url, headers=self.__create_header(), params=vars(params))
        response.raise_for_status()
        return SearchTicketsResponse.from_dict(response.json())

    def fetch_issue(self, ticket_id: str) -> Issue:
        url = f"https://{self.jira_domain}/rest/api/3/issue/{ticket_id}"
        response = requests.get(url, headers=self.__create_header())
        response.raise_for_status()
        return Issue.from_dict(response.json())

    def fetch_remote_link(self, ticket_id: str) -> list[RemoteLink]:
        url = f"https://{self.jira_domain}/rest/api/3/issue/{ticket_id}/remotelink"
        response = requests.get(url, headers=self.__create_header())
        response.raise_for_status()
        data = response.json()
        return [RemoteLink.from_dict(item) for item in data]

    def fetch_confluence_content(self, page_id: str) -> Optional[ConfluencePage]:
        url = f"https://{self.jira_domain}/wiki/api/v2/pages/{page_id}"
        try:
            response = requests.get(url, headers=self.__create_header())
            response.raise_for_status()
            return ConfluencePage.from_dict(response.json())
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching Confluence content for page {page_id}: {e}")
            return None

    def fetch_transitions(self, ticket_id: str) -> TransitionsResponse:
        """Fetch available transitions for a ticket, type-safe."""
        url = f"https://{self.jira_domain}/rest/api/3/issue/{ticket_id}/transitions"
        response = requests.get(url, headers=self.__create_header())
        response.raise_for_status()
        return TransitionsResponse.from_dict(response.json())

    def do_transition(self, ticket_id: str, transition_id: str) -> None:
        url = f"https://{self.jira_domain}/rest/api/3/issue/{ticket_id}/transitions"
        payload = {
            "transition": {
                "id": transition_id
            }
        }
        response = requests.post(url, headers=self.__create_header(), json=payload)
        response.raise_for_status()

    def add_comment(self, ticket_id: str, comment: dict) -> None:
        url = f"https://{self.jira_domain}/rest/api/3/issue/{ticket_id}/comment"
        payload = {
            "body": comment,
            "visibility": None  ## null
        }
        response = requests.post(url, headers=self.__create_header(), json=payload)
        response.raise_for_status()

    def fetch_myself(self) -> UserAccount:
        url = f"https://{self.jira_domain}/rest/api/3/myself"
        response = requests.get(url, headers=self.__create_header())
        response.raise_for_status()
        return UserAccount.from_dict(response.json())
