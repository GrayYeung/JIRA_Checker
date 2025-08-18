import logging
from datetime import datetime, timedelta, timezone

from check_deployment_note import check_for_deployment_note
from helper.property import JIRA_SHOULD_CHECK_DEPLOYMENT_NOTE

## Log config
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


####

def main():
    hkt = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"Starting JIRA checking script at {hkt} (HKT)...")

    try:
        if JIRA_SHOULD_CHECK_DEPLOYMENT_NOTE:
            check_for_deployment_note()
        logging.info("Done JIRA checking script!")
    except Exception as e:
        logging.error(f"Unexpected error during JIRA checking: {e}")
        raise e


if __name__ == "__main__":
    main()
