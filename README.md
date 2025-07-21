# Slack Exporter & Importer

This project provides scripts to **export messages (and optionally files) from a Slack channel**, and to **import them into another Slack workspace**.

---

## How to Install

1. **Clone the repository** and navigate into the project folder:

   ```bash
   git clone <REPO_URL>
   cd <repo-folder>
   ```

2. **Create a Python virtual environment** (recommended):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # On macOS/Linux
   # .venv\Scripts\activate    # On Windows (CMD)
   # .venv\Scripts\Activate.ps1 # On Windows (PowerShell)
   ```

3. **Install required dependencies:**

   ```bash
   pip install slack_sdk python-dotenv requests
   ```

4. **Create a `.env` file** in the root directory and add:
   ```
   SLACK_USER_TOKEN=xoxp-your-slack-user-token-here
   SLACK_BOT_TOKEN=xoxb-your-bot-token-here
   SLACK_SIGNING_SECRET=your-signing-secret-here
   ```

---

## How to Run the Project

### 1. Export messages from a Slack channel

- **Export messages only:**

  ```bash
  python exporter.py -c --ch <CHANNEL_ID> -o ./exports --json
  ```

- **Export messages and download attached files:**

  ```bash
  python exporter.py -c --ch <CHANNEL_ID> --files -o ./exports --json
  ```

- **Export messages from a specific date (e.g., last 1 day):**

  ```bash
  python exporter.py -c --ch <CHANNEL_ID> --files -o ./exports --json --fr $(date -v-1d +%s)
  ```

  > On Linux, use:  
  > `--fr $(date -d '1 day ago' +%s)`

- **Export messages between two dates:**
  ```bash
  python exporter.py -c --ch <CHANNEL_ID> --files -o ./exports --json --fr <start_timestamp> --to <end_timestamp>
  ```

#### Output Location

After running the export, the exported JSON file will be saved at:

```
./exports/slack_export_<date_time_stamp>/channel_<CHANNEL_ID>.json
```

Example:

```
/Users/youruser/Desktop/SlackExporter/slack-exporter/exports/slack_export_2025-07-21_192459/channel_C08MLV9BXNU.json
```

If you export files, they will be saved in:

```
./exports/slack_export_<date_time_stamp>/files/
```

---

### 2. Import messages into another Slack workspace

- **Import messages (and post file links, not upload files):**
  ```bash
  python slack_importer.py import /full/path/to/channel_<CHANNEL_ID>.json <DEST_CHANNEL_ID>
  ```

Example:

```bash
python slack_importer.py import /Users/youruser/Desktop/SlackExporter/slack-exporter/exports/slack_export_2025-07-21_192459/channel_C08MLV9BXNU.json C097D4GP0KA
```

- The first argument is the full path to your exported JSON file.
- The second argument is the destination channel ID in your new Slack workspace.

---

## Additional Commands

- **Activate the Python virtual environment:**

  - macOS/Linux:
    ```bash
    source .venv/bin/activate
    ```
  - Windows (CMD):
    ```cmd
    .venv\Scripts\activate
    ```
  - Windows (PowerShell):
    ```powershell
    .venv\Scripts\Activate.ps1
    ```

- **Deactivate the virtual environment:**
  ```bash
  deactivate
  ```

---

## Additional Notes

- Make sure your `.env` file is properly configured with the correct tokens for both exporting and importing.
- The importer posts file links as part of the message, not as uploaded files.
- You must have the necessary permissions (scopes) on your Slack tokens for all operations.
- For large exports/imports, processing may take some time due to Slack API rate limits.

---
