# QloApps PMS Integration Guide

## Overview

This guide explains how to configure and test the QloApps PMS integration for the Agente Hotelero IA system.

## Prerequisites

- QloApps instance (version 1.6+)
- API access enabled in QloApps
- Admin credentials to generate API key
- Network access from agent to QloApps instance

## Step 1: Generate QloApps API Key

1. Log in to your QloApps admin panel
2. Navigate to **Advanced Parameters** → **Webservice**
3. Enable webservice if not already enabled
4. Create a new API key:
   - Click "Add new webservice key"
   - Set a description (e.g., "Hotel AI Agent")
   - Select permissions (at minimum: GET for hotels, rooms, bookings; POST for bookings, customers)
   - Generate and copy the API key

## Step 2: Configure Environment Variables

Edit your `.env` file or set environment variables:

```bash
# PMS Configuration
PMS_TYPE=qloapps
PMS_BASE_URL=https://your-qloapps-domain.com
PMS_API_KEY=YOUR_GENERATED_API_KEY_HERE
PMS_HOTEL_ID=1  # Your hotel ID in QloApps (default: 1)

# Optional: PMS Integration Settings
CHECK_PMS_IN_READINESS=true  # Enable PMS health checks
PMS_TIMEOUT=30  # API timeout in seconds
```

### Configuration Parameters

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `PMS_TYPE` | PMS system type | `mock` | Yes |
| `PMS_BASE_URL` | QloApps base URL (without /api) | - | Yes |
| `PMS_API_KEY` | Webservice API key | - | Yes |
| `PMS_HOTEL_ID` | Default hotel ID | 1 | No |
| `CHECK_PMS_IN_READINESS` | Include PMS in health checks | true | No |
| `PMS_TIMEOUT` | Request timeout (seconds) | 30 | No |

## Step 3: Test Connection

Run the setup script to validate your configuration:

```bash
# Test all components
python scripts/setup_qloapps.py test

# Test connection only
python scripts/setup_qloapps.py connection

# Interactive setup
python scripts/setup_qloapps.py setup
```

Expected output:
```
✅ Connection: OK
✅ Hotels: 1 found
✅ Room Types: 5 found
✅ Availability: 3 rooms available

🎉 QloApps integration is ready!
```

## Step 4: Verify Room Type Mapping

The adapter uses a room type mapping in `pms_adapter.py`. Verify it matches your QloApps setup:

```python
ROOM_TYPE_MAPPING = {
    "individual": 1,
    "doble": 2,
    "suite": 3,
    "familiar": 4,
}
```

To list your actual room types:

```bash
python scripts/setup_qloapps.py test | grep "ROOM TYPES" -A 20
```

Update the mapping dictionary if your IDs differ.

## Step 5: Docker Compose Setup

For production deployment with real QloApps:

```bash
# Use the 'pms' profile to include QloApps + MySQL
docker compose --profile pms up -d

# Or for local dev with mock PMS (no QloApps needed)
docker compose up -d
```

### Production Configuration

1. Update `docker-compose.production.yml` with QloApps service:

```yaml
services:
  agente-api:
    environment:
      - PMS_TYPE=qloapps
      - PMS_BASE_URL=https://qloapps.yourhotel.com
      - PMS_API_KEY=${PMS_API_KEY}
      - PMS_HOTEL_ID=${PMS_HOTEL_ID:-1}
```

2. Set secrets in `.env.production`:

```bash
PMS_API_KEY=your_production_api_key_here
```

## API Endpoints Covered

The integration implements the following QloApps operations:

### Room Management
- `GET /api/rooms` - List room types
- `GET /api/rooms/{id}` - Get room type details
- `GET /api/rooms/availability` - Check availability

### Booking Management
- `POST /api/bookings` - Create booking
- `GET /api/bookings/{id}` - Get booking details
- `PUT /api/bookings/{id}` - Update booking status
- `DELETE /api/bookings/{id}` - Cancel booking

### Customer Management
- `POST /api/customers` - Create customer
- `GET /api/customers/{id}` - Get customer details
- `GET /api/customers?filter[email]={email}` - Search by email

### Hotel Management
- `GET /api/hotels` - List hotels
- `GET /api/hotels/{id}` - Get hotel details

## Caching Strategy

The adapter implements intelligent caching:

- **Room Types**: Cached for 1 hour (3600s)
- **Availability**: Cached for 5 minutes (300s)
- **Bookings**: Not cached (always fresh data)

Cache is automatically invalidated on mutations (create/update/cancel bookings).

## Circuit Breaker Configuration

The PMS adapter includes a circuit breaker for resilience:

- **Failure Threshold**: 5 consecutive failures
- **Recovery Timeout**: 30 seconds
- **States**: CLOSED → OPEN → HALF_OPEN

Monitor circuit breaker status via Prometheus:
```
pms_circuit_breaker_state{service="pms_adapter"}
```

## Monitoring & Metrics

Key Prometheus metrics for PMS integration:

```
# Operations counter
pms_operations_total{operation="check_availability",status="success"}

# Latency histogram
pms_api_latency_seconds{endpoint="/api/availability",method="GET"}

# Cache performance
pms_cache_hits_total{operation="get_room_types"}
pms_cache_misses_total{operation="get_room_types"}

# Circuit breaker state (0=closed, 1=open, 2=half-open)
pms_circuit_breaker_state{service="pms_adapter"}

# Error counter
pms_errors_total{operation="create_booking",error_type="rate_limit"}
```

View in Grafana: http://localhost:3000 (default credentials: admin/admin)

## Troubleshooting

### Connection Failed

**Symptoms**: `❌ Connection failed` in setup script

**Solutions**:
1. Verify QloApps is accessible: `curl -I https://your-qloapps.com`
2. Check API key permissions in QloApps admin
3. Ensure webservice is enabled in QloApps
4. Verify firewall/network allows connection
5. Check logs: `docker logs agente-api` or `tail -f logs/app.log`

### Authentication Error (401)

**Symptoms**: `PMSAuthError: Unauthorized`

**Solutions**:
1. Regenerate API key in QloApps
2. Update `PMS_API_KEY` in `.env`
3. Verify API key has required permissions (GET, POST for relevant resources)
4. Check QloApps webservice logs

### Rate Limiting (429)

**Symptoms**: `PMSRateLimitError: Rate limit exceeded`

**Solutions**:
1. Increase QloApps rate limits in admin panel
2. Enable Redis caching to reduce API calls
3. Adjust cache TTLs in `pms_adapter.py`
4. Monitor metrics to identify high-traffic operations

### No Room Types Found

**Symptoms**: `⚠️ No room types found`

**Solutions**:
1. Verify rooms are configured in QloApps
2. Check hotel ID: `python scripts/setup_qloapps.py test`
3. Ensure API key has GET permission for rooms resource
4. Check QloApps database: `SELECT * FROM ps_htl_room_type`

### Booking Creation Fails

**Symptoms**: `Failed to create booking: Invalid room type`

**Solutions**:
1. Update `ROOM_TYPE_MAPPING` dictionary to match your QloApps room type IDs
2. Verify room availability for selected dates
3. Check guest information format (all required fields)
4. Enable debug logging: `LOG_LEVEL=DEBUG` in `.env`

## Development vs Production

### Local Development (Mock PMS)

For local development without QloApps:

```bash
# Use mock adapter
PMS_TYPE=mock

# Start without pms profile
docker compose up -d
```

Mock adapter simulates QloApps responses for testing.

### Staging/Production (Real PMS)

For staging and production:

```bash
# Use real QloApps
PMS_TYPE=qloapps
PMS_BASE_URL=https://qloapps.yourhotel.com
PMS_API_KEY=your_real_api_key

# Start with pms profile (if self-hosting QloApps)
docker compose --profile pms up -d
```

## Security Best Practices

1. **Never commit API keys**: Use `.env` files (gitignored)
2. **Use HTTPS**: Always connect to QloApps over HTTPS
3. **Rotate keys**: Regularly regenerate API keys
4. **Least privilege**: Grant only required permissions to API key
5. **Monitor access**: Enable QloApps webservice audit logs
6. **Secrets management**: Use Docker secrets or vault in production

## Next Steps

After successful setup:

1. ✅ Run integration tests: `make test`
2. ✅ Deploy to staging: `make deploy ENV=staging`
3. ✅ Monitor metrics in Grafana
4. ✅ Test booking flow end-to-end
5. ✅ Configure AlertManager for PMS failures

## Support

- **QloApps Documentation**: https://qloapps.com/documentation/
- **Project Documentation**: See `/docs/OPERATIONS_MANUAL.md`
- **Issue Tracker**: Report integration issues via project repository

## Changelog

- **2025-01-07**: Initial QloApps integration (Option B implementation)
- **Phase 1**: QloApps client with full API coverage
- **Phase 2**: Adapter integration with caching and circuit breaker
- **Phase 3**: Setup tooling and documentation (this file)
