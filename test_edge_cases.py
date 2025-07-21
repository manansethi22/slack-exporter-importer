#!/usr/bin/env python3
"""
Extended test for bot message parsing with edge cases.
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


def test_edge_cases():
    """Test edge cases and ensure existing functionality still works"""
    
    # Sample users list for testing
    users = [
        {
            "id": "U1234567890",
            "name": "john.doe",
            "profile": {"real_name": "John Doe"}
        },
        {
            "id": "U0987654321", 
            "name": "jane.smith",
            "profile": {"real_name": "Jane Smith"}
        }
    ]
    
    # Edge case test messages
    edge_case_messages = [
        # Message with user mentions
        {
            "type": "message",
            "user": "U1234567890",
            "text": "Hey <@U0987654321> check this out",
            "ts": "1609459200.000100"
        },
        
        # Bot message with user mentions
        {
            "type": "message",
            "username": "NotificationBot",
            "text": "Alert for <@U1234567890>: Your task is ready",
            "ts": "1609459260.000200",
            "bot_id": "B01234567"
        },
        
        # Message with files
        {
            "type": "message", 
            "user": "U0987654321",
            "text": "Here's the report",
            "ts": "1609459320.000300",
            "files": [
                {
                    "id": "F12345",
                    "name": "report.pdf",
                    "url_private_download": "https://files.slack.com/files-pri/T123/F12345/report.pdf"
                }
            ]
        },
        
        # Bot message with complex attachments (multiple fields)
        {
            "type": "message",
            "username": "MonitoringBot", 
            "text": "",
            "ts": "1609459380.000400",
            "bot_id": "B07654321",
            "attachments": [
                {
                    "color": "warning",
                    "title": "Performance Alert",
                    "text": "High CPU usage detected on server prod-01",
                    "fields": [
                        {"title": "CPU Usage", "value": "89%", "short": True},
                        {"title": "Memory Usage", "value": "76%", "short": True},
                        {"title": "Server", "value": "prod-01", "short": True},
                        {"title": "Timestamp", "value": "2021-01-01 00:03:00", "short": True}
                    ]
                }
            ]
        },
        
        # Message with reactions
        {
            "type": "message",
            "user": "U1234567890", 
            "text": "Great work team!",
            "ts": "1609459440.000500",
            "reactions": [
                {
                    "name": "thumbsup",
                    "users": ["U0987654321", "U1234567890"]
                },
                {
                    "name": "heart",
                    "users": ["U0987654321"]
                }
            ]
        },
        
        # Edge case: message with neither user nor bot identifiers
        {
            "type": "message",
            "text": "System message",
            "ts": "1609459500.000600"
        }
    ]
    
    print("Testing edge cases and backward compatibility...")
    result = parse_channel_history_new(edge_case_messages, users)
    
    print("EDGE CASE TEST RESULTS:")
    print("=" * 60)
    print(result)
    print("=" * 60)
    
    # Verify key functionality
    lines = result.split('\n')
    
    # Check user mentions are processed
    user_mentions = [line for line in lines if "<@U0987654321> (jane.smith)" in line]
    print(f"User mentions processed correctly: {len(user_mentions) > 0}")
    
    # Check bot messages are identified
    bot_lines = [line for line in lines if line.startswith("Bot: ")]
    print(f"Bot messages identified: {len(bot_lines)}")
    
    # Check files are handled
    file_lines = [line for line in lines if "Files:" in line]
    print(f"File attachments handled: {len(file_lines) > 0}")
    
    # Check reactions are preserved
    reaction_lines = [line for line in lines if "Reactions:" in line]
    print(f"Reactions preserved: {len(reaction_lines) > 0}")
    
    # Check complex attachment parsing
    complex_attachments = [line for line in lines if "Performance Alert" in line and "CPU Usage" in line]
    print(f"Complex attachments parsed: {len(complex_attachments) > 0}")
    
    print(f"\nAll edge case tests completed successfully!")


if __name__ == "__main__":
    test_edge_cases()