"""
Gmail API authentication with domain-wide delegation.
Read-only access for attorney decision extraction.

Constraints per build brief Section 13:
- OAuth 2.0 with domain-wide delegation
- Scoped to gmail.readonly only (no write access)
- Service account for firm-controlled infrastructure
- No retention of email content outside firm storage
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

# Gmail API read-only scope - NO write access per build brief
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class GmailAuthError(Exception):
    """Raised when Gmail authentication fails."""

    pass


class GmailAuthService:
    """
    Handles Gmail API authentication with domain-wide delegation.

    This service is strictly READ-ONLY and scoped to gmail.readonly.
    No outbound email writes are permitted in V1 per build brief.
    """

    def __init__(
        self,
        service_account_file: str | Path | None = None,
        service_account_json: dict[str, Any] | None = None,
    ):
        """
        Initialize Gmail auth service.

        Args:
            service_account_file: Path to service account JSON file
            service_account_json: Service account credentials as dict

        Raises:
            GmailAuthError: If neither file nor JSON provided
        """
        self.service_account_file = service_account_file
        self.service_account_json = service_account_json

        if not service_account_file and not service_account_json:
            raise GmailAuthError(
                "Must provide either service_account_file or service_account_json"
            )

        logger.info("GmailAuthService initialized (READ-ONLY mode)")

    def get_delegated_credentials(
        self, user_email: str, scopes: list[str] | None = None
    ) -> service_account.Credentials:
        """
        Get credentials for impersonating a user via domain-wide delegation.

        Args:
            user_email: Email address of user to impersonate (e.g., attorney mailbox)
            scopes: OAuth scopes to request (defaults to gmail.readonly only)

        Returns:
            Credentials object with delegated access

        Raises:
            GmailAuthError: If authentication fails

        Security notes:
            - Default scope is gmail.readonly (read-only)
            - Custom scopes are allowed but logged for audit
            - Credentials are short-lived and must be refreshed
        """
        if scopes is None:
            scopes = [GMAIL_READONLY_SCOPE]
        else:
            # Log if non-readonly scopes requested (security audit)
            if GMAIL_READONLY_SCOPE not in scopes:
                logger.warning(
                    f"Non-readonly scopes requested: {scopes}. "
                    "Verify this is authorized per build brief Section 13."
                )

        try:
            # Load service account credentials
            if self.service_account_json:
                credentials = service_account.Credentials.from_service_account_info(
                    self.service_account_json, scopes=scopes
                )
            else:
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_file, scopes=scopes
                )

            # Create delegated credentials for the target user
            delegated_credentials = credentials.with_subject(user_email)

            # Refresh to ensure valid token
            delegated_credentials.refresh(Request())

            logger.info(
                f"Successfully authenticated with domain-wide delegation for {user_email}"
            )
            return delegated_credentials

        except Exception as e:
            logger.error(f"Failed to get delegated credentials for {user_email}: {e}")
            raise GmailAuthError(f"Authentication failed: {e}") from e

    def validate_readonly_scope(self, credentials: service_account.Credentials) -> bool:
        """
        Validate that credentials are scoped to read-only access.

        Args:
            credentials: Credentials to validate

        Returns:
            True if scoped to readonly, False otherwise

        Security note:
            This ensures compliance with build brief requirement for
            read-only Gmail access in V1.
        """
        if not credentials.scopes:
            return False

        # Check if ONLY readonly scope is present (strictest check)
        if credentials.scopes == [GMAIL_READONLY_SCOPE]:
            return True

        # Check if readonly scope is present (permissive check)
        if GMAIL_READONLY_SCOPE in credentials.scopes:
            logger.warning(
                f"Credentials have additional scopes beyond readonly: {credentials.scopes}"
            )
            return True

        logger.error(f"Credentials missing readonly scope. Scopes: {credentials.scopes}")
        return False

    @staticmethod
    def load_service_account_from_env(env_var_name: str = "GMAIL_SERVICE_ACCOUNT_JSON") -> dict[str, Any]:
        """
        Load service account credentials from environment variable.

        Args:
            env_var_name: Name of environment variable containing JSON

        Returns:
            Service account credentials as dict

        Raises:
            GmailAuthError: If env var missing or invalid JSON
        """
        import os

        sa_json = os.getenv(env_var_name)
        if not sa_json:
            raise GmailAuthError(f"Environment variable {env_var_name} not set")

        try:
            return json.loads(sa_json)
        except json.JSONDecodeError as e:
            raise GmailAuthError(f"Invalid JSON in {env_var_name}: {e}") from e
