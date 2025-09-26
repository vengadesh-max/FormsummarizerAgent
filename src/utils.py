# utils.py
"""
Utility functions for the Intelligent Form Agent.
Handles environment variables and API key management.
"""

import os
from dotenv import load_dotenv

# Load .env file automatically if present
load_dotenv()


def get_gemini_api_key() -> str:
    """
    Fetches the Gemini API key from environment variables.
    Raises an error if not found.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found in environment variables. "
            "Please set it in your system or .env file."
        )
    return api_key
