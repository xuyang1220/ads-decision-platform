from __future__ import annotations

from ads_platform.landscape.artifact import EmpiricalLandscapeArtifact
from ads_platform.landscape.empirical import EmpiricalTable, SegmentCurve
from ads_platform.schemas.landscape import LandscapeContext


def test_artifact_roundtrip(tmp_path):
    artifact = EmpiricalLandscapeArtifact(
        model_version="test_v1",
        tables_by_key={
            "channel:feed|global": EmpiricalTable(
                bids=[0.5, 1.0, 2.0],
                win_probs=[0.1, 0.3, 0.7],
                expected_costs=[0.05, 0.2, 0.8],
            )
        },
        default_curve=SegmentCurve(slope=1.0, midpoint=1.0, cost_fraction=0.5),
        metadata={"source": "unit_test"},
    )
    path = tmp_path / "landscape.json"
    artifact.write_json(path)
    loaded = EmpiricalLandscapeArtifact.read_json(path)
    model = loaded.build_model()
    est = model.estimate(
        bid=1.0,
        context=LandscapeContext(campaign_id="c", adgroup_id="a", segment_id=None, channel="feed"),
    )
    assert est.model_version == "test_v1"
    assert est.win_prob > 0
    assert loaded.metadata["source"] == "unit_test"
