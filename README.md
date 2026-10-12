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
2. Run `python\main.py`. Blank paths and unspecified settings, including output
   format (`md` or `txt`), are requested in the terminal.
3. Confirm the paths and start processing.

All user-editable options belong in `settings.json`; no Python files need to be
edited. Keep your local `settings.json` private; it is excluded from Git.

Converted notes and copied attachments are saved in the output folder.
Both formats include created and modified dates at the top of each converted
note.
The final summary reports metadata matches, mismatches, name conflicts, and the
total number of output files in the selected format.
Folders are retained when they contain images or nested folders; other folders
are flattened, regardless of their names.

## Missing Dates

Set `missing_date_behavior` in `settings.json` to:

- `missing` - write `missing date` in the file.
- `conflict` - also report missing or invalid dates in the processing report.

No external Python packages required.