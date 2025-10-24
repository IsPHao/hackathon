class BaseAgentError(Exception):
    pass


class ValidationError(BaseAgentError):
    pass


class APIError(BaseAgentError):
    pass


class StorageError(BaseAgentError):
    pass


class ProcessError(BaseAgentError):
    pass


class ParseError(BaseAgentError):
    pass


class GenerationError(BaseAgentError):
    pass


class SynthesisError(BaseAgentError):
    pass


class CompositionError(BaseAgentError):
    pass


class DownloadError(BaseAgentError):
    pass
