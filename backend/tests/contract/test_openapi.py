import yaml
from openapi_spec_validator import validate

from tests.support import CONTRACT


def test_contract_is_a_valid_openapi_document() -> None:
    validate(yaml.safe_load(CONTRACT.read_text()))
