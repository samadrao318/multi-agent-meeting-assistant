"""
LLM factory for creating model instances.
"""

from langchain_openai import AzureChatOpenAI
from .config import settings


def create_llm() -> AzureChatOpenAI:
    """Create and return Azure OpenAI model instance."""
    
    model = AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        deployment_name=settings.azure_openai_deployment,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )
    
    return model