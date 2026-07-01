"""
Simple notification system for Hombre.
Stores recent notifications about workspace events, new conclusions, etc.

This is what happens when you let a Satanist write notification systems.
"""

import json
import logging
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from routes.supabase import get_admin_client, is_admin_configured

log = logging.getLogger("hombre")

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

DATA_DIR = Path(__file__).parent.parent / "data"
NOTIFICATIONS_FILE = DATA_DIR / "notifications.json"
MAX_NOTIFICATIONS = 50


class DismissRequest(BaseModel):
    id: str = Field(..., description="Notification ID to dismiss")


def _load_notifications() -> list[dict]:
    """Load notifications from disk."""
    if not NOTIFICATIONS_FILE.exists():
        return []
    try:
        data = json.loads(NOTIFICATIONS_FILE.read_text())
        if not isinstance(data, list):
            return []
        return data
    except (json.JSONDecodeError, Exception) as e:
        log.error("Failed to load notifications.json: %s", e)
        return []


def _load_notifications_supabase(type: str | None = None, workspace_id: str | None = None) -> list[dict]:
    """Load notifications from Supabase."""
    client = get_admin_client()
    if not client:
        return []

    try:
        query = client.table("notifications").select("*")
        if type:
            query = query.eq("type", type)
        if workspace_id:
            query = query.eq("workspace_id", workspace_id)
        query = query.order("created_at", desc=True).limit(MAX_NOTIFICATIONS)
        result = query.execute()

        return [
            {
                "id": row["id"],
                "type": row["type"],
                "title": row["message"],  # Supabase uses 'message', local uses 'title'
                "details": "",
                "workspace_id": row.get("workspace_id", ""),
                "created_at": row["created_at"],
                "dismissed": row.get("dismissed", False),
            }
            for row in (result.data or [])
        ]
    except Exception as e:
        log.error("Failed to load notifications from Supabase: %s", e)
        return []


def _save_notifications(notifications: list[dict]) -> None:
    """Persist notifications to disk, keeping only the most recent ones."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Keep only the most recent MAX_NOTIFICATIONS
    notifications = notifications[:MAX_NOTIFICATIONS]
    try:
        NOTIFICATIONS_FILE.write_text(json.dumps(notifications, indent=2))
    except Exception as e:
        log.error("Failed to write notifications.json: %s", e)


def _save_notification_supabase(notif_type: str, title: str, details: str, workspace_id: str) -> None:
    """Insert a notification into Supabase."""
    client = get_admin_client()
    if not client:
        return

    try:
        client.table("notifications").insert(
            {
                "type": notif_type,
                "message": title,
                "workspace_id": workspace_id,
            }
        ).execute()
    except Exception as e:
        log.error("Failed to save notification to Supabase: %s", e)


def _dismiss_notification_supabase(notification_id: str) -> bool:
    """Dismiss a notification in Supabase."""
    client = get_admin_client()
    if not client:
        return False

    try:
        result = (
            client.table("notifications")
            .update({"dismissed": True})
            .eq("id", notification_id)
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        log.error("Failed to dismiss notification in Supabase: %s", e)
        return False


def _make_notification(notif_type: str, title: str, details: str = "", workspace_id: str = "") -> dict:
    """Create a notification object."""
    return {
        "id": f"{notif_type}_{int(time.time() * 1000)}",
        "type": notif_type,
        "title": title,
        "details": details,
        "workspace_id": workspace_id,
        "created_at": time.time(),
        "dismissed": False,
    }


def notify_conclusion_created(workspace_id: str, conclusion_id: str, title: str = "") -> None:
    """Record a notification for a new conclusion."""
    notif_title = title or f"New conclusion: {conclusion_id[:16]}..."
    details = f"Conclusion {conclusion_id} was created in workspace {workspace_id}"

    if is_admin_configured():
        _save_notification_supabase("conclusion_created", notif_title, details, workspace_id)
        return

    notif = _make_notification("conclusion_created", notif_title, details, workspace_id)
    notifications = _load_notifications()
    notifications.insert(0, notif)
    _save_notifications(notifications)


def notify_workspace_event(workspace_id: str, event: str, details: str = "") -> None:
    """Record a workspace-level event notification."""
    event_details = details or f"Event in workspace {workspace_id}"

    if is_admin_configured():
        _save_notification_supabase("workspace_event", event, event_details, workspace_id)
        return

    notif = _make_notification("workspace_event", event, event_details, workspace_id)
    notifications = _load_notifications()
    notifications.insert(0, notif)
    _save_notifications(notifications)


@router.get("")
async def get_notifications(type: str | None = None, workspace_id: str | None = None):
    """Get recent notifications, optionally filtered by type and/or workspace."""
    # --- Supabase path ---
    if is_admin_configured():
        notifications = _load_notifications_supabase(type, workspace_id)
        active = [n for n in notifications if not n.get("dismissed", False)]
        return {"notifications": active, "total": len(active)}

    # --- File-based fallback ---
    notifications = _load_notifications()

    if type:
        notifications = [n for n in notifications if n.get("type") == type]
    if workspace_id:
        notifications = [n for n in notifications if n.get("workspace_id") == workspace_id]

    # Only return non-dismissed notifications by default
    active = [n for n in notifications if not n.get("dismissed", False)]

    return {"notifications": active, "total": len(active)}


@router.post("/dismiss")
async def dismiss_notification(req: DismissRequest):
    """Dismiss a notification by ID."""
    # --- Supabase path ---
    if is_admin_configured():
        found = _dismiss_notification_supabase(req.id)
        if not found:
            raise HTTPException(status_code=404, detail="notification_not_found")
        return {"status": "dismissed", "id": req.id}

    # --- File-based fallback ---
    notifications = _load_notifications()

    found = False
    for notif in notifications:
        if notif["id"] == req.id:
            notif["dismissed"] = True
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="notification_not_found")

    _save_notifications(notifications)
    return {"status": "dismissed", "id": req.id}
