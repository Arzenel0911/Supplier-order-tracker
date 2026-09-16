import calendar
import sqlite3
from datetime import date, datetime
from pathlib import Path

import streamlit as st

# ------------------------------------------------------------
# Page configuration
# ------------------------------------------------------------
st.set_page_config(
    page_title="History",
    page_icon="🕘",
    layout="wide",
)

# Same project layout as inventory.py: this file lives in pages/, so the
# database sits one level up, next to app.py.
APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = APP_DIR / "supplier_orders.db"


# ------------------------------------------------------------
# Styling — kept consistent with the Orders and Inventory pages
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    h1 {
        font-weight: 800 !important;
        letter-spacing: -0.01em;
    }

    [data-testid="stCaptionContainer"] {
        color: #94a3b8 !important;
    }

    .stButton button,
    .stFormSubmitButton button {
        border-radius: 8px !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        border-color: #263042 !important;
    }

    /* Filter toolbar */
    .history-filter-label {
        font-size: 12.5px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #94a3b8;
        margin-bottom: 4px;
    }

    /* One history entry */
    .history-entry {
        display: flex;
        align-items: flex-start;
        gap: 14px;
        padding: 14px 16px;
        margin-bottom: 10px;
        border-radius: 10px;
        background: #161d2b;
        border: 1px solid #263042;
        border-left: 4px solid var(--accent, #64748b);
    }

    .history-entry-icon {
        font-size: 22px;
        line-height: 1;
        margin-top: 2px;
    }

    .history-entry-body {
        flex: 1;
        min-width: 0;
    }

    .history-entry-top {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 10px;
        flex-wrap: wrap;
    }

    .history-entry-type {
        font-weight: 700;
        font-size: 15px;
        color: #f1f5f9;
    }

    .history-entry-time {
        font-size: 12.5px;
        color: #94a3b8;
        white-space: nowrap;
    }

    .history-entry-desc {
        font-size: 14px;
        color: #cbd5e1;
        margin-top: 3px;
    }

    .history-entry-qty {
        display: inline-block;
        margin-top: 6px;
        padding: 2px 9px;
        border-radius: 999px;
        background: rgba(148, 163, 184, 0.12);
        font-size: 12.5px;
        font-weight: 600;
        color: #e2e8f0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# Database
# ------------------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_history_db():
    """Idempotent safety net — Orders and Inventory already create this
    table, but a fresh session could land on this page first."""
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS history_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action_type TEXT NOT NULL,
            item_name TEXT NOT NULL DEFAULT '',
            quantity TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.commit()
    conn.close()


def get_history(filter_date=None, filter_year=None, filter_month=None, ascending=False):
    """Latest first by default (set ascending=True to reverse). If
    filter_date (a date object) is given, only rows on that calendar date
    are returned. Otherwise, if filter_year and filter_month are both
    given, only rows in that calendar month are returned. If neither is
    given, all history is returned."""
    conn = get_connection()
    order_dir = "ASC" if ascending else "DESC"
    if filter_date is not None:
        rows = conn.execute(
            f"""
            SELECT * FROM history_log
            WHERE date(timestamp) = ?
            ORDER BY timestamp {order_dir}, id {order_dir}
            """,
            (filter_date.isoformat(),),
        ).fetchall()
    elif filter_year is not None and filter_month is not None:
        rows = conn.execute(
            f"""
            SELECT * FROM history_log
            WHERE strftime('%Y', timestamp) = ? AND strftime('%m', timestamp) = ?
            ORDER BY timestamp {order_dir}, id {order_dir}
            """,
            (str(filter_year), f"{filter_month:02d}"),
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT * FROM history_log ORDER BY timestamp {order_dir}, id {order_dir}"
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_history_date_bounds():
    """Earliest and latest dates that actually have history entries, used
    to keep the date picker sensible. Falls back to today if empty."""
    conn = get_connection()
    row = conn.execute(
        "SELECT MIN(date(timestamp)) AS min_d, MAX(date(timestamp)) AS max_d "
        "FROM history_log"
    ).fetchone()
    conn.close()

    if row and row["min_d"] and row["max_d"]:
        return date.fromisoformat(row["min_d"]), date.fromisoformat(row["max_d"])

    today = date.today()
    return today, today


# ------------------------------------------------------------
# Presentation helpers
# ------------------------------------------------------------
ACTION_STYLE = {
    "Order Added": ("🟢", "#16a34a"),
    "Order Edited": ("✏️", "#3b82f6"),
    "Order Deleted": ("🗑️", "#dc2626"),
    "Order Marked as Complete": ("✅", "#16a34a"),
    "Order Cancelled": ("🚫", "#f59e0b"),
    "Stock Added": ("➕", "#16a34a"),
    "Stock Removed": ("➖", "#dc2626"),
}
DEFAULT_STYLE = ("📌", "#64748b")


def format_timestamp(ts_text):
    try:
        dt = datetime.strptime(ts_text, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return ts_text, ""
    return dt.strftime("%d-%m-%Y"), dt.strftime("%I:%M %p").lstrip("0")


def render_entry(entry):
    icon, color = ACTION_STYLE.get(entry["action_type"], DEFAULT_STYLE)
    day_text, time_text = format_timestamp(entry["timestamp"])

    quantity_html = ""
    if entry["quantity"]:
        quantity_html = (
            f'<span class="history-entry-qty">Qty: {entry["quantity"]}</span><br>'
        )

    st.markdown(
        f"""
        <div class="history-entry" style="--accent: {color};">
            <div class="history-entry-icon">{icon}</div>
            <div class="history-entry-body">
                <div class="history-entry-top">
                    <span class="history-entry-type">{entry['action_type']}</span>
                    <span class="history-entry-time">{day_text} · {time_text}</span>
                </div>
                <div class="history-entry-desc">{entry['description']}</div>
                {quantity_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# Page
# ------------------------------------------------------------
init_history_db()

st.title("🕘 History")
st.caption(
    "A permanent activity log of every order and inventory action taken "
    "in this application."
)

st.divider()

# ------------------------------------------------------------
# Filter toolbar
# ------------------------------------------------------------
MONTH_NAMES = [calendar.month_name[m] for m in range(1, 13)]

with st.container(border=True):
    filter_col, sort_col, extra_col1, extra_col2, _spacer = st.columns(
        [1.3, 1.3, 1.3, 1.1, 1.6]
    )

    with filter_col:
        st.markdown('<div class="history-filter-label">View</div>', unsafe_allow_html=True)
        view_choice = st.selectbox(
            "View",
            ["All History", "Specific Date", "By Month"],
            label_visibility="collapsed",
        )

    with sort_col:
        st.markdown('<div class="history-filter-label">Sort</div>', unsafe_allow_html=True)
        sort_order = st.selectbox(
            "Sort",
            ["Descending", "Ascending"],
            label_visibility="collapsed",
        )

    selected_date = None
    selected_month_name = None
    selected_year = None

    if view_choice == "Specific Date":
        min_date, max_date = get_history_date_bounds()
        # Let the picker range comfortably cover previous months even if
        # history is sparse, without restricting how far back one can go.
        picker_min = min(min_date, date.today().replace(day=1))
        with extra_col1:
            selected_date = st.date_input(
                "Select a date",
                value=max_date,
                min_value=picker_min,
                max_value=date.today(),
                format="DD-MM-YYYY",
                label_visibility="collapsed",
            )

    elif view_choice == "By Month":
        min_date, max_date = get_history_date_bounds()
        year_min = min(min_date.year, date.today().year)
        year_max = max(max_date.year, date.today().year)
        year_options = list(range(year_max, year_min - 1, -1))

        today = date.today()
        default_month_index = (
            today.month - 1 if year_min <= today.year <= year_max else max_date.month - 1
        )
        default_year = today.year if today.year in year_options else year_options[0]

        with extra_col1:
            selected_month_name = st.selectbox(
                "Month",
                MONTH_NAMES,
                index=default_month_index,
                label_visibility="collapsed",
            )
        with extra_col2:
            selected_year = st.selectbox(
                "Year",
                year_options,
                index=year_options.index(default_year),
                label_visibility="collapsed",
            )

selected_month_number = (
    MONTH_NAMES.index(selected_month_name) + 1 if selected_month_name else None
)

# ------------------------------------------------------------
# Entries
# ------------------------------------------------------------
entries = get_history(
    filter_date=selected_date,
    filter_year=selected_year,
    filter_month=selected_month_number,
    ascending=(sort_order == "Ascending"),
)

if view_choice == "Specific Date" and selected_date is not None:
    st.subheader(f"📅 {selected_date.strftime('%d-%m-%Y')}")
elif view_choice == "By Month" and selected_month_name and selected_year:
    st.subheader(f"📅 {selected_month_name} {selected_year}")
else:
    st.subheader("📜 All History")

order_text = "oldest first" if sort_order == "Ascending" else "newest first"
st.caption(f"{len(entries)} action(s) — {order_text}.")

if not entries:
    if view_choice == "Specific Date":
        st.info("No actions were recorded on that date.")
    elif view_choice == "By Month":
        st.info(
            f"No history for this month ({selected_month_name} {selected_year})."
        )
    else:
        st.info(
            "No history yet. Actions like adding an order, editing it, "
            "marking it complete, cancelling it, deleting it, or adding/"
            "removing inventory stock will show up here."
        )
else:
    for entry in entries:
        render_entry(entry)