import logging
from typing import Optional

import requests


#### Type ####

class Assignee:
    def __init__(self, account_id: str, email_address: str, display_name: str, active: bool, time_zone: str):
        self.account_id = account_id
        self.email_address = email_address
        self.display_name = display_name
        self.active = active
        self.time_zone = time_zone

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            account_id=data.get('accountId', ''),
            email_address=data.get('emailAddress', ''),
            display_name=data.get('displayName', ''),
            active=data.get('active', False),
            time_zone=data.get('timeZone', '')
        )


class Status:
    def __init__(self, id: str, name: str, description: str):
        self.id = id
        self.name = name
        self.description = description

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', '')
        )


class Fields:
    def __init__(self, assignee: Optional[Assignee] = None, status: Optional[Status] = None, **kwargs):
        self.assignee = assignee
        self.status = status
        # Store any additional fields that weren't explicitly defined
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def from_dict(cls, data: dict):
        assignee = Assignee.from_dict(data['assignee']) if data.get('assignee') else None
        status = Status.from_dict(data['status']) if data.get('status') else None

        # Extract known fields and pass the rest as kwargs
        known_fields = {'assignee', 'status'}
        other_fields = {k: v for k, v in data.items() if k not in known_fields}

        return cls(
            assignee=assignee,
            status=status,
            **other_fields
        )


class Issue:
    def __init__(
            self,
            id: str,
            key: str,
            self_url: str,
            expand: str,
            fields: Fields
    ):
        self.id = id
        self.key = key
        self.self_url = self_url
        self.expand = expand
        self.fields = fields

    @classmethod
    def from_dict(cls, data: dict):
        fields = Fields.from_dict(data.get('fields', {}))
        return cls(
            id=data.get('id', ''),
            key=data.get('key', ''),
            self_url=data.get('self', ''),
            expand=data.get('expand', ''),
            fields=fields
        )


class SearchTicketsParams:
    def __init__(self, jql: str, fields: list[str], max_results: int = 200):
        self.jql = jql
        self.fields = ",".join(fields)
        self.maxResults = max_results


class SearchTicketsResponse:
    def __init__(self, expand: str, start_at: int, max_results: int, total: int, issues: list[Issue]):
        self.expand = expand
        self.start_at = start_at
        self.max_results = max_results
        self.total = total
        self.issues = issues

    @classmethod
    def from_dict(cls, data: dict):
        issues = [Issue.from_dict(issue_data) for issue_data in data.get('issues', [])]
        return cls(
            expand=data.get('expand', ''),
            start_at=data.get('startAt', 0),
            max_results=data.get('maxResults', 0),
            total=data.get('total', 0),
            issues=issues
        )


class RemoteLinkStatusIcon:
    def __init__(self, icon: Optional[dict] = None):
        self.icon = icon or {}

    @classmethod
    def from_dict(cls, data: dict):
        return cls(icon=data.get('icon', {}))


class RemoteLinkStatus:
    def __init__(self, icon: Optional[dict] = None):
        self.icon = icon or {}

    @classmethod
    def from_dict(cls, data: dict):
        return cls(icon=data.get('icon', {}))


class RemoteLinkObject:
    def __init__(self, url: str, title: str, icon: Optional[dict] = None, status: Optional[RemoteLinkStatus] = None):
        self.url = url
        self.title = title
        self.icon = icon or {}
        self.status = status

    @classmethod
    def from_dict(cls, data: dict):
        status = None
        if 'status' in data:
            status = RemoteLinkStatus.from_dict(data['status'])
        return cls(
            url=data.get('url', ''),
            title=data.get('title', ''),
            icon=data.get('icon', {}),
            status=status
        )


class RemoteLink:
    def __init__(
            self,
            id: int,
            self_url: str,
            global_id: str,
            relationship: str,
            object: RemoteLinkObject
    ):
        self.id = id
        self.self_url = self_url
        self.global_id = global_id
        self.relationship = relationship
        self.object = object

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=int(data.get('id', 0)),
            self_url=data.get('self', ''),
            global_id=data.get('globalId', ''),
            relationship=data.get('relationship', ''),
            object=RemoteLinkObject.from_dict(data.get('object', {}))
        )


class ConfluencePageVersion:
    def __init__(
            self,
            number: int,
            message: str,
            minor_edit: bool,
            author_id: str,
            created_at: str,
            ncs_step_version: str
    ):
        self.number = number
        self.message = message
        self.minor_edit = minor_edit
        self.author_id = author_id
        self.created_at = created_at
        self.ncs_step_version = ncs_step_version

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            number=data.get('number', 0),
            message=data.get('message', ''),
            minor_edit=data.get('minorEdit', False),
            author_id=data.get('authorId', ''),
            created_at=data.get('createdAt', ''),
            ncs_step_version=data.get('ncsStepVersion', '')
        )


class ConfluencePage:
    def __init__(
            self,
            title: str,
            id: str,
    ):
        self.title = title
        self.id = id

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            title=data.get('title', ''),
            id=data.get('id', '')
        )


class TransitionStatus:
    def __init__(self, self_url: str, description: str, icon_url: str, name: str, id: str):
        self.self_url = self_url
        self.description = description
        self.icon_url = icon_url
        self.name = name
        self.id = id

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            self_url=data.get('self', ''),
            description=data.get('description', ''),
            icon_url=data.get('iconUrl', ''),
            name=data.get('name', ''),
            id=data.get('id', '')
        )


class Transition:
    def __init__(
            self,
            id: str,
            name: str,
            to: TransitionStatus,
            has_screen: bool,
            is_global: bool,
            is_initial: bool,
            is_available: bool,
            is_conditional: bool,
            is_looped: bool
    ):
        self.id = id
        self.name = name
        self.to = to
        self.has_screen = has_screen
        self.is_global = is_global
        self.is_initial = is_initial
        self.is_available = is_available
        self.is_conditional = is_conditional
        self.is_looped = is_looped

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            to=TransitionStatus.from_dict(data.get('to', {})),
            has_screen=data.get('hasScreen', False),
            is_global=data.get('isGlobal', False),
            is_initial=data.get('isInitial', False),
            is_available=data.get('isAvailable', False),
            is_conditional=data.get('isConditional', False),
            is_looped=data.get('isLooped', False)
        )


class TransitionsResponse:
    def __init__(self, expand: str, transitions: list[Transition]):
        self.expand = expand
        self.transitions = transitions

    @classmethod
    def from_dict(cls, data: dict):
        transitions = [Transition.from_dict(t) for t in data.get('transitions', [])]
        return cls(
            expand=data.get('expand', ''),
            transitions=transitions
        )


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

    def fetch_myself(self) -> Assignee:
        url = f"https://{self.jira_domain}/rest/api/3/myself"
        response = requests.get(url, headers=self.__create_header())
        response.raise_for_status()
        return Assignee.from_dict(response.json())
