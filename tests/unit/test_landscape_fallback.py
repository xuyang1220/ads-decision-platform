from ads_platform.landscape.fallback import candidate_fallback_keys
from ads_platform.schemas.landscape import LandscapeContext


def test_candidate_fallback_order_prefers_specific_to_global():
    context = LandscapeContext(campaign_id="camp", adgroup_id="ag", segment_id=7, channel="feed")
    levels = candidate_fallback_keys(context)
    assert levels[0] == ("adgroup_segment", "adgroup:ag|segment:7")
    assert levels[-1] == ("global", "global")
