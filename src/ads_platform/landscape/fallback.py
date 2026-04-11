from __future__ import annotations

from ads_platform.schemas.landscape import LandscapeContext


def candidate_fallback_keys(context: LandscapeContext) -> list[tuple[str, str]]:
    """Return ordered fallback keys as (level, key) pairs."""
    pairs: list[tuple[str, str]] = []
    if context.adgroup_id and context.segment_id is not None:
        pairs.append(("adgroup_segment", f"adgroup:{context.adgroup_id}|segment:{context.segment_id}"))
    if context.campaign_id and context.segment_id is not None:
        pairs.append(("campaign_segment", f"campaign:{context.campaign_id}|segment:{context.segment_id}"))
    if context.channel and context.segment_id is not None:
        pairs.append(("channel_segment", f"channel:{context.channel}|segment:{context.segment_id}"))
    if context.adgroup_id:
        pairs.append(("adgroup_global", f"adgroup:{context.adgroup_id}|global"))
    if context.campaign_id:
        pairs.append(("campaign_global", f"campaign:{context.campaign_id}|global"))
    if context.channel:
        pairs.append(("channel_global", f"channel:{context.channel}|global"))
    pairs.append(("global", "global"))
    return pairs
