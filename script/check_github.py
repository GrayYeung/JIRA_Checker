import json
import logging
import re

import requests

from constants import *
from environment import *
from exception.exceptionmodel import UnexpectedException
from github import github_client
from github.githubmodel import GitHubSearchPullRequest, GitHubSearchIssuesResponse
from jira import *
from jira.jiramodel import *
from .utils import print_conclusion, should_skip_by_label, should_skip_by_tailing_next_part, extract_assignee_id, \
    perform_transition, find_heading_ticket, determine_relationship

##
reviewer_field = REVIEWER_FIELD  # This is the field ID for the Reviewer field in JIRA
whitelisted_label = WHITELISTED_LABEL
gh_field = GH_FIELD  # This is the field ID for the GitHub field in JIRA


####

def check_for_github() -> bool:
    """
    Search GitHub directly for open or draft pull requests related to each JIRA issue.
    """
    logging.info("Checking for open git pull request... ⚠️")

    tickets = fetch_tickets()
    ticket_keys = [ticket.key for ticket in tickets]
    logging.info(f"Found {len(ticket_keys)} tickets: {ticket_keys}")

    bad_tickets: list[str] = []
    error_tickets: list[str] = []

    for ticket in tickets:
        ticket_key = ticket.key

        logging.info(f"[{ticket_key}] Processing ticket...")

        try:
            if should_skip_by_label(ticket, whitelisted_label):
                logging.info(f"[{ticket_key}] Skipping due to whitelisted label...")
                continue

            if should_skip_by_tailing_next_part(ticket):
                logging.info(f"[{ticket_key}] Skipping due to tailing 'Part N' cloned ticket...")
                continue

            open_prs = nest_check_open_prs(ticket, None)
            if not open_prs:
                logging.info(f"[{ticket_key}] No open Pull Request found. All good ✅")
                continue

            logging.info(f"[{ticket_key}] Found {len(open_prs)} open pull requests ❌")
            ## Action
            do_transition(ticket_key)
            add_comment(ticket, open_prs)

            bad_tickets.append(ticket_key)

        except (requests.exceptions.RequestException, UnexpectedException) as e:
            logging.error(f"[{ticket_key}] Encountered {type(e).__name__}: {e}")
            error_tickets.append(ticket_key)
            continue

    print_conclusion(bad_tickets, error_tickets)
    return len(error_tickets) == 0


####

def fetch_tickets() -> list[Issue]:
    ## get the last week updated tickets
    ### Done: Story, Debt
    ### Accepted: Incident, Bugs
    status_list = ['Done', 'Accepted']
    time_range = "5d"  # e.g.: h,d,w
    time_buffer = "1d"  # e.g.: h,d,w; for cache buffer on info
    project = JIRA_PROJECT_KEY

    jql = f'updated >= -{time_range} and updated < -{time_buffer} and status IN ({", ".join(status_list)}) and project = {project}'
    fields = ["assignee", "status", "labels", "issuelinks", "summary", reviewer_field, gh_field]

    params = SearchTicketsParams(
        jql=jql,
        fields=fields,
    )

    logging.info("Fetching tickets with JQL: '%s'...", jql)
    response: SearchTicketsResponse = jira_client.fetch_search(params)

    return response.issues


def nest_check_open_prs(ticket: Issue, linked_ticket_key: Optional[str]) -> list[GitHubSearchPullRequest]:
    ticket_key = ticket.key

    ## check heading ticket
    heading_key = find_heading_ticket(ticket)
    if heading_key:
        logging.info(
            f"[{determine_relationship(ticket_key, heading_key)}] Tracing for its heading ticket ({heading_key})..."
        )
        heading_ticket = jira_client.fetch_issue(heading_key)
        heading_result = nest_check_open_prs(heading_ticket, ticket_key)
        if heading_result:
            return heading_result

    ## check this ticket
    if not has_open_pr_in_jira(ticket):
        logging.info(f"[{ticket_key}] Skipping GitHub API calls: JIRA reports no OPEN pull request")
        return []

    result = search_open_prs_from_github(ticket_key)
    logging.info(f"[{determine_relationship(ticket_key, linked_ticket_key)}] Open PRs: {len(result)}")
    return result


def has_open_pr_in_jira(ticket: Issue) -> bool:
    """Return whether JIRA's GitHub development field reports at least one open pull request."""
    raw_value = getattr(ticket.fields, gh_field, None) if ticket.fields else None
    field_data = parse_jira_github_field(raw_value)
    if not field_data:
        return False

    cached_value = field_data.get('cachedValue')
    if not isinstance(cached_value, dict):
        return False
    summary = cached_value.get('summary')
    if not isinstance(summary, dict):
        return False
    pull_request = summary.get('pullrequest')
    if not isinstance(pull_request, dict):
        return False
    overall = pull_request.get('overall')
    if not isinstance(overall, dict):
        return False

    return overall.get('open') is True


def parse_jira_github_field(raw_value: object) -> dict | None:
    """Parse customfield_10000, whose JIRA representation embeds JSON after ``json=``."""
    if isinstance(raw_value, dict):
        return raw_value
    if not isinstance(raw_value, str):
        return None

    try:
        parsed = json.loads(raw_value)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        json_start = raw_value.find('json=')
        if json_start == -1:
            return None

        try:
            parsed, _ = json.JSONDecoder().raw_decode(raw_value[json_start + len('json='):])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None


def search_open_prs_from_github(ticket_key: str) -> list[GitHubSearchPullRequest]:
    """Find and validate open or draft pull requests directly from GitHub Search."""
    organization = (GITHUB_ORGANIZATION or '').strip()
    if not organization:
        logging.warning(f"[{ticket_key}] Skipping direct GitHub search: GITHUB_ORGANIZATION is not configured")
        return []

    search_response: GitHubSearchIssuesResponse = github_client.search_open_prs(organization, ticket_key)
    result: list[GitHubSearchPullRequest] = []
    for search_pr in search_response.items:
        if search_pr.state == 'open' and search_pr.html_url and not check_with_gh(search_pr.html_url, ticket_key):
            result.append(search_pr)

    logging.info(f"[{ticket_key}] Direct GitHub Search open PRs: {len(result)}")
    return result


def check_with_gh(url: str | None, ticket_key: str) -> bool:
    """
    :return TRUE if the status at gh is closed.
    """
    if not url:
        return False

    ## Example URL: https://github.com/owner/repo/pull/123
    m = re.match(r"https://github.com/([^/]+)/([^/]+)/pull/(\d+)", url)
    if not m:
        return False

    owner, repo, pr_number = m.group(1), m.group(2), int(m.group(3))
    pr = github_client.fetch_pr(owner, repo, pr_number)

    ## Consider closed if state is 'closed' or merged_at is not None
    if pr.state == 'closed' or pr.merged_at is not None:
        return True

    normalized_ticket_key = ticket_key.casefold()
    title = (pr.title or '').casefold()
    head_ref = (pr.head.ref or '').casefold()
    if normalized_ticket_key not in title and normalized_ticket_key not in head_ref:
        logging.info(f"[{ticket_key}] Skipping GH PR check as title and head branch not related")
        return True

    return False


def add_comment(ticket: Issue, open_prs: list[GitHubSearchPullRequest]):
    ticket_key = ticket.key
    user = jira_client.fetch_myself().display_name or "JIRA"
    assignee_id = extract_assignee_id(ticket)
    reviewer_id = extract_reviewer_id(ticket)

    comment = {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": f"{user} (bot 🤖):",
                        "marks": [
                            {
                                "type": "strong"
                            },
                            {
                                "type": "underline"
                            }
                        ]
                    }
                ]
            },
            ## Optional mention
            *([{
                "type": "paragraph",
                "content": [
                    {
                        "type": "mention",
                        "attrs": {
                            "id": f"{assignee_id}"
                        }
                    }
                ]
            }] if assignee_id else []),
            ## Optional mention
            *([{
                "type": "paragraph",
                "content": [
                    {
                        "type": "mention",
                        "attrs": {
                            "id": f"{reviewer_id}"
                        }
                    }
                ]
            }] if reviewer_id else []),
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "GitHub Search found some pull requests that are still "
                    },
                    {
                        "type": "text",
                        "text": "OPEN",
                        "marks": [
                            {
                                "type": "underline"
                            }
                        ]
                    },
                    {
                        "type": "text",
                        "text": " on this Done ticket or its heading clone:"
                    }
                ]
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "inlineCard",
                                        "attrs": {
                                            "url": pr.html_url
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": " "
                                    }
                                ]
                            }
                        ]
                    } for pr in open_prs if not None
                ]
            },
            {
                "type": "paragraph",
                "content": []
            },
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "Please:"
                    }
                ]
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Check the PR status on GitHub;"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Or, consider to convert the PR into DRAFT;"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Or, if you want to suppress this type of scanning on this ticket, add this label: "
                                    },
                                    {
                                        "type": "text",
                                        "text": f"{whitelisted_label}",
                                        "marks": [
                                            {
                                                "type": "code"
                                            }
                                        ]
                                    },
                                    {
                                        "type": "text",
                                        "text": ";"
                                    },
                                ]
                            }
                        ]
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Or, setup a cloned ticket for proper follow-up"
                                    }
                                ]
                            }
                        ]
                    }

                ]
            }
        ]
    }

    jira_client.add_comment(ticket_key, comment)
    logging.info(f"[{ticket_key}] Added comment 🟡")

    return


def extract_reviewer_id(ticket: Issue) -> Optional[str]:
    reviewer_data = getattr(ticket.fields, reviewer_field, None)
    if reviewer_data:
        reviewer = UserAccount.from_dict(reviewer_data)
        return reviewer.account_id
    return None


def do_transition(ticket_key: str) -> None:
    """
    Perform the transition to "Reopen" state for a given ticket.
    :param ticket_key: Ticket in "Done" / "Accepted" status
    """

    ## Perform the transition once
    target_state = "Reopen (CAT)"
    perform_transition(ticket_key, target_state)
