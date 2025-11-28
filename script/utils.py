import logging
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
    if target_state == "Rework":
        ## To "Rework", the reason is mandatory
        reopen_or_rework_reason_field_id = "customfield_13259"
        code_review_feedback_id = "14403"

        additional_fields = {
            "fields": {
                reopen_or_rework_reason_field_id: [
                    {
                        "id": code_review_feedback_id
                    }
                ]
            }
        }
        additional_fields_dict.update(additional_fields)

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

    logging.info(f"[{ticket_key}] Transited to '{target_state}' ({target_transition_id})")
    return


def find_target_transition_id(transitions: list[Transition], target_state: str) -> str | None:
    for transition in transitions:
        if transition.to:
            if transition.to.name == target_state:
                return transition.id

    return None
