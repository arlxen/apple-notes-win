import json
from pathlib import Path


IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".heic", ".heif", ".tif", ".tiff", ".bmp",
}

DEFAULTS = {
    "source": "",
    "metadata": "",
    "output": "",
    "date_format": "%m-%d-%Y %H:%M:%S",
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

    with path.open(encoding="utf-8") as file:
        settings = json.load(file)

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
