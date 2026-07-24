import json
from typing import Any, Dict


class InvalidJSONResponseError(ValueError):
    pass


def _extract_json_payload(response_text: str) -> str:
    start = response_text.find("{")
    end = response_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise InvalidJSONResponseError("No valid JSON object found in model output.")
    return response_text[start : end + 1]


def _validate_response_schema(parsed: Any) -> Dict[str, Any]:
    if not isinstance(parsed, dict):
        raise InvalidJSONResponseError("Model response must be a JSON object.")

    if "document_type" not in parsed or "structured_data" not in parsed:
        raise InvalidJSONResponseError(
            "JSON response must include 'document_type' and 'structured_data'."
        )

    if not isinstance(parsed["structured_data"], dict):
        raise InvalidJSONResponseError("'structured_data' must be a JSON object.")

    return parsed


def parse_json_response(response_text: str) -> Dict[str, Any]:
    json_payload = _extract_json_payload(response_text)
    try:
        parsed = json.loads(json_payload)
    except json.JSONDecodeError as exc:
        raise InvalidJSONResponseError("Model response contained invalid JSON payload.") from exc
    return _validate_response_schema(parsed)
