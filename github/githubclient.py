import requests

from .githubmodel import GitHubPullRequest, GitHubSearchIssuesResponse


#### Client ####

class GitHubClient:

    def __init__(self, gh_token):
        self.gh_token = gh_token

    def __create_header(self) -> dict[str, str]:
        return {
            'Authorization': f'token {self.gh_token}',
            'Accept': 'application/vnd.github+json'
        }

    def fetch_pr(self, owner: str, repo: str, pr_number: int) -> GitHubPullRequest:
        url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}'

        response = requests.get(url, headers=self.__create_header())
        response.raise_for_status()
        data = response.json()
        return GitHubPullRequest.from_dict(data)

    def search_open_prs(self, organization: str, ticket_key: str) -> GitHubSearchIssuesResponse:
        """Find open (including draft) pull requests in an organization mentioning a JIRA ticket key."""
        url = 'https://api.github.com/search/issues'
        params = {
            'q': f'{ticket_key} is:pr is:open org:{organization}',
            'per_page': 100
        }

        response = requests.get(url, headers=self.__create_header(), params=params)
        response.raise_for_status()
        return GitHubSearchIssuesResponse.from_dict(response.json())

