# Post-Mortem Template

## Incident Overview

**Incident ID**: INC-[YYYYMMDD]-[###]
**Date**: [Date]
**Duration**: [Start Time] - [End Time] ([Total Duration])
**Severity**: [P0/P1/P2/P3]
**Incident Commander**: [Name]
**Responders**: [List of responders]

## Executive Summary

[Brief, non-technical summary of what happened, impact to users, and resolution]

## Timeline

| Time (UTC) | Event | Action Taken | Responder |
|------------|-------|--------------|-----------|
| [Time] | [Initial detection/alert] | [Action] | [Person] |
| [Time] | [Event] | [Action] | [Person] |
| [Time] | [Resolution] | [Action] | [Person] |

## Impact Assessment

### User Impact
- **Affected Users**: [Number/percentage of users affected]
- **Geographic Impact**: [Regions affected]
- **Feature Impact**: [Which features were unavailable/degraded]
- **Business Impact**: [Revenue, bookings, guest satisfaction impact]

### Technical Impact
- **Services Affected**: [List of services]
- **Data Integrity**: [Any data loss or corruption]
- **SLO Impact**: [Which SLOs were breached]
- **Error Budget**: [Error budget consumed]

## Root Cause Analysis

### What Happened
[Detailed technical explanation of the root cause]

### Why It Happened
[Contributing factors, how the issue wasn't caught earlier]

### How It Was Detected
[Monitoring, alerts, user reports]

## Resolution

### Immediate Fix
[What was done to restore service]

### Verification
[How the fix was verified]

### Recovery Time
- **Time to Detection**: [Duration]
- **Time to Mitigation**: [Duration]
- **Time to Resolution**: [Duration]

## What Went Well

- [List things that worked well during incident response]
- [Good monitoring/alerting that helped]
- [Effective communication/coordination]
- [Quick diagnosis/resolution]

## What Could Be Improved

- [Detection could have been faster because...]
- [Resolution could have been faster because...]
- [Communication could have been better because...]
- [Monitoring gaps identified]

## Action Items

| Action Item | Owner | Due Date | Priority | Status |
|------------|--------|----------|----------|---------|
| [Specific action to prevent recurrence] | [Name] | [Date] | [High/Medium/Low] | [Open/In Progress/Complete] |
| [Monitoring/alerting improvement] | [Name] | [Date] | [High/Medium/Low] | [Open/In Progress/Complete] |
| [Process improvement] | [Name] | [Date] | [High/Medium/Low] | [Open/In Progress/Complete] |
| [Documentation update] | [Name] | [Date] | [High/Medium/Low] | [Open/In Progress/Complete] |

## Lessons Learned

### Technical Lessons
- [What we learned about our systems]
- [What we learned about failure modes]
- [What we learned about monitoring/alerting]

### Process Lessons
- [What we learned about incident response]
- [What we learned about communication]
- [What we learned about escalation]

## Metrics

### Reliability Metrics
- **MTTR**: [Mean Time to Recovery]
- **MTBF**: [Mean Time Between Failures for this type of incident]
- **SLO Compliance**: [Impact on monthly SLO compliance]

### Response Metrics
- **Alert Latency**: [Time from incident start to first alert]
- **Response Time**: [Time from alert to first responder action]
- **Communication Time**: [Time to notify stakeholders]

## Related Incidents

- [Links to similar past incidents]
- [Pattern analysis if applicable]

## Supporting Data

### Dashboards
- [Links to relevant Grafana dashboards during incident]
- [Screenshots of key metrics]

### Logs
- [Key log entries that helped with diagnosis]
- [Log analysis findings]

### Commands Used
```bash
# Commands that were helpful during incident response
make health
docker logs agente-api --since="2024-01-01T10:00:00"
curl -s "http://prometheus:9090/api/v1/query?query=..."
```

## Follow-up

### Post-Incident Review Meeting
- **Date**: [Date of review meeting]
- **Attendees**: [List of attendees]
- **Key Decisions**: [Important decisions made]

### Communication
- **Internal Teams**: [How teams were notified of learnings]
- **External**: [Customer communication if applicable]
- **Blog Post**: [If public post-mortem warranted]

## Appendices

### A. Technical Details
[Detailed technical information, stack traces, configuration details]

### B. Communication Log
[Slack/email threads, status page updates]

### C. Monitoring Data
[Detailed metrics, graphs, raw data]

---

**Document Status**: [Draft/Final]
**Next Review**: [Date]
**Approved By**: [Manager/Tech Lead]
**Distribution**: [Who should receive this document]