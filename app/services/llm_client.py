"""
LLM client abstraction supporting multiple providers.
Supports free/open models like Llama, Mistral, Qwen via Ollama or OpenAI-compatible APIs.
"""
from typing import Protocol
import httpx
from app.config import Settings
from app.core.logging import get_logger
from app.core.exceptions import LLMException

logger = get_logger(__name__)


class LLMClient(Protocol):
    """Protocol for LLM client implementations."""
    
    async def ask(self, system_prompt: str, user_prompt: str) -> str:
        """
        Send a question to the LLM and get a response.
        
        Args:
            system_prompt: System/instruction prompt
            user_prompt: User question/prompt
            
        Returns:
            The LLM's response text
            
        Raises:
            LLMException: If the LLM call fails
        """
        ...


class OllamaLLMClient:
    """
    LLM client for Ollama (local open-source models).
    
    Supports models like Llama, Mistral, Qwen running locally via Ollama.
    Default endpoint: http://localhost:11434/api/chat
    """
    
    def __init__(self, settings: Settings):
        self.base_url = settings.llm_api_base_url.rstrip("/")
        self.model_name = settings.llm_model_name
        self.timeout = settings.llm_timeout
        logger.info(f"Initialized OllamaLLMClient with model: {self.model_name} at {self.base_url}")
    
    async def ask(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call Ollama API.
        
        Ollama endpoint: POST /api/chat
        Request format:
        {
          "model": "llama3",
          "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."}
          ],
          "stream": false
        }
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"Calling Ollama API: {url}")
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                data = response.json()
                # Ollama response format: {"message": {"role": "assistant", "content": "..."}}
                answer = data.get("message", {}).get("content", "")
                
                if not answer:
                    raise LLMException("Empty response from Ollama")
                
                logger.debug(f"Received response from Ollama: {len(answer)} chars")
                return answer
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
            raise LLMException(f"Ollama HTTP error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Ollama request error: {str(e)}")
            raise LLMException(f"Failed to connect to Ollama: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error calling Ollama: {str(e)}")
            raise LLMException(f"Ollama error: {str(e)}")


class OpenAICompatibleLLMClient:
    """
    LLM client for OpenAI-compatible APIs.
    
    Works with any service that implements OpenAI's /v1/chat/completions endpoint:
    - vLLM server
    - OpenRouter (for various open models)
    - Text Generation Inference
    - Custom deployments of Llama/Mistral/Qwen
    """
    
    def __init__(self, settings: Settings):
        self.base_url = settings.llm_api_base_url.rstrip("/")
        self.model_name = settings.llm_model_name
        self.api_key = settings.llm_api_key
        self.timeout = settings.llm_timeout
        logger.info(f"Initialized OpenAICompatibleLLMClient with model: {self.model_name} at {self.base_url}")
    
    async def ask(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call OpenAI-compatible API.
        
        Endpoint: POST /v1/chat/completions
        Request format (OpenAI standard):
        {
          "model": "model-name",
          "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."}
          ],
          "temperature": 0.7
        }
        """
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7
        }
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"Calling OpenAI-compatible API: {url}")
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                # OpenAI response format: {"choices": [{"message": {"content": "..."}}]}
                answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not answer:
                    raise LLMException("Empty response from LLM")
                
                logger.debug(f"Received response from LLM: {len(answer)} chars")
                return answer
                
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM HTTP error: {e.response.status_code} - {e.response.text}")
            raise LLMException(f"LLM HTTP error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"LLM request error: {str(e)}")
            raise LLMException(f"Failed to connect to LLM: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error calling LLM: {str(e)}")
            raise LLMException(f"LLM error: {str(e)}")


def get_llm_client(settings: Settings) -> LLMClient:
    """
    Factory function to create the appropriate LLM client based on settings.
    
    Args:
        settings: Application settings
        
    Returns:
        LLMClient instance
        
    Raises:
        ValueError: If the LLM provider is not supported
        
    Supported providers:
        - "ollama": For local Llama/Mistral/Qwen via Ollama
        - "openai_compatible": For any OpenAI-compatible API
    """
    provider = settings.llm_provider.lower()
    
    if provider == "ollama":
        return OllamaLLMClient(settings)
    elif provider == "openai_compatible":
        return OpenAICompatibleLLMClient(settings)
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported providers: 'ollama', 'openai_compatible'"
        )