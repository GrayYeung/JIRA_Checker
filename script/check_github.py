import logging
import re

import requests

from environment import *
from exception.exceptionmodel import UnexpectedException
from github import github_client
from jira import *
from jira.dev_summary_panel_model import *
from jira.jiramodel import *
from .utils import print_conclusion, should_skip_by_label, should_skip_by_tailing_next_part, extract_assignee_id, \
    perform_transition, find_heading_ticket, determine_relationship

##
reviewer_field = "customfield_11696"  # This is the field ID for the Reviewer field in JIRA
whitelisted_label = "SuppressScanning"


####

def check_for_github() -> bool:
    """
    Ride on Git plugin in JIRA to check if there is any open PR for the issue.
    """
    logging.info("Checking for open git pull request... ⚠️")

    tickets = fetch_tickets()
    ticket_keys = [ticket.key for ticket in tickets]
    logging.info(f"Found {len(ticket_keys)} tickets: {ticket_keys}")

    bad_tickets: list[str] = []
    error_tickets: list[str] = []

    for ticket in tickets:
        ticket_key = ticket.key
        issue_id = ticket.id

        try:
            if not issue_id:
                logging.error(f"[{ticket_key}] Missing issue_id")
                error_tickets.append(ticket_key)
                continue

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
            logging.error(f"[{ticket_key}] Encountered {type(e).__name__}: {e.message}")
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
    fields = ["assignee", "status", "labels", "issuelinks", "summary", reviewer_field]

    params = SearchTicketsParams(
        jql=jql,
        fields=fields,
    )

    logging.info("Fetching tickets with JQL: '%s'...", jql)
    response: SearchTicketsResponse = jira_client.fetch_search(params)

    return response.issues


def nest_check_open_prs(ticket: Issue, linked_ticket_key: Optional[str]) -> list[PullRequest]:
    ticket_key = ticket.key
    issue_id = ticket.id

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
    resp = jira_client.get_dev_summary_panel_one_click_urls(issue_id)

    github_instance = extract_github_instance(resp)
    if not github_instance:
        logging.info(
            f"[{determine_relationship(ticket_key, linked_ticket_key)}] Skipping due to no GitHub trace found..."
        )
        return []

    result = extract_open_prs(github_instance)
    logging.info(f"[{determine_relationship(ticket_key, linked_ticket_key)}] Open PRs: {len(result)}")
    return result


def extract_github_instance(resp: DevSummaryPanelResponse) -> Optional[InstanceType]:
    if resp \
            and resp.data \
            and resp.data.developmentInformation \
            and resp.data.developmentInformation.details \
            and resp.data.developmentInformation.details.instanceTypes:
        instance_types = resp.data.developmentInformation.details.instanceTypes
        github_instance = next((it for it in instance_types if it.type == 'GitHub'), None)
        return github_instance

    return None


def extract_open_prs(github: InstanceType) -> list[PullRequest]:
    """
    Extract all OPEN PRs from a GitHub instance. (DRAFT is allowed)
    """
    result: list[PullRequest] = []

    if github.danglingPullRequests:
        opens = [pr for pr in github.danglingPullRequests if pr.status and pr.status == 'OPEN']
        for open_pr in opens:
            url = open_pr.url
            if not check_with_gh(url):
                result.append(open_pr)

    if github.repository:
        for repo in github.repository:
            if repo.pullRequests:
                opens = [pr for pr in repo.pullRequests if pr.status and pr.status == 'OPEN']
                for open_pr in opens:
                    url = open_pr.url
                    if not check_with_gh(url):
                        result.append(open_pr)

    return result


def check_with_gh(url: str | None) -> bool:
    """
    :return TRUE if the status at gh is closed.
    """
    if not url:
        return False

    ## Example URL: https://github.com/owner/repo/pull/123
    m = re.match(r"https://github.com/([^/]+)/([^/]+)/pull/(\d+)", url)
    if not m:
        return False

    owner, repo, pr_number = m.group(1), m.group(2), m.group(3)
    pr = github_client.fetch_pr(owner, repo, pr_number)

    ## Consider closed if state is 'closed' or merged_at is not None
    return pr.state == 'closed' or pr.merged_at is not None


def add_comment(ticket: Issue, open_prs: list[PullRequest]):
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
                        "text": "From 'Development' session by GitHub plugin, found some PRs are still "
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
                                            "url": pr.url
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
