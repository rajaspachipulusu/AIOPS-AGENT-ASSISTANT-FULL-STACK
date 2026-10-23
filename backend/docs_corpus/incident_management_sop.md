# Incident Management Standard Operating Procedure (SOP)

## Severity Definitions
- P1 (Critical): Complete service outage or severe business impact. Requires
  immediate response and an incident commander. Target resolution: 4 hours.
- P2 (High): Major functionality degraded, affecting many users. Target
  resolution: 1 business day.
- P3 (Medium): Minor functionality issue with a workaround available. Target
  resolution: 3 business days.
- P4 (Low): Cosmetic or very low impact issue. Target resolution: best effort.

## P1 Incident Response Steps
1. On detection, the on-call engineer immediately opens a P1 ticket and pages
   the relevant team (Linux, Windows, Network, Database, or Cloud Team based
   on the affected system).
2. An Incident Commander is assigned within 15 minutes.
3. A dedicated incident channel is created and stakeholders are notified.
4. Status updates are posted every 30 minutes until resolution.
5. Once resolved, a post-incident review (PIR) is scheduled within 3 business
   days.

## Escalation
If a P1 incident is not acknowledged within 15 minutes, it escalates
automatically to the team lead, then to the engineering manager after another
15 minutes.

## Communication
All incident communication must go through the designated incident channel.
Do not communicate incident status over direct messages only, to preserve an
auditable record.
