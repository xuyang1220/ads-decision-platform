from __future__ import annotations

from pathlib import Path

from ads_platform.data.criteo import CriteoOffsetDataset, parse_criteo_tsv_line


def test_parse_criteo_tsv_line_handles_missing_values() -> None:
    # Empty fields between tabs are missing I* / C* values in Criteo train.txt.
    line = "0\t\t2\t3\t\t5\t6\t7\t8\t9\t10\t11\t12\t13\taa\t\tcc\td\te\tf\tg\th\ti\tj\tk\tl\tm\tn\to\tp\tq\tr\ts\tt\tu\tv\tw\tx\ty\tz\n"
    row = parse_criteo_tsv_line(line)
    assert row.label == 0
    assert row.features["I1"] is None
    assert row.features["I4"] is None
    assert row.features["I2"] == "2"
    assert row.features["I13"] == "13"
    assert row.features["C1"] == "aa"
    assert row.features["C2"] is None
    assert row.features["C3"] == "cc"
    assert row.features["C26"] == "z"


def test_criteo_offset_dataset_returns_dense_sparse_and_label(tmp_path: Path) -> None:
    line1 = "1\t1\t2\t3\t4\t5\t6\t7\t8\t9\t10\t11\t12\t13\ta\tb\tc\td\te\tf\tg\th\ti\tj\tk\tl\tm\tn\to\tp\tq\tr\ts\tt\tu\tv\tw\tx\ty\tz\n"
    line2 = "0\t\t2\t\t4\t5\t\t7\t8\t\t10\t11\t12\t13\taa\tbb\tcc\tdd\tee\tff\tgg\thh\tii\tjj\tkk\tll\tmm\tnn\too\tpp\tqq\trr\tss\ttt\tuu\tvv\tww\txx\tyy\tzz\n"
    data_path = tmp_path / "train.txt"
    data_path.write_text(line1 + line2)
    dataset = CriteoOffsetDataset(data_path=data_path)
    item = dataset[0]
    assert item["dense_x"].shape[0] == 13
    assert item["sparse_x"].shape[0] == 26
    assert item["label"].item() == 1.0
