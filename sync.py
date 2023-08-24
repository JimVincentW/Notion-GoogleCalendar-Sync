import os
import pytz
from notion_client import Client
from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event
from dateutil.parser import parse
from datetime import timedelta, datetime

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


def update_time_to_noon(notion, notion_event):
    try:
        page_id = notion_event['id']
        date_start = notion_event['properties']['Date']['date']['start']

        if "T" not in date_start:
            new_date_start = date_start + "T12:00:00+02:00"
            new_date_end = date_start + "T13:00:00+02:00"
        else:
            if "T00:00:00" in date_start:
                new_date_start = date_start.split("T")[0] + "T12:00:00+02:00"
                new_date_end = date_start.split("T")[0] + "T13:00:00+02:00"

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
        print(f"Updated event with ID {page_id} to start at noon (Berlin timezone).")
    except Exception as e:
        print(f"Failed to update event with ID {notion_event.get('id', 'UNKNOWN_ID')}. Error: {e}")


def update_notion_events_to_noon(notion, notion_events):
    for event in notion_events:
        date_start = event['properties']['Date']['date']['start']
        if "T00:00:00" in date_start or "T" not in date_start:
            update_time_to_noon(notion, event)


def has_matching_summary(event, target_summary):
    titles = event['properties'].get('Name', {}).get('title', [])
    return titles and titles[0]['plain_text'] == target_summary


def sync_from_gc_to_notion(notion, database_id, gc_events_list):
    gc_to_notion_skipped_count = 0
    gc_to_notion_added_count = 0
    added_events_details = []

    for event in gc_events_list:
        event_date = event.start.date().isoformat()
        event_summary = event.summary

        response = notion.databases.query(
            database_id=database_id,
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
                parent={"database_id": database_id},
                properties={
                    "Name": {"title": [{"text": {"content": event.summary}}]},
                    "Date": {"date": {"start": event.start.isoformat(), "end": event.end.isoformat()}},
                    "Art": {"multi_select": [{"name": "Termine/ To-Do"}]}
                }
            )
            added_events_details.append(f"Added {event_summary} from Google Calendar to Notion")
        else:
            gc_to_notion_skipped_count += 1

    return gc_to_notion_added_count, gc_to_notion_skipped_count, added_events_details


def sync_from_notion_to_gc(calendar, notion_events, gc_events_set):
    notion_to_gc_skipped_count = 0
    notion_to_gc_added_count = 0
    added_events_details = []
    yesterday = (datetime.today() - timedelta(days=1)).date()

    for event in notion_events:
        try:
            if not event['properties']['Name']['title']:
                continue

            title = event['properties']['Name']['title'][0]['plain_text']
            date_str = event['properties']['Date']['date']['start']
            date = parse(date_str)

            if date.date() >= datetime.today().date():
                if "T" not in date_str:
                    date_naive = datetime.strptime(date_str, '%Y-%m-%d') + timedelta(hours=12)
                    date = berlin.localize(date_naive)

                key = (date.date().isoformat(), title)

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

    return notion_to_gc_added_count, notion_to_gc_skipped_count, added_events_details


def main():
    notion, calendar = initialize_clients()
    notion_database_id = os.environ["NOTION_DATABASE_ID"]
    start_time, end_time = determine_time_range()

    gc_events_list = fetch_gc_events(calendar, start_time, end_time)
    notion_events = fetch_notion_events(notion, notion_database_id, start_time, end_time)

    gc_events_set = set()
    for e in gc_events_list:
        if e.start and e.summary:
            if isinstance(e.start, datetime):
                gc_events_set.add((e.start.date().isoformat(), e.summary))
            else:
                gc_events_set.add((e.start.isoformat(), e.summary))

    update_notion_events_to_noon(notion, notion_events)

    gc_to_notion_added_count, gc_to_notion_skipped_count, gc_added_events = sync_from_gc_to_notion(notion, notion_database_id, gc_events_list)
    notion_to_gc_added_count, notion_to_gc_skipped_count, notion_added_events = sync_from_notion_to_gc(calendar, notion_events, gc_events_set)

    print(f"{gc_to_notion_skipped_count} Google Calendar events skipped as already existing in Notion.")
    print(f"{notion_to_gc_skipped_count} Notion events skipped as already existing in Google Calendar.")
    
    total_added_events = gc_to_notion_added_count + notion_to_gc_added_count
    print(f"{total_added_events} new events added:")
    
    for event_detail in gc_added_events + notion_added_events:
        print("-->  " + event_detail)


if __name__ == "__main__":
    main()