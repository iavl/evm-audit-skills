# Recon and Routing

Run Recon against the complete audit root. Its Feature Map v4 records the
scope digest, compilation-input digest, and compilation coverage. Selector rejects a missing, incomplete,
or mismatched scope before filtering. Routing v6 applies environment, Domain,
then canonical feature gates. PRESENT Domains are selected, UNKNOWN Domains are
Deferred with tiny screening cards, and only confirmed absence is filtered.
Screen cards can promote candidates to Deep Review but never filter uncertainty.
The manifest is immutable; `render_runtime.py` never re-runs routing. Domain
resolution and `screen-results.json` are separately evidenced artifacts.
