"""Schema validation for startup settings payloads."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

_ALIAS_TO_CANONICAL: dict[str, str] = {
    "runtime_mode": "mode",
    "runtime_profile": "profile",
    "ui_backend": "ui.backend",
    "sync_backend": "sync.backend",
}

_CANONICAL_TEMPLATE: dict[str, Any] = {
    "profile": None,
    "runtime": {
        "loop_mode": "oneshot",
        "poll_interval_seconds": 1.0,
        "idle_timeout_seconds": None,
        "max_runtime_seconds": None,
    },
    "paths": {
        "root": None,
        "watch": "incoming",
        "dest": "processed",
        "staging": "tmp",
    },
    "ui": {"backend": "headless"},
    "sync": {"backend": "noop", "api_token": None},
    "ingestion": {"retry_limit": 3, "retry_delay_seconds": 1.0},
    "naming": {"prefix": "DPOST", "policy": "prefix_only"},
    "plugins": {"pc_name": None, "device_plugins": ()},
}

_ENUMS: dict[str, set[str]] = {
    "mode": {"headless", "desktop"},
    "runtime.loop_mode": {"oneshot", "continuous"},
    "ui.backend": {"headless", "desktop"},
    "sync.backend": {"noop", "kadi"},
    "naming.policy": {"prefix_only", "prefix_date"},
}


@dataclass(frozen=True)
class SettingsSchemaIssue:
    """Machine-readable schema issue emitted by validator."""

    code: str
    path: str
    message: str
    hint: str | None = None

    def as_dict(self) -> dict[str, str]:
        """Serialize issue for diagnostics payloads."""
        payload = {
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }
        if self.hint:
            payload["hint"] = self.hint
        return payload


class SettingsSchemaError(ValueError):
    """Base class for startup schema validation failures."""

    def __init__(
        self, message: str, *, issues: tuple[SettingsSchemaIssue, ...]
    ) -> None:
        super().__init__(message)
        self.issues = issues


class SettingsSchemaMissingFieldError(SettingsSchemaError):
    """Raised when required fields are missing."""


class SettingsSchemaValueError(SettingsSchemaError):
    """Raised when a field has invalid shape or enum value."""


class SettingsSchemaConstraintError(SettingsSchemaError):
    """Raised when cross-field validation fails."""


class SettingsSchemaAliasError(SettingsSchemaError):
    """Raised when a legacy alias conflicts with canonical field values."""


def validate_raw_settings(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate raw startup settings and return canonical normalized payload."""
    if not isinstance(raw, Mapping):
        issue = SettingsSchemaIssue(
            code="invalid_type",
            path="$",
            message="Settings payload must be a mapping.",
            hint="Provide startup settings as a dictionary-like object.",
        )
        raise SettingsSchemaValueError(
            "Invalid startup settings payload.", issues=(issue,)
        )

    canonical = _normalize_aliases(raw)
    merged = _merge_with_template(canonical)
    _validate_required_fields(merged)
    _normalize_tokens(merged)
    _validate_enums(merged)
    _validate_constraints(merged)
    return merged


def _normalize_aliases(raw: Mapping[str, Any]) -> dict[str, Any]:
    canonical = deepcopy(dict(raw))
    for alias, canonical_path in _ALIAS_TO_CANONICAL.items():
        if alias not in canonical:
            continue

        alias_value = canonical.pop(alias)
        if _path_exists(canonical, canonical_path):
            canonical_value = _get_path(canonical, canonical_path)
            if canonical_value != alias_value:
                issue = SettingsSchemaIssue(
                    code="alias_collision",
                    path=alias,
                    message=(
                        f"Alias field {alias!r} conflicts with canonical field "
                        f"{canonical_path!r}."
                    ),
                    hint="Use canonical field names only.",
                )
                raise SettingsSchemaAliasError(
                    "Conflicting startup settings aliases detected.",
                    issues=(issue,),
                )
        else:
            _set_path(canonical, canonical_path, alias_value)
    return canonical


def _merge_with_template(raw: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(_CANONICAL_TEMPLATE)
    for key, value in raw.items():
        if key not in {
            "mode",
            "profile",
            "runtime",
            "paths",
            "ui",
            "sync",
            "ingestion",
            "naming",
            "plugins",
        }:
            issue = SettingsSchemaIssue(
                code="unknown_field",
                path=key,
                message=f"Unknown startup settings field: {key!r}.",
                hint="Remove unknown keys or update schema owner.",
            )
            raise SettingsSchemaValueError(
                "Unknown startup settings field.", issues=(issue,)
            )

        if key in merged and isinstance(merged[key], dict):
            if not isinstance(value, Mapping):
                issue = SettingsSchemaIssue(
                    code="invalid_type",
                    path=key,
                    message=f"Expected mapping at {key!r}.",
                    hint="Provide nested fields as a dictionary.",
                )
                raise SettingsSchemaValueError(
                    "Invalid nested settings type.", issues=(issue,)
                )
            merged[key] = _merge_nested_dict(
                block_name=key,
                base=merged[key],
                override=value,
            )
            continue

        merged[key] = value
    return merged


def _merge_nested_dict(
    *,
    block_name: str,
    base: Mapping[str, Any],
    override: Mapping[str, Any],
) -> dict[str, Any]:
    merged = deepcopy(dict(base))
    for key, value in override.items():
        if key not in merged:
            issue = SettingsSchemaIssue(
                code="unknown_field",
                path=f"{block_name}.{key}",
                message=f"Unknown nested field {key!r} under {block_name!r}.",
                hint="Remove unknown keys or update schema owner.",
            )
            raise SettingsSchemaValueError(
                "Unknown nested startup settings field.", issues=(issue,)
            )
        merged[key] = value
    return merged


def _validate_required_fields(payload: Mapping[str, Any]) -> None:
    if "mode" not in payload:
        issue = SettingsSchemaIssue(
            code="missing_field",
            path="mode",
            message="Required startup field 'mode' is missing.",
            hint="Set mode to 'headless' or 'desktop'.",
        )
        raise SettingsSchemaMissingFieldError(
            "Missing required startup field.", issues=(issue,)
        )

    if (
        not _path_exists(payload, "paths.root")
        or not str(_get_path(payload, "paths.root") or "").strip()
    ):
        issue = SettingsSchemaIssue(
            code="missing_field",
            path="paths.root",
            message="Required startup field 'paths.root' is missing.",
            hint="Provide a root directory in paths.root.",
        )
        raise SettingsSchemaMissingFieldError(
            "Missing required startup field.", issues=(issue,)
        )


def _normalize_tokens(payload: dict[str, Any]) -> None:
    payload["mode"] = str(payload["mode"]).strip().lower()

    profile = payload.get("profile")
    payload["profile"] = None if profile is None else str(profile).strip().lower()

    payload["runtime"]["loop_mode"] = (
        str(payload["runtime"]["loop_mode"]).strip().lower()
    )
    payload["runtime"]["poll_interval_seconds"] = _coerce_non_negative_float(
        payload["runtime"].get("poll_interval_seconds", 1.0),
        path="runtime.poll_interval_seconds",
    )
    payload["runtime"]["idle_timeout_seconds"] = _coerce_optional_non_negative_float(
        payload["runtime"].get("idle_timeout_seconds"),
        path="runtime.idle_timeout_seconds",
    )
    payload["runtime"]["max_runtime_seconds"] = _coerce_optional_non_negative_float(
        payload["runtime"].get("max_runtime_seconds"),
        path="runtime.max_runtime_seconds",
    )

    payload["ui"]["backend"] = str(payload["ui"]["backend"]).strip().lower()
    payload["sync"]["backend"] = str(payload["sync"]["backend"]).strip().lower()
    payload["naming"]["policy"] = str(payload["naming"]["policy"]).strip().lower()

    pc_name = payload["plugins"].get("pc_name")
    if pc_name is None:
        payload["plugins"]["pc_name"] = None
    else:
        payload["plugins"]["pc_name"] = str(pc_name).strip().lower() or None

    device_plugins = payload["plugins"].get("device_plugins", ())
    if device_plugins is None or device_plugins == "":
        payload["plugins"]["device_plugins"] = ()
    else:
        if not isinstance(device_plugins, tuple | list):
            issue = SettingsSchemaIssue(
                code="invalid_type",
                path="plugins.device_plugins",
                message="plugins.device_plugins must be a sequence of plugin ids.",
                hint="Provide plugins.device_plugins as a list or tuple of strings.",
            )
            raise SettingsSchemaValueError(
                "Invalid startup settings field type.",
                issues=(issue,),
            )

        normalized_plugins: list[str] = []
        for plugin_id in device_plugins:
            token = str(plugin_id).strip().lower()
            if not token:
                issue = SettingsSchemaIssue(
                    code="invalid_value",
                    path="plugins.device_plugins",
                    message=(
                        "plugins.device_plugins entries must be non-empty strings."
                    ),
                    hint="Remove empty plugin ids from plugins.device_plugins.",
                )
                raise SettingsSchemaValueError(
                    "Invalid startup settings field value.",
                    issues=(issue,),
                )
            normalized_plugins.append(token)
        payload["plugins"]["device_plugins"] = tuple(normalized_plugins)


def _validate_enums(payload: Mapping[str, Any]) -> None:
    for path, allowed in _ENUMS.items():
        value = _get_path(payload, path)
        if value not in allowed:
            issue = SettingsSchemaIssue(
                code="invalid_enum",
                path=path,
                message=(
                    f"Unsupported value {value!r} at {path!r}. "
                    f"Allowed values: {', '.join(sorted(allowed))}."
                ),
                hint="Use one of the allowed enum values.",
            )
            raise SettingsSchemaValueError(
                "Invalid startup enum value.", issues=(issue,)
            )


def _validate_constraints(payload: Mapping[str, Any]) -> None:
    if payload["mode"] == "desktop" and payload["ui"]["backend"] != "desktop":
        issue = SettingsSchemaIssue(
            code="constraint_violation",
            path="ui.backend",
            message="Desktop mode requires desktop UI backend.",
            hint="Set ui.backend='desktop' for desktop mode.",
        )
        raise SettingsSchemaConstraintError(
            "Cross-field startup settings constraint violation.",
            issues=(issue,),
        )


def _path_exists(payload: Mapping[str, Any], dotted_path: str) -> bool:
    cursor: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(cursor, Mapping) or part not in cursor:
            return False
        cursor = cursor[part]
    return True


def _get_path(payload: Mapping[str, Any], dotted_path: str) -> Any:
    cursor: Any = payload
    for part in dotted_path.split("."):
        cursor = cursor[part]
    return cursor


def _set_path(payload: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    cursor = payload
    for part in parts[:-1]:
        existing = cursor.get(part)
        if not isinstance(existing, dict):
            cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = value


def _coerce_non_negative_float(value: Any, *, path: str) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        issue = SettingsSchemaIssue(
            code="invalid_type",
            path=path,
            message=f"{path} must be numeric.",
            hint="Provide a numeric seconds value.",
        )
        raise SettingsSchemaValueError(
            "Invalid startup settings field type.", issues=(issue,)
        ) from exc

    if normalized < 0:
        issue = SettingsSchemaIssue(
            code="invalid_value",
            path=path,
            message=f"{path} must be >= 0.",
            hint="Use a non-negative seconds value.",
        )
        raise SettingsSchemaValueError(
            "Invalid startup settings field value.", issues=(issue,)
        )
    return normalized


def _coerce_optional_non_negative_float(value: Any, *, path: str) -> float | None:
    if value is None:
        return None
    return _coerce_non_negative_float(value, path=path)
