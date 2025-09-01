import logging
from datetime import datetime, timedelta, timezone

from environment import *
from exception.exceptionmodel import UnexpectedException
from script import check_for_deployment_note, check_for_linked_dependency

## Log config
logging.basicConfig(
    level=LOGGER_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
)


####

def main():
    hkt = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"Starting JIRA checking script at {hkt} (HKT)...")

    is_all_good = True

    try:
        if JIRA_SHOULD_CHECK_DEPLOYMENT_NOTE:
            result = check_for_deployment_note()
            if not result:
                is_all_good = False

        if JIRA_SHOULD_CHECK_LINKED_DEPENDENCY:
            result = check_for_linked_dependency()
            if not result:
                is_all_good = False
        logging.info("Done JIRA checking script!")
    except Exception as e:
        logging.error(f"Unexpected error during JIRA checking: {e}")
        raise e

    if not is_all_good:
        raise UnexpectedException("One or more checks failed. Please review the logs for details.")


if __name__ == "__main__":
    main()
