import pytest
from shared.domain.identity import IntId
from shared.domain.errors import ValidationError


class SampleId(IntId):
    pass


def test_intid_holds_value():
    assert SampleId(5).value == 5


def test_intid_is_frozen():
    i = SampleId(5)
    with pytest.raises(Exception):
        i.value = 6  # type: ignore[misc]


def test_intid_equality_by_value_and_type():
    assert SampleId(5) == SampleId(5)
    assert SampleId(5) != SampleId(6)


def test_intid_rejects_non_positive():
    with pytest.raises(ValidationError):
        SampleId(0)
    with pytest.raises(ValidationError):
        SampleId(-1)
