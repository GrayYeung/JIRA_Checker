import logging
import re
from typing import Any

import requests

from exception.exceptionmodel import UnexpectedException
from jira import *
from jira.jiramodel import *


###

def should_skip_by_label(ticket: Issue, whitelisted_label: str) -> bool:
    labels = getattr(ticket.fields, "labels", None) if ticket.fields else None
    if labels:
        if whitelisted_label in labels:
            return True

    return False


def should_skip_by_tailing_next_part(ticket: Issue) -> bool:
    issue_links = extract_issuelinks(ticket)
    for link in issue_links:
        if link.type.inward == "is cloned by":
            inward_issue = getattr(link, "inward_issue", None)
            if not inward_issue:
                continue

            cloned_ticket_summary = inward_issue.fields.get("summary", "")

            ## part N or Part N
            regex_pattern = r".*\b[Pp][Aa][Rr][Tt]\s*\d+.*$"
            if re.match(regex_pattern, cloned_ticket_summary):
                return True

            ## CLONE - ${original_summary}
            if "CLONE" in cloned_ticket_summary:
                return True

    return False


def extract_issuelinks(ticket: Issue) -> list[IssueLink]:
    issue_links = getattr(ticket.fields, "issuelinks", None)
    if issue_links and isinstance(issue_links, list):
        return [IssueLink.from_dict(link) for link in issue_links if isinstance(link, dict)]
    return []


def extract_assignee_id(ticket: Issue) -> Optional[str]:
    """
    Find the assignee id of a ticket.
    """

    assignee = ticket.fields.assignee
    return assignee.account_id if assignee else None


def extract_reporter_id(ticket: Issue) -> Optional[str]:
    """
    Find the reporter id of a ticket.
    """

    reporter = ticket.fields.reporter
    return reporter.account_id if reporter else None


def print_conclusion(bad_tickets: list[str], error_tickets: list[str]):
    logging.info("Conclusion: \n%d bad tickets: %s, \n%d error tickets: %s",
                 len(bad_tickets), bad_tickets,
                 len(error_tickets), error_tickets
                 )


def perform_transition(ticket_key: str, target_state: str) -> None:
    response: TransitionsResponse = jira_client.fetch_transitions(ticket_key)
    available_transitions = response.transitions
    target_transition_id = find_target_transition_id(available_transitions, target_state)

    if not target_transition_id:
        error_msg = f"[{ticket_key}] Target state '{target_state}' not found"
        logging.error(error_msg)
        raise UnexpectedException(error_msg)

    additional_fields_dict: dict[str, Any] = {}

    ## To "Rework" / "Reopen", the reason is mandatory
    reopen_or_rework_reason_field_id = "customfield_13259"
    code_review_feedback_id = "14403"
    if target_state == "Rework":
        set_fields = {
            "fields": {
                reopen_or_rework_reason_field_id: [
                    {
                        "id": code_review_feedback_id
                    }
                ]
            }
        }
        additional_fields_dict.update(set_fields)

    if target_state == "Reopen (CAT)":
        set_fields = {
            "fields": {
                reopen_or_rework_reason_field_id: [
                    {
                        "id": code_review_feedback_id
                    }
                ]
            }
        }

        ### Explicitly patch since transition not support that field update in one go
        jira_client.update_ticket_fields(ticket_key, set_fields)
        logging.info(f"[{ticket_key}] Patched ticket with Reopen/Rework reason field")

    ## Perform the transition
    try:
        jira_client.do_transition(
            ticket_key,
            target_transition_id,
            additional_fields_dict if additional_fields_dict else None
        )
    except requests.exceptions.RequestException:
        ## some issue type did not contain the additional fields
        jira_client.do_transition(ticket_key, target_transition_id)

    logging.info(f"[{ticket_key}] Transited to '{target_state}' (id: {target_transition_id})")
    return


def find_target_transition_id(transitions: list[Transition], target_state: str) -> str | None:
    for transition in transitions:
        if transition.to:
            if transition.to.name == target_state:
                return transition.id

    return None
