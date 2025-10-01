# 🎯 Deployment Action Plan

**Generated**: October 1, 2025  
**Current Status**: ✅ **READY FOR PRODUCTION CONFIGURATION**  
**Phase**: Post-Merge Validation Complete

---

## 📊 Current State Dashboard

```
╔══════════════════════════════════════════════════════════════╗
║                   SYSTEM STATUS DASHBOARD                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  📦 Phase 5: MERGED ✅                                        ║
║  🧪 Tests: 46/46 (100%) ✅                                    ║
║  🔍 Lint: PASS ✅                                             ║
║  🚦 Preflight: GO (30.0/50) ✅                                ║
║  📝 Docs: COMPLETE ✅                                         ║
║  🔄 Git: Clean & Synced ✅                                    ║
║  💾 Backups: Not configured ⚠️                                ║
║  🔐 Prod Secrets: Not configured ⚠️                           ║
║  🚀 Deployment: Pending 🔄                                    ║
║                                                               ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 🎯 3-Phase Deployment Strategy

### **Phase 1: Configuration** ⚙️ (Current)
**Goal**: Prepare production environment  
**Duration**: 2-4 hours  
**Owner**: DevOps/Admin

#### Tasks:
1. **Create production `.env` file**
   ```bash
   cd agente-hotel-api
   cp .env.example .env.production
   # Edit .env.production with real secrets
   ```

2. **Configure secrets** (use secure vault/password manager):
   - [ ] `PMS_API_KEY` - Get from QloApps admin panel
   - [ ] `PMS_HOTEL_ID` - Hotel identifier in QloApps
   - [ ] `WHATSAPP_ACCESS_TOKEN` - Meta Business API token
   - [ ] `WHATSAPP_VERIFY_TOKEN` - Webhook verification token
   - [ ] `WHATSAPP_PHONE_NUMBER_ID` - WhatsApp Business phone ID
   - [ ] `GMAIL_CLIENT_ID` - Google Cloud Console OAuth
   - [ ] `GMAIL_CLIENT_SECRET` - Google Cloud Console OAuth
   - [ ] `GMAIL_REFRESH_TOKEN` - OAuth refresh token
   - [ ] `SECRET_KEY` - Generate: `openssl rand -hex 32`
   - [ ] `POSTGRES_PASSWORD` - Strong password for DB
   - [ ] `REDIS_PASSWORD` - Strong password for Redis

3. **SSL Certificates** (for NGINX):
   ```bash
   # Option A: Let's Encrypt (automated)
   certbot certonly --standalone -d your-domain.com
   
   # Option B: Manual certificates
   cp /path/to/cert.crt agente-hotel-api/docker/nginx/ssl/production.crt
   cp /path/to/cert.key agente-hotel-api/docker/nginx/ssl/production.key
   ```

4. **Environment variables**:
   ```bash
   # In .env.production
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   DEBUG=false
   PMS_TYPE=qloapps  # Remove mock
   ```

5. **Validate configuration**:
   ```bash
   make validate-env  # Check all required vars set
   ```

**Deliverable**: ✅ `.env.production` file with all secrets configured

---

### **Phase 2: Staging Deployment** 🧪 (Next)
**Goal**: Validate in staging environment  
**Duration**: 4-8 hours  
**Owner**: DevOps + QA

#### Tasks:
1. **Deploy to staging**:
   ```bash
   # Copy production config to staging
   cp .env.production .env.staging
   # Adjust staging-specific vars (different DB, etc.)
   
   # Start staging stack
   docker compose -f docker-compose.yml \
                  -f docker-compose.staging.yml \
                  --profile pms up -d
   ```

2. **Health checks**:
   ```bash
   make health
   # Verify all services healthy:
   # - agente-api: http://staging.domain.com/health/ready
   # - postgres: Connection OK
   # - redis: Connection OK
   # - prometheus: http://staging.domain.com:9090
   # - grafana: http://staging.domain.com:3000
   ```

3. **Functional testing**:
   ```bash
   # Run full test suite against staging
   TEST_ENV=staging make test
   
   # Manual smoke tests:
   # - Send test WhatsApp message
   # - Check reservation flow
   # - Verify PMS integration
   # - Test NLP responses
   # - Check metrics collection
   ```

4. **Performance testing**:
   ```bash
   # Run k6 smoke test
   npm run smoke:test
   
   # Check canary metrics
   make canary-diff
   ```

5. **Security validation**:
   ```bash
   # Run security scan
   make security-fast
   
   # Verify headers
   curl -I https://staging.domain.com/health/live
   # Check for: X-Frame-Options, X-Content-Type-Options, etc.
   ```

6. **Monitor for 24-48 hours**:
   - Watch Grafana dashboards
   - Check AlertManager (no false positives)
   - Review logs for errors
   - Validate metrics accuracy

**Deliverable**: ✅ Staging environment fully operational with 24h+ stability

---

### **Phase 3: Production Deployment** 🚀 (Final)
**Goal**: Go live with production  
**Duration**: 2-4 hours (+ 48h monitoring)  
**Owner**: DevOps + Product

#### Pre-Deployment Checklist:
- [ ] Staging validated (24h+ uptime)
- [ ] All tests passing in staging
- [ ] Security scan clean
- [ ] Preflight score ≤ 50 (GO)
- [ ] Backup strategy configured
- [ ] Rollback plan documented
- [ ] Monitoring alerts configured
- [ ] Team notified of deployment window
- [ ] Maintenance window scheduled (if needed)

#### Tasks:
1. **Pre-deployment backup**:
   ```bash
   # Backup current production (if upgrading)
   make backup
   # Store backup in secure location
   ```

2. **Deploy production**:
   ```bash
   # Use production config
   cp .env.production .env
   
   # Deploy with production profile
   docker compose -f docker-compose.yml \
                  -f docker-compose.production.yml \
                  --profile pms up -d
   
   # Alternative: Use deployment script
   ./scripts/deploy.sh production
   ```

3. **Immediate validation** (first 15 minutes):
   ```bash
   # Health checks
   make health
   
   # Service status
   docker compose ps
   
   # Check logs for errors
   make logs | grep -i error
   
   # Verify endpoints
   curl https://domain.com/health/ready
   curl https://domain.com/metrics
   ```

4. **Smoke testing** (first 30 minutes):
   ```bash
   # Run automated smoke tests
   npm run smoke:test
   
   # Manual critical path tests:
   # 1. WhatsApp message → Response
   # 2. Reservation creation → PMS sync
   # 3. Check availability → Correct data
   # 4. NLP intent recognition → Proper routing
   ```

5. **Canary monitoring** (first 2 hours):
   ```bash
   # Compare metrics with baseline
   make canary-diff
   
   # Check:
   # - P95 latency (should be ≤ 10% increase)
   # - Error rate (should be ≤ 50% increase)
   # - Throughput (should be stable)
   ```

6. **Extended monitoring** (48 hours):
   - **Grafana dashboards**:
     - Request rate and latency
     - Error rates by service
     - PMS circuit breaker state
     - Tenant resolution metrics
     - NLP confidence scores
   
   - **AlertManager**:
     - No critical alerts
     - Review warnings
   
   - **Logs**:
     - No recurring errors
     - Check correlation IDs for tracing

7. **Post-deployment validation**:
   ```bash
   # Final preflight check
   make preflight
   
   # Generate status report
   ./scripts/generate-status-summary.sh
   ```

**Deliverable**: ✅ Production deployment successful with 48h+ stability

---

## 🚨 Rollback Plan

### Triggers for Rollback:
- Critical error rate > 5%
- P95 latency > 2x baseline
- PMS integration failures > 10%
- Data corruption detected
- Security breach identified

### Rollback Procedure:
```bash
# 1. Stop current deployment
docker compose down

# 2. Restore from backup
./scripts/restore.sh <backup-timestamp>

# 3. Start previous version
docker compose -f docker-compose.previous.yml up -d

# 4. Validate rollback
make health
make test

# 5. Notify team
# Send alert via configured channels
```

**Rollback Time**: Target < 15 minutes

---

## 📈 Success Metrics

### Health Indicators:
- **Uptime**: > 99.5% (SLA target)
- **Error rate**: < 1%
- **P95 latency**: < 500ms (API endpoints)
- **PMS sync**: > 99% success rate
- **WhatsApp delivery**: > 98%
- **NLP accuracy**: > 85% intent recognition

### Business Metrics:
- Guest satisfaction with AI responses
- Reservation conversion rate
- Response time to guest inquiries
- Staff time saved (automation)

---

## 🛠️ Tools & Commands Reference

### Quick Commands:
```bash
# Environment setup
make dev-setup              # Copy .env.example
make install                # Install dependencies

# Quality checks
make test                   # Run all tests
make lint                   # Lint code
make fmt                    # Format code
make preflight              # Risk assessment
make security-fast          # Security scan

# Docker operations
make docker-up              # Start all services
make docker-down            # Stop all services
make docker-logs            # View logs
make health                 # Health checks

# Deployment
make backup                 # Backup databases
make restore                # Restore from backup
make canary-diff            # Canary analysis

# Monitoring
make logs                   # Follow all logs
make metrics                # View metrics endpoint
```

### Service URLs:
- **API**: http://localhost:8000
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093

---

## 📞 Escalation Path

### Issue Severity Levels:

**P0 - Critical** (Service down):
- Contact: DevOps Lead + CTO
- Response: Immediate (< 5 min)
- Action: Execute rollback plan

**P1 - High** (Degraded performance):
- Contact: DevOps Team
- Response: < 15 min
- Action: Investigate and mitigate

**P2 - Medium** (Non-critical issues):
- Contact: Development Team
- Response: < 1 hour
- Action: Create ticket and plan fix

**P3 - Low** (Minor issues):
- Contact: Development Team
- Response: Next business day
- Action: Backlog item

---

## 📚 Documentation Checklist

Before deployment, ensure:
- [ ] `.github/copilot-instructions.md` reviewed
- [ ] `STATUS_DEPLOYMENT.md` current
- [ ] `POST_MERGE_VALIDATION.md` verified
- [ ] `MERGE_COMPLETED.md` archived
- [ ] `agente-hotel-api/docs/OPERATIONS_MANUAL.md` ready
- [ ] `agente-hotel-api/README-Infra.md` updated
- [ ] Runbooks for common scenarios prepared
- [ ] Team trained on monitoring tools

---

## 🎯 Next Immediate Actions

### Today (Oct 1, 2025):
1. ✅ Review this deployment plan
2. ⚠️ Begin Phase 1: Configuration
   - Gather all production secrets
   - Create `.env.production` file
   - Generate SSL certificates

### Tomorrow (Oct 2, 2025):
3. 🔄 Complete Phase 1: Configuration
   - Validate all secrets
   - Test local startup with prod config
   - Document any issues

### This Week:
4. 🧪 Begin Phase 2: Staging Deployment
   - Deploy to staging environment
   - Run full test suite
   - Monitor for 24-48 hours

### Next Week:
5. 🚀 Phase 3: Production Deployment
   - Execute production deployment
   - Monitor closely for 48 hours
   - Generate final report

---

## ✅ Sign-Off

**Plan Approved By**: ___________________  
**Date**: ___________________  
**Next Review**: After Phase 1 completion

---

**Document Status**: ✅ **ACTIVE**  
**Last Updated**: October 1, 2025  
**Next Update**: After each phase completion
