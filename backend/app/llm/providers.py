"""LLM provider implementations - abstract interface for different LLM backends."""
import json
import time
import requests
from abc import ABC, abstractmethod
from typing import List, Optional
from loguru import logger

from app.schemas import ExtractResponse, ExtractedItem
from app.models import SideEnum, CategoryEnum


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def call(self, prompt: str, system_prompt: str, max_retries: int = 3) -> str:
        """
        Call the LLM with a prompt and system prompt.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            max_retries: Maximum number of retries
            
        Returns:
            Response text
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (for full LLMs like GPT-4)."""
    
    def __init__(self, api_key: Optional[str], model: str):
        self.api_key = api_key
        self.model = model
        self.client = None
        if api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
            except ImportError:
                logger.warning("OpenAI package not installed. Install with: pip install openai")
    
    def is_available(self) -> bool:
        return self.client is not None
    
    def call(self, prompt: str, system_prompt: str, max_retries: int = 3) -> str:
        """Call OpenAI API with retries and timeout."""
        if not self.client:
            raise ValueError("OpenAI client not initialized. Check OPENAI_API_KEY.")
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,  # Deterministic
                    timeout=6.0,
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"OpenAI call attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise


class OllamaProvider(LLMProvider):
    """Ollama provider (for local SLMs like Qwen2.5, Llama, Mistral, etc.)."""
    
    def __init__(self, base_url: str, model: str, use_chat_api: bool = None):
        self.base_url = base_url.rstrip('/')
        self.model = model
        # Auto-detect if model is instruction-tuned (contains 'instruct' or 'chat')
        # Instruction models work better with chat API
        if use_chat_api is None:
            self.use_chat_api = 'instruct' in model.lower() or 'chat' in model.lower()
        else:
            self.use_chat_api = use_chat_api
        self._check_availability()
    
    def _check_availability(self):
        """Check if Ollama is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=1)
            if response.status_code == 200:
                logger.info(f"Ollama available at {self.base_url}, using {'chat' if self.use_chat_api else 'generate'} API")
            else:
                logger.warning(f"Ollama returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not connect to Ollama at {self.base_url}: {e}")
    
    def is_available(self) -> bool:
        """Check if Ollama is available."""
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=1)
            return response.status_code == 200
        except Exception:
            return False
    
    def call(self, prompt: str, system_prompt: str, max_retries: int = 3) -> str:
        """Call Ollama API with retries. Uses chat API for instruction models, generate API for others."""
        for attempt in range(max_retries):
            try:
                if self.use_chat_api:
                    # Use chat API for instruction-tuned models (better for structured outputs)
                    response = requests.post(
                        f"{self.base_url}/api/chat",
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": prompt}
                            ],
                            "stream": False,
                            "keep_alive": 0,
                            "options": {
                                "temperature": 0.0,  # Deterministic
                                "num_predict": 512,
                            }
                        },
                        timeout=10.0,  # Longer timeout for local models
                    )
                    response.raise_for_status()
                    result = response.json()
                    # Chat API returns message content
                    return result.get("message", {}).get("content", "")
                else:
                    # Use generate API for base/completion models
                    full_prompt = f"{system_prompt}\n\n{prompt}"
                    response = requests.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": full_prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.0,  # Deterministic
                            }
                        },
                        timeout=10.0,  # Longer timeout for local models
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result.get("response", "")
            except Exception as e:
                logger.warning(f"Ollama call attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise


class DisabledProvider(LLMProvider):
    """Provider that skips LLM calls (for debugging)."""
    
    def is_available(self) -> bool:
        return True
    
    def call(self, prompt: str, system_prompt: str, max_retries: int = 3) -> str:
        """Return empty string when LLM is disabled."""
        logger.info("LLM_DISABLED: skipping LLM call")
        return ""


def create_provider(provider_type: str, **kwargs) -> LLMProvider:
    """
    Factory function to create the appropriate LLM provider.
    
    Args:
        provider_type: One of 'openai', 'ollama', 'disabled'
        **kwargs: Provider-specific configuration
        
    Returns:
        LLMProvider instance
    """
    provider_type = provider_type.lower()
    
    if provider_type == "openai":
        return OpenAIProvider(
            api_key=kwargs.get("api_key"),
            model=kwargs.get("model", "gpt-4-turbo-preview")
        )
    elif provider_type == "ollama":
        return OllamaProvider(
            base_url=kwargs.get("base_url", "http://localhost:11434"),
            model=kwargs.get("model", "qwen2.5:3b-instruct"),
            use_chat_api=kwargs.get("use_chat_api")
        )
    elif provider_type == "disabled":
        return DisabledProvider()
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")

