# from models.deepseek_model import DeepSeekModel
from models.zhipu_model import ZhipuModel
from config.settings import settings

class ModelFactory:
    @staticmethod
    def create_model(provider: str = None):
        provider = provider or settings.MODEL_CONFIG.get('provider', 'zhipu')
        if provider == 'zhipu':
            return ZhipuModel(
                api_key=settings.MODEL_CONFIG['api_key'],
                model_name=settings.MODEL_CONFIG.get('model_name', 'glm-5')
            )
        # elif provider == 'deepseek':
        #     return DeepSeekModel(
        #         api_key=settings.MODEL_CONFIG['api_key'],
        #         model_name=settings.MODEL_CONFIG.get('model_name', 'deepseek-chat'),
        #         timeout=settings.MODEL_CONFIG.get('timeout', 5)
        #     )
        else:
            raise ValueError(f"Unsupported model provider: {provider}")