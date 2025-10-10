# 🚀 Deployment Documentation

**Sistema Agente Hotelero IA - Deployment & Infrastructure**  
**Actualizado**: 10 de Octubre, 2025  
**Audiencia**: DevOps, Platform Engineers, Release Managers

---

## 📋 Quick Navigation

| Document | Purpose | Audience | Priority |
|----------|---------|----------|----------|
| **[Deployment Guide](deployment-guide.md)** | Complete deployment procedures | DevOps/Platform | 🔥 Critical |
| **[QloApps Configuration](qloapps-configuration.md)** | PMS integration setup | DevOps/Integrations | 🔥 Critical |
| **[QloApps Integration](qloapps-integration.md)** | PMS integration details | Backend/DevOps | ⚡ High |
| **[Deployment Readiness Checklist](deployment-readiness-checklist.md)** | Pre-deployment validation | Release Manager | ⚡ High |

---

## 🎯 Deployment Overview

### Deployment Environments
```
🔄 CI/CD Pipeline Flow
├── 🧪 Development (Local Docker)
├── 🔍 Testing (Staging Environment)
├── 🚦 Pre-Production (UAT Environment)
└── 🏭 Production (Multi-AZ Deployment)
```

### Infrastructure Components
- **Application**: FastAPI on Docker containers
- **Database**: PostgreSQL with streaming replication
- **Cache**: Redis Cluster for high availability
- **PMS Integration**: QloApps with MySQL backend
- **Monitoring**: Prometheus + Grafana + AlertManager
- **Load Balancer**: NGINX with SSL termination
- **Secrets**: HashiCorp Vault or AWS Secrets Manager

---

## 🚨 Critical Deployment Documents

### 📖 Deployment Guide
**File**: [deployment-guide.md](deployment-guide.md)  
**Purpose**: Complete deployment procedures and infrastructure setup  
**Contents**:
- Environment setup procedures
- Docker deployment configurations
- Database migration procedures
- Security configuration
- Monitoring setup
- Rollback procedures

**When to Use**: New deployments, environment setup, release deployments

---

### 🏨 QloApps Configuration
**File**: [qloapps-configuration.md](qloapps-configuration.md)  
**Purpose**: PMS system configuration and setup  
**Contents**:
- QloApps installation procedures
- Database configuration
- API endpoint configuration
- Authentication setup
- Integration testing procedures

**When to Use**: PMS setup, configuration changes, integration issues

---

### 🔗 QloApps Integration
**File**: [qloapps-integration.md](qloapps-integration.md)  
**Purpose**: Detailed PMS integration implementation  
**Contents**:
- API integration patterns
- Data synchronization procedures
- Error handling strategies
- Performance optimization
- Testing and validation

**When to Use**: Integration development, troubleshooting, API changes

---

### ✅ Deployment Readiness Checklist
**File**: [deployment-readiness-checklist.md](deployment-readiness-checklist.md)  
**Purpose**: Pre-deployment validation and sign-off  
**Contents**:
- Technical readiness validation
- Security requirements verification
- Performance benchmarks
- Monitoring setup verification
- Business acceptance criteria

**When to Use**: Before every production deployment, release sign-off

---

## 🏗️ Deployment Architecture

### Production Deployment (High Availability)
```
📊 Load Balancer (NGINX)
├── 🔄 App Instance 1 (agente-api)
├── 🔄 App Instance 2 (agente-api) 
└── 🔄 App Instance 3 (agente-api)

💾 Database Layer
├── 📊 PostgreSQL Primary
└── 📊 PostgreSQL Replica (Read-only)

⚡ Cache Layer
├── 🔴 Redis Master
└── 🔴 Redis Slave

🏨 PMS Integration
├── 📋 QloApps API
└── 💾 MySQL Database

📈 Monitoring Stack
├── 📊 Prometheus
├── 📈 Grafana
└── 🚨 AlertManager
```

### Development Deployment (Docker Compose)
```
🐳 Docker Compose Stack
├── agente-api (FastAPI application)
├── postgres (Database)
├── redis (Cache)
├── qloapps (PMS - Optional)
├── mysql (QloApps DB - Optional)
├── prometheus (Metrics)
├── grafana (Dashboards)
└── alertmanager (Alerts)
```

---

## 🚀 Deployment Types

### 🔵 Blue-Green Deployment (Production)
**Use Case**: Zero-downtime production deployments  
**Process**:
1. Deploy to inactive environment (Blue/Green)
2. Run validation tests
3. Switch traffic to new environment
4. Monitor for issues
5. Keep previous environment as rollback option

**Documentation**: [deployment-guide.md](deployment-guide.md) → Blue-Green Section

---

### 🟢 Rolling Deployment (Staging)
**Use Case**: Gradual rollout with continuous availability  
**Process**:
1. Update instances one at a time
2. Health check each instance before proceeding
3. Monitor metrics during rollout
4. Automatic rollback on failure

**Documentation**: [deployment-guide.md](deployment-guide.md) → Rolling Section

---

### 🟡 Canary Deployment (Beta Features)
**Use Case**: New feature validation with limited exposure  
**Process**:
1. Deploy to subset of users (5-10%)
2. Monitor business and technical metrics
3. Gradually increase traffic percentage
4. Full rollout or rollback based on results

**Documentation**: [deployment-guide.md](deployment-guide.md) → Canary Section

---

### 🔴 Emergency Deployment (Hotfixes)
**Use Case**: Critical security patches or urgent bug fixes  
**Process**:
1. Fast-track testing with reduced validation
2. Direct deployment to production
3. Enhanced monitoring during deployment
4. Post-deployment validation and communication

**Documentation**: [deployment-guide.md](deployment-guide.md) → Emergency Section

---

## 🔧 Environment Configuration

### Environment Variables by Environment

#### Development
```bash
ENVIRONMENT=development
DEBUG=true
PMS_TYPE=mock
POSTGRES_URL=postgresql://localhost:5432/agente_dev
REDIS_URL=redis://localhost:6379
LOG_LEVEL=DEBUG
```

#### Staging
```bash
ENVIRONMENT=staging
DEBUG=false
PMS_TYPE=qloapps
POSTGRES_URL=postgresql://staging-db:5432/agente_staging
REDIS_URL=redis://staging-redis:6379
LOG_LEVEL=INFO
```

#### Production
```bash
ENVIRONMENT=production
DEBUG=false
PMS_TYPE=qloapps
POSTGRES_URL=postgresql://prod-db:5432/agente_prod
REDIS_URL=redis://prod-redis:6379
LOG_LEVEL=WARNING
```

### Secret Management
- **Development**: `.env` files (excluded from git)
- **Staging/Production**: HashiCorp Vault or cloud secret managers
- **CI/CD**: Encrypted environment variables
- **Container Secrets**: Docker secrets or Kubernetes secrets

---

## 📊 Deployment Validation

### Pre-Deployment Checklist
- [ ] **Code Review**: All changes peer-reviewed and approved
- [ ] **Tests**: All automated tests passing (unit, integration, E2E)
- [ ] **Security**: Security scanning completed (no HIGH/CRITICAL issues)
- [ ] **Performance**: Load testing completed (meets SLA requirements)
- [ ] **Documentation**: Deployment documentation updated
- [ ] **Rollback Plan**: Rollback procedure documented and tested

### Post-Deployment Validation
- [ ] **Health Checks**: All health endpoints returning 200 OK
- [ ] **Core Functionality**: Critical user flows validated
- [ ] **PMS Integration**: QloApps API connectivity verified
- [ ] **Database**: Connection and query performance validated
- [ ] **Monitoring**: All metrics and alerts functioning
- [ ] **Performance**: Response times within SLA thresholds

### Smoke Tests (Automated)
```bash
# Core API Health
curl http://api.hotel.com/health/ready

# WhatsApp Webhook
curl -X POST http://api.hotel.com/webhooks/whatsapp -d '{test payload}'

# PMS Integration
curl http://api.hotel.com/api/pms/health

# Database Connectivity
curl http://api.hotel.com/health/database

# Redis Connectivity
curl http://api.hotel.com/health/cache
```

---

## 🔄 Release Management

### Release Cadence
- **Major Releases**: Monthly (new features)
- **Minor Releases**: Bi-weekly (enhancements, bug fixes)
- **Patch Releases**: As needed (critical fixes)
- **Hotfixes**: Emergency (security, critical bugs)

### Release Process
1. **Planning**: Feature planning and estimation
2. **Development**: Feature development with testing
3. **Staging**: Deployment to staging environment
4. **UAT**: User acceptance testing
5. **Production**: Production deployment
6. **Validation**: Post-deployment validation
7. **Communication**: Release notes and communication

### Release Documentation
- **Release Notes**: Feature descriptions and breaking changes
- **Deployment Guide**: Specific deployment instructions
- **Rollback Plan**: Steps to revert if issues occur
- **Communication Plan**: Stakeholder communication strategy

---

## 🚨 Emergency Procedures

### Critical Issue Response
1. **Immediate**: Stop deployment if in progress
2. **Assess**: Determine impact and severity
3. **Rollback**: Execute rollback if necessary
4. **Communicate**: Notify stakeholders and users
5. **Investigate**: Root cause analysis
6. **Fix**: Develop and test fix
7. **Deploy**: Emergency deployment of fix
8. **Post-Mortem**: Document lessons learned

### Rollback Procedures
- **Blue-Green**: Switch traffic back to previous environment
- **Rolling**: Rollback instances to previous version
- **Database**: Database migration rollback (if applicable)
- **Cache**: Clear cache to prevent stale data issues
- **Monitoring**: Verify metrics return to normal

---

## 🔧 Tools & Infrastructure

### CI/CD Tools
- **Source Control**: Git (GitHub/GitLab)
- **CI/CD Pipeline**: GitHub Actions / GitLab CI / Jenkins
- **Container Registry**: Docker Hub / AWS ECR / GitLab Registry
- **Deployment**: Docker Compose / Kubernetes / AWS ECS

### Infrastructure Tools
- **Orchestration**: Docker Compose (dev) / Kubernetes (prod)
- **Load Balancing**: NGINX / AWS ALB / Google Cloud Load Balancer
- **Database**: PostgreSQL (managed service recommended)
- **Cache**: Redis (managed service recommended)
- **Monitoring**: Prometheus + Grafana + AlertManager

### Development Tools
- **Local Development**: Docker Compose
- **API Testing**: Postman / Insomnia
- **Load Testing**: Artillery / Apache Bench / K6
- **Security Scanning**: Trivy / Snyk / OWASP ZAP

---

## 📞 Deployment Support

### Deployment Team Contacts
- **Release Manager**: release-manager@hotel.com
- **Platform Engineering**: platform-team@hotel.com
- **On-Call Engineer**: +1-555-DEPLOY (24/7)
- **Emergency Escalation**: cto@hotel.com

### Support Channels
- **Slack**: #deployment-support
- **Email**: deployment-team@hotel.com
- **Incident**: PagerDuty → Deployment Team

### Vendor Support
- **Cloud Provider**: AWS/GCP/Azure Enterprise Support
- **Database**: PostgreSQL Professional Support
- **Monitoring**: Grafana Enterprise Support
- **PMS**: QloApps Technical Support

---

## 📝 Documentation Maintenance

- **Owner**: Platform Engineering Team
- **Review Frequency**: After each deployment
- **Update Triggers**: Infrastructure changes, process improvements
- **Approval Process**: Team lead review + senior engineer sign-off

---

**📍 Navigation**: [← Back to Main Docs](../../README.md) | [Features →](../features/) | [Operations →](../operations/) | [Archive →](../archive/)

---

**🚨 Emergency Deployment?** → [deployment-guide.md](deployment-guide.md) → Emergency Procedures Section