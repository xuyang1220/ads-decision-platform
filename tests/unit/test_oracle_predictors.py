from ads_platform.ctr.calibrator import IdentityCalibrator
from ads_platform.ctr.predictor import NoisyOracleCTRPredictor, OracleCTRPredictor
from ads_platform.schemas.request import AdCandidate, RequestContext


def _request() -> RequestContext:
    return RequestContext(
        request_id="req_1",
        timestamp_ms=1,
        user_id=None,
        device_type="mobile",
        country="US",
        placement="feed",
        app_or_site="demo",
    )


def test_oracle_predictor_reads_candidate_extra() -> None:
    predictor = OracleCTRPredictor(calibrator=IdentityCalibrator())
    candidate = AdCandidate(
        ad_id="ad_1",
        campaign_id="camp_1",
        adgroup_id="ag_1",
        advertiser_id=None,
        base_bid=1.0,
        features={},
        extra={"oracle_pctr": 0.12},
    )
    pred = predictor.predict(_request(), candidate)
    assert abs(pred.pctr_raw - 0.12) < 1e-9
    assert abs(pred.pctr_calibrated - 0.12) < 1e-9


def test_noisy_oracle_predictor_is_deterministic() -> None:
    predictor = NoisyOracleCTRPredictor(calibrator=IdentityCalibrator(), noise_sigma=0.4)
    candidate = AdCandidate(
        ad_id="ad_1",
        campaign_id="camp_1",
        adgroup_id="ag_1",
        advertiser_id=None,
        base_bid=1.0,
        features={},
        extra={"oracle_pctr": 0.12},
    )
    pred1 = predictor.predict(_request(), candidate)
    pred2 = predictor.predict(_request(), candidate)
    assert abs(pred1.pctr_raw - pred2.pctr_raw) < 1e-12
    assert 0.0 < pred1.pctr_raw < 1.0
