# Validation and scenario findings

Raw records: 2,521; exact duplicates removed: 20; quarantined: 62; accepted: 2,439.
Reconciliation difference: 0.

Accepted total insured value (TIV): $2,717,968,000. TIV in historical MMI VI or greater cells: $739,801,000.
These are synthetic asset values exposed to one historical event, not expected losses.

## Exceptions and recommendations

rule
outside_california_study_extent    30
invalid_coordinate                 25
invalid_tiv                        10
invalid_occupancy                  10
missing_property_id                 5
invalid_year                        5
conflicting_property_id             2

Require source-system coordinate and positive-value checks. Resolve conflicting property IDs with the data owner; both conflicting records are quarantined.
Recover missing attributes from authoritative property records. Never impute coordinates or insured value for exposure reporting.
Review high-value concentration cells for accumulation limits. A low scenario intensity does not establish low future hazard.
Rule counts overlap: one rejected record can trigger multiple rules. The accepted portfolio excludes entire records failing any rule.
