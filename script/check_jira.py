import logging
import os
import re
from datetime import datetime, timedelta, timezone

import requests

## JIRA config
JIRA_TOKEN = os.getenv('JIRA_TOKEN')
JIRA_DOMAIN = os.getenv('JIRA_DOMAIN')
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY')


## Log config
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


####
def check_for_deployment_note() -> None:
    """
    Step of checking:
    1. Sort-out potential target tickets
    2. Evaluate isTarget
    3. Perform transition to "Rework"
    4. Leave comment as notice
    """

    ticket_keys = fetch_tickets()
    logging.info("Found %d target ticket: %s", len(ticket_keys), ticket_keys)

    bad_tickets = []
    error_tickets = []
    for ticket_id in ticket_keys:
        logging.info(f"[{ticket_id}] Processing ticket...")

        try:
            remote_links = fetch_remote_link(ticket_id)

            if not is_valid(remote_links, ticket_id):
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

    url = f"https://{JIRA_DOMAIN}/rest/api/3/search"

    # get the last week updated tickets with DeploymentNote label
    status_list = ['"DONE (Development)"', 'Accepted']
    time_range = "5d"  # e.g.: h,d,w
    project = JIRA_PROJECT_KEY

    jql = f'updated >= -{time_range} and labels IN (DeploymentNote) and status IN ({", ".join(status_list)}) and project = {project}'
    fields = "assignee,status"

    params = {
        "jql": jql,
        "fields": fields,
        "maxResults": 200,
    }

    logging.info("Fetching tickets with JQL: '%s'...", jql)
    response = requests.get(url, headers=__create_header(), params=params)
    response.raise_for_status()

    return [
        issue["key"]
        for issue in response.json().get("issues", [])
    ]


def __create_header() -> dict[str, str]:
    """
    Create headers for JIRA API requests.
    :return: Dictionary of headers
    """

    return {
        "Authorization": f"Basic {JIRA_TOKEN}",
        "Accept": "application/json"
    }


def fetch_remote_link(ticket_id: str) -> list[dict]:
    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/{ticket_id}/remotelink"

    response = requests.get(url, headers=__create_header())
    response.raise_for_status()

    return response.json()


def is_valid(remote_link_resp: list[dict], key: str) -> bool:
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
        if remote_link.get("relationship") == "mentioned in":
            url = remote_link.get("object", {}).get("url")
            if not url:
                continue

            page_id = extract_page_id(url)
            if not page_id:
                continue

            content = fetch_confluence_content(page_id)
            if not content:
                continue

            title = content["title"]
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


def fetch_confluence_content(page_id: str) -> dict | None:
    url = f"https://{JIRA_DOMAIN}/wiki/api/v2/pages/{page_id}"

    try:
        response = requests.get(url, headers=__create_header())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Confluence content for page {page_id}: {e}")
        return None


def do_transition(ticket_id: str) -> None:
    """
    Perform the transition to "Rework" state for a given ticket.
    :param ticket_id:
    """

    available_transitions = fetch_transitions(ticket_id)

    target_state = "Rework"
    target_state_id = find_target_state_id(available_transitions, target_state)

    if not target_state_id:
        logging.error(f"[{ticket_id}] Target state '{target_state}' not found")
        return

    ## Perform the transition

    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/{ticket_id}/transitions"

    payload = {
        "transition": {
            "id": target_state_id
        }
    }

    response = requests.post(url, headers=__create_header(), json=payload)
    response.raise_for_status()

    logging.info(f"[{ticket_id}] Transited to '{target_state}'")
    return


def fetch_transitions(ticket_id: str) -> list[dict]:
    """Fetch available transitions for a ticket."""

    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/{ticket_id}/transitions"

    response = requests.get(url, headers=__create_header())
    response.raise_for_status()

    return response.json().get("transitions", [])


def find_target_state_id(transitions: list[dict], target_state: str) -> str | None:
    for transition in transitions:
        if transition.get("name") == target_state:
            return transition.get("id")

    return None


def add_comment(ticket_id: str) -> None:
    """
    Add a comment to the ticket to notify about the transition.
    For simplicity, we will use a static comment.

    :param ticket_id:
    """

    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/{ticket_id}/comment"

    user = "Gray"
    assignee_id = find_assignee_id(ticket_id)

    payload = {
        "body": {
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
    }

    response = requests.post(url, headers=__create_header(), json=payload)
    response.raise_for_status()

    logging.info(f"[{ticket_id}] Added comment")
    return

def find_assignee_id(ticket_id: str) -> str | None:
    """
    Find the assignee id of a ticket.
    :param ticket_id: The ID of the ticket
    """

    response = fetch_ticket(ticket_id)
    assignee = response.get("fields", {}).get("assignee")
    return assignee.get("accountId") if assignee else None

def fetch_ticket(ticket_id: str) -> dict:
    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue/{ticket_id}"

    response = requests.get(url, headers=__create_header())
    response.raise_for_status()

    return response.json()


####

def main():
    hkt = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"Starting JIRA checking script at {hkt} (HKT)...")

    try:
        check_for_deployment_note()
        logging.info("Done JIRA checking script!")
    except Exception as e:
        logging.error(f"Unexpected error during JIRA checking: {e}")
        raise e


if __name__ == "__main__":
    main()
