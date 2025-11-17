class TenantFeatureFlagService:
    _instance = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TenantFeatureFlagService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Initialize your feature flags and tenant-specific overrides
        self.features = {
            'feature_a': {'enabled': True, 'value': 'default_value', 'degradation_level': 0},
            'feature_b': {'enabled': False, 'value': 'fallback_value', 'degradation_level': 1},
        }

    def is_enabled(self, feature_name, tenant_id=None):
        key = (feature_name, tenant_id)
        if key in self._cache:
            return self._cache[key]['enabled']
        feature = self.features.get(feature_name)
        if feature:
            enabled = feature['enabled']
            if tenant_id:
                # Check if tenant-specific override exists
                tenant_override = self.get_tenant_override(tenant_id, feature_name)
                if tenant_override:
                    enabled = tenant_override['enabled']
            self._cache[key] = {'enabled': enabled}
            return enabled
        return False

    def get_value(self, feature_name, tenant_id=None):
        key = (feature_name, tenant_id)
        if key in self._cache:
            return self._cache[key].get('value')
        feature = self.features.get(feature_name)
        if feature:
            value = feature['value']
            if tenant_id:
                tenant_override = self.get_tenant_override(tenant_id, feature_name)
                if tenant_override:
                    value = tenant_override['value']
            self._cache[key] = {'value': value}
            return value
        return None

    def get_degradation_level(self, feature_name, tenant_id=None):
        key = (feature_name, tenant_id)
        if key in self._cache:
            return self._cache[key].get('degradation_level')
        feature = self.features.get(feature_name)
        if feature:
            degradation_level = feature['degradation_level']
            if tenant_id:
                tenant_override = self.get_tenant_override(tenant_id, feature_name)
                if tenant_override:
                    degradation_level = tenant_override['degradation_level']
            self._cache[key] = {'degradation_level': degradation_level}
            return degradation_level
        return None

    def get_tenant_override(self, tenant_id, feature_name):
        # Logic to retrieve tenant-specific feature flag overrides, e.g., from a database or hardcoded values.
        tenant_overrides = {
            'tenant_1': {'feature_a': {'enabled': False, 'value': 'tenant_value1', 'degradation_level': 2}},
            'tenant_2': {'feature_b': {'enabled': True, 'value': 'tenant_value2', 'degradation_level': 1}},
        }
        return tenant_overrides.get(tenant_id, {}).get(feature_name)

    # Example usage:
    # service = TenantFeatureFlagService()
    # is_feature_a_enabled = service.is_enabled('feature_a', 'tenant_1')
