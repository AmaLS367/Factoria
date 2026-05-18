import pytest
from pydantic import ValidationError

from backend.utils.schemas import LLMExtractionResponse


def test_accepts_valid_shape() -> None:
    model = LLMExtractionResponse.model_validate(
        {"values": {"Name": "Widget"}, "confidence": {"Name": 0.9}}
    )
    assert model.values == {"Name": "Widget"}
    assert model.confidence == {"Name": 0.9}


def test_confidence_defaults_to_empty_dict() -> None:
    model = LLMExtractionResponse.model_validate({"values": {"Name": "Widget"}})
    assert model.confidence == {}


def test_extras_are_ignored() -> None:
    model = LLMExtractionResponse.model_validate(
        {"values": {"a": "b"}, "confidence": {}, "garbage": 123}
    )
    assert not hasattr(model, "garbage")


def test_rejects_missing_values() -> None:
    with pytest.raises(ValidationError):
        LLMExtractionResponse.model_validate({"confidence": {"a": 0.5}})


def test_rejects_non_dict_values() -> None:
    with pytest.raises(ValidationError):
        LLMExtractionResponse.model_validate({"values": ["a", "b"], "confidence": {}})


def test_accepts_heterogeneous_field_values() -> None:
    # values/confidence are dict[str, Any] — field-level normalization happens downstream
    model = LLMExtractionResponse.model_validate(
        {"values": {"a": "x", "b": 42}, "confidence": {"a": "high", "b": None}}
    )
    assert model.values == {"a": "x", "b": 42}
    assert model.confidence == {"a": "high", "b": None}
