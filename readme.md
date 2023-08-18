# Notion-Google Calendar Sync

Synchronize events between a Notion database and a Google Calendar.

## Description

This script provides two-way synchronization:
1. It adds events from Google Calendar to a Notion database that aren't already present in the database.
2. It adds events from the Notion database to Google Calendar if they aren't already present in the calendar.

## Setup

### Prerequisites

- Python 3.x
- Notion API token
- Google Calendar API credentials (for `gcsa` package)

### Installation

1. Clone this repository:
git clone https://github.com/JimVincentW/Notion-GoogleCalendar-Syncer.git
cd Notion-GoogleCalendar-Syncer

2. Install the required packages:
pip install -r requirements.txt



3. Set up the Google Calendar API following the `gcsa` package [instructions](https://gcsa.readthedocs.io/en/latest/quickstart.html#authorization).

4. Add your Notion API token and other configuration details to the environment variables.
export NOTION_TOKEN=xxx
export NOTION_DATABASE_ID=xxx
export GMAIL_ADDRESS=xxx


### Running the Script for one time sync
```bash
python sync.py
``````


### Running the Script for looping sync
```bash
python loop.py
``````
