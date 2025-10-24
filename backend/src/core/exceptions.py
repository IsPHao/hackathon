class PipelineError(Exception):
    pass


class AgentError(Exception):
    pass


class RetryExhaustedError(Exception):
    pass


class ValidationError(Exception):
    pass


class APIError(Exception):
    pass
