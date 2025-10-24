class NovelParserError(Exception):
    pass


class ValidationError(NovelParserError):
    pass


class ParseError(NovelParserError):
    pass


class APIError(NovelParserError):
    pass
