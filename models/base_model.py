from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseModel(ABC):
    """所有AI模型的抽象基类"""

    @abstractmethod
    def predict(self, input_data: Dict[str, Any]) -> float:
        """
        同步预测接口，返回一个浮点数信号（例如情绪分数）
        input_data: 包含模型所需字段，如新闻标题、文本等
        """
        pass

    @abstractmethod
    async def apredict(self, input_data: Dict[str, Any]) -> float:
        """异步预测接口，用于实盘异步调用"""
        pass

    @abstractmethod
    def batch_predict(self, inputs: list) -> list:
        """批量预测，用于回测预计算"""
        pass

