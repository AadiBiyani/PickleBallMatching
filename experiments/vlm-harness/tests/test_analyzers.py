"""The registry must keep working with other models' one-argument factories."""

import pytest

from harness.analyzers import base
from harness.analyzers.fake import FakeAnalyzer


def test_one_argument_factory_accepts_default_cli_options(monkeypatch):
    calls = []

    # Matches the factory signature in MediaPipe PR #3, without loading a model.
    def make_model(model):
        calls.append(model)
        return FakeAnalyzer(model)

    monkeypatch.setitem(base._FACTORIES, "mediapipe", make_model)
    for spec, expected in [("mediapipe", ""), (" MEDIAPIPE : pose-landmarker-lite ", "pose-landmarker-lite")]:
        analyzer = base.create_analyzer(spec, positions_path=None, player_id=None)
        assert analyzer.model_id == (expected or "fake")
    assert calls == ["", "pose-landmarker-lite"]


@pytest.mark.parametrize("options", [{"positions_path": "positions.json"}, {"player_id": "player_1"}])
def test_other_models_reject_yolo_options_before_construction(monkeypatch, options):
    def make_model(model):
        pytest.fail("An analyzer must not be constructed with invalid configuration")

    monkeypatch.setitem(base._FACTORIES, "mediapipe", make_model)
    with pytest.raises(ValueError, match="only to the yolo"):
        base.create_analyzer("mediapipe:pose-landmarker-lite", **options)
