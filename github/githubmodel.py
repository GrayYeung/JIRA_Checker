from typing import Optional, List


# Model for GitHub User
class GitHubUser:
    def __init__(self, login: Optional[str], id: Optional[int], avatar_url: Optional[str], html_url: Optional[str],
                 type: Optional[str], site_admin: bool):
        self.login = login
        self.id = id
        self.avatar_url = avatar_url
        self.html_url = html_url
        self.type = type
        self.site_admin = site_admin

    @staticmethod
    def from_dict(data: dict):
        return GitHubUser(
            login=data.get('login'),
            id=data.get('id'),
            avatar_url=data.get('avatar_url'),
            html_url=data.get('html_url'),
            type=data.get('type'),
            site_admin=data.get('site_admin', False)
        )


# Model for GitHub Pull Request
class GitHubPullRequest:
    def __init__(self, id: Optional[int], number: Optional[int], title: Optional[str], body: Optional[str],
                 user: GitHubUser, state: Optional[str], merged_at: Optional[str], assignees: List[GitHubUser]):
        self.id = id
        self.number = number
        self.title = title
        self.body = body
        self.user = user
        self.state = state
        self.merged_at = merged_at
        self.assignees = assignees  # List of GitHubUser

    @staticmethod
    def from_dict(data: dict):
        user = GitHubUser.from_dict(data.get('user', {}))
        assignees = [GitHubUser.from_dict(u) for u in data.get('assignees', [])]
        return GitHubPullRequest(
            id=data.get('id'),
            number=data.get('number'),
            title=data.get('title'),
            body=data.get('body'),
            user=user,
            state=data.get('state'),
            merged_at=data.get('merged_at'),
            assignees=assignees
        )
