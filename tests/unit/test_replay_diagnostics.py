from ads_platform.evaluation.replay_diagnostics import build_calibration_table, build_policy_row, build_predicted_vs_observed
from ads_platform.replay.runner import ReplaySummary


def test_predicted_vs_observed_summary():
    summary = ReplaySummary(
        num_auctions=2,
        num_candidates=10,
        num_winners=2,
        predicted_clicks=1.2,
        observed_clicks_on_selected=1,
        realized_spend=3.0,
        avg_predicted_ctr_selected=0.6,
        avg_effective_bid_selected=1.5,
    )
    metrics = build_predicted_vs_observed(summary)
    assert abs(metrics['absolute_gap'] - 0.2) < 1e-9
    assert abs(metrics['prediction_to_observation_ratio'] - 1.2) < 1e-9


def test_calibration_table_selected_rows():
    per_auction = [
        {
            'decision_logs': [
                {'selected': True, 'pctr_calibrated': 0.12, 'observed_clicked': 0, 'bid_effective': 1.0},
                {'selected': True, 'pctr_calibrated': 0.18, 'observed_clicked': 1, 'bid_effective': 2.0},
                {'selected': False, 'pctr_calibrated': 0.95, 'observed_clicked': 1, 'bid_effective': 3.0},
            ]
        }
    ]
    table = build_calibration_table(per_auction, num_buckets=5)
    assert sum(row.num_selected for row in table) == 2
    assert any(row.observed_clicks == 1 for row in table)


def test_policy_row_contains_ctr_and_ratio():
    summary = ReplaySummary(
        num_auctions=10,
        num_candidates=50,
        num_winners=10,
        predicted_clicks=2.5,
        observed_clicks_on_selected=2,
        realized_spend=5.0,
        avg_predicted_ctr_selected=0.25,
        avg_effective_bid_selected=1.1,
    )
    row = build_policy_row('oracle', summary)
    assert row['policy'] == 'oracle'
    assert row['observed_ctr_selected'] == 0.2
    assert row['predicted_vs_observed_ratio'] == 1.25
