# Stage 6B.9 Dictionary Admission Policy

Only evidence-ledger records with `review_status=approved` may create dictionary rows. The source must be valid and verified, the location must be usable, the evidence strength must be `strong` or `very_strong`, and the statement must directly support the token without unresolved contradiction.

One canonical uppercase dictionary row is created per approved token. `normalized_token` follows the existing uppercase normalization convention. The primary association is copied conservatively; alternatives are populated only when the approved evidence framework supports them. Shared, borrowed, and adapted names are never forced into exclusive associations.

Dictionary metadata is copied from the approved evidence and source registry: evidence type, position scope, source type, source ID, verified URL, location-derived evidence note, reviewer, and date. `category=supporting` is used for these approved documented associations because the approved records document naming-system or contextual associations rather than universal identity claims.

`evidence_score` is an internal reference-evidence strength score, not a probability: `very_strong=4`, `strong=3`, `moderate=2`, `weak=1`, `ambiguous=0`, and `non_informative=0`.

The dictionary describes **likely community/linguistic association based on name patterns**. It does not establish an individual's actual ethnicity. Dataset frequency, co-occurrence, name position, prefixes, and the duplicate `sname.txt` source are not documentary evidence.
