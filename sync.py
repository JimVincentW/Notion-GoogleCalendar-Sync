import os
from notion_client import Client
from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event
from dateutil.parser import parse
from datetime import timedelta, datetime

os.environ["NOTION_TOKEN"] = "<NOTION_TOKEN>"
notion = Client(auth=os.environ["NOTION_TOKEN"])
notion_databas_id = "xxx"
calendar = GoogleCalendar('your_email@gmail.com')

# Time range for events to sync
start_time = datetime.combine(datetime.today().date(), datetime.min.time())
end_time = datetime(2023, 12, 1)

# Fetch events from Google Calendar
gc_events = calendar.get_events(time_min=start_time, time_max=end_time)

# Fetch events from the Notion database
response = notion.databases.query(
    **{
        "database_id": notion_databas_id,
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

# Create a set for Notion and Google Calendar events
notion_events_set = {(e['Date']['start'], e['Name'][0]['text']['content']) for e in notion_events if 'Date' in e and 'Name' in e and len(e['Name']) > 0}
gc_events_set = {(e.start.isoformat(), e.summary) for e in gc_events}

# Add Google Calendar events to Notion database
for event in gc_events:
    if (event.start.isoformat(), event.summary) not in notion_events_set:
        notion.pages.create(
            parent={"database_id": notion_databas_id},
            properties={
                "Name": {"title": [{"text": {"content": event.summary}}]},
                "Date": {"date": {"start": event.start.isoformat(), "end": event.end.isoformat()}},
                "Art": {"multi_select": [{"name": "Termine/ To-Do"}]}
            }
        )

# Add Notion events to Google Calendar
for event in notion_events:
    title = event['properties']['Name']['title'][0]['plain_text']
    date = parse(event['properties']['Date']['date']['start'])

    if (date.isoformat(), title) not in gc_events_set:
        gc_event = Event(
            title,
            start=date,
            end=(date + timedelta(hours=1))  # assuming the event is 1 hour
        )
        calendar.add_event(gc_event)
