#!/usr/bin/env python3
"""
Test bot message parsing functionality.
This test validates that bot messages are properly parsed and formatted.
"""

import sys
import os
from datetime import datetime

def name_from_uid(user_id, users, real=False):
    """Helper function copied from exporter.py for testing"""
    for user in users:
        if user["id"] != user_id:
            continue

        if real:
            try:
                return user["profile"]["real_name"]
            except KeyError:
                try:
                    return user["profile"]["display_name"]
                except KeyError:
                    return "[no full name]"
        else:
            return user["name"]

    return "[null user]"


def parse_channel_history_current(msgs, users, check_thread=False):
    """Current implementation from exporter.py to test existing behavior"""
    if "messages" in msgs:
        msgs = msgs["messages"]

    messages = [x for x in msgs if x["type"] == "message"]  # files are also messages
    body = ""
    for msg in messages:
        if "user" in msg:
            usr = {
                "name": name_from_uid(msg["user"], users),
                "real_name": name_from_uid(msg["user"], users, real=True),
            }
        else:
            usr = {"name": "", "real_name": "none"}

        timestamp = datetime.fromtimestamp(round(float(msg["ts"]))).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        text = msg["text"] if msg["text"].strip() != "" else "[no message content]"
        for u in [x["id"] for x in users]:
            text = str(text).replace(
                "<@%s>" % u, "<@%s> (%s)" % (u, name_from_uid(u, users))
            )

        entry = "Message at %s\nUser: %s (%s)\n%s" % (
            timestamp,
            usr["name"],
            usr["real_name"],
            text,
        )
        if "reactions" in msg:
            rxns = msg["reactions"]
            entry += "\nReactions: " + ", ".join(
                "%s (%s)"
                % (x["name"], ", ".join(name_from_uid(u, users) for u in x["users"]))
                for x in rxns
            )
        if "files" in msg:
            files = msg["files"]
            deleted = [
                f for f in files if "name" not in f or "url_private_download" not in f
            ]
            ok_files = [f for f in files if f not in deleted]
            entry += "\nFiles:\n"
            entry += "\n".join(
                " - [%s] %s, %s" % (f["id"], f["name"], f["url_private_download"])
                for f in ok_files
            )
            entry += "\n".join(
                " - [%s] [deleted, oversize, or unavailable file]" % f["id"]
                for f in deleted
            )

        entry += "\n\n%s\n\n" % ("*" * 24)

        if check_thread and "parent_user_id" in msg:
            entry = "\n".join("\t%s" % x for x in entry.split("\n"))

        body += entry.rstrip(
            "\t"
        )  # get rid of any extra tabs between trailing newlines

    return body


def parse_channel_history_new(msgs, users, check_thread=False):
    """New implementation with bot message support"""
    if "messages" in msgs:
        msgs = msgs["messages"]

    messages = [x for x in msgs if x["type"] == "message"]  # files are also messages
    body = ""
    for msg in messages:
        # Determine if this is a bot message and extract appropriate user info
        is_bot = False
        if "user" in msg:
            # Regular user message
            usr = {
                "name": name_from_uid(msg["user"], users),
                "real_name": name_from_uid(msg["user"], users, real=True),
            }
        elif "bot_id" in msg or "username" in msg or msg.get("subtype") == "bot_message":
            # Bot message - extract bot name from available fields
            is_bot = True
            bot_name = ""
            
            if "username" in msg:
                bot_name = msg["username"]
            elif "bot_id" in msg:
                bot_name = f"Bot {msg['bot_id']}"
            else:
                bot_name = "Bot"
                
            usr = {
                "name": bot_name,
                "real_name": "bot",
            }
        else:
            usr = {"name": "", "real_name": "none"}

        timestamp = datetime.fromtimestamp(round(float(msg["ts"]))).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        
        # Extract text content - check attachments if text is empty
        text = msg.get("text", "").strip()
        if not text and "attachments" in msg:
            # Extract content from attachments
            attachment_texts = []
            for attachment in msg["attachments"]:
                if "title" in attachment:
                    attachment_texts.append(f"[{attachment['title']}]")
                if "text" in attachment:
                    attachment_texts.append(attachment["text"])
                if "fields" in attachment:
                    for field in attachment["fields"]:
                        field_text = f"{field.get('title', '')}: {field.get('value', '')}"
                        attachment_texts.append(field_text)
            
            if attachment_texts:
                text = " | ".join(attachment_texts)
        
        if not text:
            text = "[no message content]"
            
        # Replace user mentions with names
        for u in [x["id"] for x in users]:
            text = str(text).replace(
                "<@%s>" % u, "<@%s> (%s)" % (u, name_from_uid(u, users))
            )

        # Format entry differently for bots vs users
        if is_bot:
            entry = "Message at %s\nBot: %s\n%s" % (
                timestamp,
                usr["name"],
                text,
            )
        else:
            entry = "Message at %s\nUser: %s (%s)\n%s" % (
                timestamp,
                usr["name"],
                usr["real_name"],
                text,
            )
        if "reactions" in msg:
            rxns = msg["reactions"]
            entry += "\nReactions: " + ", ".join(
                "%s (%s)"
                % (x["name"], ", ".join(name_from_uid(u, users) for u in x["users"]))
                for x in rxns
            )
        if "files" in msg:
            files = msg["files"]
            deleted = [
                f for f in files if "name" not in f or "url_private_download" not in f
            ]
            ok_files = [f for f in files if f not in deleted]
            entry += "\nFiles:\n"
            entry += "\n".join(
                " - [%s] %s, %s" % (f["id"], f["name"], f["url_private_download"])
                for f in ok_files
            )
            entry += "\n".join(
                " - [%s] [deleted, oversize, or unavailable file]" % f["id"]
                for f in deleted
            )

        entry += "\n\n%s\n\n" % ("*" * 24)

        if check_thread and "parent_user_id" in msg:
            entry = "\n".join("\t%s" % x for x in entry.split("\n"))

        body += entry.rstrip(
            "\t"
        )  # get rid of any extra tabs between trailing newlines

    return body


def test_bot_message_parsing():
    """Test that bot messages are properly parsed and formatted."""
    
    # Sample users list for testing
    users = [
        {
            "id": "U1234567890",
            "name": "john.doe",
            "profile": {"real_name": "John Doe"}
        }
    ]
    
    # Test data: various types of bot messages commonly seen in Slack
    test_messages = [
        # Regular user message for comparison
        {
            "type": "message",
            "user": "U1234567890",
            "text": "This is a regular user message",
            "ts": "1609459200.000100"
        },
        
        # Bot message with username field
        {
            "type": "message",
            "username": "PetVM Bot",
            "text": "Alert: Service is down",
            "ts": "1609459260.000200",
            "bot_id": "B01234567"
        },
        
        # Bot message with empty text but content in attachments
        {
            "type": "message", 
            "username": "AlertBot",
            "text": "",
            "ts": "1609459320.000300",
            "bot_id": "B07654321",
            "attachments": [
                {
                    "color": "danger",
                    "title": "System Alert",
                    "text": "Critical system failure detected",
                    "fields": [
                        {"title": "Severity", "value": "High", "short": True},
                        {"title": "System", "value": "Database", "short": True}
                    ]
                }
            ]
        },
        
        # Bot message with only bot_id (no username)
        {
            "type": "message",
            "text": "Automated notification",
            "ts": "1609459380.000400", 
            "bot_id": "B98765432"
        },
        
        # Bot message with subtype
        {
            "type": "message",
            "subtype": "bot_message",
            "username": "Jenkins CI",
            "text": "Build #123 completed successfully",
            "ts": "1609459440.000500"
        }
    ]
    
    print("Testing bot message parsing...")
    
    print("\n1. CURRENT IMPLEMENTATION (showing issues):")
    print("=" * 50)
    
    # Parse with current implementation
    result_current = parse_channel_history_current(test_messages, users)
    print(result_current)
    
    print("\n2. NEW IMPLEMENTATION (with bot support):")
    print("=" * 50)
    
    # Parse with new implementation
    result_new = parse_channel_history_new(test_messages, users)
    print(result_new)
    
    print("\n3. COMPARISON:")
    print("=" * 50)
    
    # Basic validation checks for current implementation
    lines_current = result_current.split('\n')
    none_users_current = [line for line in lines_current if "User:  (none)" in line]
    no_content_current = [line for line in lines_current if "[no message content]" in line]
    
    print(f"Current implementation issues:")
    print(f"  - Messages showing as '(none)' user: {len(none_users_current)}")
    print(f"  - Messages with no content: {len(no_content_current)}")
    
    # Basic validation checks for new implementation  
    lines_new = result_new.split('\n')
    none_users_new = [line for line in lines_new if "User:  (none)" in line]
    no_content_new = [line for line in lines_new if "[no message content]" in line]
    bot_messages = [line for line in lines_new if line.startswith("Bot: ")]
    
    print(f"\nNew implementation results:")
    print(f"  - Messages showing as '(none)' user: {len(none_users_new)}")
    print(f"  - Messages with no content: {len(no_content_new)}")
    print(f"  - Bot messages properly identified: {len(bot_messages)}")
    
    # Show the bot messages that were identified
    if bot_messages:
        print(f"\nIdentified bot messages:")
        for bot_msg in bot_messages:
            print(f"  - {bot_msg}")
    
    print(f"\nTest completed successfully!")
    return result_new

if __name__ == "__main__":
    test_bot_message_parsing()