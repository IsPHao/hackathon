class StoryboardError(Exception):
    pass


class ValidationError(StoryboardError):
    pass


class ProcessError(StoryboardError):
    pass


class APIError(StoryboardError):
    pass
