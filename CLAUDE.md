# Website mirror

Mode: downstream-only; deployment: disabled

The source of truth is `MIZOKI-3-5/MIZOKICloudRun`. All website development,
tests, Actions and production deployments belong there. Submit changes there;
this repository receives a one-way copy of explicitly approved website files.
Do not deploy from this repository or sync its changes back into CloudRun.

`MIRROR_SOURCE.json` identifies the authoritative source commit and file hashes.
A source snapshot is not a claim that those bytes are deployed. Files absent
from that manifest are historical material, not authoritative website sources.
Internal documents, secrets and source workflows are excluded from the mirror.

The mirror is public. Do not add private operational data or credentials.

Agent instructions: work in MIZOKICloudRun. Do not create deploy automation here.
