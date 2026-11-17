"""Deterministic alert fingerprinting and normalization."""

from __future__ import annotations

import hashlib
from typing import Any

# Fingerprint algorithm version
FINGERPRINT_VERSION = 1


def normalize_string(value: str | None) -> str:
    """Normalize text by stripping whitespace and lowering case."""
    if not value:
        return ""
    return value.strip().lower()


def generate_fingerprint(
    service_key: str,
    alert_type: str,
    severity: str,
    resource: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Calculate stable, deterministic fingerprint hash.
    
    Excludes volatile fields like timestamps, event IDs, and request IDs.
    Uses SHA-256 over normalized canonical components.
    """
    norm_service = normalize_string(service_key)
    norm_type = normalize_string(alert_type)
    norm_severity = normalize_string(severity)
    norm_resource = normalize_string(resource)

    # Build stable signature string
    canonical_repr = f"v{FINGERPRINT_VERSION}|{norm_service}|{norm_type}|{norm_severity}|{norm_resource}"
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()
