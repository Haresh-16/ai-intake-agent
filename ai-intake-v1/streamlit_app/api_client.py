"""HTTP client for FastAPI backend communication."""

from typing import Optional, Dict, Any
import httpx


class IntakeAPIClient:
    """Client for communicating with the AI Intake Agent FastAPI backend."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the API client.

        Args:
            base_url: Base URL of the FastAPI backend
        """
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)

    def send_message(
        self,
        conversation_id: Optional[str],
        prospect_data: Dict[str, Any],
        content: str,
    ) -> Dict[str, Any]:
        """Send a message to the intake conversation endpoint.

        Args:
            conversation_id: Existing conversation ID or None for new conversation
            prospect_data: Prospect information dict
            content: Message content from the prospect

        Returns:
            Response dict with conversation_id, sanitized_content,
            suggested_next_prompt, and current_stage

        Raises:
            httpx.HTTPStatusError: If the request fails
            httpx.ConnectError: If connection to backend fails
            httpx.TimeoutException: If request times out
        """
        payload = {
            "conversation_id": conversation_id,
            "prospect": prospect_data,
            "role": "prospect",
            "content": content,
        }

        response = self.client.post(
            f"{self.base_url}/api/intake/messages", json=payload
        )
        response.raise_for_status()
        return response.json()

    def finalize_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Finalize a conversation and generate intake summary.

        Args:
            conversation_id: ID of the conversation to finalize

        Returns:
            Response dict with conversation_id and complete summary

        Raises:
            httpx.HTTPStatusError: If the request fails
            httpx.ConnectError: If connection to backend fails
            httpx.TimeoutException: If request times out
        """
        response = self.client.post(
            f"{self.base_url}/api/intake/conversations/{conversation_id}/finalize"
        )
        response.raise_for_status()
        return response.json()

    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Retrieve a conversation with all messages and summary.

        Args:
            conversation_id: ID of the conversation to retrieve

        Returns:
            Response dict with conversation details, messages, and summary

        Raises:
            httpx.HTTPStatusError: If the request fails
            httpx.ConnectError: If connection to backend fails
            httpx.TimeoutException: If request times out
        """
        response = self.client.get(
            f"{self.base_url}/api/intake/conversations/{conversation_id}"
        )
        response.raise_for_status()
        return response.json()

    def close(self):
        """Close the HTTP client."""
        self.client.close()
