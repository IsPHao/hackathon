class PipelineError(Exception):
    """工作流执行错误,当Pipeline执行失败时抛出"""
    pass


class PipelineStageError(PipelineError):
    """
    Pipeline阶段错误
    
    当Pipeline在特定阶段失败时抛出,保留错误链和阶段信息。
    
    Attributes:
        stage: 失败的阶段名称
        original_error: 原始异常对象
    """
    
    def __init__(self, stage: str, original_error: Exception):
        self.stage = stage
        self.original_error = original_error
        super().__init__(f"Pipeline failed at stage '{stage}': {original_error}")


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
