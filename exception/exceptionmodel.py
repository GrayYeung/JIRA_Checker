class UnexpectedException(Exception):
    """Custom exception for unexpected errors."""

    def __init__(self, message="Expected error occurred"):
        self.message = message
        super().__init__(self.message)
