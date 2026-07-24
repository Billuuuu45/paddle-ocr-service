import json
import logging
import socket
from typing import Any, Dict, Optional

import httpx

from config import settings
from services.response_validator import InvalidJSONResponseError, parse_json_response
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)


class GPTServiceError(Exception):
    pass


class GPTTimeoutError(GPTServiceError):
    pass


class GPTConnectionError(GPTServiceError):
    pass


class GPTAPIError(GPTServiceError):
    pass


class SLMService:
    def __init__(self, settings_obj: Optional[settings.__class__] = None):
        self.settings = settings_obj or settings
        self.endpoint = self.settings.gpt_endpoint
        self.payload_type = self.settings.gpt_payload_type.lower()
        self.model_name = self.settings.gpt_model
        self.temperature = self.settings.gpt_temperature
        self.max_tokens = self.settings.gpt_max_tokens
        self.timeout = self.settings.gpt_timeout
        self.api_key = self.settings.gpt_api_key

    def _infer_payload_type(self, endpoint: str) -> str:
        if self.payload_type != "auto":
            return self.payload_type

        if any(token in endpoint for token in ["/v1/chat/completions", "/api/chat"]):
            return "chat"

        if any(token in endpoint for token in ["/v1/completions", "/api/generate"]):
            return "completions"

        return "chat"

    def _build_payload_for_endpoint(self, prompt: str, endpoint: str) -> Dict[str, Any]:
        payload_type = self._infer_payload_type(endpoint)
        base_payload = {
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if payload_type == "chat":
            base_payload["messages"] = [{"role": "user", "content": prompt}]
            return base_payload

        if payload_type == "prompt":
            base_payload["prompt"] = prompt
            return base_payload

        base_payload["input"] = prompt
        return base_payload

    def _is_localhost(self, hostname: Optional[str]) -> bool:
        return hostname in {"localhost", "127.0.0.1"}

    def _is_port_open(self, hostname: str, port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.2)
                return sock.connect_ex((hostname, port)) == 0
        except OSError:
            return False

    def _probe_local_ports(self, hostname: str, base_port: Optional[int]) -> list[int]:
        candidates = [8000, 8001, 8002, 8003, 8004, 8005, 8080, 8081, 8082, 8888, 5000, 5001, 5002, 5003]
        if base_port and base_port not in candidates:
            candidates.insert(0, base_port)

        open_ports = []
        for port in candidates:
            if port == base_port:
                continue
            if self._is_port_open(hostname, port):
                open_ports.append(port)

        return open_ports

    @staticmethod
    def _extract_model_text(response_json: Dict[str, Any]) -> str:
        if "choices" in response_json:
            choices = response_json.get("choices") or []
            if not choices:
                raise GPTAPIError("GPT response did not contain any choices.")
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                if "message" in first_choice and isinstance(first_choice["message"], dict):
                    content = first_choice["message"].get("content")
                    if content is not None:
                        return content
                if "delta" in first_choice and isinstance(first_choice["delta"], dict):
                    content = first_choice["delta"].get("content")
                    if content is not None:
                        return content
                if "text" in first_choice and first_choice["text"] is not None:
                    return first_choice["text"]
                if "content" in first_choice and first_choice["content"] is not None:
                    return first_choice["content"]

        if "content" in response_json:
            return str(response_json["content"])

        if "output" in response_json:
            output = response_json["output"]
            if isinstance(output, list) and output:
                item = output[0]
                if isinstance(item, dict):
                    return item.get("content", "") or str(item)
                return str(item)
            if isinstance(output, dict) and "content" in output:
                return str(output["content"])
            return str(output)

        if "result" in response_json:
            return json.dumps(response_json["result"])

        if isinstance(response_json, str):
            return response_json

        raise GPTAPIError("Unable to extract text from GPT response.")

    def _candidate_endpoints(self) -> list[str]:
        parsed = urlparse(self.endpoint)
        base = f"{parsed.scheme}://{parsed.netloc}"
        candidates = [
            self.endpoint,
            urljoin(base, "/v1/chat/completions"),
            urljoin(base, "/v1/completions"),
            urljoin(base, "/api/chat"),
            urljoin(base, "/api/generate"),
        ]

        if self._is_localhost(parsed.hostname):
            open_ports = self._probe_local_ports(parsed.hostname, parsed.port)
            logger.debug("Local open ports discovered for GPT endpoint: %s", open_ports)
            for port in open_ports:
                port_base = f"{parsed.scheme}://{parsed.hostname}:{port}"
                candidates.extend(
                    [
                        urljoin(port_base, "/v1/chat/completions"),
                        urljoin(port_base, "/v1/completions"),
                        urljoin(port_base, "/api/chat"),
                        urljoin(port_base, "/api/generate"),
                    ]
                )

        unique_candidates = list(dict.fromkeys(candidates))
        logger.info("Candidate endpoints: %s", unique_candidates)
        return unique_candidates

    async def _send_request(self, prompt: str) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        candidates = self._candidate_endpoints()
        timeout = httpx.Timeout(self.timeout, connect=self.timeout)
        last_timeout: Optional[Exception] = None
        last_connection: Optional[Exception] = None

        async with httpx.AsyncClient(timeout=timeout) as client:
            for candidate in candidates:
                payload = self._build_payload_for_endpoint(prompt, candidate)
                logger.info("Trying GPT candidate endpoint %s", candidate)
                logger.debug("GPT request payload: %s", payload)

                try:
                    response = await client.post(candidate, json=payload, headers=headers)
                except httpx.TimeoutException as exc:
                    last_timeout = exc
                    logger.warning(
                        "GPT request to %s timed out after %s seconds.", candidate, self.timeout
                    )
                    continue
                except httpx.RequestError as exc:
                    last_connection = exc
                    logger.warning("Failed to connect to GPT endpoint %s: %s", candidate, exc)
                    continue

                logger.info("GPT endpoint %s responded with status %s", candidate, response.status_code)
                logger.debug("GPT response body: %s", response.text)

                if response.status_code == 404:
                    logger.warning("GPT endpoint %s returned 404 Not Found.", candidate)
                    continue

                try:
                    response_json = response.json()
                except json.JSONDecodeError as exc:
                    raise GPTAPIError("GPT endpoint returned invalid JSON.") from exc

                if response.status_code >= 400:
                    message = response_json.get("error") or response.text
                    raise GPTAPIError(f"GPT endpoint error: {message}")

                self.endpoint = candidate
                return response_json

        if last_timeout is not None and last_connection is None:
            raise GPTTimeoutError(
                f"GPT requests timed out for all candidate endpoints after {self.timeout}s."
            ) from last_timeout

        raise GPTConnectionError(
            "Failed to connect to GPT endpoint. Attempted endpoints: "
            f"{', '.join(candidates)}. Verify GPT_ENDPOINT and that the model server is running."
        ) from last_connection

    async def validate_endpoint(self) -> None:
        parsed = urlparse(self.endpoint)
        if parsed.hostname in {"localhost", "127.0.0.1"} and parsed.port == 8000:
            logger.warning(
                "Configured GPT endpoint %s uses port 8000, which appears to be the same port as this OCR FastAPI app."
                " Ensure GPT_ENDPOINT points to the model server, not the OCR service.",
                self.endpoint,
            )

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        timeout = httpx.Timeout(self.timeout, connect=self.timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.head(self.endpoint, headers=headers)
                logger.info("Validated GPT endpoint %s with status %s", self.endpoint, response.status_code)
                if response.status_code == 404:
                    logger.warning(
                        "GPT endpoint validation returned 404. The configured endpoint may be incorrect or the server may not expose this route."
                    )
                elif response.status_code == 401:
                    logger.warning(
                        "GPT endpoint validation returned 401 Unauthorized. Check GPT_API_KEY and OpenRouter credentials."
                    )
                elif response.status_code == 405:
                    logger.info(
                        "GPT endpoint %s does not support HEAD; endpoint appears reachable.",
                        self.endpoint,
                    )
            except httpx.RequestError as exc:
                logger.warning(
                    "GPT endpoint validation failed for %s: %s. Verify GPT_ENDPOINT and that the model server is running.",
                    self.endpoint,
                    exc,
                )
                if parsed.hostname in {"localhost", "127.0.0.1"} and parsed.port == 8000:
                    logger.warning(
                        "Port 8000 is likely the OCR FastAPI app. If your model server is running locally, set GPT_ENDPOINT to its actual host and port."
                    )

    async def generate_structured_json(self, prompt: str, retries: int = 1) -> Dict[str, Any]:
        last_error: Optional[Exception] = None

        for attempt in range(1, retries + 2):
            try:
                response_json = await self._send_request(prompt)
                model_text = self._extract_model_text(response_json).strip()
                logger.info("Received model response for JSON parsing.")
                parsed = parse_json_response(model_text)
                logger.info("GPT JSON response validated successfully.")
                return parsed
            except InvalidJSONResponseError as exc:
                last_error = exc
                logger.warning("Invalid JSON response on attempt %s: %s", attempt, exc)
                if attempt > retries:
                    raise
                continue
            except GPTServiceError:
                raise
            except Exception as exc:
                raise GPTAPIError("Unexpected GPT service error.") from exc

        raise GPTAPIError("Failed to parse GPT output after retries.")
