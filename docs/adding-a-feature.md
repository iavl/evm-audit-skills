# Adding a Feature

Add the feature to `data/features.json` with a description, an explicit
`absence_policy`, and allowed absence evidence kinds. Add a presence detector to
`scripts/recon.py` only when it can produce concrete source evidence. Presence
heuristics must never prove absence.
