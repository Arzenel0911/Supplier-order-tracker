# Supplier Order Tracker

A lightweight, offline-first supplier order tracker built with Python, Streamlit and SQLite.

## Features

- Add supplier orders
- Item name, supplier, quantity, order date, expected delivery date, price
- Status: Pending / In Progress / Completed / Cancelled
- Optional personal reminder date + note
- Startup deadline/reminder alerts
- Search by item or supplier
- Filter by status
- One-click "Mark Completed"
- Delete orders with confirmation
- CSV export
- SQLite database stored beside the application

## Requirements

Python 3.10+ is recommended.

The first installation of Python/Streamlit/Pandas normally requires internet access to download packages.
After installation, the application and its data can run locally without a cloud account or online database.

## Windows

1. Install Python from python.org and make sure "Add Python to PATH" is enabled.
2. Open Command Prompt.
3. Move into this folder:

   cd path\to\supplier_order_tracker

4. Create a virtual environment:

   python -m venv .venv

5. Activate it:

   .venv\Scripts\activate

6. Install dependencies:

   pip install -r requirements.txt

7. Start the application:

   python -m streamlit run app.py

8. Your browser should open automatically. If not, open the local address printed in the terminal.

## macOS

1. Install Python 3.10+.
2. Open Terminal.
3. Move into this folder:

   cd /path/to/supplier_order_tracker

4. Create a virtual environment:

   python3 -m venv .venv

5. Activate it:

   source .venv/bin/activate

6. Install dependencies:

   pip install -r requirements.txt

7. Start the application:

   python3 -m streamlit run app.py

8. Open the local address printed in the terminal if the browser does not open automatically.

## Daily use

Every time the app is started:

- SQLite database is opened/created automatically.
- Saved orders are scanned.
- Overdue reminders and delivery deadlines are shown at the top.
- Orders can be searched and filtered.
- Active orders can be marked Completed with one click.

## Data location

The database is:

    supplier_orders.db

It is created in the same folder as `app.py`.

To back up the application data, simply copy `supplier_orders.db` somewhere safe.

## Running later

After the first setup, activate the virtual environment and run:

Windows:
    .venv\Scripts\activate
    python -m streamlit run app.py

macOS:
    source .venv/bin/activate
    python3 -m streamlit run app.py

## Important

Do not delete `supplier_orders.db` unless you intentionally want to delete all saved orders.
