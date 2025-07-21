#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()

try:
    HEADERS = {"Authorization": "Bearer %s" % os.environ["SLACK_USER_TOKEN"]}
except KeyError:
    print("Missing SLACK_USER_TOKEN in environment variables")
    exit(1)

def check_rate_limits():
    print("Checking current rate limit status...")
    
    # Make a simple API call to see rate limit headers
    r = requests.get(
        "https://slack.com/api/api.test",  # Simplest possible API call
        headers=HEADERS
    )
    
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.json()}")
    
    # Check rate limit headers
    print("\nRate Limit Headers:")
    for header_name in r.headers:
        if 'rate' in header_name.lower() or 'limit' in header_name.lower():
            print(f"{header_name}: {r.headers[header_name]}")
    
    if r.status_code == 429:
        retry_after = r.headers.get('Retry-After', 'Unknown')
        print(f"\n❌ Currently rate limited! Wait {retry_after} seconds")
    else:
        print(f"\n✅ Not currently rate limited")

if __name__ == "__main__":
    check_rate_limits()