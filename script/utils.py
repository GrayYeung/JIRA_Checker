import logging

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
