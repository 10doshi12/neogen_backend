# utils/api_key_rotator.py
import threading

class APIKeyRotator:
    """
    A thread-safe class to rotate through a list of API keys.
    This allows us to distribute requests across multiple free-tier keys
    to avoid rate-limiting.
    """
    def __init__(self, api_keys: list[str]):
        if not api_keys:
            raise ValueError("API keys list cannot be empty.")
        self.api_keys = api_keys
        self.current_index = 0
        self.lock = threading.Lock()

    def get_key(self) -> str:
        """
        Atomically gets the next API key from the list.
        """
        with self.lock:
            key = self.api_keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            return key