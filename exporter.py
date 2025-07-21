#!/usr/bin/env python3
import os
import sys
import requests
import json
from timeit import default_timer
from datetime import datetime
import argparse
from dotenv import load_dotenv
from pathvalidate import sanitize_filename
from time import sleep

# when rate-limited, add this to the wait time
ADDITIONAL_SLEEP_TIME = 5  # Increased from 2 to 5 seconds

env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.isfile(env_file):
    load_dotenv(env_file)


# write handling


def post_response(response_url, text):
    requests.post(response_url, json={"text": text})


# use this to say anything
# will print to stdout if no response_url is given
# or post_response to given url if provided
def handle_print(text, response_url=None):
    if response_url is None:
        print(text)
    else:
        post_response(response_url, text)


# slack api (OAuth 2.0) now requires auth tokens in HTTP Authorization header
# instead of passing it as a query parameter
try:
    HEADERS = {"Authorization": "Bearer %s" % os.environ["SLACK_USER_TOKEN"]}
except KeyError:
    handle_print("Missing SLACK_USER_TOKEN in environment variables", response_url)
    sys.exit(1)


def _get_data(url, params):
    return requests.get(url, headers=HEADERS, params=params)


def get_data(url, params):
    """Enhanced rate-limiting handler with exponential backoff"""

    success = False
    attempt = 0
    base_sleep = 1  # Start with 1 second

    while not success:
        r = _get_data(url, params)
        attempt += 1
        
        # Debug: print what we're requesting
        print(f"API Request #{attempt} to: {url}")
        print(f"Status: {r.status_code}")
        
        # Print rate limit headers if available
        if 'X-RateLimit-Remaining' in r.headers:
            print(f"Rate limit remaining: {r.headers.get('X-RateLimit-Remaining')}")
        if 'X-RateLimit-Reset' in r.headers:
            print(f"Rate limit resets at: {r.headers.get('X-RateLimit-Reset')}")

        if r.status_code != 429:
            success = True
            # Add a small delay between successful requests to be gentle
            if attempt > 1:  # Only if we had to retry
                sleep(1)
        else:
            # Rate limited - use exponential backoff
            retry_after = int(r.headers.get("Retry-After", base_sleep * (2 ** (attempt - 1))))
            sleep_time = retry_after + ADDITIONAL_SLEEP_TIME
            print(f"Rate-limited on {url}. Retrying after {sleep_time} seconds (attempt {attempt}).")
            sleep(sleep_time)
            
            # Cap the exponential backoff at 60 seconds
            if base_sleep * (2 ** attempt) < 60:
                base_sleep = base_sleep * 2
            
    return r


# pagination handling


def get_at_cursor(url, params, cursor=None, response_url=None):
    if cursor is not None:
        params["cursor"] = cursor

    r = get_data(url, params)

    if r.status_code != 200:
        handle_print("ERROR: %s %s" % (r.status_code, r.reason), response_url)
        # Print response body for debugging
        try:
            error_data = r.json()
            handle_print(f"Error details: {error_data}", response_url)
        except:
            handle_print(f"Error response body: {r.text}", response_url)
        sys.exit(1)

    d = r.json()

    try:
        if d["ok"] is False:
            handle_print("I encountered an error: %s" % d, response_url)
            sys.exit(1)

        next_cursor = None
        if "response_metadata" in d and "next_cursor" in d["response_metadata"]:
            next_cursor = d["response_metadata"]["next_cursor"]
            if str(next_cursor).strip() == "":
                next_cursor = None

        return next_cursor, d

    except KeyError as e:
        handle_print("Something went wrong: %s." % e, response_url)
        return None, []


def paginated_get(url, params, combine_key=None, response_url=None):
    next_cursor = None
    result = []
    page = 1
    
    while True:
        print(f"Fetching page {page}...")
        next_cursor, data = get_at_cursor(
            url, params, cursor=next_cursor, response_url=response_url
        )

        try:
            new_items = data if combine_key is None else data[combine_key]
            result.extend(new_items)
            print(f"Page {page}: Got {len(new_items)} items (total: {len(result)})")
        except KeyError as e:
            handle_print("Something went wrong: %s." % e, response_url)
            sys.exit(1)

        if next_cursor is None:
            break
            
        page += 1
        # Add a small delay between pages to be gentle on the API
        sleep(1)

    print(f"Completed pagination: {len(result)} total items")
    return result


# GET requests


def channel_list(team_id=None, response_url=None):
    params = {
        "team_id": team_id,
        "types": "public_channel,private_channel",
        "limit": 100,  # Reduced from 200 to be more conservative
        "exclude_archived": True,  # Skip archived channels to reduce load
    }

    return paginated_get(
        "https://slack.com/api/conversations.list",
        params,
        combine_key="channels",
        response_url=response_url,
    )


def get_file_list():
    current_page = 1
    total_pages = 1
    while current_page <= total_pages:
        print(f"Fetching files page {current_page}/{total_pages}")
        response = get_data("https://slack.com/api/files.list", params={"page": current_page})
        json_data = response.json()
        total_pages = json_data["paging"]["pages"]
        for file in json_data["files"]:
            yield file
        current_page += 1


def channel_history(channel_id, response_url=None, oldest=None, latest=None):
    params = {
        "channel": channel_id,
        "limit": 100,  # Reduced from 200 to be more conservative
    }

    if oldest is not None:
        params["oldest"] = oldest
    if latest is not None:
        params["latest"] = latest

    print(f"Getting history for channel {channel_id}")
    return paginated_get(
        "https://slack.com/api/conversations.history",
        params,
        combine_key="messages",
        response_url=response_url,
    )


def user_list(team_id=None, response_url=None):
    params = {
        "limit": 100,  # Reduced from 200
        "team_id": team_id,
    }

    return paginated_get(
        "https://slack.com/api/users.list",
        params,
        combine_key="members",
        response_url=response_url,
    )


def channel_replies(timestamps, channel_id, response_url=None):
    replies = []
    total_threads = len(timestamps)
    
    for i, timestamp in enumerate(timestamps, 1):
        print(f"Getting thread {i}/{total_threads} (ts: {timestamp})")
        params = {
            "channel": channel_id,
            "ts": timestamp,
            "limit": 100,  # Reduced from 200
        }
        thread_replies = paginated_get(
            "https://slack.com/api/conversations.replies",
            params,
            combine_key="messages",
            response_url=response_url,
        )
        replies.append(thread_replies)
        
        # Add delay between thread requests
        if i < total_threads:  # Don't sleep after the last request
            sleep(1)

    return replies


# parsing functions


def parse_channel_list(channels, users):
    result = ""
    for channel in channels:
        ch_id = channel["id"]
        ch_name = channel["name"] if "name" in channel else ""
        ch_private = (
            "private " if "is_private" in channel and channel["is_private"] else ""
        )
        ch_type = "channel"
        
        if "creator" in channel:
            ch_ownership = "created by %s" % name_from_uid(channel["creator"], users)
        else:
            ch_ownership = ""
        ch_name = " %s:" % ch_name if ch_name.strip() != "" else ch_name
        result += "[%s]%s %s%s %s\n" % (
            ch_id,
            ch_name,
            ch_private,
            ch_type,
            ch_ownership,
        )

    return result


def name_from_uid(user_id, users, real=False):
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


def name_from_ch_id(channel_id, channels):
    for channel in channels:
        if channel["id"] == channel_id:
            return (channel["name"], "Channel")
    return "[null channel]"


def parse_user_list(users):
    result = ""
    for u in users:
        entry = "[%s]" % u["id"]

        try:
            entry += " %s" % u["name"]
        except KeyError:
            pass

        try:
            entry += " (%s)" % u["profile"]["real_name"]
        except KeyError:
            pass

        try:
            entry += ", %s" % u["tz"]
        except KeyError:
            pass

        u_type = ""
        if "is_admin" in u and u["is_admin"]:
            u_type += "admin|"
        if "is_owner" in u and u["is_owner"]:
            u_type += "owner|"
        if "is_primary_owner" in u and u["is_primary_owner"]:
            u_type += "primary_owner|"
        if "is_restricted" in u and u["is_restricted"]:
            u_type += "restricted|"
        if "is_ultra_restricted" in u and u["is_ultra_restricted"]:
            u_type += "ultra_restricted|"
        if "is_bot" in u and u["is_bot"]:
            u_type += "bot|"
        if "is_app_user" in u and u["is_app_user"]:
            u_type += "app_user|"

        if u_type.endswith("|"):
            u_type = u_type[:-1]

        entry += ", " if u_type.strip() != "" else ""
        entry += "%s\n" % u_type
        result += entry

    return result


def parse_channel_history(msgs, users, check_thread=False):
    if "messages" in msgs:
        msgs = msgs["messages"]

    messages = [x for x in msgs if x["type"] == "message"]
    body = ""
    for msg in messages:
        # Handle both user and bot messages
        if "user" in msg:
            usr = {
                "name": name_from_uid(msg["user"], users),
                "real_name": name_from_uid(msg["user"], users, real=True),
                "type": "user"
            }
        elif "bot_id" in msg or "username" in msg:
            # Handle bot messages
            bot_name = msg.get("username", msg.get("bot_id", "Bot"))
            usr = {
                "name": bot_name,
                "real_name": bot_name,
                "type": "bot"
            }
        else:
            usr = {"name": "Unknown", "real_name": "Unknown", "type": "unknown"}

        timestamp = datetime.fromtimestamp(round(float(msg["ts"]))).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        
        # Get message text, handle different message types
        text = ""
        if "text" in msg and msg["text"].strip():
            text = msg["text"]
        elif "attachments" in msg:
            # Handle bot messages with attachments (like your PetVM alerts)
            attachments = msg["attachments"]
            for att in attachments:
                if "text" in att:
                    text += att["text"] + "\n"
                if "title" in att:
                    text += f"Title: {att['title']}\n"
                if "fields" in att:
                    for field in att["fields"]:
                        title = field.get('title', '')
                        value = field.get('value', '')
                        text += f"{title}: {value}\n"
        
        if not text.strip():
            text = "[no message content]"

        # Replace user mentions
        for u in [x["id"] for x in users]:
            text = str(text).replace(
                "<@%s>" % u, "<@%s> (%s)" % (u, name_from_uid(u, users))
            )

        # Format the entry differently for bots vs users
        if usr["type"] == "bot":
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

        # Add reactions if present
        if "reactions" in msg:
            rxns = msg["reactions"]
            entry += "\nReactions: " + ", ".join(
                "%s (%s)"
                % (x["name"], ", ".join(name_from_uid(u, users) for u in x["users"]))
                for x in rxns
            )

        # Add files if present
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

        body += entry.rstrip("\t")

    return body


def parse_replies(threads, users):
    body = ""
    for thread in threads:
        body += parse_channel_history(thread, users, check_thread=True)
        body += "\n"

    return body


def download_file(destination_path, url, attempt=0):
    if os.path.exists(destination_path):
        print("Skipping existing %s" % destination_path)
        return True

    print(f"Downloading file on attempt {attempt} to {destination_path}")
        
    try:
        response = requests.get(url, headers=HEADERS)
        with open(destination_path, "wb") as fh:
            fh.write(response.content)
    except Exception as err:
        print(f"Unexpected error on {destination_path} attempt {attempt}; {err=}, {type(err)=}")
        return False
    else:
        return True


def save_files(file_dir):
    total = 0
    start = default_timer()
    for file_info in get_file_list():
        url = file_info["url_private"]
        file_info["name"] = sanitize_filename(file_info["name"])
        destination_filename = "{id}-{name}".format(**file_info)
        os.makedirs(file_dir, exist_ok=True)
        destination_path = os.path.join(file_dir, destination_filename)

        download_success = False
        attempt = 1
        while not download_success and attempt <= 10:
           download_success = download_file(destination_path, url, attempt)
           attempt += 1

        if not download_success:
            raise Exception("Failed to download from {url} after {attempt} tries")

        total += 1

    end = default_timer()
    seconds = int(end - start)
    print("Downloaded %i files in %i seconds" % (total, seconds))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o",
        help="Directory in which to save output files (if left blank, prints to stdout)",
    )
    parser.add_argument(
        "--lc", action="store_true", help="List all conversations in your workspace"
    )
    parser.add_argument(
        "--lu", action="store_true", help="List all users in your workspace"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Give the requested output in raw JSON format (no parsing)",
    )
    parser.add_argument(
        "-c", action="store_true", help="Get history for all accessible conversations"
    )
    parser.add_argument("--ch", help="With -c, restrict export to given channel ID")
    parser.add_argument(
        "--fr",
        help="With -c, Unix timestamp (seconds since Jan. 1, 1970) for earliest message",
        type=str,
    )
    parser.add_argument(
        "--to",
        help="With -c, Unix timestamp (seconds since Jan. 1, 1970) for latest message",
        type=str,
    )
    parser.add_argument(
        "-r",
        action="store_true",
        help="Get reply threads for all accessible conversations",
    )
    parser.add_argument(
        "--files",
        action="store_true",
        help="Download all files",
    )
    parser.add_argument(
        "--gentle",
        action="store_true",
        help="Use extra delays between requests to avoid rate limiting",
    )

    a = parser.parse_args()
    ts = str(datetime.strftime(datetime.now(), "%Y-%m-%d_%H%M%S"))
    sep_str = "*" * 24

    # Adjust sleep times if gentle mode is requested
    if a.gentle:
        ADDITIONAL_SLEEP_TIME = 10
        print("Gentle mode enabled: Using extra delays to avoid rate limiting")

    if a.o is None and a.files:
        print("If you specify --files you also need to specify an output directory with -o")
        sys.exit(1)

    if a.o is not None:
        out_dir_parent = os.path.abspath(
            os.path.expanduser(os.path.expandvars(a.o))
        )
        out_dir = os.path.join(out_dir_parent, "slack_export_%s" % ts)

    def save(data, filename):
        if a.o is None:
            json.dump(data, sys.stdout, indent=4)
        else:
            filename = filename + ".json" if a.json else filename + ".txt"
            os.makedirs(out_dir, exist_ok=True)
            full_filepath = os.path.join(out_dir, filename)
            print("Writing output to %s" % full_filepath)
            with open(full_filepath, mode="w", encoding="utf-8") as f:
                if a.json:
                    json.dump(data, f, indent=4)
                else:
                    f.write(data)

    def save_replies(channel_hist, channel_id, channel_list, users):
        reply_timestamps = [x["ts"] for x in channel_hist if "reply_count" in x]
        if reply_timestamps:
            print(f"Found {len(reply_timestamps)} threads in channel {channel_id}")
            ch_replies = channel_replies(reply_timestamps, channel_id)
            if a.json:
                data_replies = ch_replies
            else:
                ch_name, ch_type = name_from_ch_id(channel_id, channel_list)
                header_str = "Threads in %s: %s\n%s Messages" % (
                    ch_type,
                    ch_name,
                    len(ch_replies),
                )
                data_replies = parse_replies(ch_replies, users)
                data_replies = "%s\n%s\n\n%s" % (header_str, sep_str, data_replies)
            save(data_replies, "channel-replies_%s" % channel_id)
        else:
            print(f"No threads found in channel {channel_id}")

    def save_channel(channel_hist, channel_id, channel_list, users):
        if a.json:
            data_ch = channel_hist
        else:
            data_ch = parse_channel_history(channel_hist, users)
            ch_name, ch_type = name_from_ch_id(channel_id, channel_list)
            header_str = "%s Name: %s" % (ch_type, ch_name)
            data_ch = (
                "Channel ID: %s\n%s\n%s Messages\n%s\n\n"
                % (channel_id, header_str, len(channel_hist), sep_str)
                + data_ch
            )
        save(data_ch, "channel_%s" % channel_id)
        if a.r:
            save_replies(channel_hist, channel_id, channel_list, users)

    # Start the export process
    print("Starting Slack export...")
    print(f"Timestamp: {ts}")
    
    try:
        print("Getting channel list...")
        ch_list = channel_list()
        print("Getting user list...")
        user_list_data = user_list()

        if a.lc:
            data = ch_list if a.json else parse_channel_list(ch_list, user_list_data)
            save(data, "channel_list")
        if a.lu:
            data = user_list_data if a.json else parse_user_list(user_list_data)
            save(data, "user_list")
        if a.c:
            ch_id = a.ch
            if ch_id:
                print(f"Exporting single channel: {ch_id}")
                ch_hist = channel_history(ch_id, oldest=a.fr, latest=a.to)
                save_channel(ch_hist, ch_id, ch_list, user_list_data)
            else:
                print(f"Exporting all {len(ch_list)} channels...")
                for i, ch_info in enumerate(ch_list, 1):
                    ch_id = ch_info["id"]
                    ch_name = ch_info.get("name", "unknown")
                    print(f"\nChannel {i}/{len(ch_list)}: {ch_name} ({ch_id})")
                    ch_hist = channel_history(ch_id, oldest=a.fr, latest=a.to)
                    save_channel(ch_hist, ch_id, ch_list, user_list_data)
        elif a.r:
            print("Exporting reply threads for all channels...")
            for ch_info in ch_list:
                ch_id = ch_info["id"]
                ch_name = ch_info.get("name", "unknown")
                print(f"\nGetting threads for channel: {ch_name} ({ch_id})")
                ch_hist = channel_history(ch_id, oldest=a.fr, latest=a.to)
                save_replies(ch_hist, ch_id, ch_list, user_list_data)

        if a.files and a.o is not None:
            print("Downloading files...")
            save_files(out_dir)

        print("\nExport completed successfully!")
        
    except KeyboardInterrupt:
        print("\nExport interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during export: {e}")
        sys.exit(1)