# Slack Exporter & Importer

Easily export messages (including bot messages, attachments, and files) from a Slack workspace and import them into another workspace.

---

## Installation

1. **Clone this repository:**

   ```bash
   git clone https://github.com/yourusername/slack-exporter.git
   cd slack-exporter
   ```

2. **Create and activate a Python virtual environment:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   _(If you don't have `requirements.txt`, see the list at the end of this README.)_

4. **Create and configure your `.env` file:**
   - Copy the example or create a new `.env` file at the project root.
   - Set your Slack tokens:
     ```
     SLACK_USER_TOKEN=xoxp-...   # For exporting (see below)
     SLACK_BOT_TOKEN=xoxb-...    # For importing (see below)
     ```

---

## Exporting Messages & Files

### 1. List Channels and Users

To get a list of channels:

```bash
python exporter.py --lc
```

To get a list of users:

```bash
python exporter.py --lu
```

### 2. Export all messages from a channel

```bash
python exporter.py -c --ch <CHANNEL_ID> -o ./exports
```

Example:

```bash
python exporter.py -c --ch C03UD84TRKP -o ./exports
```

### 3. Export messages from the last N days

**For the last 1 day:**

```bash
python exporter.py -c --ch <CHANNEL_ID> -o ./exports --fr $(python -c "from datetime import datetime, timedelta; import time; print(int(time.mktime((datetime.now() - timedelta(days=1)).timetuple())))")
```

**For the last 7 days:**

```bash
python exporter.py -c --ch <CHANNEL_ID> -o ./exports --fr $(python -c "from datetime import datetime, timedelta; import time; print(int(time.mktime((datetime.now() - timedelta(days=7)).timetuple())))")
```

### 4. Export files from Slack

To download all files and attachments:

```bash
python exporter.py --files -o ./exports
```

### 5. Export raw JSON (Recommended for import)

```bash
python exporter.py -c --ch <CHANNEL_ID> -o ./exports --json
```

---

## Importing Messages

### 1. Prepare your Slack App for Import

- **Create a Slack App** in your _destination_ workspace with at least these scopes:
  - `chat:write`
  - `channels:read`
  - `groups:read`
- **Install the app** to your destination workspace.
- **Add your bot to the target channel** (in Slack: `/invite @YourBotName`).

### 2. Set up `.env` for Import:

Your `.env` must include:

```
SLACK_BOT_TOKEN=xoxb-...   # From your Slack App (destination workspace)
```

### 3. List channels in your destination workspace

```bash
python slack_importer.py list-channels
```

_Copy the channel ID for your import._

### 4. Import messages

```bash
python slack_importer.py import ./exports/slack_export_*/channel_<CHANNEL_ID>.json <DEST_CHANNEL_ID>
```

Example:

```bash
python slack_importer.py import ./exports/slack_export_2025-07-21_154237/channel_C03UD84TRKP.json C097D4GP0KA
```

---

## Tips & Notes

- **Bot Messages and Attachments:** This tool preserves bot message content, including structured attachments (fields, titles, etc.).
- **Files:** Exporter will download files if you use the `--files` option, but importer does not automatically upload files.
- **Rate Limits:** Both export and import scripts handle Slack API rate limits, but for large imports, consider waiting between runs.
- **Headers:** By default, the importer only posts the original message content (no extra import header).
- **Customization:** Edit the scripts as needed for more advanced formatting.

---

## Requirements

If you need to create a `requirements.txt`:

```
slack-sdk
requests
python-dotenv
pathvalidate
```

_(Optional: If you use slack_bolt for other scripts, add `slack-bolt`)_

---

## License

MIT

---

## Contact

For questions or improvements, open an issue or pull request!
