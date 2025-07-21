#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    HEADERS = {"Authorization": "Bearer %s" % os.environ["SLACK_USER_TOKEN"]}
except KeyError:
    print("Missing SLACK_USER_TOKEN in environment variables")
    exit(1)

def simple_test():
    # Test 1: Get channel info (single API call)
    print("Test 1: Getting channel info...")
    r1 = requests.get(
        "https://slack.com/api/conversations.info",
        headers=HEADERS,
        params={"channel": "C03UD84TRKP"}
    )
    print(f"Status: {r1.status_code}")
    if r1.status_code == 200:
        data = r1.json()
        if data.get("ok"):
            print(f"Channel name: {data['channel']['name']}")
        else:
            print(f"Error: {data.get('error')}")
    else:
        print(f"HTTP Error: {r1.status_code}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Get just a few messages (limit to 5)
    print("Test 2: Getting recent messages (limit 5)...")
    r2 = requests.get(
        "https://slack.com/api/conversations.history",
        headers=HEADERS,
        params={
            "channel": "C03UD84TRKP",
            "limit": 5
        }
    )
    print(f"Status: {r2.status_code}")
    if r2.status_code == 200:
        data = r2.json()
        if data.get("ok"):
            print(f"Found {len(data['messages'])} messages")
            print(f"Has more: {data.get('has_more', False)}")
        else:
            print(f"Error: {data.get('error')}")
    elif r2.status_code == 429:
        print(f"Rate limited! Retry-After: {r2.headers.get('Retry-After')} seconds")
    else:
        print(f"HTTP Error: {r2.status_code}")

if __name__ == "__main__":
    simple_test()