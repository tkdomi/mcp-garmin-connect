import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from supabase import create_client, Client

from src.config import settings

logger = logging.getLogger(__name__)

DATA_TYPES = {
    "sleep": settings.cache_ttl_historical,
    "daily_stats": settings.cache_ttl_daily,
    "body_battery": settings.cache_ttl_daily,
    "activity": settings.cache_ttl_daily,
}


class CacheService:
    def __init__(self):
        self.client: Client = create_client(settings.supabase_url, settings.supabase_key)

    def _is_expired(self, synced_at: str, ttl_hours: int) -> bool:
        synced = datetime.fromisoformat(synced_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - synced > timedelta(hours=ttl_hours)

    def get(self, data_type: str, recorded_date: str) -> Optional[dict]:
        """Return cached data if exists and not expired, else None."""
        try:
            result = (
                self.client.table("health_data")
                .select("raw_data, synced_at")
                .eq("data_type", data_type)
                .eq("recorded_date", recorded_date)
                .single()
                .execute()
            )

            if not result.data:
                return None

            ttl = DATA_TYPES.get(data_type, 1)
            if self._is_expired(result.data["synced_at"], ttl):
                logger.debug(f"Cache expired for {data_type} / {recorded_date}")
                return None

            logger.debug(f"Cache hit: {data_type} / {recorded_date}")
            return result.data["raw_data"]

        except Exception as e:
            logger.warning(f"Cache read error ({data_type}/{recorded_date}): {e}")
            return None

    def set(self, data_type: str, recorded_date: str, data: dict) -> bool:
        """Upsert data into cache."""
        try:
            self.client.table("health_data").upsert({
                "data_type": data_type,
                "recorded_date": recorded_date,
                "raw_data": data,
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }, on_conflict="data_type,recorded_date").execute()
            logger.debug(f"Cache set: {data_type} / {recorded_date}")
            return True
        except Exception as e:
            logger.warning(f"Cache write error ({data_type}/{recorded_date}): {e}")
            return False

    def get_stale(self, data_type: str, recorded_date: str) -> Optional[dict]:
        """Return cached data regardless of TTL (fallback on API failure)."""
        try:
            result = (
                self.client.table("health_data")
                .select("raw_data")
                .eq("data_type", data_type)
                .eq("recorded_date", recorded_date)
                .single()
                .execute()
            )
            return result.data["raw_data"] if result.data else None
        except Exception as e:
            logger.warning(f"Stale cache read error: {e}")
            return None

    def get_range(self, data_type: str, from_date: str, to_date: str) -> list[dict]:
        """Return all cached records for a data type within a date range."""
        try:
            result = (
                self.client.table("health_data")
                .select("recorded_date, raw_data")
                .eq("data_type", data_type)
                .gte("recorded_date", from_date)
                .lte("recorded_date", to_date)
                .order("recorded_date", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.warning(f"Cache range read error: {e}")
            return []
