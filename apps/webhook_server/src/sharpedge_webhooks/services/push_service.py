"""FCM push notification service using Firebase Admin SDK."""
from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger("sharpedge.push_service")


def initialize_firebase(service_account_json: str) -> bool:
    """Initialize the Firebase app from a JSON string of service account credentials.

    Returns True if Firebase is ready to use, False if not configured.
    Safe to call multiple times — only initializes once.
    """
    if not service_account_json:
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials

        try:
            firebase_admin.get_app()
            return True
        except ValueError:
            pass  # App not yet initialized

        cred_dict = json.loads(service_account_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        logger.info("push_service: Firebase app initialized")
        return True
    except Exception as exc:
        logger.error("push_service: Firebase initialization failed – %s", exc)
        return False


def _get_supabase_service_client():
    """Return a Supabase client using the service role key."""
    from supabase import create_client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def send_push_to_user(
    user_id: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> int:
    """Send an FCM push notification to all registered devices for a user.

    Returns the count of successful sends. Fails silently per token.
    """
    from firebase_admin import messaging
    import firebase_admin.exceptions

    try:
        client = _get_supabase_service_client()
        resp = (
            client.table("user_device_tokens")
            .select("fcm_token")
            .eq("user_id", user_id)
            .execute()
        )
        tokens = [row["fcm_token"] for row in (resp.data or []) if row.get("fcm_token")]
    except Exception as exc:
        logger.error("push_service: token query failed for user %s – %s", user_id, exc)
        return 0

    return _send_to_tokens(tokens, title, body, data)


def send_push_to_all_users(
    title: str,
    body: str,
    data: dict | None = None,
) -> int:
    """Send an FCM push notification to all active device tokens (broadcast).

    Returns the count of successful sends.
    """
    try:
        client = _get_supabase_service_client()
        resp = (
            client.table("user_device_tokens")
            .select("fcm_token")
            .execute()
        )
        tokens = [row["fcm_token"] for row in (resp.data or []) if row.get("fcm_token")]
    except Exception as exc:
        logger.error("push_service: broadcast token query failed – %s", exc)
        return 0

    return _send_to_tokens(tokens, title, body, data)


def _send_to_tokens(
    tokens: list[str],
    title: str,
    body: str,
    data: dict | None = None,
) -> int:
    """Send FCM messages to a list of tokens. Returns successful send count."""
    from firebase_admin import messaging
    import firebase_admin.exceptions

    success_count = 0
    str_data = {k: str(v) for k, v in (data or {}).items()}

    for token in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=str_data,
                token=token,
            )
            messaging.send(message)
            success_count += 1
        except firebase_admin.exceptions.FirebaseError as exc:
            logger.warning("push_service: FCM send failed for token %s… – %s", token[:8], exc)
        except Exception as exc:
            logger.warning("push_service: unexpected error for token %s… – %s", token[:8], exc)

    return success_count
