import logging
from dataclasses import is_dataclass, asdict
from typing import Any, Mapping

import requests

from .dev_summary_panel_model import *
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
        url = f'https://{self.jira_domain}/rest/api/3/search/jql'
        response = requests.get(url, headers=self.__create_header(), params=vars(params))
        response.raise_for_status()
        return SearchTicketsResponse.from_dict(response.json())

    def fetch_issue(self, ticket_key: str) -> Issue:
        url = f"https://{self.jira_domain}/rest/api/3/issue/{ticket_key}"
        response = requests.get(url, headers=self.__create_header())
        response.raise_for_status()
        return Issue.from_dict(response.json())

    def fetch_remote_link(self, ticket_key: str) -> list[RemoteLink]:
        url = f"https://{self.jira_domain}/rest/api/3/issue/{ticket_key}/remotelink"
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

    def update_ticket_fields(self, ticket_key: str, payload: dict) -> None:
        url = f"https://{self.jira_domain}/rest/api/3/issue/{ticket_key}"
        response = requests.put(url, headers=self.__create_header(), json=payload)
        response.raise_for_status()

    def fetch_transitions(self, ticket_key: str) -> TransitionsResponse:
        """Fetch available transitions for a ticket, type-safe."""
        url = f"https://{self.jira_domain}/rest/api/3/issue/{ticket_key}/transitions"
        response = requests.get(url, headers=self.__create_header())
        response.raise_for_status()
        return TransitionsResponse.from_dict(response.json())

    def do_transition(
            self,
            ticket_key: str,
            transition_id: str,
            additional_fields: Mapping[str, Any] | object | None = None
    ) -> None:
        url = f"https://{self.jira_domain}/rest/api/3/issue/{ticket_key}/transitions"

        fields_dict: dict[str, Any] = {}
        if additional_fields:
            if isinstance(additional_fields, Mapping):
                fields_dict = dict(additional_fields)
            elif is_dataclass(additional_fields):
                fields_dict = asdict(additional_fields)
            else:
                try:
                    fields_dict = {
                        k: v for k, v in vars(additional_fields).items()
                        if not k.startswith('_')
                    }
                except TypeError as e:
                    raise TypeError("additional_fields must be a mapping, dataclass, or object with attributes") from e

        payload = {
            "transition": {"id": transition_id}
        }
        if fields_dict:
            payload.update(fields_dict)

        response = requests.post(url, headers=self.__create_header(), json=payload)
        response.raise_for_status()

    def add_comment(self, ticket_key: str, comment: dict) -> None:
        url = f"https://{self.jira_domain}/rest/api/3/issue/{ticket_key}/comment"
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

    def invoke_graphql(self, payload: GraphqlQueryParam) -> dict[str, Any]:
        url = f"https://{self.jira_domain}/jsw2/graphql"
        response = requests.post(url, headers=self.__create_header(), json=payload.to_dict())
        response.raise_for_status()
        return response.json()

    def get_dev_summary_panel_one_click_urls(self, issue_id: str) -> DevSummaryPanelResponse:
        operation_name = 'DevSummaryPanelOneClickUrls'
        query = """
                query DevSummaryPanelOneClickUrls($issueId: ID!) {
                    developmentInformation(issueId: $issueId) {
                        details {
                            instanceTypes {
                                id
                                type
                                devStatusErrorMessages
                                repository {
                                    avatarUrl
                                    name
                                    branches {
                                        createPullRequestUrl
                                        name
                                        url
                                    }
                                    commits {
                                        url
                                    }
                                    pullRequests {
                                        url
                                        status
                                    }
                                }
                                danglingPullRequests {
                                    url
                                    status
                                }
                                buildProviders {
                                    id
                                    builds {
                                        url
                                        state
                                    }
                                }
                            }
                        }
                    }
                }
        """
        variables = {
            "issueId": issue_id
        }

        payload = GraphqlQueryParam(operation_name, query, variables)
        response = self.invoke_graphql(payload)
        return DevSummaryPanelResponse.from_dict(response)
