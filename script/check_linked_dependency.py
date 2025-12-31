import logging

import requests

from environment import *
from jira import *
from jira.jiramodel import *
from .utils import print_conclusion, should_skip_by_label, extract_reporter_id, extract_issuelinks

##
sprint_field = "customfield_10122"  # This is the field ID for the Sprint field in JIRA
whitelisted_label = "SuppressScanning"


####


def check_for_linked_dependency():
    """
    :return: `true` if ticket contains a valid remote link
    """
    logging.info("Checking for linked dependencies... ⚠️")

    tickets = fetch_tickets()
    ticket_keys = [ticket.key for ticket in tickets]
    logging.info(f"Found {len(ticket_keys)} tickets with linked dependencies: {ticket_keys}")

    bad_tickets: list[str] = []
    error_tickets: list[str] = []

    for ticket in tickets:
        ticket_key = ticket.key
        warnings = []

        try:
            if should_skip_by_label(ticket, whitelisted_label):
                logging.info(f"[{ticket_key}] Skipping due to whitelisted label...")
                continue

            ticket_sprints = extract_sprints(ticket)
            if not ticket_sprints:
                logging.info(f"[{ticket_key}] Skipping due to no sprint...")
                continue

            linked_issues = extract_issuelinks(ticket)
            if not linked_issues:
                logging.info(f"[{ticket_key}] Skipping due to no linked issues found...")
                continue

            for linked_issue in linked_issues:
                if not should_process(linked_issue):
                    logging.info(f"[{ticket_key}] Skipping due to not in target relations...")
                    continue

                ## only concerns start
                logging.info(f"[{ticket_key}] Processing ticket on {linked_issue}...")

                if linked_issue.inward_issue:
                    linked_ticket = jira_client.fetch_issue(linked_issue.inward_issue.key)
                    linked_ticket_sprints = extract_sprints(linked_ticket)

                    if not is_origin_started_later(ticket_sprints, linked_ticket_sprints):
                        msg = f"{ticket_key} should be at later/same sprint than {linked_ticket.key}"
                        logging.warning(f"[{ticket_key}] {msg} (Linked ticket) ❌")
                        warnings.append(msg)

                if linked_issue.outward_issue:
                    linked_ticket = jira_client.fetch_issue(linked_issue.outward_issue.key)
                    linked_ticket_sprints = extract_sprints(linked_ticket)

                    if not is_origin_started_earlier(ticket_sprints, linked_ticket_sprints):
                        msg = f"{ticket_key} should be at earlier/same sprint than {linked_ticket.key}"
                        logging.warning(f"[{ticket_key}] {msg} (Linked ticket) ❌")
                        warnings.append(msg)

            if warnings:
                logging.info(f"[{ticket_key}] Found {len(warnings)} warnings, adding to ticket comments...")

                ## Action
                add_comment(ticket, warnings)

                bad_tickets.append(f"{ticket_key} ({len(warnings)})")

        except requests.exceptions.RequestException as e:
            logging.error(f"[{ticket_key}] Encountered RequestException: {e}")
            error_tickets.append(ticket_key)
            continue

    print_conclusion(bad_tickets, error_tickets)
    return len(error_tickets) == 0


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


def extract_sprints(ticket: Issue) -> list[Sprint]:
    """
    Expect this parsing will be used in this script only
    """
    sprints = getattr(ticket.fields, sprint_field, None)
    if sprints and isinstance(sprints, list):
        return [Sprint.from_dict(sprint) for sprint in sprints if isinstance(sprint, dict)]
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


def add_comment(ticket: Issue, warnings: list[str]) -> None:
    """
    Add a comment to the ticket.
    """

    ticket_key = ticket.key
    user = jira_client.fetch_myself().display_name or "JIRA"
    reporter_id = extract_reporter_id(ticket)

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
                            "id": f"{reporter_id}"
                        }
                    }
                ]
            }] if reporter_id else []),
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

    jira_client.add_comment(ticket_key, comment)
    logging.info(f"[{ticket_key}] Added comment")

    return
