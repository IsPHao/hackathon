from abc import ABC, abstractmethod
from typing import Any, Dict
from uuid import UUID


class Agent(ABC):
    """
    Agent基类
    
    所有Agent必须继承此类并实现execute方法。
    
    注意：当前各个Agent实现使用了不同的方法名（如parse、generate、create等），
    这是为了保持API的语义清晰性。虽然不完全符合统一接口原则，但更符合实际使用场景。
    
    建议：
    1. 保持现有各Agent的专用方法名（parse、generate、synthesize等）
    2. 可选：为需要统一调用的场景实现execute方法作为适配器
    3. Pipeline直接调用各Agent的专用方法，保持代码可读性
    
    当前实现状态：
    - NovelParserAgent.parse() - 解析小说
    - ImageGeneratorAgent.generate() - 生成图像
    - VoiceSynthesizerAgent.synthesize() - 合成语音
    - StoryboardAgent.create() - 创建分镜
    - CharacterConsistencyAgent.manage() - 管理角色
    - VideoComposerAgent.compose() - 合成视频
    """
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """
        执行Agent的核心逻辑
        
        此方法定义了统一的Agent接口。各个具体Agent可以选择：
        1. 直接实现execute方法
        2. 实现专用方法（如parse、generate），并在execute中调用
        3. 仅实现专用方法，不实现execute（适用于明确场景）
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            Any: Agent执行结果
        
        Note:
            当前Pipeline实现直接调用各Agent的专用方法，
            而不是调用execute方法，以保持代码的可读性和明确性。
        """
        pass


class Pipeline(ABC):
    """
    Pipeline基类
    
    所有Pipeline必须继承此类并实现execute方法。
    """
    
    @abstractmethod
    async def execute(self, project_id: UUID, *args, **kwargs) -> Dict[str, Any]:
        """
        执行Pipeline的工作流
        
        Args:
            project_id: 项目唯一标识符
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            Dict[str, Any]: Pipeline执行结果
        """
        pass
