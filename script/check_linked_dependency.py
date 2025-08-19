import logging

import requests

from environment import *
from jira import *
from jira.jiramodel import *

##
sprint_field = "customfield_10122"  # This is the field ID for the Sprint field in JIRA
whitelisted_label = "SuppressScanning"


####


def check_for_linked_dependency():
    logging.info("Checking for linked dependencies... ⚠️")

    tickets = fetch_tickets()
    ticket_ids = [ticket.key for ticket in tickets]
    logging.info(f"Found {len(ticket_ids)} tickets with linked dependencies: {ticket_ids}")

    bad_tickets = []
    error_tickets = []

    for ticket in tickets:
        ticket_id = ticket.key
        warnings = []

        try:
            if should_skip_by_label(ticket):
                logging.info(f"[{ticket_id}] Skipping due to whitelisted label...")
                continue

            ticket_sprints = extract_sprints(ticket)
            if not ticket_sprints:
                logging.info(f"[{ticket_id}] Skipping due to no sprint...")
                continue

            linked_issues = extract_issuelinks(ticket)
            if not linked_issues:
                logging.info(f"[{ticket_id}] Skipping due to no linked issues found...")
                continue

            for linked_issue in linked_issues:
                if not should_process(linked_issue):
                    logging.info(f"[{ticket_id}] Skipping due to not in target relations...")
                    continue

                ## only concerns start
                logging.info(f"[{ticket_id}] Processing ticket on {linked_issue}...")

                if linked_issue.inward_issue:
                    linked_ticket = jira_client.fetch_issue(linked_issue.inward_issue.key)
                    linked_ticket_sprints = extract_sprints(linked_ticket)

                    if not is_origin_started_later(ticket_sprints, linked_ticket_sprints):
                        msg = f"{ticket_id} should be at later/same sprint than {linked_ticket.key}"
                        logging.warning(f"[{ticket_id}] {msg} (Linked ticket) ❌")
                        warnings.append(msg)

                if linked_issue.outward_issue:
                    linked_ticket = jira_client.fetch_issue(linked_issue.outward_issue.key)
                    linked_ticket_sprints = extract_sprints(linked_ticket)

                    if not is_origin_started_earlier(ticket_sprints, linked_ticket_sprints):
                        msg = f"{ticket_id} should be at earlier/same sprint than {linked_ticket.key}"
                        logging.warning(f"[{ticket_id}] {msg} (Linked ticket) ❌")
                        warnings.append(msg)

            if warnings:
                logging.info(f"[{ticket_id}] Found {len(warnings)} warnings, adding to ticket comments...")
                add_comment(ticket_id, warnings)
                bad_tickets.append(f"{ticket_id} ({len(warnings)})")

        except requests.exceptions.RequestException as e:
            logging.error(f"[{ticket_id}] Encountered RequestException: {e}")
            error_tickets.append(ticket_id)
            continue

    logging.info("Conclusion: \n%d bad tickets: %s, \n%d error tickets: %s",
                 len(bad_tickets), bad_tickets,
                 len(error_tickets), error_tickets
                 )
    return


####

def fetch_tickets() -> list[Issue]:
    ## get the last week updated tickets with sprint values
    status_list = ['Backlog', 'New']
    time_range = "5d"  # e.g.: h,d,w
    project = JIRA_PROJECT_KEY

    jql = f'updated >= -{time_range} and sprint != empty and issueLinkType IS NOT EMPTY and status IN ({", ".join(status_list)}) and project = {project}'
    fields = ["assignee", "status", "labels", f"{sprint_field}", "issuelinks"]

    params = SearchTicketsParams(
        jql=jql,
        fields=fields,
    )

    logging.info("Fetching tickets with JQL: '%s'...", jql)
    response: SearchTicketsResponse = jira_client.fetch_search(params)

    return response.issues


def should_skip_by_label(ticket: Issue) -> bool:
    labels = ticket.fields.labels
    if labels:
        if whitelisted_label in labels:
            return True

    return False


def extract_sprints(ticket: Issue) -> list[Sprint]:
    """
    Expect this parsing will be used in this script only
    """
    sprints = getattr(ticket.fields, sprint_field, None)
    if sprints and isinstance(sprints, list):
        return [Sprint.from_dict(sprint) for sprint in sprints if isinstance(sprint, dict)]
    return []


def extract_issuelinks(ticket: Issue) -> list[IssueLink]:
    """
    Expect this parsing will be used in this script only
    """
    issue_links = getattr(ticket.fields, "issuelinks", None)
    if issue_links and isinstance(issue_links, list):
        return [IssueLink.from_dict(link) for link in issue_links if isinstance(link, dict)]
    return []


def should_process(issue_link: IssueLink) -> bool:
    """
    Check if the issue link is of a type that indicates a dependency relationship.
    """

    if not issue_link:
        return False

    target_type_names = [
        "Gantt Start to End",  ## "start is earliest end of" / "earliest end is start of"
        "Gantt End to Start"  ## "has to be done after" / "has to be done before"
    ]

    return issue_link.type.name in target_type_names


def is_origin_started_earlier(origin: list[Sprint], compare: list[Sprint]) -> bool:
    """
    Check if the earliest start date of the origin sprints is earlier than or equal to the earliest start date of the compare sprints.
    """
    logging.debug(f"Checking if {origin} is earlier than {compare}")

    soonest_origin = min(
        (sprint.start_date for sprint in origin if sprint.start_date),
        default=None
    )
    soonest_compare = min(
        (sprint.start_date for sprint in compare if sprint.start_date),
        default=None
    )

    ## Sprint value at value to None
    if not soonest_origin and not soonest_compare:
        return True

    if not soonest_origin and soonest_compare:
        return False

    if soonest_origin and not soonest_compare:
        return True

    return soonest_origin <= soonest_compare  ## equal is inclusive


def is_origin_started_later(origin: list[Sprint], compare: list[Sprint]) -> bool:
    return is_origin_started_earlier(compare, origin)  ## swap the order due to equal is inclusive


def add_comment(ticket_id: str, warnings: list[str]) -> None:
    """
    Add a comment to the ticket.
    """

    user = jira_client.fetch_myself().display_name or "JIRA"
    assignee_id = find_reporter_id(ticket_id)

    comment = {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": f"{user} (bot):",
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
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "Found invalid dependency relationships:"
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
                                        "text": warning
                                    }
                                ]
                            }
                        ]
                    } for warning in warnings
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
                                        "text": "Check if the sprint value or linked relationship is as expected;"
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
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }

    jira_client.add_comment(ticket_id, comment)
    logging.info(f"[{ticket_id}] Added comment")

    return


def find_reporter_id(ticket_id: str) -> str | None:
    """
    Find the reporter id of a ticket.
    :param ticket_id: The ID of the ticket
    """

    response: Issue = jira_client.fetch_issue(ticket_id)
    reporter = response.fields.reporter
    return reporter.account_id if reporter else None
