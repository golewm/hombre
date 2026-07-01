"""
Supabase client module for Hombre.

Provides lazy-initialized clients with anon and service role keys.
If Supabase isn't configured, everything falls back to file-based storage.

I sold my soul to Satan for this integration. Worst trade ever.
"""

import os
import logging
from typing import Optional, Any

log = logging.getLogger("hombre")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")  # anon/public key
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")  # service role key

_client = None
_admin_client = None


def get_client():
    """Get the Supabase client (anon key)."""
    global _client
    if _client is None and SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        log.info("Supabase anon client initialized")
    return _client


def get_admin_client():
    """Get the Supabase admin client (service key)."""
    global _admin_client
    if _admin_client is None and SUPABASE_URL and SUPABASE_SERVICE_KEY:
        from supabase import create_client
        _admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        log.info("Supabase admin client initialized")
    return _admin_client


def is_configured():
    """Check if Supabase is configured."""
    return bool(SUPABASE_URL and SUPABASE_KEY)


def is_admin_configured():
    """Check if Supabase admin (service key) is configured."""
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


def reset_clients():
    """Reset clients (for testing or reconfiguration)."""
    global _client, _admin_client
    _client = None
    _admin_client = None
