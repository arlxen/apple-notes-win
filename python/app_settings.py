import json
import re
from datetime import datetime
from pathlib import Path


_STRFTIME_DIRECTIVES = frozenset("aAwdbBmyYHIpMSfzZjUWcxXGuV%")


def is_valid_output_date_format(value):
    if not isinstance(value, str) or not value:
        return False

    index = 0
    while index < len(value):
        if value[index] != "%":
            index += 1
            continue

        index += 1
        if index == len(value):
            return False

        if value[index] in "_-0^#":
            index += 1
        if index < len(value) and value[index] in "EO":
            index += 1
        if index < len(value) and value[index] == ":":
            while index < len(value) and value[index] == ":":
                index += 1
            if index == len(value) or value[index] != "z":
                return False
        elif index == len(value) or value[index] not in _STRFTIME_DIRECTIVES:
            return False

        index += 1

    try:
        datetime(2000, 1, 2, 3, 4, 5).strftime(value)
    except (ValueError, OverflowError):
        return False
    return True


def escape_windows_paths(text):
    def escape(match):
        value = re.sub(
            r"\\+",
            lambda slashes: slashes.group() + (
                "\\" if len(slashes.group()) % 2 else ""
            ),
            match.group(2),
        )
        return match.group(1) + value + match.group(3)

    return re.sub(
        r'("(?:source|metadata|output)"\s*:\s*")([^"]*)(")',
        escape,
        text,
    )


IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".heic", ".heif", ".tif", ".tiff", ".bmp",
}

DEFAULTS = {
    "source": "",
    "metadata": "",
    "output": "",
    "date_format": "%m-%d-%Y %H:%M:%S",
    "output_date_format": None,
    "output_format": None,
    "confirm_before_processing": True,
    "missing_date_behavior": "missing",
}


def load_settings():
    path = Path(__file__).resolve().parent.parent / "settings.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"Settings file not found: {path}. "
            f"Copy {path.with_name('settings.example.json')} to {path}."
        )

    settings_text = path.read_text(encoding="utf-8")
    settings = json.loads(escape_windows_paths(settings_text))

    if not isinstance(settings, dict):
        raise ValueError("settings.json must contain a JSON object.")

    values = DEFAULTS | settings
    for name in ("source", "metadata", "output"):
        value = values[name]
        if not isinstance(value, str):
            raise ValueError(f"Setting '{name}' must be a path string.")
        values[name] = Path(value).expanduser() if value.strip() else None

    if not isinstance(values["date_format"], str):
        raise ValueError("Setting 'date_format' must be a string.")

    output_date_format = values["output_date_format"]
    values["output_date_format"] = (
        output_date_format
        if is_valid_output_date_format(output_date_format)
        else None
    )

    output_format = values["output_format"]
    if isinstance(output_format, str):
        output_format = output_format.casefold().lstrip(".")
    values["output_format"] = (
        output_format if output_format in {"md", "txt"} else None
    )

    if not isinstance(values["confirm_before_processing"], bool):
        raise ValueError("Setting 'confirm_before_processing' must be true or false.")

    if values["missing_date_behavior"] not in {"missing", "conflict"}:
        raise ValueError(
            "Setting 'missing_date_behavior' must be 'missing' or 'conflict'."
        )

    return values
