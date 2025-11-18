import time
from typing import Optional, Dict, Any
import logging
from dynamic_tenant_service import get_tenant_meta
from core.constants import DEFAULT_TENANT_CONFIG

# Configure structured logging
logger = logging.getLogger(__name__)

class TenantConfigService:
    _instance = None
    _cache: Dict[str, Dict[str, Any]] = {}
    _cache_timestamp: Dict[str, float] = {}
    _cache_ttl: int = 300  # Cache TTL in seconds

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TenantConfigService, cls).__new__(cls)
        return cls._instance

    def get_tenant_config(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetch tenant configuration.

        Args:
            tenant_id (Optional[str]): The ID of the tenant.

        Returns:
            Dict[str, Any]: The tenant configuration data.
        """
        try:
            if tenant_id:
                # Check cache first
                if tenant_id in self._cache and (time.time() - self._cache_timestamp[tenant_id]) < self._cache_ttl:
                    logger.debug("Returning cached config for tenant ID: %s", tenant_id)
                    return self._cache[tenant_id]

                # Fetch tenant metadata
                tenant_meta = get_tenant_meta(tenant_id)
                if not tenant_meta:
                    logger.warning("No tenant metadata found for tenant ID: %s, falling back to defaults", tenant_id)
                    return DEFAULT_TENANT_CONFIG
                # Cache the result
                self._cache[tenant_id] = tenant_meta
                self._cache_timestamp[tenant_id] = time.time()
                logger.info("Fetched and cached config for tenant ID: %s", tenant_id)
                return tenant_meta
            else:
                logger.info("Fetching global defaults as tenant_id is None")
                return DEFAULT_TENANT_CONFIG
        except Exception as e:
            logger.error("Error fetching tenant config for tenant ID: %s, error: %s", tenant_id, e)
            return DEFAULT_TENANT_CONFIG

    def invalidate_cache(self, tenant_id: Optional[str] = None) -> None:
        """Invalidate cache for a specific tenant or all tenants.

        Args:
            tenant_id (Optional[str]): The ID of the tenant.
        """
        if tenant_id:
            if tenant_id in self._cache:
                del self._cache[tenant_id]
                del self._cache_timestamp[tenant_id]
                logger.info("Cache invalidated for tenant ID: %s", tenant_id)
            else:
                logger.warning("Attempted to invalidate non-existing cache for tenant ID: %s", tenant_id)
        else:
            self._cache.clear()
            self._cache_timestamp.clear()
            logger.info("Cache invalidated for all tenants")


def get_tenant_config_service() -> TenantConfigService:
    """Get the singleton instance of TenantConfigService.

    Returns:
        TenantConfigService: The singleton instance.
    """
    return TenantConfigService()