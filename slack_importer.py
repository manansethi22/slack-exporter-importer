#!/usr/bin/env python3
import json
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Use slack_sdk instead of slack_bolt for simple scripting
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
if not SLACK_BOT_TOKEN:
    print("Please set SLACK_BOT_TOKEN in your .env file")
    sys.exit(1)

client = WebClient(token=SLACK_BOT_TOKEN)

def list_channels():
    """List all channels in the workspace to help find target channel ID"""
    try:
        # List both public and private channels
        response = client.conversations_list(types="public_channel,private_channel", limit=1000)
        channels = response['channels']
        print("Available channels:")
        for channel in channels:
            print(f"  {channel['name']} - {channel['id']}")
    except SlackApiError as e:
        print(f"Error listing channels: {e.response['error']}")

def extract_message_text(msg):
    """Extracts text from Slack export message, including attachments/fields"""
    text = msg.get('text', '').strip()

    # If no text, try attachments (for bots)
    if not text and "attachments" in msg and isinstance(msg["attachments"], list):
        for att in msg["attachments"]:
            if "title" in att:
                text += f"*{att['title']}*\n"
            if "text" in att:
                text += f"{att['text']}\n"
            if "fields" in att:
                for field in att["fields"]:
                    title = field.get('title', '')
                    value = field.get('value', '')
                    text += f"{title}: {value}\n"
        text = text.strip()

    if not text:
        text = "[No content]"

    return text

def import_messages(json_file_path, target_channel_id):
    """Import messages from JSON file to Slack channel"""

    print(f"Loading messages from {json_file_path}")

    with open(json_file_path, 'r') as f:
        messages = json.load(f)

    print(f"Found {len(messages)} messages to import")

    imported_count = 0
    failed_count = 0

    # Sort messages by timestamp (oldest first)
    messages.sort(key=lambda x: float(x['ts']))

    for i, msg in enumerate(messages, 1):
        try:
            # Skip system messages and message deletions
            if msg.get('type') != 'message' or msg.get('subtype') in ['message_deleted', 'channel_join', 'channel_leave']:
                continue

            # Extract message text (handles attachments)
            text = extract_message_text(msg)

            # Add original timestamp and user info as context
            original_time = datetime.fromtimestamp(float(msg['ts'])).strftime('%Y-%m-%d %H:%M:%S')

            if 'user' in msg:
                user_info = f"Originally posted by user {msg['user']}"
            elif 'username' in msg:
                user_info = f"Originally posted by bot {msg['username']}"
            else:
                user_info = "Originally posted by unknown user"

            # Prepare the message with context
            # Only send the message content, as it appeared originally (no import header)
            import_text = text

            result = client.chat_postMessage(
                channel=target_channel_id,
                 text=import_text,
                username="Import Bot",
                icon_emoji=":inbox_tray:"
            )

            imported_count += 1
            print(f"✅ Imported message {i}/{len(messages)} (ts: {msg['ts']})")

            # Rate limiting - be gentle with Slack API
            time.sleep(1)  # 1 second between messages

        except SlackApiError as e:
            failed_count += 1
            print(f"❌ Failed to import message {i}: {e.response['error']}")
            continue
        except Exception as e:
            failed_count += 1
            print(f"❌ Failed to import message {i}: {str(e)}")
            continue

    print(f"\n📊 Import Summary:")
    print(f"   ✅ Successfully imported: {imported_count}")
    print(f"   ❌ Failed: {failed_count}")
    print(f"   📝 Total processed: {len(messages)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python slack_importer.py <command> [args]")
        print("Commands:")
        print("  list-channels                    - List all channels")
        print("  import <json_file> <channel_id>  - Import messages")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list-channels":
        list_channels()
    elif command == "import":
        if len(sys.argv) != 4:
            print("Usage: python slack_importer.py import <json_file> <channel_id>")
            sys.exit(1)

        json_file = sys.argv[2]
        channel_id = sys.argv[3]

        if not os.path.exists(json_file):
            print(f"Error: File {json_file} not found")
            sys.exit(1)

        import_messages(json_file, channel_id)
    else:
        print(f"Unknown command: {command}")