import requests

from .githubmodel import GitHubPullRequest


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
