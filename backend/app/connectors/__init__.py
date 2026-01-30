"""
Ad Platform MVP - Connectors Module

Platform API connectors.
"""

from app.connectors.base import BaseConnector
from app.connectors.google_ads import GoogleAdsConnector

__all__ = ["BaseConnector", "GoogleAdsConnector"]
