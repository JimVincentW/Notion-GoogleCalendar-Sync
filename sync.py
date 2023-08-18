import os
from notion_client import Client
from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event
from dateutil.parser import parse
from datetime import timedelta, datetime

notion = Client(auth=os.environ["NOTION_TOKEN"])
notion_database_id = os.environ["NOTION_DATABASE_ID"]
calendar = GoogleCalendar(os.environ["GMAIL_ADDRESS"])

# Time range for events to sync
start_time = datetime.combine(datetime.today().date(), datetime.min.time())
end_time = datetime(2023, 12, 1)
yesterday = (datetime.today() - timedelta(days=1)).date()


# Fetch events from Google Calendar and convert to a list
gc_events_list = list(calendar.get_events(time_min=start_time, time_max=end_time))
print(f"Number of events fetched from Google Calendar: {len(gc_events_list)}")

# Fetch events from Notion
response = notion.databases.query(
    **{
        "database_id": notion_database_id,
        "filter": {
            "property": "Date",
            "date": {
                "after": start_time.isoformat(),
                "before": end_time.isoformat()
            },
        },
    }
)
notion_events = response['results']
print(f"Number of events fetched from Notion: {len(notion_events)}")

# Construct sets for events
gc_events_set = set()
for e in gc_events_list:
    if e.start and e.summary:
        if isinstance(e.start, datetime):
            gc_events_set.add((e.start.date().isoformat(), e.summary))
        else:
            # This is an all-day event in Google Calendar
            gc_events_set.add((e.start.isoformat(), e.summary))


notion_events_set = set()
for e in notion_events:
    try:
        date = e['properties']['Date']['date']['start'].split("T")[0]
        title = e['properties']['Name']['title'][0]['plain_text']
        notion_events_set.add((date, title))
    except KeyError:
        continue

# Add Google Calendar events to Notion database
for event in gc_events_list:
    event_date = event.start.date().isoformat()
    event_summary = event.summary

    # Fetch events from Notion for the same day
    response = notion.databases.query(
        **{
            "database_id": notion_database_id,
            "filter": {
                "property": "Date",
                "date": {
                    "on_or_before": f"{event_date}T23:59:59Z",
                    "on_or_after": f"{event_date}T00:00:00Z",
                },
            },
        }
    )
    notion_same_day_events = response['results']

    # Check if event with same summary exists
    if not any(event['properties']['Name']['title'][0]['plain_text'] == event_summary for event in notion_same_day_events):
        print(f"Adding {event_summary} from Google Calendar to Notion.")
        notion.pages.create(
            parent={"database_id": notion_database_id},
            properties={
                "Name": {"title": [{"text": {"content": event.summary}}]},
                "Date": {"date": {"start": event.start.isoformat(), "end": event.end.isoformat()}},
                "Art": {"multi_select": [{"name": "Termine/ To-Do"}]}
            }
        )
    else:
        print(f"Skipping {event_summary} as it already exists in Notion.")

# Add Notion events to Google Calendar
for event in notion_events:
    try:
        title = event['properties']['Name']['title'][0]['plain_text']
        date_str = event['properties']['Date']['date']['start']
        date = parse(date_str)

        # Check if the event is not from yesterday
        if date.date() != yesterday:
            # Check if the Notion event has a time or not
            if "T" in date_str:  # the event has a specific time
                key = (date.date().isoformat(), title)
            else:  # all-day event
                key = (date_str, title)

            if key not in gc_events_set:
                print(f"Adding {title} from Notion to Google Calendar.")
                gc_event = Event(
                    title,
                    start=date,
                    end=(date + timedelta(hours=1)) if "T" in date_str else date
                )
                calendar.add_event(gc_event)
            else:
                print(f"Skipping {title} as it already exists in Google Calendar.")
    except KeyError:
        continue

