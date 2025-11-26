import logging
import re
from typing import Any

import requests

from environment import *
from exception.exceptionmodel import UnexpectedException
from jira import *
from jira.jiramodel import *
from .utils import print_conclusion, should_skip_by_label, extract_assignee_id

##
whitelisted_label = "SuppressScanning"


####

def check_for_deployment_note() -> bool:
    """
    Step of checking:
    1. Sort-out potential target tickets
    2. Evaluate isTarget
    3. Perform transition to "Rework"
    4. Leave comment as notice

    :return: `true` if all operations succeed
    """

    logging.info("Checking for Deployment Note... ⚠️")

    tickets = fetch_tickets()
    ticket_keys = [ticket.key for ticket in tickets]
    logging.info("Found %d target ticket: %s", len(ticket_keys), ticket_keys)

    bad_tickets: list[str] = []
    error_tickets: list[str] = []

    for ticket in tickets:
        ticket_key = ticket.key
        logging.info(f"[{ticket_key}] Processing ticket...")

        try:
            if should_skip_by_label(ticket, whitelisted_label):
                logging.info(f"[{ticket_key}] Skipping due to whitelisted label...")
                continue

            remote_links_response: list[RemoteLink] = jira_client.fetch_remote_link(ticket_key)

            if not is_valid(remote_links_response, ticket):
                ## Action
                do_transition(ticket_key)
                add_comment(ticket)

                bad_tickets.append(ticket_key)
                continue
        except (requests.exceptions.RequestException, UnexpectedException) as e:
            logging.error(f"[{ticket_key}] Encountered {type(e).__name__}: {e.message}")
            error_tickets.append(ticket_key)
            continue

    print_conclusion(bad_tickets, error_tickets)
    return len(error_tickets) == 0


####

def fetch_tickets() -> list[Issue]:
    ## get the last week updated tickets with DeploymentNote label
    status_list = ['"DONE (Development)"', 'Accepted']
    time_range = "5d"  # e.g.: h,d,w
    project = JIRA_PROJECT_KEY

    jql = f'updated >= -{time_range} and labels IN (DeploymentNote) and status IN ({", ".join(status_list)}) and project = {project}'
    fields = ["assignee", "status", "fixVersions"]

    params = SearchTicketsParams(
        jql=jql,
        fields=fields,
    )

    logging.info("Fetching tickets with JQL: '%s'...", jql)
    response: SearchTicketsResponse = jira_client.fetch_search(params)

    return response.issues


def is_valid(remote_link_resp: list[RemoteLink], ticket: Issue) -> bool:
    """
    Validate by:
    1. Extract each remote link by `relationship` field
    2. Invoke the remote link API to examine its content

    :param ticket: Ticket
    :param remote_link_resp: See fetch_remote_link
    :return: `true` if ticket contains a valid remote link
    """

    key = ticket.key

    if not remote_link_resp:
        logging.info(f"[{key}] No remote links found")
        return False

    for remote_link in remote_link_resp:
        if remote_link.relationship == "mentioned in":
            url = remote_link.object.url
            if not url:
                continue

            page_id = extract_page_id(url)
            if not page_id:
                continue

            content = jira_client.fetch_confluence_content(page_id)
            if not content:
                continue

            version = extract_version(content.title)
            if not version:
                continue

            is_match = is_match_with_issue(version, ticket)
            if is_match:
                logging.info(f"[{key}] Found valid remote link for page_id: {page_id} ✅")
                return True

    logging.info(f"[{key}] No valid remote links found")
    return False


def extract_page_id(url: str) -> Optional[str]:
    ## Extract pageId from the query parameters of the URL
    match = re.search(r'pageId=(\d+)', url)
    if match:
        return match.group(1)
    return None


def extract_version(title: str) -> Optional[str]:
    """
    :param title: Assume title contain "Release X.Y.Z" or "Release some feature" pattern
    :return: "X.Y.Z" or "some feature"
    """

    title = title.lower()
    match = re.search(r'release(.*)', title)
    if match:
        return match.group(1).strip()
    return None


def is_match_with_issue(candidate: str, ticket: Issue) -> bool:
    versions = getattr(ticket.fields, "fixVersions", None) if ticket.fields else None
    if not versions:
        return False

    for version_data in versions:
        version = FixVersion.from_dict(version_data)
        if version.name:
            extracted_name = extract_version(version.name)
            ## Assume either candidate will be shorter or extracted_name will be shorter
            if candidate.lower() in extracted_name.lower() or extracted_name.lower() in candidate.lower():
                return True

    return False


## TODO: move to util
def do_transition(ticket_key: str) -> None:
    """
    Perform the transition to "Rework" state for a given ticket.
    :param ticket_key: Ticket in "DONE (Development)" status; Assume "Accepted" status cannot do transition
    """

    try:
        ## Perform the transition once
        target_state = "Rework"
        perform_transition(ticket_key, target_state)
    except UnexpectedException:
        ## e.g.: for incident type
        perform_transition_for_special_workflow(ticket_key)


def find_target_transition_id(transitions: list[Transition], target_state: str) -> str | None:
    for transition in transitions:
        if transition.to:
            if transition.to.name == target_state:
                return transition.id

    return None


## TODO: extract out
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


def perform_transition_for_special_workflow(ticket_key: str) -> None:
    transition_states = [
        "Ready (for Testing)",
        "Testing In Progress",
        "Rework"
    ]

    for state in transition_states:
        perform_transition(ticket_key, state)


def add_comment(ticket: Issue) -> None:
    """
    Add a comment to the ticket to notify about the transition.
    For simplicity, we will use a static comment.
    """

    ticket_key = ticket.key
    user = jira_client.fetch_myself().display_name or "JIRA"
    assignee_id = extract_assignee_id(ticket)

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
                        "text": "This issue is reopened because it is labelled with "
                    },
                    {
                        "type": "text",
                        "text": "DeploymentNote",
                        "marks": [
                            {
                                "type": "code"
                            }
                        ]
                    },
                    {
                        "type": "text",
                        "text": ", and has transitioned to "
                    },
                    {
                        "type": "text",
                        "text": "Done",
                        "marks": [
                            {
                                "type": "code"
                            }
                        ]
                    },
                    {
                        "type": "text",
                        "text": ";"
                    }
                ]
            },
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "However, cannot find any "
                    },
                    {
                        "type": "text",
                        "text": "mentioned on",
                        "marks": [
                            {
                                "type": "code"
                            }
                        ]
                    },
                    {
                        "type": "text",
                        "text": " in the "
                    },
                    {
                        "type": "text",
                        "text": "Confluence content",
                        "marks": [
                            {
                                "type": "code"
                            }
                        ]
                    },
                    {
                        "type": "text",
                        "text": " section."
                    }
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
                                        "text": "Prepare the Deployment Note;"
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
                                        "text": "Or, if there is, make sure that the Confluence page for Release has "
                                    },
                                    {
                                        "type": "text",
                                        "text": "explicitly",
                                        "marks": [
                                            {
                                                "type": "em"
                                            },
                                            {
                                                "type": "underline"
                                            }
                                        ]
                                    },
                                    {
                                        "type": "text",
                                        "text": " mentioned this ticket key"
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
