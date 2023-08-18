import os
from notion_client import Client
from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event
from dateutil.parser import parse
from datetime import timedelta, datetime



notion = Client(auth=os.environ["NOTION_TOKEN"])
notion_database_id = os.environ["NOTION_DATABASE_ID"]
calendar = GoogleCalendar(os.environ["GMAIL_ADDRESS"])

start_time = datetime.combine(datetime.today().date(), datetime.min.time())
end_time = datetime(2023, 12, 1)
yesterday = (datetime.today() - timedelta(days=1)).date()

gc_events_list = list(calendar.get_events(time_min=start_time, time_max=end_time))

response = notion.databases.query(
    database_id=notion_database_id,
    filter={
        "property": "Date",
        "date": {
            "after": start_time.isoformat(),
            "before": end_time.isoformat()
        },
    }
)
notion_events = response['results']
for event in notion_events:
    date_start = event['properties']['Date']['date']['start']
    if "T00:00:00" in date_start:
        print(f"Event with ID {event['id']} starts at midnight.")

# Function to update the time of the event in Notion to 12 PM.
def update_time_to_noon(notion_event):
    page_id = notion_event['id']
    date_start = notion_event['properties']['Date']['date']['start']
    date_end = notion_event['properties']['Date']['date'].get('end')

    # Convert the start time to 12 PM.
    new_date_start = date_start.split("T")[0] + "T12:00:00Z"

    # If there's an end time, adjust it accordingly.
    if date_end and "T" in date_end:
        new_date_end = date_end.split("T")[0] + "T13:00:00Z"
    elif date_end:  # Only date is provided without time.
        new_date_end = date_end
    else:  # If there's no end time specified.
        new_date_end = new_date_start

    # Use the Notion API to update the page's properties.
    notion.pages.update(
        page_id=page_id,
        properties={
            "Date": {
                "date": {
                    "start": new_date_start,
                    "end": new_date_end
                }
            }
        }
    )
    print(f"Updated event with ID {page_id} to start at noon.")



gc_events_set = set()
for e in gc_events_list:
    if e.start and e.summary:
        if isinstance(e.start, datetime):
            gc_events_set.add((e.start.date().isoformat(), e.summary))
        else:
            gc_events_set.add((e.start.isoformat(), e.summary))

notion_events_set = set()
for event in notion_events:
    try:
        date_start = event['properties']['Date']['date']['start']
        if "T00:00:00" in date_start:
            update_time_to_noon(event)
    except KeyError:
        continue

def has_matching_summary(event, target_summary):
    titles = event['properties'].get('Name', {}).get('title', [])
    return titles and titles[0]['plain_text'] == target_summary

gc_to_notion_skipped_count = 0
gc_to_notion_added_count = 0
notion_to_gc_skipped_count = 0
notion_to_gc_added_count = 0
added_events_details = []  # List to store detailed information of added events

for event in gc_events_list:
    event_date = event.start.date().isoformat()
    event_summary = event.summary

    response = notion.databases.query(
        database_id=notion_database_id,
        filter={
            "property": "Date",
            "date": {
                "on_or_before": f"{event_date}T23:59:59Z",
                "on_or_after": f"{event_date}T00:00:00Z",
            },
        }
    )
    notion_same_day_events = response['results']

    if not any(has_matching_summary(event, event_summary) for event in notion_same_day_events):
        gc_to_notion_added_count += 1
        notion.pages.create(
            parent={"database_id": notion_database_id},
            properties={
                "Name": {"title": [{"text": {"content": event.summary}}]},
                "Date": {"date": {"start": event.start.isoformat(), "end": event.end.isoformat()}},
                "Art": {"multi_select": [{"name": "Termine/ To-Do"}]}
            }
        )
        added_events_details.append(f"Added {event_summary} from Google Calendar to Notion")
    else:
        gc_to_notion_skipped_count += 1

for event in notion_events:
    try:
        if not event['properties']['Name']['title']:
            continue

        title = event['properties']['Name']['title'][0]['plain_text']
        date_str = event['properties']['Date']['date']['start']
        date = parse(date_str)

        if date.date() != yesterday:
            key = (date.date().isoformat(), title) if "T" in date_str else (date_str, title)

            if key not in gc_events_set:
                notion_to_gc_added_count += 1
                gc_event = Event(
                    title,
                    start=date,
                    end=(date + timedelta(hours=1)) if "T" in date_str else date
                )
                calendar.add_event(gc_event)
                added_events_details.append(f"Added {title} from Notion to Google Calendar")
            else:
                notion_to_gc_skipped_count += 1
    except KeyError:
        continue

print(f"{gc_to_notion_skipped_count} Google Calendar events skipped as already existing in Notion.")
print(f"{notion_to_gc_skipped_count} Notion events skipped as already existing in Google Calendar.")
print(f"{gc_to_notion_added_count + notion_to_gc_added_count} new events added.")
for event_detail in added_events_details:
    print(event_detail)

