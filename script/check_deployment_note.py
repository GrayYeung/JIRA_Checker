import logging
import re

import requests

from environment import *
from jira import *
from jira.jiramodel import *


####

def check_for_deployment_note() -> None:
    """
    Step of checking:
    1. Sort-out potential target tickets
    2. Evaluate isTarget
    3. Perform transition to "Rework"
    4. Leave comment as notice
    """

    logging.info("Checking for Deployment Note... ⚠️")

    ticket_keys = fetch_tickets()
    logging.info("Found %d target ticket: %s", len(ticket_keys), ticket_keys)

    bad_tickets = []
    error_tickets = []
    for ticket_id in ticket_keys:
        logging.info(f"[{ticket_id}] Processing ticket...")

        try:
            remote_links_response: list[RemoteLink] = jira_client.fetch_remote_link(ticket_id)

            if not is_valid(remote_links_response, ticket_id):
                do_transition(ticket_id)
                add_comment(ticket_id)
                bad_tickets.append(ticket_id)
                continue
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

def fetch_tickets() -> list[str]:
    """
    :return: List of ticket Ids
    """

    # get the last week updated tickets with DeploymentNote label
    status_list = ['"DONE (Development)"', 'Accepted']
    time_range = "5d"  # e.g.: h,d,w
    project = JIRA_PROJECT_KEY

    jql = f'updated >= -{time_range} and labels IN (DeploymentNote) and status IN ({", ".join(status_list)}) and project = {project}'
    fields = ["assignee", "status"]

    params = SearchTicketsParams(
        jql=jql,
        fields=fields,
    )

    logging.info("Fetching tickets with JQL: '%s'...", jql)
    response: SearchTicketsResponse = jira_client.fetch_search(params)

    return [
        issue.key
        for issue in response.issues
    ]


def is_valid(remote_link_resp: list[RemoteLink], key: str) -> bool:
    """
    Validate by:
    1. Extract each remote link by `relationship` field
    2. Invoke the remote link API to examine its content

    :param key: Ticket key
    :param remote_link_resp: See fetch_remote_link
    :return: `true` if ticket contains a valid remote link
    """

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

            title = content.title
            if "release" in title.lower():
                logging.info(f"[{key}] Found valid remote link for page_id: {page_id} ✅")
                return True

    logging.info(f"[{key}] No valid remote links found")
    return False


def extract_page_id(url: str) -> str | None:
    ## Extract pageId from the query parameters of the URL
    match = re.search(r'pageId=(\d+)', url)
    if match:
        return match.group(1)
    return None


def do_transition(ticket_id: str) -> None:
    """
    Perform the transition to "Rework" state for a given ticket.
    :param ticket_id:
    """

    response: TransitionsResponse = jira_client.fetch_transitions(ticket_id)
    available_transitions = response.transitions
    target_state = "Rework"
    target_state_id = find_target_state_id(available_transitions, target_state)

    if not target_state_id:
        logging.error(f"[{ticket_id}] Target state '{target_state}' not found, trying to transit with special workflow")
        ## e.g.: for incident type
        perform_transition_for_special_workflow(ticket_id)
        return

    ## Perform the transition
    perform_transition(ticket_id, target_state)
    return


def find_target_state_id(transitions: list[Transition], target_state: str) -> str | None:
    for transition in transitions:
        if transition.to:
            if transition.to.name == target_state:
                return transition.id

    return None


def perform_transition(ticket_id: str, target_state: str) -> None:
    response: TransitionsResponse = jira_client.fetch_transitions(ticket_id)
    available_transitions = response.transitions
    target_state_id = find_target_state_id(available_transitions, target_state)

    if not target_state_id:
        logging.error(f"[{ticket_id}] Target state '{target_state}' not found")
        return

    ## Perform the transition
    jira_client.do_transition(ticket_id, target_state_id)
    logging.info(f"[{ticket_id}] Transited to '{target_state}'")
    return


def perform_transition_for_special_workflow(ticket_id: str) -> None:
    transition_states = [
        "Ready (for Testing)",
        "Testing In Progress",
        "Rework"
    ]

    for state in transition_states:
        perform_transition(ticket_id, state)


def add_comment(ticket_id: str) -> None:
    """
    Add a comment to the ticket to notify about the transition.
    For simplicity, we will use a static comment.

    :param ticket_id:
    """

    user = jira_client.fetch_myself().display_name or "JIRA"
    assignee_id = find_assignee_id(ticket_id)

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

    jira_client.add_comment(ticket_id, comment)
    logging.info(f"[{ticket_id}] Added comment")
    return


def find_assignee_id(ticket_id: str) -> str | None:
    """
    Find the assignee id of a ticket.
    :param ticket_id: The ID of the ticket
    """

    response: Issue = jira_client.fetch_issue(ticket_id)
    assignee = response.fields.assignee
    return assignee.account_id if assignee else None
