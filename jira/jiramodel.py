from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List


#### Type ####
@dataclass
class Sprint:
    name: str
    state: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]

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


@dataclass
class UserAccount:
    account_id: str = ''
    email_address: str = ''
    display_name: str = ''
    active: bool = False
    time_zone: str = ''

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            account_id=data.get('accountId', ''),
            email_address=data.get('emailAddress', ''),
            display_name=data.get('displayName', ''),
            active=data.get('active', False),
            time_zone=data.get('timeZone', '')
        )


@dataclass
class Status:
    id: str = ''
    name: str = ''
    description: str = ''

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', '')
        )


@dataclass
class FixVersion:
    id: str = ''
    name: str = ''
    description: str = ''
    archived: bool = False
    released: bool = False
    releaseDate: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            archived=data.get('archived', False),
            released=data.get('released', False),
            releaseDate=datetime.fromisoformat(data.get('releaseDate', '').replace('Z', '+00:00'))
            if data.get('releaseDate') else None
        )


@dataclass
class Fields:
    assignee: Optional[UserAccount] = None
    reporter: Optional[UserAccount] = None
    status: Optional[Status] = None
    labels: Optional[List[str]] = None

    def __post_init__(self):
        # This will be used to store additional fields
        pass

    @classmethod
    def from_dict(cls, data: dict):
        assignee = UserAccount.from_dict(data['assignee']) if data.get('assignee') else None
        reporter = UserAccount.from_dict(data['reporter']) if data.get('reporter') else None
        status = Status.from_dict(data['status']) if data.get('status') else None
        labels = data.get('labels', None)

        # Create instance
        instance = cls(
            assignee=assignee,
            reporter=reporter,
            status=status,
            labels=labels
        )

        # Store any additional fields that weren't explicitly defined
        known_fields = {'assignee', 'reporter', 'status', 'labels'}
        for key, value in data.items():
            if key not in known_fields:
                setattr(instance, key, value)

        return instance


@dataclass
class Issue:
    id: str = ''
    key: str = ''
    self_url: str = ''
    expand: str = ''
    fields: Optional[Fields] = None

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


@dataclass
class SearchTicketsParams:
    jql: str
    fields: str = field(init=False)
    maxResults: int = 200
    nextPageToken: Optional[str] = None

    def __init__(self, jql: str, fields: List[str], max_results: int = 200, next_page_token: str = None):
        self.jql = jql
        self.fields = ",".join(fields)
        self.maxResults = max_results
        self.nextPageToken = next_page_token


@dataclass
class SearchTicketsResponse:
    isLast: bool
    nextPageToken: Optional[str]
    issues: List[Issue] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        issues = [Issue.from_dict(issue_data) for issue_data in data.get('issues', [])]
        return cls(
            isLast=data.get('isLast', True),
            nextPageToken=data.get('nextPageToken'),
            issues=issues
        )


@dataclass
class RemoteLinkStatusIcon:
    icon: Dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(icon=data.get('icon', {}))


@dataclass
class RemoteLinkStatus:
    icon: Dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(icon=data.get('icon', {}))


@dataclass
class RemoteLinkObject:
    url: str = ''
    title: str = ''
    icon: Dict = field(default_factory=dict)
    status: Optional[RemoteLinkStatus] = None

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


@dataclass
class RemoteLink:
    id: int = 0
    self_url: str = ''
    global_id: str = ''
    relationship: str = ''
    object: Optional[RemoteLinkObject] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=int(data.get('id', 0)),
            self_url=data.get('self', ''),
            global_id=data.get('globalId', ''),
            relationship=data.get('relationship', ''),
            object=RemoteLinkObject.from_dict(data.get('object', {}))
        )


@dataclass
class ConfluencePageVersion:
    number: int = 0
    message: str = ''
    minor_edit: bool = False
    author_id: str = ''
    created_at: str = ''
    ncs_step_version: str = ''

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


@dataclass
class ConfluencePage:
    title: str = ''
    id: str = ''

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            title=data.get('title', ''),
            id=data.get('id', '')
        )


@dataclass
class TransitionStatus:
    self_url: str = ''
    description: str = ''
    icon_url: str = ''
    name: str = ''
    id: str = ''

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            self_url=data.get('self', ''),
            description=data.get('description', ''),
            icon_url=data.get('iconUrl', ''),
            name=data.get('name', ''),
            id=data.get('id', '')
        )


@dataclass
class Transition:
    id: str = ''
    name: str = ''
    to: Optional[TransitionStatus] = None
    has_screen: bool = False
    is_global: bool = False
    is_initial: bool = False
    is_available: bool = False
    is_conditional: bool = False
    is_looped: bool = False

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


@dataclass
class TransitionsResponse:
    expand: str = ''
    transitions: List[Transition] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        transitions = [Transition.from_dict(t) for t in data.get('transitions', [])]
        return cls(
            expand=data.get('expand', ''),
            transitions=transitions
        )


@dataclass
class LinkedIssue:
    key: str = ''
    fields: Dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        fields = data.get('fields', {})
        return cls(
            key=data.get('key', ''),
            fields=fields
        )


@dataclass
class IssueLinkType:
    name: str = ''
    inward: str = ''
    outward: str = ''

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            name=data.get('name', ''),
            inward=data.get('inward', ''),
            outward=data.get('outward', ''),
        )


@dataclass
class IssueLink:
    id: str = ''
    type: Optional[IssueLinkType] = None
    inward_issue: Optional[LinkedIssue] = None
    outward_issue: Optional[LinkedIssue] = None

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


@dataclass
class GraphqlQueryParam:
    operationName: str
    query: str
    variables: Dict

    def to_dict(self) -> dict:
        return {
            'operationName': self.operationName,
            'query': self.query,
            'variables': self.variables
        }
