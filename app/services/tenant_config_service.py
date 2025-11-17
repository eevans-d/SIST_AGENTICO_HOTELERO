import time
from typing import Dict, Any, Optional

class TenantConfigService:
    """Service to manage tenant-specific configuration."""

    def __init__(self, dynamic_tenant_service: Any, defaults: Dict[str, Any]) -> None:
        self.dynamic_tenant_service = dynamic_tenant_service
        self.defaults = defaults
        self.cache: Dict[str, Any] = {}
        self.cache_ttl: int = 300  # 5 minutes

    async def get_business_hours(self, tenant_id: str) -> Dict[str, Any]:
        """Retrieve business hours for the tenant.

        Args:
            tenant_id (str): The ID of the tenant.

        Returns:
            Dict[str, Any]: A dictionary containing start_hour, end_hour, timezone, and weekend_mode.
        """
        return await self._fetch_from_cache_or_service(
            tenant_id, self._retrieve_business_hours
        )

    async def get_nlp_thresholds(self, tenant_id: str) -> Dict[str, float]:
        """Retrieve NLP confidence thresholds for the tenant.

        Args:
            tenant_id (str): The ID of the tenant.

        Returns:
            Dict[str, float]: A dictionary containing very_low, low, and high thresholds.
        """
        return await self._fetch_from_cache_or_service(
            tenant_id, self._retrieve_nlp_thresholds
        )

    async def get_late_checkout_policy(self, tenant_id: str) -> Dict[str, Any]:
        """Retrieve late checkout policy for the tenant.

        Args:
            tenant_id (str): The ID of the tenant.

        Returns:
            Dict[str, Any]: A dictionary containing enabled, default_time, and fee_percentage.
        """
        return await self._fetch_from_cache_or_service(
            tenant_id, self._retrieve_late_checkout_policy
        )

    async def get_response_template_overrides(self, tenant_id: str) -> Dict[str, str]:
        """Retrieve custom response templates for the tenant.

        Args:
            tenant_id (str): The ID of the tenant.

        Returns:
            Dict[str, str]: A dictionary of custom templates.
        """
        return await self._fetch_from_cache_or_service(
            tenant_id, self._retrieve_response_template_overrides
        )

    async def _fetch_from_cache_or_service(self, tenant_id: str, fetch_method: Any) -> Any:
        """Fetch data either from the cache or the service if cache is expired.

        Args:
            tenant_id (str): The ID of the tenant.
            fetch_method (Callable): The method to fetch data if cache is expired.

        Returns:
            Any: The fetched data.
        """
        current_time = time.time()
        if tenant_id in self.cache:
            cached_time, data = self.cache[tenant_id]
            if (current_time - cached_time) < self.cache_ttl:
                return data

        # Cache expired, fetch from service
        data = await fetch_method(tenant_id)
        self.cache[tenant_id] = (current_time, data)
        return data

    async def _retrieve_business_hours(self, tenant_id: str) -> Dict[str, Any]:
        # Integration with dynamic_tenant_service
        metadata = await self.dynamic_tenant_service.fetch_metadata(tenant_id)
        return {
            'start_hour': metadata.get('start_hour', self.defaults['business_hours']['start_hour']),
            'end_hour': metadata.get('end_hour', self.defaults['business_hours']['end_hour']),
            'timezone': metadata.get('timezone', self.defaults['business_hours']['timezone']),
            'weekend_mode': metadata.get('weekend_mode', self.defaults['business_hours']['weekend_mode'])
        }

    async def _retrieve_nlp_thresholds(self, tenant_id: str) -> Dict[str, float]:
        # Integration with dynamic_tenant_service
        metadata = await self.dynamic_tenant_service.fetch_metadata(tenant_id)
        return {
            'very_low': metadata.get('nlp_thresholds', {}).get('very_low', self.defaults['nlp_thresholds']['very_low']),
            'low': metadata.get('nlp_thresholds', {}).get('low', self.defaults['nlp_thresholds']['low']),
            'high': metadata.get('nlp_thresholds', {}).get('high', self.defaults['nlp_thresholds']['high'])
        }

    async def _retrieve_late_checkout_policy(self, tenant_id: str) -> Dict[str, Any]:
        # Integration with dynamic_tenant_service
        metadata = await self.dynamic_tenant_service.fetch_metadata(tenant_id)
        return {
            'enabled': metadata.get('late_checkout_policy', {}).get('enabled', self.defaults['late_checkout_policy']['enabled']),
            'default_time': metadata.get('late_checkout_policy', {}).get('default_time', self.defaults['late_checkout_policy']['default_time']),
            'fee_percentage': metadata.get('late_checkout_policy', {}).get('fee_percentage', self.defaults['late_checkout_policy']['fee_percentage'])
        }

    async def _retrieve_response_template_overrides(self, tenant_id: str) -> Dict[str, str]:
        # Integration with dynamic_tenant_service
        metadata = await self.dynamic_tenant_service.fetch_metadata(tenant_id)
        return metadata.get('response_template_overrides', self.defaults['response_template_overrides'])

