import logging


###

def print_conclusion(bad_tickets: list[str], error_tickets: list[str]):
    logging.info("Conclusion: \n%d bad tickets: %s, \n%d error tickets: %s",
                 len(bad_tickets), bad_tickets,
                 len(error_tickets), error_tickets
                 )
