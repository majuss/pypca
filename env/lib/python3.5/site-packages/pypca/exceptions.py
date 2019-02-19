"""The exceptions used by pypca."""


class PCAException(Exception):
    """Class to throw general PCA exception."""

    def __init__(self, error, details=None):
        """Initialize PCAException."""
        # Call the base class constructor with the parameters it needs
        super(PCAException, self).__init__(error[1])

        self.errcode = error[0]
        self.message = error[1]
        self.details = details