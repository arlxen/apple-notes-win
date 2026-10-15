# Apple Notes Export Converter for Windows

A simple Python script to convert Apple Notes exports into Markdown or plain-text files.

Made for users who requested a copy of their data from Apple.

## Files Needed

- **Notes folder:** The `Notes` folder from your Apple data export. You can request your data on [Apple's official website](https://privacy.apple.com/). The bulk download option is convenient for exporting many notes.
- **Metadata CSV:** The CSV file containing note titles and timestamps. It must include these columns: `Title`, `Created On`, and `Modified On`.

The original creation and modification dates are added to each converted note.
Metadata titles are matched without punctuation or diacritic differences, with
unique truncated and near matches used as a fallback.

## Usage

1. Copy `settings.example.json` to `settings.json` in the project folder and edit it.
2. Run `python\main.py`.
3. Confirm the paths and start processing.

All user-editable options belong in `settings.json`; no Python files need to be
edited. Keep your local `settings.json` private; it is excluded from Git.

Set `missing_date_behavior` to `missing` to write `missing date`, or `conflict`
to also report missing or invalid dates.

`date_format` describes dates in the metadata CSV. `output_date_format` controls
how dates are written to converted notes; leave it blank to use the same format
as `date_format`. Both settings use Python `datetime` format codes, for example
`%Y-%m-%d %H:%M:%S` for `2026-10-15 09:51:38`.

Converted notes and copied attachments are saved in the output folder.
Both formats include created and modified dates at the top of each converted
note. Dates may be shared by multiple notes; when a modification date is
missing, the creation date is used instead.

The final summary reports metadata matches, mismatches, name conflicts, and the
total number of output files in the selected format.
Folders are retained when they contain images or nested folders; other folders
are flattened, regardless of their names.

No external Python packages required.