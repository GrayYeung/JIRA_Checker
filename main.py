import logging
from datetime import datetime, timedelta, timezone

from environment import *
from exception.exceptionmodel import UnexpectedException
from script import check_for_deployment_note, check_for_linked_dependency, check_open_git_pull_request

## Log config
logging.basicConfig(
    level=LOGGER_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
)


####

def main():
    hkt = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"Starting JIRA checking script at {hkt} (HKT)...")

    results = []

    try:
        if JIRA_SHOULD_CHECK_DEPLOYMENT_NOTE:
            result = check_for_deployment_note()
            results.append(result)

        if JIRA_SHOULD_CHECK_LINKED_DEPENDENCY:
            result = check_for_linked_dependency()
            results.append(result)

        check_open_git_pull_request()

        logging.info("Done JIRA checking script!")
    except Exception as e:
        logging.error(f"Unexpected error during JIRA checking: {e}")
        raise e

    is_all_good = all(results)
    if not is_all_good:
        ## Raise to trigger alert from GH Actions
        raise UnexpectedException("One or more checks failed. Please review the logs for details.")


if __name__ == "__main__":
    main()
