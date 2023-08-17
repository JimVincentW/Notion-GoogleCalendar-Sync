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

4. Add your Notion API token and other configuration details directly in the script or use environment variables.

### Running the Script

```bash
python sync.py
``````

Contribution
Feel free to fork this repository, make changes, and submit pull requests. For major changes, please open an issue first to discuss the proposed change.

License
This project is open-source and available under the MIT License.

typescript
Copy code

You can create these two files in your project directory, fill in `<your-repository-link>` with your actual GitHub repository link, and `<repository-directory>` with the name of your project directory. 

This will provide a good starting point for your GitHub repository. Make sure to adjust the information as needed to better fit the specifics of your project or any additional details you'd like to include.