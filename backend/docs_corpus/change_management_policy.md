# Change Management Policy

## Change Categories
- Standard Change: Pre-approved, low-risk, repeatable change (e.g., routine
  patching). Does not require individual approval, but must be logged.
- Normal Change: Requires review and approval by the Change Advisory Board
  (CAB) before implementation. Submit requests at least 3 business days in
  advance.
- Emergency Change: Used only to resolve an active incident. Requires
  verbal approval from a manager and must be documented retroactively within
  24 hours.

## Change Windows
Production changes should be scheduled during the weekly maintenance window
(Saturday 22:00–02:00 local time) unless an emergency change is required.

## Rollback Requirements
Every normal change request must include a documented rollback plan. Changes
without a tested rollback plan will not be approved by the CAB.

## Post-Change Review
All Normal and Emergency changes are reviewed in the weekly change review
meeting to confirm success criteria were met and to capture lessons learned.
