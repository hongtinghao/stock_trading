import time

from .base_model import BaseModel
from zhipuai import ZhipuAI
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
import json

logger = logging.getLogger(__name__)


class ZhipuModel(BaseModel):
    """智谱AI模型封装，使用官方SDK"""

    def __init__(self, api_key: str, model_name: str, timeout: int = 10):
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        # 初始化客户端
        self.client = ZhipuAI(api_key=api_key, timeout=timeout)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def predict(self, input_data: dict) -> float:
        """
        输入: {'headline': '新闻标题', 'content': '新闻内容'}
        返回: 情绪分数 -1.0 ~ 1.0
        """
        prompt = self._build_prompt(input_data)
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=50,
                top_p=0.7,
                request_id=None  # 可选
            )
            # 解析返回内容
            result_text = response.choices[0].message.content
            time.sleep(2)
            score = self._parse_score(result_text)
            return score
        except Exception as e:
            logger.error(f"智谱API调用失败: {e}")
            return 0.0

    async def apredict(self, input_data: dict) -> float:
        """异步版本（需使用httpx或aiohttp，官方SDK暂未提供异步，可自行实现）"""
        # 这里可使用 httpx 异步请求，略
        pass

    def batch_predict(self, inputs: list) -> list:
        """批量预测，可串行或使用线程池"""
        # 简单串行
        return [self.predict(inp) for inp in inputs]

    def _build_prompt(self, data: dict) -> str:
        headline = data.get('headline', '')
        content = data.get('content', '')
        return f"""请分析以下财经新闻对股票价格的短期情绪影响，输出一个JSON对象，包含一个字段"score"，值为-1到1之间的浮点数，其中-1代表极度消极，0代表中性，1代表极度积极。不要输出其他内容。
新闻标题：{headline}
新闻内容：{content}
"""

    def _parse_score(self, text: str) -> float:
        """从模型返回文本中解析分数"""
        try:
            # 尝试直接解析JSON
            if text.strip().startswith('{'):
                data = json.loads(text)
                return float(data.get('score', 0.0))
            else:
                # 如果返回的不是标准JSON，尝试正则提取数字
                import re
                match = re.search(r'[-+]?\d*\.?\d+', text)
                if match:
                    score = float(match.group())
                    # 限制在[-1,1]区间
                    return max(-1.0, min(1.0, score))
                return 0.0
        except Exception as e:
            logger.warning(f"解析分数失败: {e}，原始文本: {text}")
            return 0.0