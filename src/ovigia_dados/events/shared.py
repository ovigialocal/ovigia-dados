"""Shared public surface for city-event collectors.

The implementation currently lives in the original Sympla module. New adapters import
from here so the storage/model contract can move later without coupling each source to
Sympla-specific names.
"""

from ovigia_dados.events.sympla import (
    CdxSnapshot,
    EventObservation,
    event_content_hash,
    fetch_text,
    is_porto_velho,
    materialize_observations,
    query_cdx,
)

__all__ = [
    "CdxSnapshot",
    "EventObservation",
    "event_content_hash",
    "fetch_text",
    "is_porto_velho",
    "materialize_observations",
    "query_cdx",
]
