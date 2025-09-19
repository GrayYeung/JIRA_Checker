from dataclasses import dataclass, field
from typing import List, Optional


#### DevSummaryPanelOneClickUrls DTOs ####
## From GraphQL

@dataclass
class Branch:
    createPullRequestUrl: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            createPullRequestUrl=data.get('createPullRequestUrl'),
            name=data.get('name'),
            url=data.get('url')
        )


@dataclass
class Commit:
    url: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(url=data.get('url'))


@dataclass
class PullRequest:
    url: Optional[str] = None
    status: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            url=data.get('url'),
            status=data.get('status')
        )


@dataclass
class Repository:
    avatarUrl: Optional[str] = None
    name: Optional[str] = None
    branches: List[Branch] = field(default_factory=list)
    commits: List[Commit] = field(default_factory=list)
    pullRequests: List[PullRequest] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            avatarUrl=data.get('avatarUrl'),
            name=data.get('name'),
            branches=[Branch.from_dict(b) for b in data.get('branches', [])],
            commits=[Commit.from_dict(c) for c in data.get('commits', [])],
            pullRequests=[PullRequest.from_dict(pr) for pr in data.get('pullRequests', [])]
        )


@dataclass
class Build:
    url: Optional[str] = None
    state: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            url=data.get('url'),
            state=data.get('state')
        )


@dataclass
class BuildProvider:
    id: Optional[str] = None
    builds: List[Build] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id'),
            builds=[Build.from_dict(b) for b in data.get('builds', [])]
        )


@dataclass
class InstanceType:
    id: Optional[str] = None
    type: Optional[str] = None
    devStatusErrorMessages: List[str] = field(default_factory=list)
    repository: List[Repository] = field(default_factory=list)
    danglingPullRequests: List[PullRequest] = field(default_factory=list)
    buildProviders: List[BuildProvider] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get('id'),
            type=data.get('type'),
            devStatusErrorMessages=data.get('devStatusErrorMessages', []),
            repository=[Repository.from_dict(r) for r in data.get('repository', [])],
            danglingPullRequests=[PullRequest.from_dict(dpr) for dpr in data.get('danglingPullRequests', [])],
            buildProviders=[BuildProvider.from_dict(bp) for bp in data.get('buildProviders', [])]
        )


@dataclass
class DevSummaryPanelDetails:
    instanceTypes: List[InstanceType] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            instanceTypes=[InstanceType.from_dict(it) for it in data.get('instanceTypes', [])]
        )


@dataclass
class DevSummaryPanelDevelopmentInformation:
    details: Optional[DevSummaryPanelDetails] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            details=DevSummaryPanelDetails.from_dict(data.get('details', {}))
        )


@dataclass
class DevSummaryPanelData:
    developmentInformation: Optional[DevSummaryPanelDevelopmentInformation] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            developmentInformation=DevSummaryPanelDevelopmentInformation.from_dict(
                data.get('developmentInformation', {}))
        )


@dataclass
class DevSummaryPanelResponse:
    data: Optional[DevSummaryPanelData] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            data=DevSummaryPanelData.from_dict(data.get('data', {}))
        )
