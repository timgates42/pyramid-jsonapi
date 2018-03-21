class Results:
    """Encapsulate the results of executed queries."""

    def __init__(self, is_collection, data=None, related=None):
        self.data = data or []
        self.related = related or {}

class Error:
    """Encapsulate an error condition."""

    def __init__(self, exception):
        self.exception = exception
