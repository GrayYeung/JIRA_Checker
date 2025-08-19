from datetime import datetime
from typing import Optional


#### Type ####
class Sprint:
    def __init__(
            self,
            name: str,
            state: str,
            start_date: datetime,
            end_date: datetime
    ):
        self.name = name
        self.state = state
        self.start_date = start_date
        self.end_date = end_date

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            name=data.get('name', ''),
            state=data.get('state', ''),
            start_date=datetime.fromisoformat(data.get('startDate', '').replace('Z', '+00:00'))
            if data.get('startDate') else None,
            end_date=datetime.fromisoformat(data.get('endDate', '').replace('Z', '+00:00'))
            if data.get('endDate') else None
        )

    def __str__(self):
        return f"Sprint(name='{self.name}', state='{self.state}', start_date='{self.start_date}', end_date='{self.end_date}')"

    def __repr__(self):
        return self.__str__()


class UserAccount:
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
    def __init__(
            self,
            assignee: Optional[UserAccount] = None,
            reporter: Optional[UserAccount] = None,
            status: Optional[Status] = None,
            labels: Optional[list[str]] = None,
            **kwargs
    ):
        self.assignee = assignee
        self.reporter = reporter
        self.status = status
        self.labels = labels
        # Store any additional fields that weren't explicitly defined
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def from_dict(cls, data: dict):
        assignee = UserAccount.from_dict(data['assignee']) if data.get('assignee') else None
        reporter = UserAccount.from_dict(data['reporter']) if data.get('reporter') else None
        status = Status.from_dict(data['status']) if data.get('status') else None
        labels = data.get('labels', None)

        # Extract known fields and pass the rest as kwargs
        known_fields = {'assignee', 'reporter', 'status', 'labels'}
        other_fields = {k: v for k, v in data.items() if k not in known_fields}

        return cls(
            assignee=assignee,
            reporter=reporter,
            status=status,
            labels=labels,
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
    def __init__(self, jql: str, fields: list[str], max_results: int = 200, start_at: int = 0):
        self.jql = jql
        self.fields = ",".join(fields)
        self.maxResults = max_results
        self.startAt = start_at


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


class LinkedIssue:
    def __init__(self, key: str, fields: dict):
        self.key = key
        self.fields = fields

    @classmethod
    def from_dict(cls, data: dict):
        fields = (data.get('fields', {}))
        return cls(
            key=data.get('key', ''),
            fields=fields
        )


class IssueLinkType:
    def __init__(self, name: str, inward: str, outward: str):
        self.name = name
        self.inward = inward
        self.outward = outward

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            name=data.get('name', ''),
            inward=data.get('inward', ''),
            outward=data.get('outward', ''),
        )


class IssueLink:
    def __init__(
            self,
            id: str,
            type: IssueLinkType,
            inward_issue: Optional[LinkedIssue] = None,
            outward_issue: Optional[LinkedIssue] = None
    ):
        self.id = id
        self.type = type
        self.inward_issue = inward_issue
        self.outward_issue = outward_issue

    @classmethod
    def from_dict(cls, data: dict):
        id = data.get('id', '')
        type_obj = IssueLinkType.from_dict(data.get('type', {}))
        inward_issue = LinkedIssue.from_dict(data['inwardIssue']) if data.get('inwardIssue') else None
        outward_issue = LinkedIssue.from_dict(data['outwardIssue']) if data.get('outwardIssue') else None

        return cls(
            id=id,
            type=type_obj,
            inward_issue=inward_issue,
            outward_issue=outward_issue
        )

    def __str__(self):
        if self.inward_issue:
            return f"IssueLink inward ({self.type.inward} -> {self.inward_issue.key})"
        elif self.outward_issue:
            return f"IssueLink outward ({self.type.outward} -> {self.outward_issue.key})"
        else:
            return f"IssueLink (id={self.id})"

    def __repr__(self):
        return self.__str__()
