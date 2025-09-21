"""Centralised URL definitions for service endpoints."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShoppingURLs:
    """URL mapping for the shopping session orchestrator."""

    health: str = "/health"
    sessions: str = "/v1/sessions"


SHOPPING_URLS = ShoppingURLs()

__all__ = ["SHOPPING_URLS", "ShoppingURLs"]
