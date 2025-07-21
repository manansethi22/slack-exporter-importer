# Slack Exporter & Importer

This project provides scripts to **export messages (and optionally files) from a Slack channel**, and to **import them into another Slack workspace**.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Setup](#setup)
- [Slack Exporter Usage](#slack-exporter-usage)
  - [Basic Export](#basic-export)
  - [Export With Files](#export-with-files)
  - [Export With Date Range](#export-with-date-range)
  - [Where Are Exported Files Saved?](#where-are-exported-files-saved)
- [Slack Importer Usage](#slack-importer-usage)
  - [Basic Import](#basic-import)
  - [Import Only File Links](#import-only-file-links)
  - [How to Specify File Paths](#how-to-specify-file-paths)
- [Environment Variables](#environment-variables)
- [Tips & Troubleshooting](#tips--troubleshooting)
- [Credits](#credits)

---

## Features

- Export all messages from a Slack channel.
- **Optionally download attached files** (if enabled in the exporter).
- Import messages into another Slack workspace/channel.
- **Import can post links to files** from the export (instead of uploading the files themselves).

---

## Requirements

- Python 3.7+
- `slack_sdk`
- `python-dotenv`
- `requests` (if downloading files)

Install dependencies with:

```bash
pip install slack_sdk python-dotenv requests
```

---

## Setup

1. **Clone this repository** and `cd` into it.
2. **Create a `.env` file** with the following variables:

   ```
   # For exporter (user token needed for file downloads)
   SLACK_USER_TOKEN=xoxp-your-slack-user-token-here

   # For importer (bot token for your destination workspace)
   SLACK_BOT_TOKEN=xoxb-your-bot-token-here
   ```

3. (Optional) Ensure your user/bot token has the required permissions for reading/writing messages and files on Slack.

---

## Slack Exporter Usage

### Basic Export

Export all messages from a channel:

```bash
python exporter.py -c --ch <CHANNEL_ID> -o ./exports --json
```

- `<CHANNEL_ID>`: Slack channel ID you want to export.

### Export With Files

To also export (download) files attached to messages:

```bash
python exporter.py -c --ch <CHANNEL_ID> --files -o ./exports --json
```

This will download attached files (if implemented in the exporter) to a `files/` directory within the export folder.

### Export With Date Range

Export messages **from a specific date** (e.g., last 1 day):

```bash
python exporter.py -c --ch <CHANNEL_ID> --files -o ./exports --json --fr $(date -v-1d +%s)
```

- `--fr <timestamp>`: Start date as Unix timestamp (seconds since epoch).

Export messages **between two dates**:

```bash
python exporter.py -c --ch <CHANNEL_ID> --files -o ./exports --json --fr <start_timestamp> --to <end_timestamp>
```

### Where Are Exported Files Saved?

- The **JSON export** will be saved in a subfolder like:
  ```
  ./exports/slack_export_<date_time_stamp>/channel_<CHANNEL_ID>.json
  ```
- **If you export files**, they will be saved in:
  ```
  ./exports/slack_export_<date_time_stamp>/files/
  ```

---

## Slack Importer Usage

### Basic Import

Import messages into a destination channel:

```bash
python slack_importer.py import /full/path/to/channel_<CHANNEL_ID>.json <DEST_CHANNEL_ID>
```

- First argument: Full path to your exported JSON file.
- Second argument: Destination channel ID in your new Slack workspace.

### Import Only File Links

If you exported **without files** (or don't want to upload files), the importer will **post file links** in the message using the `permalink` or `url_private` field.

### How to Specify File Paths

- Always give the **full path** to your exported JSON file, e.g.:
  ```
  /Users/youruser/Desktop/SlackExporter/slack-exporter/exports/slack_export_2025-07-21_192459/channel_C08MLV9BXNU.json
  ```
- Destination channel ID (e.g., `C097D4GP0KA`) is required.

---

## Environment Variables

- `SLACK_USER_TOKEN`: Required for exporting messages and downloading files (should have necessary scopes).
- `SLACK_BOT_TOKEN`: Required for importing messages into your destination workspace.

Set these in your `.env` file in the root directory.

---

## Tips & Troubleshooting

- Always check you have the correct permissions and tokens for each workspace.
- If you want to **import files as file links** (not uploading), use the provided `slack_importer.py`. If you want to actually upload files, you must first export them with the exporter and then use a different importer.
- For large exports/imports, Slack API rate limits may slow down the process. The importer waits 1 second between messages by default.
- To get your channel ID, you can use the exporter’s `list-channels` command or look at the URL in Slack.

---

## Credits

- [slack_sdk](https://github.com/slackapi/python-slack-sdk)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
