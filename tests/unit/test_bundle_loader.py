from ads_platform.ctr.bundle import CTRBundleLoader
from ads_platform.schemas.request import AdCandidate, RequestContext


def test_bundle_loader_predicts_probability() -> None:
    bundle = CTRBundleLoader.load("artifacts/demo_bundle")
    result = bundle.predictor.predict(
        RequestContext(
            request_id="req",
            timestamp_ms=1,
            user_id="u",
            device_type="mobile",
            country="US",
            placement="feed",
            app_or_site="app",
        ),
        AdCandidate(
            ad_id="ad_1",
            campaign_id="cmp_1",
            adgroup_id="ag_1",
            base_bid=1.0,
            features={"historical_ctr": 0.02},
        ),
    )
    assert 0.0 <= result.pctr_raw <= 1.0
    assert 0.0 <= result.pctr_calibrated <= 1.0
    assert result.model_version == "deepfm_demo_v1"
