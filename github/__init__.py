from environment import *
from . import githubmodel

from .githubclient import GitHubClient

## Initialize the gh client with environment configuration
github_client = GitHubClient(GITHUB_TOKEN)

## Define what gets exported when using "from github import *"
__all__ = [
    # Client
    'github_client',

    # Core Models
    'githubmodel',
]
