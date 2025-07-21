import json
import os
import sys
import time
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def usage():
    print("Usage: python slack_importer.py import <json_file> <channel_id>")
    sys.exit(1)

def extract_message_text(msg):
    text = msg.get('text', '').strip()
    # Append file links if present
    if 'files' in msg and isinstance(msg['files'], list):
        for file_obj in msg['files']:
            # Use either permalink or url_private
            link = file_obj.get('permalink') or file_obj.get('url_private')
            if link:
                title = file_obj.get('title', file_obj.get('name', 'file'))
                text += f"\n<{link}|File: {title}>"
    return text

def import_messages(json_file_path, channel_id):
    try:
        with open(json_file_path, 'r') as f:
            messages = json.load(f)
    except Exception as e:
        print(f"❌ Failed to read JSON file: {e}")
        sys.exit(1)

    print(f"Loaded {len(messages)} messages from {json_file_path}")
    messages.sort(key=lambda x: float(x['ts']))
    for i, msg in enumerate(messages, 1):
        # Skip certain system messages
        if msg.get('type') != 'message' or msg.get('subtype') in ['message_deleted', 'channel_join', 'channel_leave']:
            continue
        text = extract_message_text(msg)
        if text.strip():
            try:
                client.chat_postMessage(
                    channel=channel_id,
                    text=text,
                    username="Import Bot",
                    icon_emoji=":inbox_tray:"
                )
                print(f"✅ Imported message {i}/{len(messages)}")
                time.sleep(1)
            except SlackApiError as e:
                print(f"❌ Failed to import message {i}: {e.response['error']}")
        else:
            print(f"⚠️ Skipped empty message {i}")

if __name__ == "__main__":
    load_dotenv()
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
    if not SLACK_BOT_TOKEN:
        print("Please set SLACK_BOT_TOKEN in your .env file")
        sys.exit(1)
    client = WebClient(token=SLACK_BOT_TOKEN)

    if len(sys.argv) < 4 or sys.argv[1] != "import":
        usage()

    json_file = sys.argv[2]
    channel_id = sys.argv[3]
    import_messages(json_file, channel_id)