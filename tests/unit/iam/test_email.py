import pytest
from contexts.iam.domain.value_objects import Email
from shared.domain.errors import ValidationError


def test_valid_email():
    assert Email("owner@pyme.com").address == "owner@pyme.com"


@pytest.mark.parametrize("bad", ["", "no-at", "a@b", "a@@b.com", "a b@c.com"])
def test_invalid_email_rejected(bad):
    with pytest.raises(ValidationError):
        Email(bad)
