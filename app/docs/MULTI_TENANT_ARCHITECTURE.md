# Multi-Tenant Orchestrator Refactoring Documentation

## Overview of TenantContext Propagation System
The TenantContext propagation system is designed to manage the context of a tenant across various service layers. It ensures that requests can be identified and processed according to the specific tenant they belong to. This involves the use of middleware that captures the tenant information from the incoming request and makes it available throughout the application lifecycle.

## TenantConfigService Usage and Configuration
The TenantConfigService is responsible for loading and providing configuration settings related to tenants. It can be set up as follows:

```javascript
const tenantConfigService = new TenantConfigService();
// Configuration for tenant 'A'
tenantConfigService.setConfig('tenantA', { featureX: true, timeout: 3000 });
```

### Configuration Example
To configure the TenantConfigService, you can load data from a JSON file or a database, streamlining the process of managing tenant-specific configurations.

## TenantFeatureFlagService with Examples
The TenantFeatureFlagService allows for feature toggling on a per-tenant basis. Here’s an example of how to use it:

```javascript
const featureFlagService = new TenantFeatureFlagService();

// Check if a feature is enabled for a tenant
const isFeatureEnabled = featureFlagService.isEnabled('tenantA', 'newFeature');
if (isFeatureEnabled) {
    // Execute feature specific logic
}
```

## Integration Guide for Orchestrator Handlers
Integrating orchestrator handlers with the multi-tenant system involves:
1. Implementing tenant-awareness in all handlers.
2. Utilizing the provided TenantContext when processing requests.
3. Following standard practices to ensure consistency across services.

## Code Examples Showing Before/After Refactoring
**Before Refactoring:**
```javascript
function handleRequest(req) {
    const tenant = getTenantFromRequest(req);
    // Process request without tenant context
}
```
**After Refactoring:**
```javascript
function handleRequest(req) {
    const tenantContext = TenantContext.get(req);
    // Process request with tenant context awareness
}
```

## Testing Guidelines for Multi-Tenant Scenarios
To test multi-tenant scenarios, ensure that:
- Tests cover different tenant configurations.
- Each tenant’s context is isolated during tests.
- Utilize mocking frameworks to simulate tenant behavior.

## Grafana Dashboard Configuration for Tenant Metrics
To configure Grafana dashboards for tenant metrics, you can use the following steps:
1. Add a new data source pointing to your metrics storage.
2. Create panels for each tenant, utilizing tenant IDs to filter metrics.
3. Use Grafana queries to aggregate data for specific tenants.

```json
{
    "targets": [{
        "target": "sum(rate(requests_total{tenantId=\"tenantA\"}[5m]))"
    }],
    "format": "time_series"
}
```

This configuration allows monitoring of tenant specific metrics effectively, ensuring that the performance of each tenant can be tracked individually.