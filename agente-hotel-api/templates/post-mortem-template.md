# Post-Mortem Report: [Incident Title]

**Incident ID**: INC-YYYYMMDD-XXXX  
**Date**: YYYY-MM-DD  
**Duration**: [Start Time] - [End Time] (X hours Y minutes)  
**Severity**: [CRITICAL / HIGH / MEDIUM / LOW]  
**Status**: Draft / Under Review / Approved

---

## Executive Summary

> _Brief 2-3 sentence overview of what happened, impact, and resolution_

**What Happened**:  
[One sentence description of the incident]

**Impact**:  
- Users Affected: [Number/Percentage]
- Revenue Impact: $[Amount] (estimated)
- Reputation Impact: [High/Medium/Low]

**Root Cause**:  
[One sentence root cause]

**Resolution**:  
[One sentence how it was resolved]

---

## Incident Details

### Detection
- **How Detected**: [Automated alert / User report / Monitoring / Other]
- **Detection Time**: YYYY-MM-DD HH:MM:SS UTC
- **Alert Source**: [Prometheus / User / Logs / Other]
- **Time to Detection**: [X minutes from start]

### Response
- **First Responder**: [@username]
- **Incident Commander**: [@username]
- **Response Time**: [X minutes from detection]
- **Escalation**: [Yes/No] - [Details if yes]
- **Teams Involved**:
  - Backend Team: [@member1, @member2]
  - DevOps Team: [@member1]
  - External Support: [None / Vendor name]

### Communication
- **Internal Notification**: [Slack / Email / PagerDuty]
- **External Notification**: [Yes/No] - [Status page update / Customer email]
- **Stakeholders Informed**:
  - Engineering: [Time]
  - Management: [Time]
  - Customers: [Time or N/A]

---

## Timeline

> _All times in UTC. Include key events, decisions, and actions taken._

| Time | Event | Actor | Notes |
|------|-------|-------|-------|
| HH:MM | Incident began | System | [What started failing] |
| HH:MM | Alert fired | Prometheus | [Alert name and threshold] |
| HH:MM | Investigation started | @user | [Initial hypothesis] |
| HH:MM | Root cause identified | @user | [What was found] |
| HH:MM | Mitigation applied | @user | [Action taken] |
| HH:MM | Service restored | System | [Verification method] |
| HH:MM | Monitoring period ended | @user | [Confirmed stable] |
| HH:MM | Post-mortem scheduled | @user | [Date/time] |

**Key Milestones**:
- **Time to Detect**: X minutes
- **Time to Investigate**: Y minutes
- **Time to Mitigate**: Z minutes
- **Time to Resolve**: Total W minutes
- **MTTR (Mean Time to Recovery)**: W minutes

---

## Impact Analysis

### User Impact
- **Affected Users**: [Number or percentage]
- **User Experience**: [Complete outage / Degraded performance / Intermittent errors]
- **Geography**: [Specific regions or global]
- **Duration**: [How long users were affected]

### Business Impact
- **Revenue Impact**: $[Amount] (estimated)
  - Lost Transactions: [Number]
  - Average Transaction Value: $[Amount]
  - Calculation: [Show math]
- **SLA Breach**: [Yes/No] - [Details]
- **Customer Complaints**: [Number received]
- **Reputation Impact**: [Assessment]

### Technical Impact
- **Services Affected**:
  - agente-api: [Full outage / Degraded]
  - Database: [Normal / Impacted]
  - PMS Integration: [Normal / Impacted]
  - WhatsApp: [Normal / Impacted]
- **Data Impact**: [None / Delayed / Lost]
- **Monitoring Impact**: [Metrics gaps / Alert flooding]

### Metrics
```
Error Rate: X% (normal: <1%)
Response Time P95: X seconds (normal: <1s)
Availability: XX.X% (SLA: 99.9%)
Request Volume: X requests (X% of normal)
```

---

## Root Cause Analysis

### What Happened
[Detailed technical explanation of what went wrong. Include specific components, configurations, code, or infrastructure that failed.]

### Why It Happened
[Explain the underlying cause. Why did the system behave this way? What conditions led to the failure?]

### Contributing Factors
1. **[Factor 1]**: [Description]
2. **[Factor 2]**: [Description]
3. **[Factor 3]**: [Description]

### What Worked Well
- [Something that helped detect quickly]
- [Something that helped resolve quickly]
- [Good process or tool that was effective]

### What Didn't Work Well
- [Something that delayed detection]
- [Something that complicated response]
- [Gap in monitoring or runbook]

---

## Resolution & Recovery

### Immediate Actions Taken
1. **[Action 1]**: [Time] - [Description]
2. **[Action 2]**: [Time] - [Description]
3. **[Action 3]**: [Time] - [Description]

### Mitigation Steps
```bash
# Commands or configuration changes applied
[Include actual commands used]
```

### Verification
- **Health Checks**: [Endpoints tested]
- **Smoke Tests**: [Tests run]
- **Monitoring**: [Metrics reviewed]
- **Duration**: [How long monitored before close]

### Rollback (if applicable)
- **Rollback Performed**: [Yes/No]
- **Rollback Time**: [X minutes]
- **Version Rolled Back To**: [Version/commit]
- **Rollback Method**: [Automatic / Manual / Blue-green switch]

---

## Action Items

### Immediate (This Week)
- [ ] **[Action]** - Owner: [@user] - Due: [Date] - [Track in Issue #XX]
- [ ] **[Action]** - Owner: [@user] - Due: [Date] - [Track in Issue #XX]

### Short-term (This Month)
- [ ] **[Action]** - Owner: [@user] - Due: [Date] - [Track in Issue #XX]
- [ ] **[Action]** - Owner: [@user] - Due: [Date] - [Track in Issue #XX]

### Long-term (This Quarter)
- [ ] **[Action]** - Owner: [@user] - Due: [Date] - [Track in Issue #XX]
- [ ] **[Action]** - Owner: [@user] - Due: [Date] - [Track in Issue #XX]

### Tracking
- Create GitHub issues for all action items
- Link to project board: [URL]
- Review progress in next team meeting: [Date]

---

## Prevention

### Monitoring Improvements
- **[Improvement 1]**: [Description]
  - New Alert: [Alert name and threshold]
  - Expected Detection Time: [X minutes improvement]
  
- **[Improvement 2]**: [Description]
  - Dashboard: [Link to new dashboard]
  - Metrics: [New metrics added]

### Process Improvements
- **[Improvement 1]**: [Description]
  - Documentation: [Link to updated runbook]
  - Training: [Schedule for team review]
  
- **[Improvement 2]**: [Description]
  - Automation: [Script or tool to create]
  - Testing: [Test scenario to add]

### Technical Improvements
- **[Improvement 1]**: [Description]
  - Code Change: [Link to PR]
  - Configuration: [What to change]
  
- **[Improvement 2]**: [Description]
  - Infrastructure: [Resource to add]
  - Dependency: [Upgrade or replace]

---

## Lessons Learned

### What We Learned
1. **[Lesson 1]**: [Description]
2. **[Lesson 2]**: [Description]
3. **[Lesson 3]**: [Description]

### Process Observations
- **Detection**: [What worked / What needs improvement]
- **Response**: [What worked / What needs improvement]
- **Communication**: [What worked / What needs improvement]
- **Resolution**: [What worked / What needs improvement]

### Similar Incidents
- **[Date]**: [Incident title] - [Similarity]
- **Pattern Detected**: [Yes/No] - [If yes, what pattern]

---

## Appendices

### A. Relevant Logs
```
[Key log entries that helped diagnose or show the issue]
```

### B. Metrics & Graphs
- [Link to Grafana dashboard snapshot]
- [Link to Prometheus query results]
- [Screenshot of key metric during incident]

### C. Related Documentation
- Runbook Used: [Link]
- Configuration Files: [Links]
- Code References: [GitHub links with line numbers]

### D. Communication Logs
- Slack Thread: [Link]
- Email Thread: [Link if applicable]
- Status Page Updates: [Link]

### E. External References
- Vendor Status Page: [Link if applicable]
- Related CVE: [If security incident]
- Community Discussion: [Link if applicable]

---

## Review & Approval

### Post-Mortem Meeting
- **Date**: YYYY-MM-DD HH:MM
- **Attendees**: [@user1, @user2, @user3]
- **Meeting Notes**: [Link to meeting notes]

### Review Feedback
| Reviewer | Feedback | Status |
|----------|----------|--------|
| [@user] | [Comments] | Addressed / Pending |
| [@user] | [Comments] | Addressed / Pending |

### Approval
- **Reviewed By**: [@manager] - Date: [YYYY-MM-DD]
- **Approved By**: [@director] - Date: [YYYY-MM-DD]
- **Published**: [Yes/No] - [Where published]

---

## Follow-up

### Action Item Progress (Update Weekly)
| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| [Action] | [@user] | ⏸️ Not Started | - |
| [Action] | [@user] | ⏳ In Progress | [ETA] |
| [Action] | [@user] | ✅ Complete | [Completion date] |

### Next Review Date
- **Scheduled**: [YYYY-MM-DD]
- **Purpose**: Review action item completion
- **Attendees**: [Team leads]

---

**Document Owner**: [@incident-commander]  
**Created**: YYYY-MM-DD  
**Last Updated**: YYYY-MM-DD  
**Version**: 1.0  
**Status**: Draft / Under Review / Approved / Archived

---

## Template Notes

_Remove this section in actual post-mortem_

**How to Use This Template**:
1. Create post-mortem within 24 hours of incident resolution
2. Schedule post-mortem meeting within 48-72 hours
3. Complete all sections with specific details
4. Be blameless - focus on systems and processes, not individuals
5. Create actionable items with owners and due dates
6. Get approval from management
7. Share with team and stakeholders
8. Track action items to completion
9. Review effectiveness of improvements quarterly

**Blameless Culture**:
- Focus on "what" and "why", not "who"
- Human error is a symptom, not a root cause
- Look for system improvements, not blame
- Encourage open and honest discussion
- Learn and improve together
