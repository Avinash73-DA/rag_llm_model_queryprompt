import logging
import asyncio
import httpx 
from typing import Optional, Dict, Any

# --- Basic Logger Setup ---
# (This is just so the log messages in the class will print to your console)
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class LLM_ClientException(Exception):
    """Custom exception for LLM client errors."""
    pass

class LLM_Client:
    """
    An asynchronous client for LLM APIs, supporting both
    Google Gemini and a local Ollama instance.
    """
    
    def __init__(self, gemini_key: Optional[str] = None):
        """
        Initializes the client. gemini_key is optional.
        If not provided, only local Ollama calls will work.
        """
        self.gemini_base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.ollama_base_url = "http://localhost:11434"
        self.client: Optional[httpx.AsyncClient] = None
        self.gemini_headers: Optional[Dict[str, str]] = None

        if gemini_key:
            self.gemini_headers = {
                "Content-Type": "application/json",
                "X-goog-api-key": gemini_key
            }
            log.info("Gemini API key loaded.")
        else:
            log.info("No Gemini API key provided. Only Ollama models will be available.")

    async def start_session(self):
        """Creates the persistent httpx.AsyncClient."""
        if not self.client:
            log.info("Starting LLM_Client HTTP session...")
            self.client = httpx.AsyncClient(timeout=120.0) #Timeout can be altered

    async def close_session(self):
        """Closes the persistent httpx.AsyncClient."""
        if self.client:
            log.info("Closing LLM_Client HTTP session...")
            await self.client.aclose()
            self.client = None

    # --- Gemini Methods ---

    async def _async_gemini_generate_content(self, model_name: str, prompt: str) -> str:
        """
        The core async method that handles API calls to Gemini.
        """
        if not self.client:
            log.warning("LLM client session not started. Starting a temporary one.")
            await self.start_session()
        
        if not self.gemini_headers:
            log.error("Cannot call Gemini: No GEMINI_API_KEY was provided.")
            raise LLM_ClientException("Gemini API key not provided.")

        url = f"{self.gemini_base_url}/{model_name}:generateContent"
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0}
        }

        retries = 0
        max_retries = 3
        log.info(f"Gemini Model: {model_name} Triggered")

        while retries < max_retries:
            try:
                # Pass Gemini-specific headers with the request
                response = await self.client.post(url, json=data, headers=self.gemini_headers)

                if response.status_code == 200:
                    output = response.json()
                    try:
                        candidate = output["candidates"][0]
                        finish_reason = candidate.get("finishReason", "UNKNOWN")

                        if finish_reason not in ("STOP", "MAX_TOKENS"):
                            log.warning(f"LLM call finished with reason: {finish_reason}")
                            raise LLM_ClientException(f"LLM generation stopped for reason: {finish_reason}")
                        
                        text_output = candidate["content"]["parts"][0]["text"]
                        return text_output.strip()

                    except (KeyError, IndexError, TypeError) as e:
                        log.error(f"Failed to parse valid 200 response from Gemini: {e}")
                        log.debug(f"Raw malformed response: {output}")
                        raise LLM_ClientException("Failed to parse Gemini API response.")
                
                else:
                    log.error(f"API call failed with Error {response.status_code}: {response.text}")
                    retries += 1
                    await asyncio.sleep(2 ** retries)

            except httpx.RequestError as e:
                log.error(f"HTTP request failed: {e}")
                retries += 1
                await asyncio.sleep(2 ** retries)
            
            except Exception as e:
                log.error(f"An unexpected error occurred: {e}")
                raise LLM_ClientException(f"LLM generation failed: {e}")

        raise LLM_ClientException(f"Failed to get a response from Gemini API after {max_retries} retries.")

    async def gemini_flash_2_0(self, prompt: str) -> str:
        """Generates content using Gemini 2.0 Flash."""
        return await self._async_gemini_generate_content("gemini-2.0-flash", prompt)

    async def gemini_flash_2_5(self, prompt: str) -> str:
        """Generates content using Gemini 2.5 Flash."""
        return await self._async_gemini_generate_content("gemini-2.5-flash", prompt)

    # --- Ollama Methods (NEW) ---

    async def _async_ollama_generate_content(self, model_name: str, prompt: str) -> str:
        """
        The core async method that handles API calls to local Ollama.
        """
        if not self.client:
            log.warning("LLM client session not started. Starting a temporary one.")
            await self.start_session()
        
        url = f"{self.ollama_base_url}/api/chat"
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }

        retries = 0
        max_retries = 3
        log.info(f"Ollama Model: {model_name} Triggered")

        while retries < max_retries:
            try:
                # No special headers needed for local Ollama
                response = await self.client.post(url, json=data)

                if response.status_code == 200:
                    output = response.json()
                    try:
                        # Ollama's response structure is different
                        text_output = output["message"]["content"]
                        return text_output.strip()
                    except (KeyError, IndexError, TypeError) as e:
                        log.error(f"Failed to parse valid 200 response from Ollama: {e}")
                        log.debug(f"Raw malformed response: {output}")
                        raise LLM_ClientException("Failed to parse Ollama API response.")
                
                elif response.status_code == 404:
                    log.error(f"Ollama API call failed: Model '{model_name}' not found.")
                    raise LLM_ClientException(f"Model '{model_name}' not found. Have you run 'ollama pull {model_name}'?")
                
                else:
                    log.error(f"Ollama API call failed with Error {response.status_code}: {response.text}")
                    retries += 1
                    await asyncio.sleep(2 ** retries)

            except httpx.ConnectError as e:
                # Specific error if the Ollama server isn't running
                log.error(f"Connection to Ollama failed: {e}")
                raise LLM_ClientException("Connection to Ollama failed. Is the Ollama service running?")
            
            except httpx.RequestError as e:
                log.error(f"HTTP request failed: {e}")
                retries += 1
                await asyncio.sleep(2 ** retries)
            
            except Exception as e:
                log.error(f"An unexpected error occurred: {e}")
                raise LLM_ClientException(f"Ollama generation failed: {e}")

        raise LLM_ClientException(f"Failed to get a response from Ollama API after {max_retries} retries.")

    async def ollama_gemma_3_4b(self, prompt: str) -> str:
        """Generates content using local gemma3:4b."""
        return await self._async_ollama_generate_content("gemma3:4b", prompt)
    
    async def ollama_sqlcoder(self, prompt: str) -> str:
        """Generates content using local sqlcoder."""
        return await self._async_ollama_generate_content("sqlcoder", prompt)