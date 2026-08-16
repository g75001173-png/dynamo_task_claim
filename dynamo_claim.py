#!/usr/bin/env python3
"""Poll Handshake's claim endpoint until a task is claimed."""

import argparse
import json
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Mapping, Optional

import requests


DEFAULT_CONFIG_PATH = Path(__file__).with_name("claim_request.json")
CONFIG_ENV_VAR = "CLAIM_REQUEST_JSON"
TRANSIENT_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
TASK_ID_KEYS = {
    "annotationtaskid",
    "claimedtaskid",
    "taskid",
}
TASK_CONTAINER_KEYS = {
    "annotationtask",
    "claimedtask",
    "task",
}


@dataclass(frozen=True)
class PollingConfig:
    request_timeout_seconds: float = 15.0
    poll_interval_seconds: float = 1.0
    jitter_seconds: float = 0.25
    max_backoff_seconds: float = 30.0
    max_attempts: Optional[int] = None


@dataclass(frozen=True)
class ClaimConfig:
    url: str
    method: str
    headers: Mapping[str, str]
    body: Mapping[str, Any]
    project_id: str
    polling: PollingConfig
    proof_path: Path
    debug_path: Path
    source: str


class ConfigError(ValueError):
    """Raised when the request configuration is incomplete or invalid."""


def positive_float(value: Any, name: str, allow_zero: bool = False) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a number") from exc

    if parsed < 0 or (parsed == 0 and not allow_zero):
        comparison = "zero or greater" if allow_zero else "greater than zero"
        raise ConfigError(f"{name} must be {comparison}")
    return parsed


def optional_positive_int(value: Any, name: str) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ConfigError(f"{name} must be a positive integer or null")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a positive integer or null") from exc
    if parsed <= 0 or parsed != value:
        raise ConfigError(f"{name} must be a positive integer or null")
    return parsed


def resolve_output_path(config_path: Path, value: Any, default_name: str) -> Path:
    output_path = Path(value or default_name)
    if not output_path.is_absolute():
        output_path = config_path.parent / output_path
    return output_path


def load_config(config_path: Path) -> ClaimConfig:
    try:
        raw_config_text = config_path.read_text(encoding="utf-8")
        config_source = str(config_path)
    except FileNotFoundError:
        raw_config_text = os.environ.get(CONFIG_ENV_VAR)
        config_source = CONFIG_ENV_VAR
        if raw_config_text is None:
            raise ConfigError(
                f"Configuration not found: {config_path}. Create it from "
                f"claim_request.example.json or set {CONFIG_ENV_VAR}."
            ) from None

    try:
        raw_config = json.loads(raw_config_text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {config_source}: {exc}") from exc

    if not isinstance(raw_config, dict):
        raise ConfigError("The configuration root must be a JSON object")

    url = raw_config.get("url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ConfigError("url must be an HTTPS URL")

    method = raw_config.get("method", "POST")
    if not isinstance(method, str) or method.upper() != "POST":
        raise ConfigError("method must be POST")

    headers = raw_config.get("headers")
    if not isinstance(headers, dict) or not headers:
        raise ConfigError("headers must be a non-empty JSON object")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in headers.items()):
        raise ConfigError("every header name and value must be a string")
    if not any(name.lower() == "cookie" for name in headers):
        raise ConfigError(
            "headers must include the Cookie header copied from an authenticated request"
        )

    body = raw_config.get("body")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ConfigError("body is a string but does not contain valid JSON") from exc
    if not isinstance(body, dict):
        raise ConfigError("body must be a JSON object or a JSON-encoded object string")
    batch_item = body.get("0")
    request_json = batch_item.get("json") if isinstance(batch_item, dict) else None
    project_id = (
        request_json.get("annotationProjectId")
        if isinstance(request_json, dict)
        else None
    )
    if not isinstance(project_id, str) or not project_id.strip():
        raise ConfigError("body.0.json.annotationProjectId must be a non-empty string")

    polling_raw = raw_config.get("polling", {})
    if not isinstance(polling_raw, dict):
        raise ConfigError("polling must be a JSON object")
    polling = PollingConfig(
        request_timeout_seconds=positive_float(
            polling_raw.get("request_timeout_seconds", 15),
            "polling.request_timeout_seconds",
        ),
        poll_interval_seconds=positive_float(
            polling_raw.get("poll_interval_seconds", 1),
            "polling.poll_interval_seconds",
            allow_zero=True,
        ),
        jitter_seconds=positive_float(
            polling_raw.get("jitter_seconds", 0.25),
            "polling.jitter_seconds",
            allow_zero=True,
        ),
        max_backoff_seconds=positive_float(
            polling_raw.get("max_backoff_seconds", 30),
            "polling.max_backoff_seconds",
        ),
        max_attempts=optional_positive_int(
            polling_raw.get("max_attempts"),
            "polling.max_attempts",
        ),
    )

    return ClaimConfig(
        url=url,
        method=method.upper(),
        headers=headers,
        body=body,
        project_id=project_id,
        polling=polling,
        proof_path=resolve_output_path(
            config_path,
            raw_config.get("proof_file"),
            "session_proof.json",
        ),
        debug_path=resolve_output_path(
            config_path,
            raw_config.get("debug_file"),
            "unexpected_response.json",
        ),
        source=config_source,
    )


def normalize_key(key: Any) -> str:
    return "".join(character for character in str(key).lower() if character.isalnum())


def identifier(value: Any) -> Optional[str]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (str, int)):
        parsed = str(value).strip()
        return parsed or None
    return None


def extract_task_id(value: Any) -> Optional[str]:
    """Find task-specific IDs without mistaking a project or user ID for a task."""
    if isinstance(value, dict):
        for key, child in value.items():
            if normalize_key(key) in TASK_ID_KEYS:
                task_id = identifier(child)
                if task_id:
                    return task_id

        for key, child in value.items():
            if normalize_key(key) not in TASK_CONTAINER_KEYS or not isinstance(child, dict):
                continue
            for id_key, id_value in child.items():
                if normalize_key(id_key) in TASK_ID_KEYS | {"id"}:
                    task_id = identifier(id_value)
                    if task_id:
                        return task_id

        for child in value.values():
            task_id = extract_task_id(child)
            if task_id:
                return task_id
    elif isinstance(value, list):
        for child in value:
            task_id = extract_task_id(child)
            if task_id:
                return task_id
    return None


def contains_no_task(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() == "no_task_available"
    if isinstance(value, dict):
        return any(contains_no_task(child) for child in value.values())
    if isinstance(value, list):
        return any(contains_no_task(child) for child in value)
    return False


def first_batch_entry(value: Any) -> Any:
    if isinstance(value, list) and value:
        return value[0]
    if isinstance(value, dict) and "0" in value:
        return value["0"]
    return value


def unwrap_trpc_result(value: Any) -> Any:
    entry = first_batch_entry(value)
    if not isinstance(entry, dict):
        return entry
    result = entry.get("result", entry)
    if not isinstance(result, dict):
        return result
    data = result.get("data", result)
    if not isinstance(data, dict):
        return data
    return data.get("json", data)


def extract_trpc_error(value: Any) -> Optional[str]:
    entry = first_batch_entry(value)
    if not isinstance(entry, dict) or "error" not in entry:
        return None
    error = entry["error"]
    if isinstance(error, dict):
        error_json = error.get("json", error)
        if isinstance(error_json, dict):
            message = error_json.get("message")
            if isinstance(message, str) and message:
                return message
    return "The API returned an unspecified tRPC error"


def retry_after_seconds(response: requests.Response) -> Optional[float]:
    raw_value = response.headers.get("Retry-After")
    if not raw_value:
        return None
    try:
        return max(0.0, float(raw_value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(raw_value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def backoff_seconds(failure_count: int, config: PollingConfig) -> float:
    exponential = min(config.max_backoff_seconds, 2 ** max(0, failure_count - 1))
    return exponential + random.uniform(0, config.jitter_seconds)


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def response_json(response: requests.Response) -> Optional[Any]:
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return None


def claim(config: ClaimConfig, max_attempts: Optional[int] = None) -> int:
    session = requests.Session()
    session.headers.clear()
    session.headers.update(config.headers)

    attempt_limit = max_attempts if max_attempts is not None else config.polling.max_attempts
    attempt = 0
    transient_failures = 0

    print("[*] Polling the claim endpoint. Press Ctrl+C to stop.")
    while attempt_limit is None or attempt < attempt_limit:
        attempt += 1
        try:
            response = session.request(
                config.method,
                config.url,
                json=config.body,
                timeout=config.polling.request_timeout_seconds,
            )
        except requests.RequestException as exc:
            transient_failures += 1
            delay = backoff_seconds(transient_failures, config.polling)
            print(f"[RETRY] Request {attempt} failed: {exc}. Waiting {delay:.1f}s.")
            time.sleep(delay)
            continue

        parsed_response = response_json(response)

        if response.status_code in (401, 403):
            api_error = extract_trpc_error(parsed_response) if parsed_response is not None else None
            if api_error:
                print(f"[ACCESS] HTTP {response.status_code}: {api_error}")
            else:
                print(
                    f"[AUTH] HTTP {response.status_code}. The Cookie header is expired "
                    "or is not authorized for this project."
                )
            return 2

        if response.status_code in TRANSIENT_STATUS_CODES:
            transient_failures += 1
            delay = retry_after_seconds(response)
            if delay is None:
                delay = backoff_seconds(transient_failures, config.polling)
            delay = min(delay, config.polling.max_backoff_seconds)
            print(f"[RETRY] HTTP {response.status_code} on attempt {attempt}; waiting {delay:.1f}s.")
            time.sleep(delay)
            continue

        if not 200 <= response.status_code < 300:
            excerpt = response.text[:300].replace("\n", " ")
            print(f"[ERROR] HTTP {response.status_code}: {excerpt}")
            return 3

        if parsed_response is None:
            save_json(
                config.debug_path,
                {"http_status": response.status_code, "response_text": response.text},
            )
            print(f"[ERROR] The API returned non-JSON data. Saved to {config.debug_path}.")
            return 3

        api_error = extract_trpc_error(parsed_response)
        if api_error:
            print(f"[API ERROR] {api_error}")
            return 3

        transient_failures = 0
        claim_result = unwrap_trpc_result(parsed_response)
        task_id = extract_task_id(claim_result)
        if task_id:
            proof = {
                "claimed_at": datetime.now(timezone.utc).isoformat(),
                "attempt": attempt,
                "task_id": task_id,
                "http_status": response.status_code,
                "response": parsed_response,
            }
            save_json(config.proof_path, proof)
            print(f"[CLAIMED] Task ID: {task_id} (attempt {attempt})")
            print(f"[*] Claim response saved to {config.proof_path}")
            return 0

        if not contains_no_task(claim_result):
            save_json(
                config.debug_path,
                {"http_status": response.status_code, "response": parsed_response},
            )
            print(
                "[ERROR] The response was neither a claim nor 'no_task_available'. "
                f"Saved to {config.debug_path}."
            )
            return 3

        print(".", end="", flush=True)
        if attempt % 20 == 0:
            print(f" {attempt} attempts")
        delay = config.polling.poll_interval_seconds + random.uniform(
            0,
            config.polling.jitter_seconds,
        )
        time.sleep(delay)

    print(f"\n[*] No task was available after {attempt} attempts.")
    return 1


def positive_int_argument(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"request configuration (default: {DEFAULT_CONFIG_PATH.name})",
    )
    parser.add_argument(
        "--max-attempts",
        type=positive_int_argument,
        help="override polling.max_attempts for this run",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate configuration without making a claim request",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_config(args.config.resolve())
    except (ConfigError, OSError) as exc:
        print(f"[CONFIG] {exc}", file=sys.stderr)
        return 2

    if args.check:
        header_names = ", ".join(config.headers.keys())
        print(f"[OK] Configuration is valid for project {config.project_id}.")
        print(f"[*] Configuration source: {config.source}")
        print(f"[*] Request headers: {header_names}")
        return 0

    try:
        return claim(config, args.max_attempts)
    except KeyboardInterrupt:
        print("\n[*] Interrupted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
