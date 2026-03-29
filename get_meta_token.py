"""
Get long-lived Page Access Token using a short-lived token you paste in.
Get the short-lived token from: https://developers.facebook.com/tools/explorer
"""
import requests
import sys
import config

APP_ID = config.META_APP_ID
APP_SECRET = config.META_APP_SECRET
PAGE_ID = config.FACEBOOK_PAGE_ID

short_token = input("Paste your token from Graph API Explorer here:\n> ").strip()

# Exchange for long-lived token
print("\nExchanging for long-lived token...")
r = requests.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
    "grant_type": "fb_exchange_token",
    "client_id": APP_ID,
    "client_secret": APP_SECRET,
    "fb_exchange_token": short_token,
})
data = r.json()
if "access_token" not in data:
    print(f"Error: {data}")
    sys.exit(1)

long_token = data["access_token"]
print("Got long-lived user token.")

# Get page token
print("Getting page token...")
r2 = requests.get("https://graph.facebook.com/v19.0/me/accounts", params={"access_token": long_token})
pages = r2.json()

if "data" not in pages:
    print(f"Error: {pages}")
    sys.exit(1)

page_token = None
for page in pages["data"]:
    print(f"  Page: {page.get('name')} (ID: {page.get('id')})")
    if page["id"] == PAGE_ID:
        page_token = page["access_token"]

if not page_token:
    print(f"\nPage {PAGE_ID} not found. Pages above are what was returned.")
    sys.exit(1)

# Get Instagram ID
r3 = requests.get(f"https://graph.facebook.com/v19.0/{PAGE_ID}", params={
    "fields": "instagram_business_account",
    "access_token": page_token
})
ig_id = r3.json().get("instagram_business_account", {}).get("id", "NOT_FOUND")

print("\n" + "="*60)
print("Add these to config.py:")
print("="*60)
print(f'\nFACEBOOK_PAGE_ACCESS_TOKEN = "{page_token}"')
print(f'\nINSTAGRAM_ACCOUNT_ID = "{ig_id}"')
print("="*60)
