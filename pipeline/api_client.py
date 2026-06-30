"""
API Client for Raspberry Pi Code Generator
Handles API key rotation, rate limiting, and API calls
Created: 2025-03-26 01:28:38
Author: Sakkibbb
"""

import os
import time
import random
import requests
import logging
import json
from typing import Dict, List, Optional, Any

# Logger configuration
logger = logging.getLogger(__name__)


def load_api_keys_from_env() -> List[str]:
    """Load API keys from the GEMINI_API_KEYS environment variable (comma-separated)."""
    raw = os.environ.get("GEMINI_API_KEYS", "")
    return [key.strip() for key in raw.split(",") if key.strip()]


class APIClient:
    def __init__(self, api_keys: List[str],
                 base_url: str = "https://generativelanguage.googleapis.com/v1beta",
                 max_requests_per_minute: int = 20,
                 base_delay: float = 2.0,
                 jitter: float = 1.0,
                 max_output_tokens: int = 2048,
                 model: str = None):
        """Initialize API client with multiple API keys."""
        # Fall back to environment variable if no keys were provided
        if not api_keys:
            api_keys = load_api_keys_from_env()
        self.api_keys = api_keys
        self.base_url = base_url
        self.current_key_index = 0
        self.max_requests_per_minute = max_requests_per_minute
        self.base_delay = base_delay
        self.jitter = jitter
        self.max_output_tokens = max_output_tokens
        # Model is configurable (env GEMINI_MODEL). Default to a current free-tier model;
        # the legacy "gemini-2.0-flash" no longer has free-tier quota.
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

        # Track API call rates separately for each key
        self.api_call_times_by_key = {key_index: [] for key_index in range(len(api_keys))}

    def get_current_api_key(self) -> str:
        """Get the current API key."""
        return self.api_keys[self.current_key_index]

    def get_current_api_url(self) -> str:
        """Get the API URL with the current API key."""
        return f"{self.base_url}/models/{self.model}:generateContent?key={self.get_current_api_key()}"

    def rotate_api_key(self) -> int:
        """Rotate to the next API key in a round-robin fashion."""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.info(f"Rotated to API key index {self.current_key_index}")
        return self.current_key_index

    def manage_api_rate(self) -> None:
        """Manage API call rate for the current key to avoid exceeding limits."""
        # Bounded iterative loop (no recursion) so it cannot stack-overflow when
        # every key is saturated. At most one full pass over all keys.
        for _ in range(len(self.api_keys)):
            now = time.time()
            current_key_times = self.api_call_times_by_key[self.current_key_index]

            # Remove timestamps older than 1 minute for this key
            while current_key_times and current_key_times[0] < now - 60:
                current_key_times.pop(0)

            # Check if we've hit our rate limit for this key in the past minute
            if len(current_key_times) >= self.max_requests_per_minute:
                # Calculate how long to wait or switch to another key
                oldest_in_window = current_key_times[0]
                wait_time = 60 - (now - oldest_in_window) + 1  # +1 for safety margin

                # If waiting would be longer than 5 seconds, try another key instead
                if wait_time > 5.0 and len(self.api_keys) > 1:
                    self.rotate_api_key()
                    # Retry the check with the new key on the next loop iteration
                    continue
                else:
                    logger.info(f"Rate limit approaching for key {self.current_key_index}. Waiting {wait_time:.2f} seconds...")
                    time.sleep(wait_time)

            # Cleared to send on the current key: record the timestamp once,
            # for the key actually about to be used, after the rate decision.
            current_key_times.append(time.time())
            return

    def call_gemini_api(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        """Make a direct HTTP request to Gemini API with improved load balancing."""
        # Try with current key first, then rotate through others if needed
        for attempt in range(len(self.api_keys)):
            # Manage API rate limits for current key
            self.manage_api_rate()
            
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "topP": 0.8,
                    "topK": 40,
                    "maxOutputTokens": self.max_output_tokens
                },
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            }

            # Thinking models (2.5/3 flash) spend output tokens on internal reasoning by
            # default, which can starve the answer text; disable it for deterministic,
            # faster code generation. Harmless for non-thinking models.
            if any(t in self.model for t in ("2.5-flash", "flash-latest", "3-flash")):
                payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}

            try:
                api_url = self.get_current_api_url()
                response = requests.post(api_url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    response_data = response.json()
                    # Defensively walk the response: Gemini can return 200 with no
                    # parts (e.g. finishReason MAX_TOKENS or SAFETY). Crashing here
                    # would be swallowed by the broad except and burn a key.
                    cand = (response_data.get("candidates") or [{}])[0]
                    parts = (cand.get("content") or {}).get("parts") or []
                    text = "".join(p.get("text", "") for p in parts)

                    if not text:
                        # Empty/blocked completion is a clean miss, not a key failure.
                        # Return None instead of rotating/backing off through all keys.
                        logger.warning(
                            f"Empty/blocked response (finishReason={cand.get('finishReason')}) "
                            f"with key {self.current_key_index}"
                        )
                        return None

                    # We're successful, rotate to next key to distribute load evenly
                    self.rotate_api_key()

                    # Add random delay after successful call
                    delay = self.base_delay + random.uniform(0, self.jitter)
                    time.sleep(delay)

                    return text
                else:
                    logger.error(f"API error with key {self.current_key_index}: {response.status_code}: {response.text}")

                    # Fatal client errors fail identically on every key (malformed
                    # payload / unauthorized request), so don't retry-rotate them.
                    if response.status_code in (400, 403):
                        logger.error(
                            f"Fatal client error {response.status_code} with key "
                            f"{self.current_key_index}; not retrying other keys."
                        )
                        return None

                    if response.status_code == 429:  # Rate limit exceeded
                        logger.warning(f"Rate limit exceeded for key {self.current_key_index}. Switching to next key.")
                        # Exponential backoff with jitter before retrying with the next key
                        backoff = min(self.base_delay * (2 ** attempt), 30) + random.uniform(0, self.jitter)
                        time.sleep(backoff)
                        # Rotate to next key
                        self.rotate_api_key()
                        continue

            except Exception as e:
                logger.error(f"Error calling Gemini API with key {self.current_key_index}: {str(e)}")

            # If we're here, back off (exponential) and try the next key
            backoff = min(self.base_delay * (2 ** attempt), 30) + random.uniform(0, self.jitter)
            time.sleep(backoff)
            self.rotate_api_key()
        
        # If we've tried all keys and none worked, return None
        logger.error("All API keys failed to generate response")
        return None

    def test_api_connection(self) -> bool:
        """Test the API connection with all keys."""
        logger.info("Testing connection to Gemini API...")
        
        # Test each API key
        key_status = []
        for i, api_key in enumerate(self.api_keys):
            self.current_key_index = i
            
            test_prompt = "Write a single line of Python code that prints 'Hello World'"
            response = self.call_gemini_api(test_prompt, temperature=0.1)
            
            if response:
                # Replace emoji with plain text to avoid encoding issues on Windows
                logger.info(f"[SUCCESS] API key {i+1} connection successful")
                key_status.append(True)
            else:
                # Replace emoji with plain text to avoid encoding issues on Windows
                logger.error(f"[FAILED] API key {i+1} connection failed")
                key_status.append(False)
        
        # Check if at least one API key is working
        if any(key_status):
            # Set the current key to the first working one
            self.current_key_index = key_status.index(True)
            return True
        else:
            logger.error("All API keys failed. Please check your API keys and internet connection.")
            return False