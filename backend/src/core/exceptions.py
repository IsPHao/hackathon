class PipelineError(Exception):
    """工作流执行错误,当Pipeline执行失败时抛出"""
    pass


class AgentError(Exception):
    """Agent执行错误,当Agent执行失败时抛出"""
    pass


class RetryExhaustedError(Exception):
    """重试次数耗尽错误,当所有重试尝试都失败后抛出"""
    pass


class ValidationError(Exception):
    """数据验证错误,当输入数据不符合预期格式时抛出"""
    pass


class APIError(Exception):
    """外部API调用错误,当调用第三方API失败时抛出"""
    pass
