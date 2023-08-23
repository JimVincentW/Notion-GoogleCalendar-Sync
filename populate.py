import os
import pytz
from notion_client import Client
from gcsa.google_calendar import GoogleCalendar
from datetime import datetime, timedelta
from dateutil.parser import parse

berlin = pytz.timezone('Europe/Berlin')

def initialize_clients():
    notion = Client(auth=os.environ["NOTION_TOKEN"])
    calendar = GoogleCalendar(os.environ["GMAIL_ADDRESS"])
    return notion, calendar

def determine_time_range():
    start_time = datetime.combine(datetime.today().date(), datetime.min.time())
    end_time = datetime(2023, 12, 1)
    return start_time, end_time

def fetch_gc_events(calendar, start_time, end_time):
    return list(calendar.get_events(time_min=start_time, time_max=end_time))

def fetch_notion_events(notion, database_id, start_time, end_time):
    response = notion.databases.query(
        database_id=database_id,
        filter={
            "property": "Date",
            "date": {
                "after": start_time.isoformat(),
                "before": end_time.isoformat()
            },
        }
    )
    return response['results']

def update_notion_with_gcal_id(notion, notion_event, gcal_id):
    try:
        page_id = notion_event['id']
        notion.pages.update(
            page_id=page_id,
            properties={"external_gcal_id": {"rich_text": [{"text": {"content": gcal_id}}]}})
        print(f"Updated event with ID {page_id} with Google Calendar ID {gcal_id}.")
    except Exception as e:
        print(f"Failed to update event with ID {notion_event.get('id', 'UNKNOWN_ID')}. Error: {e}")

def main():
    notion, calendar = initialize_clients()
    notion_database_id = os.environ["NOTION_DATABASE_ID"]
    start_time, end_time = determine_time_range()

    gc_events_list = fetch_gc_events(calendar, start_time, end_time)
    notion_events = fetch_notion_events(notion, notion_database_id, start_time, end_time)

    for ne in notion_events:
        title = ne['properties']['Name']['title'][0]['plain_text']
        date_str = ne['properties']['Date']['date']['start']
        date = parse(date_str)
        
        if "T" not in date_str:
            date_naive = datetime.strptime(date_str, '%Y-%m-%d') + timedelta(hours=12)
            date = berlin.localize(date_naive)

        matching_gcal_event = next((e for e in gc_events_list if e.summary == title and e.start.date() == date.date()), None)
        if matching_gcal_event:
            update_notion_with_gcal_id(notion, ne, matching_gcal_event.event_id)

if __name__ == "__main__":
    main()
