# Deployment Readiness Checklist

## 🎯 Overview

This checklist ensures the Agente Hotelero system is fully prepared for production deployment. All items must be completed before proceeding with deployment.

## 📋 Pre-Deployment Validation

### ✅ Security & Configuration

- [ ] **SEC-001**: All hardcoded secrets removed from source code
- [ ] **SEC-002**: Production `.env.production` file created with real credentials
- [ ] **SEC-003**: All placeholder values (REPLACE_WITH_*) updated in environment file
- [ ] **SEC-004**: Strong passwords used (16+ chars, mixed case, numbers, symbols)
- [ ] **SEC-005**: WhatsApp Business API credentials properly configured
- [ ] **SEC-006**: Gmail App Password generated (not regular password)
- [ ] **SEC-007**: PMS API key obtained and tested
- [ ] **SEC-008**: SSL certificates configured for domain
- [ ] **SEC-009**: Security scan passed: `make security-fast`

### ✅ Infrastructure & Dependencies

- [ ] **INF-001**: Docker and Docker Compose installed and working
- [ ] **INF-002**: `Dockerfile.production` exists and builds successfully
- [ ] **INF-003**: Production Docker Compose file validated
- [ ] **INF-004**: Database backup procedures in place
- [ ] **INF-005**: Domain DNS configured and pointing to server
- [ ] **INF-006**: Required ports open (80, 443, 8000)
- [ ] **INF-007**: Sufficient disk space for Docker images and data
- [ ] **INF-008**: Network connectivity to all external services

### ✅ Application Readiness

- [ ] **APP-001**: All tests passing: `make test`
- [ ] **APP-002**: Linting and formatting clean: `make lint fmt`
- [ ] **APP-003**: Health endpoints responding correctly
- [ ] **APP-004**: PMS integration tested and working
- [ ] **APP-005**: WhatsApp webhook verified and working
- [ ] **APP-006**: Gmail integration tested
- [ ] **APP-007**: Audio processing working (if enabled)
- [ ] **APP-008**: Database migrations completed
- [ ] **APP-009**: Redis connectivity verified

### ✅ Monitoring & Observability

- [ ] **MON-001**: Prometheus configured and scraping metrics
- [ ] **MON-002**: Grafana dashboards imported and working
- [ ] **MON-003**: AlertManager configured with notification channels
- [ ] **MON-004**: SLO compliance validated: `make validate-slo-compliance`
- [ ] **MON-005**: Runbooks tested and up-to-date
- [ ] **MON-006**: Log aggregation working
- [ ] **MON-007**: Error tracking configured

### ✅ Performance & Resilience

- [ ] **PERF-001**: Load testing completed: `make performance-test`
- [ ] **PERF-002**: Stress testing completed: `make stress-test`
- [ ] **PERF-003**: Chaos engineering tests passed: `make resilience-test`
- [ ] **PERF-004**: Circuit breakers configured and tested
- [ ] **PERF-005**: Rate limiting configured
- [ ] **PERF-006**: Caching strategy validated
- [ ] **PERF-007**: Database performance optimized

### ✅ Operational Readiness

- [ ] **OPS-001**: Deployment scripts tested: `make validate-deployment`
- [ ] **OPS-002**: Rollback procedures documented and tested
- [ ] **OPS-003**: Backup and restore procedures validated
- [ ] **OPS-004**: Monitoring alerts configured and tested
- [ ] **OPS-005**: On-call procedures established
- [ ] **OPS-006**: Documentation updated and complete
- [ ] **OPS-007**: Team training completed

## 🚀 Deployment Process

### Phase 1: Pre-Deployment Validation

```bash
# Run comprehensive validation
make validate-deployment

# Verify all checks pass
echo "Validation complete - review output for any issues"
```

### Phase 2: Staging Deployment (Recommended)

```bash
# Deploy to staging first
make deploy-staging

# Run smoke tests on staging
curl -f http://staging.yourdomain.com/health/ready
```

### Phase 3: Production Deployment

```bash
# Option A: Standard deployment
make deploy-production

# Option B: Canary deployment (recommended)
make canary-deploy
```

### Phase 4: Post-Deployment Validation

```bash
# Check deployment status
make deployment-status

# Verify health endpoints
curl -f https://yourdomain.com/health/ready
curl -f https://yourdomain.com/health/live

# Monitor key metrics
make validate-slo-compliance
```

## 🔧 Common Pre-Deployment Issues

### Issue: Environment Variables Not Set
**Symptoms**: Application fails to start with validation errors
**Solution**: 
1. Copy `.env.example` to `.env.production`
2. Replace all `REPLACE_WITH_*` values with real credentials
3. Run `make validate-deployment` to verify

### Issue: Docker Build Failures
**Symptoms**: Production Docker build fails
**Solution**:
1. Ensure `requirements-prod.txt` is up to date
2. Check `Dockerfile.production` syntax
3. Build locally: `make build-production`

### Issue: Database Connection Failures
**Symptoms**: Application can't connect to PostgreSQL/MySQL
**Solution**:
1. Verify database credentials in `.env.production`
2. Ensure databases are running: `docker compose ps`
3. Check network connectivity between containers

### Issue: External Service Integration Failures
**Symptoms**: WhatsApp/Gmail/PMS integration not working
**Solution**:
1. Verify API credentials are correct and not expired
2. Check network connectivity to external services
3. Review service-specific authentication requirements

## 📊 Success Criteria

The deployment is considered successful when:

- [ ] All health endpoints return 200 OK
- [ ] SLO compliance is >95% across all metrics
- [ ] No critical alerts firing
- [ ] Key user journeys working end-to-end
- [ ] Performance metrics within acceptable ranges
- [ ] Monitoring and alerting operational

## 🆘 Emergency Procedures

### Immediate Rollback
```bash
# If deployment fails or critical issues arise
cd /home/runner/work/SIST_AGENTICO_HOTELERO/SIST_AGENTICO_HOTELERO/agente-hotel-api
./scripts/rollback.sh

# Or manual rollback
docker compose -f docker-compose.production.yml down
# Restore from backup
# Restart previous version
```

### Emergency Contacts
- **Technical Lead**: [Contact Information]
- **Operations**: [Contact Information]  
- **Business Owner**: [Contact Information]

## 📚 Additional Resources

- [Governance Framework](./GOVERNANCE_FRAMEWORK.md)
- [Operations Manual](./OPERATIONS_MANUAL.md)
- [Runbooks](./runbooks/)
- [Performance Testing Guide](./PHASE3_PERFORMANCE_CHAOS.md)

---

**Last Updated**: December 2024
**Version**: 1.0
**Next Review**: [Set review date]