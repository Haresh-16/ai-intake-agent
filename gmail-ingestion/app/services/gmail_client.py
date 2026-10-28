"""
Gmail API client for fetching messages and threads.
Read-only operations for attorney decision extraction.

Constraints per build brief Section 13:
- Read-only message and thread retrieval
- No outbound email writes
- Match messages to prospects by name/email/phone
- Preserve source message_id for audit trail
- No retention of email content outside firm storage (metadata/snippets only)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.gmail_auth import GmailAuthService

logger = logging.getLogger(__name__)


class GmailClientError(Exception):
    """Raised when Gmail API operations fail."""

    pass


class GmailMessage:
    """Simplified Gmail message representation for attorney decision extraction."""

    def __init__(self, message_data: dict[str, Any]):
        """
        Initialize from Gmail API message resource.

        Args:
            message_data: Raw message dict from Gmail API
        """
        self.id = message_data.get("id", "")
        self.thread_id = message_data.get("threadId", "")
        self.snippet = message_data.get("snippet", "")
        self.internal_date = message_data.get("internalDate", "0")

        # Parse headers
        self.headers = {}
        payload = message_data.get("payload", {})
        for header in payload.get("headers", []):
            name = header.get("name", "").lower()
            value = header.get("value", "")
            self.headers[name] = value

        self.subject = self.headers.get("subject", "")
        self.from_email = self.headers.get("from", "")
        self.to_email = self.headers.get("to", "")
        self.date = self.headers.get("date", "")

        # Body is NOT extracted per build brief (no retention of full content)
        # Only subject and snippet are stored for context
        self.body = None

    def get_datetime(self) -> datetime:
        """Get message datetime from internal_date timestamp."""
        try:
            timestamp_ms = int(self.internal_date)
            return datetime.fromtimestamp(timestamp_ms / 1000.0)
        except (ValueError, TypeError):
            return datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for storage/logging."""
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "subject": self.subject,
            "from": self.from_email,
            "to": self.to_email,
            "date": self.date,
            "snippet": self.snippet[:500],  # Truncate for safety
            "internal_date": self.internal_date,
        }


class GmailClient:
    """
    Gmail API client for read-only message retrieval.

    Operations:
    - Search messages by query
    - Get message/thread details
    - List messages for a mailbox

    Security:
    - Read-only access (gmail.readonly scope)
    - No message sending or modification
    - Audit logging for all fetches
    """

    def __init__(self, auth_service: GmailAuthService, user_email: str):
        """
        Initialize Gmail client for a specific mailbox.

        Args:
            auth_service: Configured GmailAuthService
            user_email: Email address of mailbox to access

        Raises:
            GmailClientError: If authentication fails
        """
        self.auth_service = auth_service
        self.user_email = user_email

        try:
            # Get delegated credentials for the mailbox
            self.credentials = auth_service.get_delegated_credentials(user_email)

            # Validate readonly scope
            if not auth_service.validate_readonly_scope(self.credentials):
                raise GmailClientError(
                    "Credentials do not have required readonly scope"
                )

            # Build Gmail API service
            self.service = build("gmail", "v1", credentials=self.credentials)

            logger.info(f"GmailClient initialized for mailbox: {user_email}")

        except Exception as e:
            logger.error(f"Failed to initialize GmailClient for {user_email}: {e}")
            raise GmailClientError(f"Client initialization failed: {e}") from e

    def search_messages(
        self,
        query: str,
        max_results: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[str], str | None]:
        """
        Search messages in mailbox using Gmail query syntax.

        Args:
            query: Gmail search query (e.g., "from:jibrael@ subject:case")
            max_results: Maximum messages to return (1-500)
            page_token: Pagination token from previous request

        Returns:
            Tuple of (message_ids, next_page_token)

        Raises:
            GmailClientError: If search fails

        Examples:
            # Search by sender
            ids, token = client.search_messages("from:jibrael@example.com")

            # Search by date and subject
            ids, token = client.search_messages("after:2024/01/01 subject:intake")

            # Search for prospect name
            ids, token = client.search_messages('"John Doe"')
        """
        try:
            logger.info(f"Searching messages with query: {query} (max: {max_results})")

            response = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=min(max_results, 500),
                    pageToken=page_token,
                )
                .execute()
            )

            messages = response.get("messages", [])
            message_ids = [msg["id"] for msg in messages]
            next_token = response.get("nextPageToken")

            logger.info(f"Found {len(message_ids)} messages")
            return message_ids, next_token

        except HttpError as e:
            logger.error(f"Gmail API error during search: {e}")
            raise GmailClientError(f"Message search failed: {e}") from e

    def get_message(self, message_id: str, format: str = "full") -> GmailMessage:
        """
        Get message details by ID.

        Args:
            message_id: Gmail message ID
            format: Message format (minimal|full|metadata)
                    'metadata' recommended to avoid fetching full body

        Returns:
            GmailMessage object

        Raises:
            GmailClientError: If fetch fails

        Security note:
            Using format='metadata' avoids fetching message body,
            reducing PII exposure per build brief.
        """
        try:
            logger.debug(f"Fetching message {message_id} with format={format}")

            response = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format=format)
                .execute()
            )

            return GmailMessage(response)

        except HttpError as e:
            logger.error(f"Gmail API error fetching message {message_id}: {e}")
            raise GmailClientError(f"Message fetch failed: {e}") from e

    def get_thread(self, thread_id: str, format: str = "metadata") -> list[GmailMessage]:
        """
        Get all messages in a thread.

        Args:
            thread_id: Gmail thread ID
            format: Message format for each message in thread

        Returns:
            List of GmailMessage objects in chronological order

        Raises:
            GmailClientError: If fetch fails

        Use case:
            Retrieve full email conversation for attorney decision extraction.
            Thread context helps LLM understand decision rationale.
        """
        try:
            logger.debug(f"Fetching thread {thread_id}")

            response = (
                self.service.users()
                .threads()
                .get(userId="me", id=thread_id, format=format)
                .execute()
            )

            messages = response.get("messages", [])
            gmail_messages = [GmailMessage(msg) for msg in messages]

            logger.info(f"Retrieved {len(gmail_messages)} messages in thread {thread_id}")
            return gmail_messages

        except HttpError as e:
            logger.error(f"Gmail API error fetching thread {thread_id}: {e}")
            raise GmailClientError(f"Thread fetch failed: {e}") from e

    def build_prospect_query(
        self,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        additional_filter: str | None = None,
    ) -> str:
        """
        Build Gmail search query to find messages related to a prospect.

        Args:
            first_name: Prospect first name
            last_name: Prospect last name
            email: Prospect email address
            phone: Prospect phone number
            additional_filter: Additional Gmail query filter

        Returns:
            Gmail search query string

        Examples:
            >>> client.build_prospect_query("Jane", "Doe", "jane@example.com")
            '("Jane Doe" OR jane@example.com)'

            >>> client.build_prospect_query(email="jane@example.com", additional_filter="from:jibrael@")
            '(jane@example.com) from:jibrael@'
        """
        parts = []

        # Add name search
        if first_name and last_name:
            parts.append(f'"{first_name} {last_name}"')
        elif first_name:
            parts.append(f'"{first_name}"')
        elif last_name:
            parts.append(f'"{last_name}"')

        # Add email search
        if email:
            parts.append(email)

        # Add phone search (may need formatting normalization)
        if phone:
            # Gmail doesn't index phone well, but try anyway
            parts.append(f'"{phone}"')

        # Combine with OR
        query = " OR ".join(parts) if parts else ""

        # Wrap in parens if multiple parts
        if len(parts) > 1:
            query = f"({query})"

        # Add additional filter with AND
        if additional_filter:
            query = f"{query} {additional_filter}".strip()

        return query

    def list_labels(self) -> list[dict[str, str]]:
        """
        List all labels in mailbox (for debugging/exploration).

        Returns:
            List of label dicts with id and name

        Raises:
            GmailClientError: If fetch fails
        """
        try:
            response = self.service.users().labels().list(userId="me").execute()
            return response.get("labels", [])
        except HttpError as e:
            logger.error(f"Gmail API error listing labels: {e}")
            raise GmailClientError(f"Label list failed: {e}") from e
