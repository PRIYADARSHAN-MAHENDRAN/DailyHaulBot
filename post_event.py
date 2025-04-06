import os
import gspread
import requests
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from pytz import timezone, utc
from datetime import timedelta
# === Config ===
ROLE_ID = "1356018983496843294"  # Replace with your actual Discord role ID
content = f"<@&{ROLE_ID}>"

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('truckersmp-events-ef7e395df282.json', scope)
client = gspread.authorize(credentials)

SHEET_ID = '1jTadn8TtRP4ip5ayN-UClntNmKDTGY70wdPgo7I7lRY'
DISCORD_WEBHOOK = 'https://discord.com/api/webhooks/1358492482580779119/o4-NQuKr1zsUb9rUZsB_EnlYNiZwb_N8uXNfxfIRiGsdR8kh4CoKliIlSb8qot-F0HHO'

# === Time Setup ===
tz_ist = timezone('Asia/Kolkata')
today = datetime.now(tz_ist).date()
month_name = today.strftime("%B %Y")  # e.g., "April 2025"

# === Load Sheet & All Worksheets ===
spreadsheet = client.open_by_key(SHEET_ID)
worksheets = spreadsheet.worksheets()

todays_event_link = None

def parse_flexible_date(date_str):
    from datetime import datetime

    date_formats = [
        "%A, %B %d, %Y %H.%M",  # Saturday, April 05, 2025 22.30
        "%a, %b %d, %Y %H.%M",  # Wed, Apr 2, 2025 22.30
        "%A, %B %d, %Y",        # Saturday, April 05, 2025
        "%a, %b %d, %Y",        # Wed, Apr 2, 2025
        "%d/%m/%Y",             # 26/4/2025
        "%d-%m-%Y"              # fallback to your original format
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None  # If all formats fail

# === Loop through all sheets and rows ===
event_links_today = []

for sheet in worksheets:
    print(f"🔍 Checking sheet: {sheet.title}")
    data = sheet.get_all_values()
    
    for row in data:
        if len(row) >= 13 and row[12].strip().startswith("https://truckersmp.com/events"):
            raw_date = row[2].strip()
            event_date = parse_flexible_date(raw_date)

            if event_date == today:
                event_url = row[12].strip()
                print(f"✅ Found event for today in '{sheet.title}': {event_url}")
                event_links_today.append(event_url)

if not event_links_today:
    print("❌ No events found for today.")
    exit(0)

# === Extract Event ID ===
# === Get Public Event IDs ===
public_events_res = requests.get("https://api.truckersmp.com/v2/events")
if public_events_res.status_code != 200:
    print("❌ Failed to fetch public events.")
    exit(1)

try:
    public_json = public_events_res.json()
    response_data = public_json.get("response", {})
    public_event_ids = []

    for category in response_data.values():
        if isinstance(category, list):
            for event in category:
                public_event_ids.append(str(event["id"]))
except Exception as e:
    print(f"❌ Failed to parse public event list: {e}")
    exit(1)
# === Helpers ===
def utc_to_ist(utc_str):
    try:
        dt_utc = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S")
        dt_ist = dt_utc + timedelta(hours=5, minutes=30)
        return dt_ist.strftime("%H:%M")
    except Exception as e:
        print(f"Error converting UTC to IST: {e}")
        return "N/A"

def format_date(utc_str):
    try:
        dt = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d-%m-%Y")
    except Exception as e:
        print(f"Error formatting date: {e}")
        return "N/A"
# === DLC ID to Name Mapping ===
DLC_ID_MAP = {
    304212: "Going East!",
    304213: "Scandinavia",
    304215: "Vive la France!",
    304216: "Italia",
    304217: "Beyond the Baltic Sea",
    304218: "Road to the Black Sea",
    304219: "Iberia",
    304220: "West Balkans",
    461910: "Heavy Cargo Pack",
    558244: "Special Transport",
    258666: "High Power Cargo Pack",
    620610: "Krone Trailer Pack",
    388470: "Cabin Accessories",
    297721: "Wheel Tuning Pack",
    645630: "Schwarzmüller Trailer Pack",
}


def get_dlc_names(dlc_ids):
    if not dlc_ids:
        return "Base Map"
    return ", ".join(DLC_ID_MAP.get(dlc_id, f"Unknown ({dlc_id})") for dlc_id in dlc_ids)

# === Loop Through All Event Links ===
for event_link in event_links_today:
    event_id = event_link.strip('/').split('/')[-1]
    
    if event_id not in public_event_ids:
        print(f"⚠️ Event {event_id} is not public. Skipping.")
        continue

    response = requests.get(f"https://api.truckersmp.com/v2/events/{event_id}")
    if response.status_code != 200:
        print(f"❌ Failed to fetch data for event {event_id}")
        continue

    event_data = response.json().get('response', {})

    # === Prepare Embed ===
    embed = {
        "title": f"📅 {event_data.get('name', 'TruckersMP Event')}",
        "url": event_link,
        "color": 16776960,
        "fields": [
            {"name": "🛠 VTC", "value": event_data.get('vtc', {}).get("name", "Unknown VTC"), "inline": True},
            {"name": "📅 Date", "value": format_date(event_data.get("start_at", "")), "inline": True},
            {"name": "⏰ Meetup (UTC)", "value": event_data.get("meetup_at", "").split(" ")[1][:5], "inline": True},
            {"name": "⏰ Meetup (IST)", "value": utc_to_ist(event_data.get("meetup_at", "")), "inline": True},
            {"name": "🚀 Start (UTC)", "value": event_data.get("start_at", "").split(" ")[1][:5], "inline": True},
            {"name": "🚀 Start (IST)", "value": utc_to_ist(event_data.get("start_at", "")), "inline": True},
            {"name": "🖥 Server", "value": event_data.get("server", {}).get("name", "Unknown Server"), "inline": True},
            {"name": "🚏 Departure", "value": event_data.get("departure", {}).get("city", "Unknown"), "inline": True},
            {"name": "🎯 Arrival", "value": event_data.get("arrival", {}).get("city", "Unknown"), "inline": True},
            {"name": "🗺 DLC Req", "value": get_dlc_names(event_data.get("dlcs", [])), "inline": True}

        ]
    }

    payload = {
        "content": f"<@&{ROLE_ID}>",
        "embeds": [embed]
    }

    resp = requests.post(DISCORD_WEBHOOK, json=payload)

    if resp.status_code in [200, 204]:
        print(f"✅ Event {event_id} successfully posted to Discord!")
    else:
        print(f"❌ Failed to post event {event_id} to Discord: {resp.status_code}")
        print(resp.text)
