from pathlib import Path

from app_settings import load_settings
from apple_notes import process
from verify import verify


def ask_path(label, configured, kind):
    while True:
        path = Path(configured).expanduser() if configured else None

        if path:
            valid = path_is_valid(path, kind)
            if valid:
                return path

            if kind == "output" and path.is_dir():
                print(
                    f"\nConfigured {label} folder is not empty. "
                    "Choose a different folder:\n  {path}"
                )
            else:
                print(f"\nConfigured {label} is missing or invalid:\n  {path}")

        entered = input(f"Enter {label} path: ").strip().strip('"')

        if not entered:
            configured = None
            continue

        path = Path(entered).expanduser()
        if path_is_valid(path, kind):
            return path

        if kind == "output" and path.is_dir():
            print("Output folder is not empty. Choose a different folder.")
            configured = None
            continue

        print("That path does not exist or has the wrong type.")
        configured = None


def path_is_valid(path, kind):
    if kind == "dir":
        return path.is_dir()
    if kind == "file":
        return path.is_file()
    if kind == "output":
        return not path.exists() or (
            path.is_dir() and not any(path.iterdir())
        )
    return True


def ask_output_format(configured):
    if configured:
        return configured

    while True:
        output_format = input("Output format (md/txt): ").strip().casefold().lstrip(".")
        if output_format in {"md", "txt"}:
            return output_format
        print("Enter 'md' for Markdown or 'txt' for plain text.")


def main():
    settings = load_settings()
    source = ask_path("Source", settings["source"], "dir")
    metadata = ask_path("Metadata", settings["metadata"], "file")
    output = ask_path("Output", settings["output"], "output")
    output_format = ask_output_format(settings["output_format"])

    if output.resolve() == source.resolve():
        raise ValueError("Output cannot be the source folder.")

    if settings["confirm_before_processing"]:
        print(f"\nSource:   {source}")
        print(f"Metadata: {metadata}")
        print(f"Output:   {output}")

        if input("\nStart processing? [y/N] ").strip().lower() != "y":
            print("Cancelled.")
            return

    result = process(
        source,
        metadata,
        output,
        settings["date_format"],
        output_format,
        settings["missing_date_behavior"],
    )
    file_count = verify(output, output_format)
    extension = f".{output_format}"
    print(
        f"Converted: {result['converted']} | "
        f"Matched: {result['matched']} | "
        f"Mismatches: {result['mismatches']} | "
        f"Conflicts: {result['conflicts']} | "
        f"Total {extension} files: {file_count}"
    )


if __name__ == "__main__":
    main()
