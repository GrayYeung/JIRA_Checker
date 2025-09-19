import logging

import requests

from environment import *
from exception.exceptionmodel import UnexpectedException
from jira import *
from jira.dev_summary_panel_model import *
from jira.jiramodel import *
from .utils import print_conclusion


###

def check_github() -> bool:
    """
    Ride on Git plugin in JIRA to check if there is any open PR for the issue.
    """
    logging.info("Checking for open git pull request... ⚠️")

    tickets = fetch_tickets()
    ticket_ids = [ticket.key for ticket in tickets]
    logging.info(f"Found {len(ticket_ids)} tickets: {ticket_ids}")

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

            resp = jira_client.get_dev_summary_panel_one_click_urls(issue_id)

            github_instance = extract_github_instance(resp)
            if not github_instance:
                logging.info(f"[{ticket_key}] Skipping due to no GitHub trace found...")
                continue

            open_prs = find_open_prs(github_instance)
            if not open_prs:
                logging.info(f"[{ticket_key}] No open Pull Request found. All good ✅")
                continue

            logging.info(f"[{ticket_key}] Found {len(open_prs)} open pull requests ❌")
            ## Action
            add_comment(ticket_key, open_prs)

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
    status_list = ['"DONE (Development)"', 'Accepted']
    time_range = "5d"  # e.g.: h,d,w
    time_buffer = "1d"  # e.g.: h,d,w; for cache buffer on info
    project = JIRA_PROJECT_KEY

    jql = f'updated >= -{time_range} and updated < -{time_buffer} and sprint != empty and status IN ({", ".join(status_list)}) and project = {project}'
    fields = ["assignee", "status"]

    params = SearchTicketsParams(
        jql=jql,
        fields=fields,
    )

    logging.info("Fetching tickets with JQL: '%s'...", jql)
    response: SearchTicketsResponse = jira_client.fetch_search(params)

    return response.issues


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


def find_open_prs(github: InstanceType) -> List[PullRequest]:
    result: list[PullRequest] = []

    if github.danglingPullRequests:
        opens = [pr for pr in github.danglingPullRequests if pr.status and pr.status == 'OPEN']
        result.extend(opens)

    if github.repository:
        for repo in github.repository:
            if repo.pullRequests:
                opens = [pr for pr in repo.pullRequests if pr.status and pr.status == 'OPEN']
                result.extend(opens)

    return result


def add_comment(ticket_id, open_prs):
    pass
