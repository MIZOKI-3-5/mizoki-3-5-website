"""Weekly owner digest — counts per stage only, behind ``PIPELINE_DIGEST`` (OFF).

The Phase D digest renderer is TypeScript
(``miz-oki-command-center-ui/components/console/posture/weekly-digest.tsx``,
RUN PACK v4.0 Phase D.3), so it cannot be imported here; this module
reproduces its SECTION SHAPE instead of forking it: a design-target header
line, titled sections, one sentence per row, every sentence marked
``[measured]`` or ``[not-wired]``. No sentence carries a number that did not
come from the store, and no sentence carries a name, an e-mail, or a host.

Sending (mail/Slack) is NOT built here — ``weekly_digest`` returns text or
``None``; a caller that ships it is a later, separately gated change.
"""
from __future__ import annotations

import os
from typing import Mapping

from .flags import digest_enabled
from .stages import FORWARD_CHAIN, Stage
from .store import PartnerStore, counts_by_stage

DIGEST_HEADER = (
    "design target until a named design-partner readout exists — every line below "
    "is a live read of the pipeline store or says not-wired"
)


def render_weekly_digest(store: PartnerStore, as_of: str) -> str:
    """Pure renderer (no flag check) — counts per stage, milestones, gaps."""
    records = store.list_all()
    counts = counts_by_stage(records)
    lines = ["Weekly design-partner pipeline digest", DIGEST_HEADER, f"as of {as_of} [measured]", ""]
    lines.append("## Pipeline")
    for stage in FORWARD_CHAIN:
        lines.append(f"- {stage.value}: {counts[stage.value]} partner(s) [measured]")
    lines.append(f"- {Stage.PAUSED.value}: {counts[Stage.PAUSED.value]} partner(s) [measured]")
    lines.append(f"- {Stage.LOST.value}: {counts[Stage.LOST.value]} partner(s) [measured]")
    lines.append(f"- total records: {len(records)} [measured]")
    lines.append("")
    lines.append("## Milestones")
    emitted = store.milestones()
    if emitted:
        for key in emitted:
            lines.append(f"- {key}: emitted [measured]")
    else:
        lines.append("- none emitted yet [measured]")
    lines.append("")
    lines.append("## Data")
    lines.append("- agent_originated_share: not-wired — stays null until Strategy S2 data exists [not-wired]")
    lines.append("- outreach consent: recorded per partner; this digest reads counts only, never a contact [measured]")
    return "\n".join(lines) + "\n"


def weekly_digest(store: PartnerStore, as_of: str, env: Mapping[str, str] | None = None) -> str | None:
    """``None`` while ``PIPELINE_DIGEST`` is off — nothing rendered, nothing sent."""
    env = os.environ if env is None else env
    if not digest_enabled(env):
        return None
    return render_weekly_digest(store, as_of)
