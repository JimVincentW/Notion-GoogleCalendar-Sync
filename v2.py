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
                "on_or_after": start_time.isoformat(),
                "on_or_before": end_time.isoformat()
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

def update_notion_event_from_gc(notion, database_id, gc_event):
    response = notion.databases.query(
        database_id=database_id,
        filter={
            "property": "external_gcal_id",
            "rich_text": {
                "equals": gc_event.id
            }
        }
    )

    if response['results']:
        page_id = response['results'][0]['id']
        properties = {
            "Name": {"title": [{"text": {"content": gc_event.summary}}]},
            "Date": {"date": {"start": gc_event.start.isoformat(), "end": gc_event.end.isoformat()}}
        }
        notion.pages.update(page_id=page_id, properties=properties)


def update_gc_event_from_notion(calendar, notion_event, gc_event_id):
    title = notion_event['properties']['Name']['title'][0]['plain_text']
    date_str = notion_event['properties']['Date']['date']['start']
    date = parse(date_str)
    updated_event = Event(title, start=date, end=date + timedelta(hours=1), event_id=gc_event_id)
    calendar.update_event(updated_event)


def delete_notion_event_by_gcal_id(notion, database_id, gcal_id):
    print(gcal_id)
    response = response = notion.databases.query(
        database_id=database_id,
        filter={
            "property": "external_gcal_id",
            "rich_text": {
                "equals": gcal_id
            }
        }
    )
    if response['results']:
        notion.pages.delete(response['results'][0]['id'])

def delete_gc_event_by_id(calendar, event_id):
    calendar.delete_event_by_id(event_id)

def add_event_to_notion(notion, database_id, gc_event):
    properties = {
        "Name": {"title": [{"text": {"content": gc_event.summary}}]},
        "Date": {"date": {"start": gc_event.start.isoformat(), "end": gc_event.end.isoformat()}},
        "Art": {"multi_select": [{"name": "Termine/ To-Do"}]},
        "external_gcal_id": {"rich_text": [{"text": {"content": gc_event.id}}]}
    }
    notion.pages.create(parent={"database_id": database_id}, properties=properties)

def update_notion_events_to_noon(notion, notion_events):
    for event in notion_events:
        date_start = event.get('properties', {}).get('Date', {}).get('date', {}).get('start', None)
        if "T00:00:00" in date_start or "T" not in date_start:
            update_time_to_noon(notion, event)


def has_matching_summary(event, target_summary):
    titles = event['properties'].get('Name', {}).get('title', [])
    return titles and titles[0]['plain_text'] == target_summary

def sync_from_gc_to_notion(notion, database_id, gc_events_list, notion_events):
    gc_to_notion_skipped_count = 0
    gc_to_notion_added_count = 0
    added_events_details = []

    for gc_event in gc_events_list:
        event_date = gc_event.start.date().isoformat()
        event_summary = gc_event.summary

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

        matching_notion_event = next((e for e in notion_same_day_events if has_matching_summary(e, event_summary)), None)
        
        if matching_notion_event:
            gc_to_notion_skipped_count += 1
            if matching_notion_event['properties']['Date']['date']['start'] != gc_event.start.isoformat():
                # Detected an edit in Google Calendar
                update_notion_event_from_gc(notion, database_id, gc_event)
        else:
            # Add the event to Notion
            add_event_to_notion(notion, database_id, gc_event)
            gc_to_notion_added_count += 1
            added_events_details.append(f"Added {event_summary} from Google Calendar to Notion")

    # To handle deletions:
    for notion_event in notion_events:
        external_gcal_id_property = notion_event['properties'].get('external_gcal_id', None)
        if external_gcal_id_property and 'rich_text' in external_gcal_id_property and external_gcal_id_property['rich_text']:
            gcal_id = external_gcal_id_property['rich_text'][0]['text']['content']
            
            # Now you can use gcal_id in your API call
            response = notion.databases.query(
                database_id=database_id,
                filter={
                    "property": "external_gcal_id",
                    "rich_text": {
                        "equals": gcal_id
                    }
                }
            )
            
            if response['results']:
                page_id = response['results'][0]['id']
                # Update the checkbox property
                notion.pages.update(page_id, properties={"Checkbox": True})
                print(f"Checked checkbox for event with external GCal ID {gcal_id}, named {notion_event['properties']['Name']['title'][0]['plain_text']}")
            else:
                print(f"No event with external GCal ID {gcal_id} found.")
        else:
            print("No 'external_gcal_id' property found in Notion event.")
            
    # Rest of your code
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

            if date.date() != yesterday:
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

    gc_to_notion_added_count, gc_to_notion_skipped_count, gc_added_events = sync_from_gc_to_notion(notion, notion_database_id, gc_events_list, notion_events)
    notion_to_gc_added_count, notion_to_gc_skipped_count, notion_added_events = sync_from_notion_to_gc(calendar, notion_events, gc_events_set)

    print(f"{gc_to_notion_skipped_count} Google Calendar events skipped as already existing in Notion.")
    print(f"{notion_to_gc_skipped_count} Notion events skipped as already existing in Google Calendar.")
    
    total_added_events = gc_to_notion_added_count + notion_to_gc_added_count
    print(f"{total_added_events} new events added:")
    
    for event_detail in gc_added_events + notion_added_events:
        print("-->  " + event_detail)


if __name__ == "__main__":
    main()