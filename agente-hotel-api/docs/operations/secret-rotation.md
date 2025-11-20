# Secret Rotation & Management Policy

**Objetivo**: Prevenir exposición de credenciales y cumplir con políticas de seguridad. Rotación regular de tokens, contraseñas y claves API.

**Cadencia**: Quarterly rotations (1 Oct, 1 Jan, 1 Apr, 1 Jul)  
**Owner**: DevOps / Security Team

---

## 1. Secrets Inventory

### 1.1 Production Secrets

| Secret Name | Type | Source | Rotation | Owner | Alert if Exposed |
|---|---|---|---|---|---|
| `DATABASE_URL` | PostgreSQL Connection | Neon Console | Quarterly + post-incident | DevOps | Critical |
| `REDIS_URL` | Redis Connection | Upstash Console | Quarterly + post-incident | DevOps | Critical |
| `PMS_API_KEY` | QloApps Auth | QloApps Admin | Quarterly | Integration | High |
| `WHATSAPP_TOKEN` | Meta Cloud API | Meta Business Manager | Quarterly | Product | High |
| `GMAIL_SERVICE_KEY` | Google Service Account | Google Cloud Console | Quarterly | Product | High |
| `JWT_SECRET` | JWT Signing Key | Generated locally | Quarterly | Backend | Critical |
| `SLACK_WEBHOOK_ALERTS` | Slack Incoming Webhook | Slack API | Quarterly | DevOps | Medium |
| `SLACK_WEBHOOK_OPS` | Slack Incoming Webhook | Slack API | Quarterly | DevOps | Medium |
| `PAGERDUTY_SERVICE_KEY` | PagerDuty Integration | PagerDuty Console | Quarterly | DevOps | Medium |

### 1.2 Development Secrets (.env.example)

| Secret | Sensitivity | Rotation | Notes |
|---|---|---|---|
| `DATABASE_URL` (dev) | Low | Never (local) | Mock data OK |
| `REDIS_URL` (dev) | Low | Never (local) | In-memory Redis OK |
| `API_KEY_DEV` | Low | Per developer | Dummy values |

### 1.3 GitHub Secrets

**Location**: Settings → Secrets and variables → Actions

**Secrets**:
```
FLY_API_TOKEN          ← Rotated quarterly
DATABASE_URL           ← From Neon (on rotation)
REDIS_URL              ← From Upstash (on rotation)
AWS_ACCESS_KEY_ID      ← If using S3 backups
AWS_SECRET_ACCESS_KEY  ← If using S3 backups
SLACK_WEBHOOK_ALERTS   ← From Slack API
SLACK_WEBHOOK_OPS      ← From Slack API
PAGERDUTY_SERVICE_KEY  ← From PagerDuty
```

---

## 2. Quarterly Rotation Procedure

**Date**: First day of Q (Oct 1, Jan 1, Apr 1, Jul 1)  
**Duration**: 2-3 hours total  
**Downtime**: 0 min (blue-green rotation strategy)

### 2.1 Pre-Rotation Checklist

```bash
# 1. Backup current secrets (encrypted)
# Store in secure location (1Password, Vault, etc.)

# 2. Get list of services using each secret
# Document in rotation log

# 3. Test rotation procedure on staging first
# Deploy staging with new secrets, validate health

# 4. Schedule maintenance window (optional, if not blue-green)
# Notify stakeholders via Slack #ops-incidents
```

### 2.2 DATABASE_URL Rotation (Neon)

**Step 1: Create New Neon Branch with Fresh Credentials**

```bash
# Option A: Create new database user with same DB
# In Neon Console:
# 1. Project: agente-hotel-prod
# 2. Settings → Roles → Create role
# 3. Role name: "api_prod_q1_2026"
# 4. Password: Generate 32-char crypto-secure password

# Option B: Create new branch, test, promote
# (See backup-restore.md for branch workflows)
```

**Step 2: Obtain New Connection String**

```bash
# From Neon Console → Branches → Connection string
# Format: postgresql://user:pass@host:port/db?sslmode=require
NEW_DATABASE_URL="postgresql://api_prod_q1_2026:..."
```

**Step 3: Blue-Green Rotation**

```bash
# 1. Add new secret to GitHub (both secrets coexist for 10 min)
gh secret set DATABASE_URL_NEW --body "$NEW_DATABASE_URL"

# 2. Deploy staging with new secret
# Verify: curl https://agente-hotel-api-staging.fly.dev/health/ready

# 3. Once staging validates, deploy production with new secret
(Comando para actualizar variable de entorno DATABASE_URL)

# 4. Wait for redeployment + health check
sleep 30
curl -f <APP_URL>/health/ready

# 5. Delete old GitHub secret
gh secret delete DATABASE_URL_OLD

# 6. In Neon: Revoke old role (prevents reconnection)
# Neon Console → Branches → Roles → Delete "api_prod_q4_2025"
```

**Step 4: Post-Rotation Validation**

```bash
# 1. Check logs for connection errors
(Comando de logs) | grep -i "connection\|error"

# 2. Verify metrics flowing
curl http://localhost:9090/api/v1/query?query=up | jq '.data.result[] | select(.labels.job=="agente-api")'

# 3. Test critical endpoints
curl -f <APP_URL>/api/guests  # Requires guest data

# 4. Update rotation log
cat >> .github/ROTATION_LOG.md <<EOF
## 2025-10-01 (Q4 2025 → Q1 2026)
- DATABASE_URL: Rotated (neon role api_prod_q4_2025 → api_prod_q1_2026)
- Status: ✅ SUCCESS
- Validation: All health checks passed, 0 errors
- Old role revoked: Yes
EOF
```

### 2.3 REDIS_URL Rotation (Upstash)

**Step 1: Create New Redis Database in Upstash**

```bash
# Via Upstash Console:
# 1. Create new database: "agente-hotel-prod-q1-2026"
# 2. Region: Same as original (gru)
# 3. DB index: 0
# 4. Obtain: Endpoint, Password
```

**Step 2: Blue-Green Migration**

```bash
# Option A: Simple rotation (if data can be cleared)
(Comando para actualizar variable de entorno REDIS_URL)

# Option B: Zero-downtime with replication
# 1. Configure Redis source replication to new instance
# (Depends on Upstash capabilities)
# 2. Verify replication lag < 100ms
# 3. Switch client connection
# 4. Monitor for errors
```

**Step 3: Cleanup**

```bash
# 1. Delete old Upstash database (after 1 week if no rollback)
# Via Upstash Console

# 2. Clear GitHub secret
gh secret delete REDIS_URL_OLD
```

### 2.4 Third-Party API Keys (PMS, WhatsApp, Gmail)

**Procedure** (varies by provider):

**PMS (QloApps)**:
1. QloApps Admin Console → API Keys
2. Generate new key (or rotate existing)
3. Copy new key
4. Update secret: (Comando para actualizar variable de entorno PMS_API_KEY)
5. Test: `curl $PMS_ENDPOINT/api/availability` with new key
6. Revoke old key

**WhatsApp (Meta)**:
1. Meta Business Manager → App → Settings → API Credentials
2. Generate new token (or create new app)
3. Update secret: (Comando para actualizar variable de entorno WHATSAPP_TOKEN)
4. Redeploy app
5. Send test message via WhatsApp to verify connection
6. Revoke old token in Meta Console

**Gmail (Google)**:
1. Google Cloud Console → APIs → Credentials
2. Create new service account key (or regenerate existing)
3. Download JSON key file
4. Encode as base64 or inject as secret
5. Update: (Comando para actualizar variable de entorno GMAIL_SERVICE_KEY)
6. Test: Send test email via Gmail API
7. Delete old key from Google Console

**JWT_SECRET**:
1. Generate new secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Update: (Comando para actualizar variable de entorno JWT_SECRET)
3. Note: All existing JWTs become invalid (users re-login)
4. Monitor for auth errors in logs

---

## 3. Incident-Driven Rotation

**Trigger**: If secret is exposed or suspected exposed

### 3.1 Detection & Containment

```bash
# 1. Immediately disable exposed secret (if possible)
# E.g., revoke token in provider console

# 2. Check if used in logs/commits (gitleaks might have missed)
git log --all -p | grep "SECRET_VALUE"

# 3. If found in commits, force-push history (if allowed)
git filter-branch -f --env-filter '
  if [ "$GIT_COMMIT" = "<commit_hash>" ]; then
    export GIT_AUTHOR_NAME="..." GIT_AUTHOR_EMAIL="..."
  fi
' -- --all
```

### 3.2 Immediate Rotation

```bash
# 1. Generate new secret (do not commit to git!)
NEW_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# 2. Update in platform only (via CLI, not GitHub)
(Comando para actualizar variable de entorno EXPOSED_SECRET)

# 3. Verify deployment + health
sleep 30 && curl -f <APP_URL>/health/ready

# 4. Document incident
cat >> SECURITY_LOG.md <<EOF
## 2025-10-25 - DATABASE_URL Exposure Incident
- **Detection Time**: 14:30 UTC
- **Detection Method**: gitleaks pre-commit hook
- **Secret**: DATABASE_URL
- **Rotation Time**: 14:32 UTC (2 min)
- **Root Cause**: Accidentally committed to git (pre-commit hook disabled)
- **Impact**: Minimal (secret in private repo only, no external access)
- **Actions Taken**:
  1. Disabled old secret in Neon
  2. Generated new DATABASE_URL
  3. Deployed new secret
  4. Force-pushed git history
  5. Re-enabled pre-commit hooks
- **Follow-Up**: Team training on git secrets
EOF
```

---

## 4. Automation: Scheduled Rotation Reminders

### 4.1 GitHub Issue Template (Quarterly)

**File**: `.github/ISSUE_TEMPLATE/secret-rotation.md`

```markdown
---
name: Quarterly Secret Rotation
about: Reminder to rotate production secrets
title: "Quarterly Secret Rotation - Q[X] 20XX"
assignees: ["devops-team"]
labels: ["ops", "security", "quarterly"]
---

# Q[X] Secret Rotation Checklist

**Date**: [QUARTER_START_DATE]  
**Due**: [QUARTER_START_DATE + 3 days]  
**Duration**: ~2-3 hours

## Secrets to Rotate
- [ ] DATABASE_URL (Neon)
- [ ] REDIS_URL (Upstash)
- [ ] FLY_API_TOKEN
- [ ] PMS_API_KEY (QloApps)
- [ ] WHATSAPP_TOKEN (Meta)
- [ ] GMAIL_SERVICE_KEY (Google)
- [ ] JWT_SECRET (if needed)
- [ ] Slack Webhooks (if regenerated)
- [ ] PagerDuty Service Key (if needed)

## Procedure
1. See: [docs/operations/secret-rotation.md](../docs/operations/secret-rotation.md)
2. Test rotation on staging first
3. Blue-green deployment to production
4. Validate health checks
5. Update ROTATION_LOG.md
6. Close issue

## References
- Runbook: docs/operations/secret-rotation.md
- Last Rotation: [LINK_TO_PREVIOUS_ISSUE]
- Staging Status: [LINK_TO_LATEST_DEPLOY]
```

### 4.2 Automated Reminder Workflow

**File**: `.github/workflows/secret-rotation-reminder.yml`

```yaml
name: Quarterly Secret Rotation Reminder

on:
  schedule:
    # Every quarter at 09:00 UTC on the 1st day
    - cron: '0 9 1 1 *'  # January 1
    - cron: '0 9 1 4 *'  # April 1
    - cron: '0 9 1 7 *'  # July 1
    - cron: '0 9 1 10 *' # October 1

jobs:
  create-rotation-issue:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Determine Quarter
        run: |
          MONTH=$(date +%m)
          YEAR=$(date +%Y)
          if [ "$MONTH" -le 3 ]; then QUARTER=1; fi
          if [ "$MONTH" -le 6 ] && [ "$MONTH" -gt 3 ]; then QUARTER=2; fi
          if [ "$MONTH" -le 9 ] && [ "$MONTH" -gt 6 ]; then QUARTER=3; fi
          if [ "$MONTH" -gt 9 ]; then QUARTER=4; fi
          echo "QUARTER=$QUARTER" >> $GITHUB_ENV
          echo "YEAR=$YEAR" >> $GITHUB_ENV

      - name: Create GitHub Issue
        uses: actions/github-script@v7
        with:
          script: |
            const quarter = process.env.QUARTER;
            const year = process.env.YEAR;
            
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `Quarterly Secret Rotation - Q${quarter} ${year}`,
              body: `# Quarterly Secret Rotation - Q${quarter} ${year}\n\n**Due**: ${new Date(new Date().setDate(new Date().getDate() + 3)).toISOString().split('T')[0]}\n\nSee checklist and runbook in issue.`,
              labels: ['ops', 'security', 'quarterly'],
              assignees: ['devops-team']
            });

      - name: Notify Slack
        run: |
          curl -X POST "${{ secrets.SLACK_WEBHOOK_OPS }}" \
            -H 'Content-Type: application/json' \
            -d '{
              "text": "🔐 Q${{ env.QUARTER }} ${{ env.YEAR }} Secret Rotation Reminder",
              "attachments": [{
                "color": "warning",
                "text": "Time to rotate production secrets. See GitHub issue for checklist."
              }]
            }'
```

---

## 5. Compliance & Auditing

### 5.1 Rotation Log

**File**: `.github/ROTATION_LOG.md`

```markdown
# Secret Rotation Audit Log

## 2025-10-01 (Q4 2025)
- DATABASE_URL: ✅ Rotated (neon role q3_2025 → q4_2025)
- REDIS_URL: ✅ Rotated (upstash db-q3 → db-q4)
- FLY_API_TOKEN: ✅ Rotated
- PMS_API_KEY: ✅ Rotated
- WHATSAPP_TOKEN: ✅ Rotated
- GMAIL_SERVICE_KEY: ⏭️ Skipped (new key just added Q3)
- JWT_SECRET: ⏭️ Skipped (not rotated unless compromise)
- **Status**: ✅ All rotations complete
- **Duration**: 2h 15min
- **Issues**: None
- **Reviewed By**: @devops-lead

## 2025-07-01 (Q3 2025)
...
```

### 5.2 Compliance Report (Annual)

**Frequency**: End of calendar year

```markdown
# Annual Secret Management Report 2025

## Rotation Compliance
| Quarter | Target | Actual | Status |
|---|---|---|---|
| Q1 | 80% | 100% | ✅ |
| Q2 | 80% | 75% | ⚠️ Delayed 2 weeks |
| Q3 | 80% | 100% | ✅ |
| Q4 | 80% | 100% | ✅ |

## Incidents
- 1 exposure incident (Q3): DATABASE_URL in git commit
  - **Response Time**: 2 minutes
  - **Rotation Time**: 5 minutes
  - **Impact**: Low (private repo)

## Tooling
- Pre-commit hooks (gitleaks): ✅ Active
- GitHub secret audit: ✅ Monthly review
- Rotation automation: ✅ 4/4 reminders triggered

## Recommendations for 2026
1. Implement hardware security key for Fly.io auth
2. Add secret versioning (keep 2 versions active for rollback)
3. Automate rotation for API keys (where provider supports)
```

---

## 6. Tools & Best Practices

### 6.1 Local Development (Never Commit Secrets!)

```bash
# 1. Use .env.local (not tracked in git)
echo ".env.local" >> .gitignore

# 2. Load from file (not set directly)
export $(cat .env.local | xargs)

# 3. Or use direnv (auto-loads .env when entering directory)
# Install: brew install direnv
echo "export $(cat .env.local | xargs)" > .envrc
direnv allow
```

### 6.2 Pre-Commit Hook (Prevent Accidental Commits)

**File**: `.git/hooks/pre-commit`

```bash
#!/bin/bash
# Prevent committing secrets

if git diff --cached | grep -qE "password|secret|token|api.?key|DATABASE_URL|REDIS_URL"; then
    echo "❌ ERROR: Secret pattern detected in staged changes"
    echo "Use 'git add -p' to review changes before committing"
    exit 1
fi
```

### 6.3 Vault Integration (Advanced)

**For teams needing centralized secret management:**

```bash
# Install Vault
brew install vault

# Start development server
vault server -dev

# Store secret
vault kv put secret/agente-hotel DATABASE_URL="postgresql://..."

# Retrieve secret
VAULT_ADDR=http://127.0.0.1:8200 vault kv get secret/agente-hotel

# Auto-rotate (plugin dependent)
# vault write database/rotate-root/agente-hotel-db rotate=true
```

---

## 7. Rotation Checklist

### 7.1 Pre-Rotation (24h before)

- [ ] Schedule maintenance window (if needed)
- [ ] Notify teams via Slack
- [ ] Test rotation procedure on staging
- [ ] Prepare new secrets (generate, not reuse old format)
- [ ] Backup current secrets (encrypted storage)
- [ ] Ensure monitoring/logging active (to catch errors)

### 7.2 During Rotation

- [ ] Deploy new secret to Fly.io
- [ ] Verify health check passes within 2 min
- [ ] Check logs for connection errors
- [ ] Validate metrics flowing to Prometheus
- [ ] Test critical endpoints

### 7.3 Post-Rotation

- [ ] Update ROTATION_LOG.md
- [ ] Revoke old credentials in provider console
- [ ] Remove temporary GitHub secrets (if used for blue-green)
- [ ] Document any issues encountered
- [ ] Close rotation GitHub issue

---

## 8. Emergency Procedures

### 8.1 Complete Secret Compromise (All Secrets Exposed)

**Timeline**: 0-30 min

1. **Isolate (0-5 min)**:
   - Revoke all Fly.io machines (pause service)
   - Notify #ops-incidents on Slack

2. **Regenerate (5-15 min)**:
   - Generate new complete set of secrets
   - Store temporarily in secure vault (1Password, etc.)

3. **Redeploy (15-25 min)**:
   - Update all secrets in Fly.io
   - Redeploy app

4. **Validate (25-30 min)**:
   - Health check passes
   - Critical endpoints respond

### 8.2 Partial Compromise (One Secret Exposed)

**Timeline**: 0-10 min (see Section 3.2 above)

---

## References

- OWASP Secret Management: https://cheatsheetseries.owasp.org/
- HashiCorp Vault: https://www.vaultproject.io/
- Git Secrets: https://github.com/awslabs/git-secrets
- Gitleaks: https://github.com/gitleaks/gitleaks

---

**Last Updated**: 2025-10-25  
**Maintained By**: Security & DevOps  
**Review Frequency**: Quarterly
