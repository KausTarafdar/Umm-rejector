"""Scoring tests: spotter events cross-referenced with word timestamps."""

from umm.scoring import build_report


def test_spotter_only() -> None:
    report = build_report(
        transcript="I think that was good",
        spotter_events=[{"label": "um", "t_start": 1.0, "t_end": 1.4}],
        duration_secs=60.0,
    )
    assert report["filler_count"] == 1
    assert report["fillers_per_minute"] == 1.0
    assert report["filler_breakdown"] == {"um": 1}
    assert report["transcript"] == "I think that was good"


def test_word_timestamps_add_missed_fillers() -> None:
    report = build_report(
        transcript="um yeah I was like thinking",
        spotter_events=[],
        duration_secs=30.0,
        word_timestamps=[
            {"word": "um", "start": 0.2, "end": 0.6},
            {"word": "yeah", "start": 1.0, "end": 1.3},
            {"word": "like", "start": 4.0, "end": 4.2},
        ],
    )
    labels = [e["label"] for e in report["filler_events"]]
    assert labels == ["um", "like"]
    assert report["words_per_minute"] == 12.0


def test_empty_transcript_no_crash() -> None:
    report = build_report(transcript="", spotter_events=[], duration_secs=0.0)
    assert report["filler_count"] == 0
    assert report["fillers_per_minute"] == 0.0
    assert report["words_per_minute"] == 0.0
