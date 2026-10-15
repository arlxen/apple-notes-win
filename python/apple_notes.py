import csv
import difflib
import re
import shutil
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from app_settings import IMAGE_EXTENSIONS


def normalize(value):
    value = unicodedata.normalize("NFKC", (value or "").strip()).casefold()
    return re.sub(r"\s+", " ", value)


def search_key(value):
    value = unicodedata.normalize("NFKD", normalize(value))
    return "".join(char for char in value if char.isalnum())


def search_tokens(value):
    tokens = (
        search_key(token)
        for token in re.findall(r"[^\W_]+", normalize(value))
    )
    return tuple(sorted({token for token in tokens if token}))


def find_metadata_matches(title, metadata, metadata_search):
    normalized = normalize(title)
    if normalized in metadata:
        return metadata[normalized]

    key = search_key(title)
    prefixes = [
        (candidate, candidate_key)
        for candidate, candidate_key, _ in metadata_search
        if min(len(key), len(candidate_key)) >= 12
        and (key.startswith(candidate_key) or candidate_key.startswith(key))
    ]
    if len(prefixes) == 1:
        return metadata[prefixes[0][0]]
    if prefixes or len(key) < 8:
        return []

    tokens = search_tokens(title)
    ranked = sorted(
        (
            score_metadata_match(
                key, tokens, candidate_key, candidate_tokens, candidate
            )
            for candidate, candidate_key, candidate_tokens in metadata_search
        ),
        reverse=True,
    )
    if (
        ranked
        and ranked[0][0] >= 0.78
        and ranked[0][1]
        and (len(ranked) == 1 or ranked[0][0] - ranked[1][0] >= 0.08)
    ):
        return metadata[ranked[0][2]]
    return []


def score_metadata_match(key, tokens, candidate_key, candidate_tokens, candidate):
    ratio = difflib.SequenceMatcher(None, key, candidate_key).ratio()
    shorter, longer = sorted((key, candidate_key), key=len)
    partial = (
        difflib.SequenceMatcher(None, shorter, longer).find_longest_match().size
        / len(shorter)
        if len(shorter) >= 12
        else 0
    )

    shared_tokens = set(tokens) & set(candidate_tokens)
    token_cover = (
        len(shared_tokens) / min(len(tokens), len(candidate_tokens))
        if tokens and candidate_tokens
        else 0
    )
    token_scores = [
        max(
            (
                difflib.SequenceMatcher(None, token, candidate_token).ratio()
                for candidate_token in candidate_tokens
            ),
            default=0,
        )
        for token in tokens
    ]
    fuzzy_cover = (
        sum(score for score in token_scores if score >= 0.84) / len(tokens)
        if tokens
        else 0
    )
    fuzzy_token_count = sum(score >= 0.84 for score in token_scores)
    token_match = (
        max(token_cover, fuzzy_cover) >= 0.8
        and (len(shared_tokens) >= 3 or (
            len(shared_tokens) >= 2
            and any(len(token) >= 6 for token in shared_tokens)
        ) or (
            fuzzy_token_count >= 2
            and any(len(token) >= 6 for token in tokens)
        ) or (
            fuzzy_token_count == 1
            and any(len(token) >= 12 for token in tokens)
        )
    ))
    token_score = max(token_cover, fuzzy_cover) if token_match else 0
    score = max(ratio, partial, token_score)
    return score, score >= 0.88 or token_match, candidate


def is_txt_file(path):
    return path.name.rstrip(" .").casefold().endswith(".txt")


def read_metadata(path):
    records = defaultdict(list)

    for encoding in ("utf-8-sig", "cp1252", "utf-16"):
        try:
            with path.open(encoding=encoding, newline="") as f:
                sample = f.read(8192)
                f.seek(0)

                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
                except csv.Error:
                    dialect = csv.excel

                def parse_row(line):
                    try:
                        return next(csv.reader(
                            [line],
                            dialect=dialect,
                            strict=True,
                        ))
                    except csv.Error:
                        return next(csv.reader(
                            [line],
                            dialect=dialect,
                            quoting=csv.QUOTE_NONE,
                        ))

                fieldnames = parse_row(f.readline())
                if fieldnames:
                    fieldnames = [
                        (name or "").strip().lstrip("\ufeff")
                        for name in fieldnames
                    ]

                required = {"Title", "Created On", "Modified On"}
                if not required.issubset(fieldnames or []):
                    raise ValueError(
                        f"Expected columns: {sorted(required)}; "
                        f"found: {fieldnames}"
                    )

                for line in f:
                    values = parse_row(line)
                    if not values:
                        continue

                    extra_fields = max(0, len(values) - len(fieldnames))
                    if extra_fields:
                        values = [
                            ",".join(values[:extra_fields + 1]),
                            *values[extra_fields + 1:],
                        ]
                    values = (values + [""] * len(fieldnames))[:len(fieldnames)]
                    row = {
                        name: (value or "").strip()
                        for name, value in zip(fieldnames, values)
                    }

                    if row.get("Title"):
                        records[normalize(row["Title"])].append({
                            "created": row.get("Created On", ""),
                            "modified": row.get("Modified On", ""),
                        })

            return records

        except UnicodeError:
            continue

    raise ValueError(f"Cannot decode metadata file: {path.name}")


def parse_date(value, date_format):
    try:
        return datetime.strptime(value, date_format)
    except (ValueError, TypeError):
        return None


def yaml_quote(value):
    value = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return '"' + value.replace("\r", "\\r").replace("\n", "\\n") + '"'


def unique_path(path, issues):
    if not path.exists():
        return path

    issues.append(f"Name conflict: {path.name}")
    index = 2

    while True:
        candidate = path.with_name(
            f"{path.stem} ({index}){path.suffix}"
        )
        if not candidate.exists():
            return candidate
        index += 1


def read_text_file(path, issues):
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeError:
            continue

    issues.append(f"Unreadable text: {path.name}")
    return path.read_text(encoding="utf-8", errors="replace")


def process(
    source,
    metadata_csv,
    output,
    date_format="%Y-%m-%d",
    output_format="md",
    missing_date_behavior="missing",
    output_date_format=None,
):
    output_format = str(output_format).strip().casefold().lstrip(".")
    if output_format not in {"md", "txt"}:
        raise ValueError("OUTPUT_FORMAT must be 'md' or 'txt'.")
    if output_date_format is None:
        output_date_format = date_format

    source, metadata_csv, output = (
        Path(p).resolve() for p in (source, metadata_csv, output)
    )

    if not source.is_dir():
        raise FileNotFoundError(f"Source folder not found: {source}")
    if not metadata_csv.is_file():
        raise FileNotFoundError(f"Metadata CSV not found: {metadata_csv}")
    if output == source or source in output.parents:
        raise ValueError("Output cannot be inside the source folder.")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output folder is not empty: {output}")

    metadata = read_metadata(metadata_csv)
    metadata_search = [
        (key, search_key(key), search_tokens(key))
        for key in metadata
    ]
    output.mkdir(parents=True, exist_ok=True)

    issues = []
    converted = 0
    matched = 0
    mismatches = 0

    def resolve_dates(matches, title):
        dates = {"created": [], "modified": []}

        for item in matches:
            for field in dates:
                value = item[field]
                parsed = parse_date(value, date_format)

                if parsed:
                    dates[field].append((parsed, value))
                elif value:
                    issues.append(f"Invalid {field} date: {title}")

        result = []

        for field in ("created", "modified"):
            values = dates[field]

            if values:
                selected = (
                    min(values, key=lambda x: x[0])
                    if field == "created"
                    else max(values, key=lambda x: x[0])
                )
                result.append(selected[0].strftime(output_date_format))
            elif field == "modified" and result[0] != "missing date":
                result.append(result[0])
            else:
                result.append("missing date")

                if missing_date_behavior == "conflict":
                    issues.append(f"Missing {field} date: {title}")

        return result

    def convert(src, dest):
        nonlocal converted, matched, mismatches

        matches = find_metadata_matches(src.stem, metadata, metadata_search)

        if matches:
            matched += 1
            created, modified = resolve_dates(matches, src.name)
        else:
            mismatches += 1
            created = modified = "missing date"

            if missing_date_behavior == "conflict":
                issues.append(f"No metadata match: {src.name}")

        content = read_text_file(src, issues)

        if output_format == "md":
            text = (
                "---\n"
                f"created: {yaml_quote(created)}\n"
                f"modified: {yaml_quote(modified)}\n"
                "---\n\n"
                + content
            )
        else:
            text = (
                f"created: {created}\n"
                f"modified: {modified}\n\n"
                + content
            )

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest = unique_path(dest, issues)
        dest.write_text(text, encoding="utf-8")
        converted += 1

    def copy_file(src, folder):
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, unique_path(folder / src.name, issues))

    def report_unknown(path):
        suffix = path.suffix.casefold()

        if suffix != ".md" and suffix not in IMAGE_EXTENSIONS:
            issues.append(f"Unrecognized file: {path.name}")

    def walk(folder, parent):
        entries = list(folder.iterdir())

        subdirs = sorted(
            (p for p in entries if p.is_dir()),
            key=lambda p: p.name.casefold(),
        )
        txt_files = sorted(
            (p for p in entries if p.is_file() and is_txt_file(p)),
            key=lambda p: p.name.casefold(),
        )
        images = [
            p for p in entries
            if p.is_file()
            and p.suffix.casefold() in IMAGE_EXTENSIONS
        ]

        target = parent if not images and not subdirs else parent / folder.name

        for txt in txt_files:
            name = txt.name.rstrip(" .")[:-4] + f".{output_format}"
            convert(txt, target / name)

        for entry in entries:
            if entry.is_file() and not is_txt_file(entry):
                copy_file(entry, target)
                report_unknown(entry)

        for subdir in subdirs:
            walk(subdir, target)

        if subdirs:
            target.mkdir(parents=True, exist_ok=True)

    for item in sorted(source.iterdir(), key=lambda p: p.name.casefold()):
        if item.is_dir():
            walk(item, output)
        elif item.is_file() and is_txt_file(item):
            convert(
                item,
                output / (
                    item.name.rstrip(" .")[:-4] + f".{output_format}"
                ),
            )
        elif item.is_file():
            copy_file(item, output)
            report_unknown(item)

    if issues:
        report_path = output / "processing_report.csv"

        with report_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Issue"])
            writer.writerows([[issue] for issue in issues])

        print(f"Report: {report_path}")

    return {
        "converted": converted,
        "issues": len(issues),
        "matched": matched,
        "mismatches": mismatches,
        "conflicts": sum(issue.startswith("Name conflict:") for issue in issues),
        "output": output,
    }
