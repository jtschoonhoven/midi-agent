# Mapping from model name to (provider, model) tuple
from api.chats.chat_types import ModelName, ModelProvider

MODEL_PROVIDER_MAP: dict[ModelName, tuple[ModelProvider, ModelName]] = {
    "claude-haiku-4-5": ("anthropic", "claude-haiku-4-5"),
    "claude-sonnet-4-5": ("anthropic", "claude-sonnet-4-5"),
    "gpt-4o-mini": ("openai", "gpt-4o-mini"),
    "gpt-4o": ("openai", "gpt-4o"),
    "gpt-5.2": ("openai", "gpt-5.2"),
    "gpt-5-mini": ("openai", "gpt-5-mini"),
    "gpt-5-nano": ("openai", "gpt-5-nano"),
}
