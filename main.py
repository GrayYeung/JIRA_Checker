import logging
from datetime import datetime, timedelta, timezone

from environment import *
from script import check_for_deployment_note, check_for_linked_dependency

## Log config
logging.basicConfig(
    level=LOGGER_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
)


####

def main():
    hkt = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"Starting JIRA checking script at {hkt} (HKT)...")

    try:
        if JIRA_SHOULD_CHECK_DEPLOYMENT_NOTE:
            check_for_deployment_note()

        if JIRA_SHOULD_CHECK_LINKED_DEPENDENCY:
            check_for_linked_dependency()
        logging.info("Done JIRA checking script!")
    except Exception as e:
        logging.error(f"Unexpected error during JIRA checking: {e}")
        raise e


if __name__ == "__main__":
    main()
