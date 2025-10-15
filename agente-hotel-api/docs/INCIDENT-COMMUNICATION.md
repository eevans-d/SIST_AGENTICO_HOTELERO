# Incident Communication Playbook

**Purpose**: Standardize communication during incidents to ensure timely, accurate, and consistent information flow to all stakeholders.

---

## Table of Contents

1. [Communication Principles](#communication-principles)
2. [Stakeholder Matrix](#stakeholder-matrix)
3. [Severity-Based Communication](#severity-based-communication)
4. [Communication Channels](#communication-channels)
5. [Message Templates](#message-templates)
6. [Timeline Requirements](#timeline-requirements)
7. [Status Page Management](#status-page-management)

---

## Communication Principles

### Core Principles
1. **Transparency**: Be honest about what we know and don't know
2. **Timeliness**: Communicate early and often
3. **Consistency**: Use standard templates and channels
4. **Empathy**: Acknowledge impact on users
5. **Blameless**: Focus on resolution, not fault

### Communication Guidelines
- ✅ Communicate within 15 minutes of incident detection
- ✅ Provide updates every 30 minutes (or as status changes)
- ✅ Use clear, non-technical language for external communication
- ✅ Include next update time in every message
- ✅ Confirm resolution and provide follow-up timeline

---

## Stakeholder Matrix

### Internal Stakeholders

| Stakeholder | SEV1 (Critical) | SEV2 (High) | SEV3 (Medium) | SEV4 (Low) |
|-------------|----------------|-------------|---------------|------------|
| **On-Call Team** | Immediately | Immediately | Immediately | Immediately |
| **Engineering Team** | Within 15 min | Within 30 min | Next business day | Weekly summary |
| **Engineering Manager** | Within 15 min | Within 30 min | Within 2 hours | Daily summary |
| **Product Team** | Within 30 min | Within 1 hour | Within 4 hours | As needed |
| **Customer Support** | Within 15 min | Within 30 min | Within 1 hour | Daily summary |
| **Executive Team** | Within 30 min | Within 2 hours | Post-resolution | Monthly report |
| **Legal/Compliance** | If data breach | If data breach | N/A | N/A |

### External Stakeholders

| Stakeholder | SEV1 (Critical) | SEV2 (High) | SEV3 (Medium) | SEV4 (Low) |
|-------------|----------------|-------------|---------------|------------|
| **All Users** | Status page update | Status page update | N/A | N/A |
| **Affected Users** | Email notification | Status page + Email | Email (post-resolution) | N/A |
| **Enterprise Customers** | Phone call + Email | Email | Email | N/A |
| **Partners/Vendors** | As needed | As needed | As needed | N/A |

---

## Severity-Based Communication

### SEV1 (Critical) - Complete Outage

**Definition**: Service completely unavailable, data loss, or security breach

**Communication Requirements**:
- **Initial**: Within 15 minutes
- **Updates**: Every 30 minutes until resolved
- **Channels**: All (Slack, Email, Status Page, Phone for VIPs)
- **Audience**: Everyone
- **Escalation**: Automatic to management

**Response Flow**:
```
Detection (0 min)
  ↓
Acknowledge & Assess (5 min)
  ↓
Internal Alert (#incidents) (10 min)
  ↓
Status Page Update (15 min)
  ↓
Management Notification (15 min)
  ↓
Customer Email (30 min)
  ↓
Regular Updates (every 30 min)
  ↓
Resolution Notice
  ↓
Post-Mortem (within 48 hours)
```

### SEV2 (High) - Degraded Service

**Definition**: Significant performance degradation or partial outage

**Communication Requirements**:
- **Initial**: Within 30 minutes
- **Updates**: Every hour until resolved
- **Channels**: Slack, Status Page, Email to affected users
- **Audience**: Engineering, Management, Affected Users
- **Escalation**: If not resolved within 2 hours

### SEV3 (Medium) - Minor Issue

**Definition**: Minor bugs, isolated failures, not affecting majority of users

**Communication Requirements**:
- **Initial**: Within 1 hour
- **Updates**: When status changes
- **Channels**: Slack internal only
- **Audience**: Engineering team
- **Escalation**: If escalates to SEV2

### SEV4 (Low) - Informational

**Definition**: No user impact, proactive maintenance, minor alerts

**Communication Requirements**:
- **Initial**: Next business day
- **Updates**: Weekly summary
- **Channels**: Slack, internal wiki
- **Audience**: Engineering team
- **Escalation**: N/A

---

## Communication Channels

### Internal Channels

#### Slack
- **#incidents** (Primary)
  - All incident updates
  - Thread per incident
  - Pin critical incidents
  - Use incident ID in thread name

- **#engineering**
  - Cross-post major incidents
  - Technical discussion
  - Link to #incidents thread

- **#customer-support**
  - User-facing updates
  - Support team preparation
  - Customer inquiry guidance

#### Email
- **incident-response@company.com**
  - Auto-forwarded to all stakeholders
  - Thread per incident
  - Include incident ID in subject

#### Status Page (Internal)
- http://status.internal.company.com
- Real-time component status
- Incident timeline
- Subscribe to updates

### External Channels

#### Status Page (Public)
- https://status.agentehotelero.com
- User-visible updates
- Non-technical language
- Updated within 15 min (SEV1), 30 min (SEV2)

#### Email
- Support email address for direct user contact
- Bulk email for widespread impact
- Individual outreach for enterprise customers

#### Social Media
- Only for major outages
- Coordinated with marketing team
- Clear, concise updates

---

## Message Templates

### Initial Alert (Internal - Slack #incidents)

```markdown
🚨 **INCIDENT DETECTED**

**Incident ID**: INC-2024-XXXX
**Severity**: SEV[1/2/3/4] - [CRITICAL/HIGH/MEDIUM/LOW]
**Status**: INVESTIGATING
**Started**: YYYY-MM-DD HH:MM UTC
**Responder**: @engineer

**Impact**:
- Service: [Service name]
- Affected: [Number/percentage of users or "All users"]
- Symptoms: [Brief description of what's failing]

**Initial Assessment**:
- [What we know so far]
- [What we're investigating]

**Next Update**: [Time]

**Dashboard**: [Link to Grafana]
**Runbook**: [Link to relevant runbook]
```

### Status Page Update (External - Initial)

```markdown
**[Service Name] - Investigating**

We are currently investigating an issue affecting [service/feature name]. Users may experience [specific symptoms]. 

We are actively investigating and will provide an update within 30 minutes.

Last updated: [HH:MM UTC]
```

### Status Page Update (External - In Progress)

```markdown
**[Service Name] - Identified**

We have identified the issue affecting [service/feature name]. The issue is [brief non-technical explanation]. 

Our engineering team is working on a fix. Expected resolution: [time or "investigating"].

Impact: [Estimated number/percentage] of users affected.

Next update: [HH:MM UTC]
Last updated: [HH:MM UTC]
```

### Status Page Update (External - Resolved)

```markdown
**[Service Name] - Resolved**

The issue affecting [service/feature name] has been resolved as of [HH:MM UTC]. All services are now operating normally.

Duration: [X hours Y minutes]

We apologize for any inconvenience. A detailed post-mortem will be published within 48 hours at [link].

Last updated: [HH:MM UTC]
```

### Email to Affected Users (Post-Resolution)

```
Subject: [Resolved] Service Disruption - [Date]

Dear [Customer/User],

We want to inform you about a service disruption that occurred on [Date] affecting [service name].

What Happened:
Between [start time] and [end time] UTC, you may have experienced [specific symptoms]. This was due to [brief, non-technical explanation].

Resolution:
Our engineering team identified and resolved the issue at [time] UTC. The service has been fully restored and is operating normally.

Impact:
- Duration: [X hours Y minutes]
- Affected: [Description of impact]
- Data: [No data was lost / Data status]

What We're Doing:
We take these incidents seriously. We are conducting a thorough analysis and implementing improvements to prevent recurrence:
- [Improvement 1]
- [Improvement 2]

We sincerely apologize for any inconvenience this may have caused. If you have any questions or concerns, please contact our support team at support@agentehotelero.com.

Thank you for your patience and understanding.

Best regards,
[Team Name]
Agente Hotelero IA
```

### Update for Management (Email)

```
Subject: Incident Update - SEV[X] - [Service Name]

Hi [Name],

Quick update on the ongoing incident:

Incident ID: INC-2024-XXXX
Severity: SEV[X]
Status: [INVESTIGATING / IDENTIFIED / MONITORING / RESOLVED]
Started: [Time]
Current Duration: [X hours Y minutes]

Impact:
- Users Affected: [Number / Percentage]
- Business Impact: [Revenue / Customer satisfaction / etc.]
- SLA Status: [On track / At risk / Breached]

Current Status:
- Root Cause: [Known / Under investigation]
- Progress: [Brief summary of actions taken]
- ETA: [Expected resolution time or "investigating"]

Next Steps:
- [Action 1]
- [Action 2]

Communication:
- Status Page: [Updated / Will update at X time]
- Customers: [Notified / Will notify if extends beyond X]

I'll send another update in [time] or sooner if status changes significantly.

Thanks,
[Your Name]
```

### Enterprise Customer Call Script

```
"Hello [Customer Name], this is [Your Name] from Agente Hotelero IA.

I'm calling to inform you about a service issue we're currently experiencing that may be affecting your operations.

[Pause for acknowledgment]

Here's what we know:
- Issue: [Brief, clear description]
- Started: [Time, duration so far]
- Impact to you: [Specific impact to their operations]
- Current status: [What we're doing]

We have our top engineers working on this right now, and we expect to have it resolved within [timeframe or "I'll update you within X minutes"].

Do you have any immediate questions or concerns I can help with?

[Answer questions]

I'll personally call you back with an update in [timeframe] or sooner when we have resolution. You can also reach me directly at [phone/email].

Again, we sincerely apologize for the inconvenience and appreciate your patience."
```

---

## Timeline Requirements

### SEV1 (Critical) Timeline

| Milestone | Time Requirement |
|-----------|------------------|
| Detection to Acknowledge | < 5 minutes |
| Detection to Internal Alert | < 10 minutes |
| Detection to Status Page Update | < 15 minutes |
| Detection to Management Notification | < 15 minutes |
| Detection to Customer Email (if prolonged) | < 30 minutes |
| Update Frequency | Every 30 minutes |
| Post-Resolution Communication | Within 2 hours |
| Post-Mortem | Within 48 hours |

### SEV2 (High) Timeline

| Milestone | Time Requirement |
|-----------|------------------|
| Detection to Acknowledge | < 15 minutes |
| Detection to Internal Alert | < 30 minutes |
| Detection to Status Page Update | < 30 minutes |
| Detection to Management Notification | < 30 minutes |
| Update Frequency | Every hour |
| Post-Resolution Communication | Within 4 hours |
| Post-Mortem | Within 1 week |

---

## Status Page Management

### When to Update Status Page

**Always Update For**:
- SEV1 incidents (complete outage)
- SEV2 incidents (degraded service)
- Planned maintenance (24 hours advance notice)

**Never Update For**:
- SEV3/SEV4 incidents (unless becomes SEV2)
- Internal-only issues
- Non-user-facing problems

### Status Page Workflow

```bash
# Create incident
curl -X POST https://api.statuspage.io/v1/pages/PAGE_ID/incidents \
  -H "Authorization: OAuth YOUR_API_KEY" \
  -d '{"incident": {"name": "API Latency Issues", "status": "investigating"}}'

# Update incident
curl -X PATCH https://api.statuspage.io/v1/pages/PAGE_ID/incidents/INCIDENT_ID \
  -H "Authorization: OAuth YOUR_API_KEY" \
  -d '{"incident": {"status": "identified", "body": "We have identified..."}}'

# Resolve incident
curl -X PATCH https://api.statuspage.io/v1/pages/PAGE_ID/incidents/INCIDENT_ID \
  -H "Authorization: OAuth YOUR_API_KEY" \
  -d '{"incident": {"status": "resolved", "body": "Issue has been resolved"}}'
```

### Status Definitions

| Status | Meaning | When to Use |
|--------|---------|-------------|
| **Investigating** | We know something is wrong | Initial alert, assessing impact |
| **Identified** | We know the cause | Root cause found, working on fix |
| **Monitoring** | Fix applied, watching | Mitigation in place, ensuring stability |
| **Resolved** | Issue fixed and verified | Confirmed resolution, normal operation |

---

## Best Practices

### Do's ✅
- Communicate early, even if you don't have all information
- Use "we" not "I" - it's a team effort
- Acknowledge impact to users
- Provide specific next update time
- Keep messages concise and clear
- Use consistent terminology
- Archive all communications for post-mortem

### Don'ts ❌
- Don't speculate on root cause without confirmation
- Don't blame individuals or teams
- Don't use technical jargon in external communications
- Don't promise specific resolution times unless confident
- Don't go silent - update even if no progress
- Don't minimize user impact

---

## Communication Checklist

### During Incident
- [ ] Acknowledge alert in PagerDuty
- [ ] Post initial alert in #incidents Slack
- [ ] Update status page (SEV1/SEV2)
- [ ] Notify management (SEV1 immediately, SEV2 if > 1 hour)
- [ ] Set reminder for next update (30 min SEV1, 1 hour SEV2)
- [ ] Provide regular updates on schedule
- [ ] Update status as it changes
- [ ] Communicate resolution
- [ ] Schedule post-mortem

### Post-Incident
- [ ] Send resolution email to affected users
- [ ] Update status page to resolved
- [ ] Post summary in #incidents
- [ ] Notify management of resolution
- [ ] Complete post-mortem within SLA
- [ ] Publish post-mortem to stakeholders
- [ ] Follow up on action items

---

**Document Owner**: @communications-lead  
**Last Updated**: 2024-10-15  
**Next Review**: 2025-01-15  
**Feedback**: #incidents Slack channel
