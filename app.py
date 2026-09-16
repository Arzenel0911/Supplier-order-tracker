import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "supplier_orders.db"

STATUSES = ["In Progress", "Completed", "Cancelled"]


# ------------------------------------------------------------
# Database
# ------------------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            supplier_name TEXT DEFAULT '',
            quantity INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Pending',
            reminder_date TEXT,
            reminder_note TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Partial/full delivery records tied to an order. Created here (if not
    # already present) so the cascading delete below always has something
    # valid to operate against.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS order_deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            delivery_date TEXT NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
        """
    )
    # Permanent activity log for the History page. Deliberately has no
    # foreign key / cascade tie to "orders" — it stores a plain-text
    # snapshot of the item name, so a row's history survives even after
    # that order is later deleted.
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


def log_history(action_type, item_name, quantity, description):
    """Append one permanent activity-log entry. Call this ONLY after the
    real database change has already been committed successfully, so a
    cancelled confirmation or a failed operation never creates a false
    entry."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO history_log
        (timestamp, action_type, item_name, quantity, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action_type,
            item_name or "",
            "" if quantity is None else str(quantity),
            description,
        ),
    )
    conn.commit()
    conn.close()


# ------------------------------------------------------------
# Undo / Redo support
# ------------------------------------------------------------
def capture_orders_state():
    """Capture the full orders + delivery tables for undo/redo."""
    conn = get_connection()
    order_rows = conn.execute("SELECT * FROM orders ORDER BY id").fetchall()
    delivery_rows = conn.execute(
        "SELECT * FROM order_deliveries ORDER BY id"
    ).fetchall()
    conn.close()
    return {
        "orders": [dict(row) for row in order_rows],
        "order_deliveries": [dict(row) for row in delivery_rows],
    }


def restore_orders_state(snapshot):
    """Restore a previously captured snapshot without creating a new history entry."""
    conn = get_connection()
    conn.execute("DELETE FROM order_deliveries")
    conn.execute("DELETE FROM orders")

    for row in snapshot["orders"]:
        conn.execute(
            """
            INSERT INTO orders
            (id, item_name, supplier_name, quantity, order_date, end_date,
             price, status, reminder_date, reminder_note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["item_name"],
                row["supplier_name"],
                row["quantity"],
                row["order_date"],
                row["end_date"],
                row["price"],
                row["status"],
                row["reminder_date"],
                row["reminder_note"],
                row["created_at"],
            ),
        )

    for row in snapshot.get("order_deliveries", []):
        conn.execute(
            """
            INSERT INTO order_deliveries
            (id, order_id, quantity, delivery_date, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["order_id"],
                row["quantity"],
                row["delivery_date"],
                row["note"],
                row["created_at"],
            ),
        )

    # Keep the AUTOINCREMENT counters ahead of the restored IDs.
    for table in ("orders", "order_deliveries"):
        max_id = conn.execute(
            f"SELECT COALESCE(MAX(id), 0) FROM {table}"
        ).fetchone()[0]
        conn.execute("DELETE FROM sqlite_sequence WHERE name=?", (table,))
        if max_id:
            conn.execute(
                "INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)",
                (table, max_id),
            )

    conn.commit()
    conn.close()


def record_history(before_state):
    """Store a pre-change snapshot and clear the redo branch."""
    st.session_state.setdefault("orders_undo_stack", [])
    st.session_state.setdefault("orders_redo_stack", [])

    st.session_state["orders_undo_stack"].append(before_state)

    # A fresh action invalidates whatever used to be re-doable.
    st.session_state["orders_redo_stack"].clear()


def undo_order_action():
    undo_stack = st.session_state.setdefault("orders_undo_stack", [])
    redo_stack = st.session_state.setdefault("orders_redo_stack", [])

    if not undo_stack:
        set_action_message("Nothing to undo.", "ℹ️")
        return False

    current_state = capture_orders_state()
    previous_state = undo_stack.pop()

    restore_orders_state(previous_state)
    redo_stack.append(current_state)

    set_action_message("Undid the last order action.", "↶")
    return True


def redo_order_action():
    undo_stack = st.session_state.setdefault("orders_undo_stack", [])
    redo_stack = st.session_state.setdefault("orders_redo_stack", [])

    if not redo_stack:
        set_action_message("Nothing to redo.", "ℹ️")
        return False

    current_state = capture_orders_state()
    next_state = redo_stack.pop()

    restore_orders_state(next_state)
    undo_stack.append(current_state)

    set_action_message("Redid the last order action.", "↷")
    return True


def set_action_message(message, icon="✅"):
    st.session_state["orders_action_message"] = f"{icon}  {message}"


def show_action_message():
    message = st.session_state.pop("orders_action_message", None)
    if message:
        st.markdown(
            f'<div class="orders-action-toast">{message}</div>',
            unsafe_allow_html=True,
        )


# ------------------------------------------------------------
# Order CRUD (all mutating actions record undo/redo history)
# ------------------------------------------------------------
def add_order(
    item_name,
    supplier_name,
    quantity,
    order_date,
    end_date,
    price,
    status,
    reminder_date,
    reminder_note,
):
    before_state = capture_orders_state()

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO orders
        (item_name, supplier_name, quantity, order_date, end_date, price,
         status, reminder_date, reminder_note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_name.strip(),
            supplier_name.strip(),
           quantity.strip(),
            order_date.isoformat(),
            end_date.isoformat(),
            float(price),
            status,
            reminder_date.isoformat() if reminder_date else None,
            reminder_note.strip(),
        ),
    )
    conn.commit()
    conn.close()

    record_history(before_state)


def get_orders():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM orders ORDER BY end_date ASC, id DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_order_by_id(order_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_status(order_id, new_status):
    before_state = capture_orders_state()

    conn = get_connection()
    conn.execute(
        "UPDATE orders SET status = ? WHERE id = ?",
        (new_status, order_id),
    )
    conn.commit()
    conn.close()

    record_history(before_state)


def edit_order(
    order_id,
    item_name,
    supplier_name,
    quantity,
    order_date,
    end_date,
    price,
    status,
    reminder_date,
    reminder_note,
):
    """Update an existing order's fields in place. Never creates a new row."""
    before_state = capture_orders_state()

    conn = get_connection()
    conn.execute(
        """
        UPDATE orders
        SET item_name = ?, supplier_name = ?, quantity = ?, order_date = ?,
            end_date = ?, price = ?, status = ?, reminder_date = ?,
            reminder_note = ?
        WHERE id = ?
        """,
        (
            item_name.strip(),
            supplier_name.strip(),
            str(quantity).strip(),
            order_date.isoformat(),
            end_date.isoformat(),
            float(price),
            status,
            reminder_date.isoformat() if reminder_date else None,
            (reminder_note or "").strip(),
            order_id,
        ),
    )
    conn.commit()
    conn.close()

    record_history(before_state)


def delete_order(order_id):
    """Delete an order and any partial/full delivery records tied to it."""
    before_state = capture_orders_state()

    conn = get_connection()
    conn.execute("DELETE FROM order_deliveries WHERE order_id = ?", (order_id,))
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

    record_history(before_state)

def get_order_alert(order):
    """Show an alert for active orders with due reminders or deadlines."""
    
    if order["status"] in ("Completed", "Cancelled"):
        return ""

    today = date.today()

    # Check personal reminder
    if order["reminder_date"]:
        reminder_date = date.fromisoformat(order["reminder_date"])

        if reminder_date < today:
            return "🔴 Reminder Overdue"

        if reminder_date == today:
            return "🚨 Reminder Today"

    # Check delivery date
    if order["end_date"]:
        end_date = date.fromisoformat(order["end_date"])
        days_left = (end_date - today).days

        if days_left < 0:
            return "🔴 Delivery Overdue"

        if days_left == 0:
            return "⚠️ Delivery Today"

        if days_left <= 3:
            return "🟠 Delivery Soon"

    return ""


def format_display_date(iso_string):
    """Convert a stored ISO date ('YYYY-MM-DD') to the dd-mm-yyyy format
    used everywhere in the UI. Storage stays ISO (needed for correct
    sorting/filtering); only the on-screen text changes."""
    if not iso_string:
        return ""
    try:
        return date.fromisoformat(iso_string).strftime("%d-%m-%Y")
    except (ValueError, TypeError):
        return iso_string


def orders_dataframe():
    rows = get_orders()
    if not rows:
        return pd.DataFrame(
            columns=[
                "ID",
                "Item Name",
                "Supplier",
                "Quantity",
                "Order Date",
                "Expected Delivery",
                "Price",
                "Status",
                "Reminder Date",
                "Reminder Note",
            ]
        )

    data = []
    for r in rows:
        data.append(
            {
                "Alert": get_order_alert(r),
                "ID": r["id"],
                "Item Name": r["item_name"],
                "Supplier": r["supplier_name"],
                "Quantity": str(r["quantity"]),
                "Order Date": r["order_date"],
                "Expected Delivery": r["end_date"],
                "Price": r["price"],
                "Status": r["status"],
                "Reminder Date": r["reminder_date"] or "",
                "Reminder Note": r["reminder_note"] or "",
            }
        )
    return pd.DataFrame(data)


# ------------------------------------------------------------
# Reminder / deadline logic
# ------------------------------------------------------------
def get_alerts(rows):
    today = date.today()
    alerts = []

    for r in rows:
        if r["status"] in ("Completed", "Cancelled"):
            continue

        item = r["item_name"]
        supplier = r["supplier_name"]
        label = f"{item} ({supplier})" if supplier else item

        # Personal reminder
        if r["reminder_date"]:
            reminder = date.fromisoformat(r["reminder_date"])
            if reminder <= today:
                note = r["reminder_note"].strip()
                message = f"Reminder due for **{label}**"
                if note:
                    message += f": {note}"
                if reminder < today:
                    message += f" — overdue since {reminder.strftime('%d-%m-%Y')}"
                alerts.append(("reminder", message))

        # Delivery deadline
        if r["end_date"]:
            end_date = date.fromisoformat(r["end_date"])
            days_left = (end_date - today).days

            if days_left < 0:
                alerts.append(
                    (
                        "overdue",
                        f"**{label}** expected delivery was **{abs(days_left)} day(s) ago** "
                        f"({end_date.strftime('%d-%m-%Y')}).",
                    )
                )
            elif days_left == 0:
                alerts.append(
                    (
                        "today",
                        f"**{label}** is expected **today**.",
                    )
                )
            elif days_left <= 3:
                alerts.append(
                    (
                        "soon",
                        f"**{label}** is expected in **{days_left} day(s)** "
                        f"({end_date.strftime('%d-%m-%Y')}).",
                    )
                )

    return alerts


# ------------------------------------------------------------
# Page
# ------------------------------------------------------------
st.set_page_config(
    page_title="Supplier Order Tracker",
    page_icon="📦",
    layout="wide",
)

# ------------------------------------------------------------
# Styling — bottom-left action popup (matches the Inventory page)
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Bottom-left orders action popup */
    .orders-action-toast {
        position: fixed;
        left: 24px;
        bottom: 24px;
        z-index: 999999;
        background: #18212f;
        color: #ffffff;
        border: 1px solid #334155;
        border-left: 4px solid #3b82f6;
        border-radius: 10px;
        padding: 12px 18px;
        min-width: 260px;
        max-width: 380px;
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35);
        font-size: 14px;
        font-weight: 600;
        animation: ordersToastLifecycle 5.3s ease-out forwards;
    }

    @keyframes ordersToastLifecycle {
        0% {
            opacity: 0;
            transform: translateY(12px);
        }
        6% {
            opacity: 1;
            transform: translateY(0);
        }
        90% {
            opacity: 1;
            transform: translateY(0);
        }
        100% {
            opacity: 0;
            transform: translateY(8px);
            pointer-events: none;
        }
    }

    /* Keep the row action buttons compact and tidy */
    div[data-testid="column"] .stPopover button,
    div[data-testid="column"] .stButton button {
        padding: 0.2rem 0.5rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

init_db()

st.session_state.setdefault("orders_undo_stack", [])
st.session_state.setdefault("orders_redo_stack", [])
st.session_state.setdefault("selected_order_ids", [])
st.session_state.setdefault("_last_selected_order_ids", [])
st.session_state.setdefault("pending_action", None)
st.session_state.setdefault("editing_order_id", None)

st.title("📦 Supplier Order Tracker")
st.caption("A simple local order tracker — your data stays in this application's folder.")

rows = get_orders()
alerts = get_alerts(rows)

# Startup alert banner
if alerts:
    st.error("🚨 **ATTENTION — DEADLINES / REMINDERS**")
    for alert_type, message in alerts:
        if alert_type in ("overdue", "reminder"):
            st.warning("⚠️ " + message)
        elif alert_type == "today":
            st.error("🔴 " + message)
        else:
            st.info("📅 " + message)

# ------------------------------------------------------------
# Sidebar: add order
# ------------------------------------------------------------
with st.sidebar:
    # KC Logo
    st.markdown(
        """
        <div style="text-align: center; padding: 10px 0 25px 0;">
            <div style="
                font-size: 52px;
                font-weight: 800;
                letter-spacing: 4px;
                color: #2563eb;
                line-height: 1;
            ">
                KC
            </div>


        """,
        unsafe_allow_html=True
    )
        # Add New Order dropdown
    with st.expander("➕ Add New Order", expanded=False):

     with st.form("add_order_form", clear_on_submit=True):
        item_name = st.text_input("Item Name *", placeholder="e.g. Steel bolts")
        supplier_name = st.text_input(
            "Supplier Name",
            placeholder="e.g. ABC Traders",
            help="Supplier Name is included so you can search/filter suppliers.",
        )

        quantity = st.text_input(
    "Quantity *",
    placeholder="e.g. 50 kg, 500 g, 10 boxes",
    help="You can enter any unit such as kg, g, pieces, boxes, litres, etc."
)

        order_date = st.date_input(
            "Date of Order",
            value=date.today(),
            format="DD-MM-YYYY",
        )

        end_date = st.date_input(
            "Expected Delivery Date *",
            value=date.today() + timedelta(days=7),
            format="DD-MM-YYYY",
        )

        price = st.number_input(
            "Price",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            help="Enter the total order price.",
        )

        status = st.selectbox("Order Status", STATUSES, index=0)

        st.markdown("### 🔔 Reminder")

        reminder_date = st.date_input(
            "Reminder Date",
            value=end_date,
            format="DD-MM-YYYY",
        )

        enable_reminder = st.checkbox(
            "Enable this reminder",
            value=False,
        )

        reminder_note = st.text_input(
            "Reminder Note",
            placeholder="e.g. Call supplier about delivery",
        )

        submitted = st.form_submit_button(
            "💾 Save Order",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            if not item_name.strip():
                st.error("Item Name is required.")
            elif not quantity.strip():
                st.error("Quantity is required.")
            elif end_date < order_date:
                st.error("Expected Delivery Date cannot be before Date of Order.")
            else:
                add_order(
                    item_name,
                    supplier_name,
                    quantity,
                    order_date,
                    end_date,
                    price,
                    status,
                    reminder_date if enable_reminder else None,
                    reminder_note if enable_reminder else "", 
                   
                )
                log_history(
                    "Order Added",
                    item_name.strip(),
                    quantity.strip(),
                    f"Order '{item_name.strip()}' added "
                    f"(Qty: {quantity.strip()}).",
                )
                set_action_message(f"Order “{item_name.strip()}” saved.", "💾")
                st.rerun()

    st.divider()
    st.caption(f"Database: {DB_PATH.name}")
    st.caption("The SQLite database is created automatically beside app.py.")


# ------------------------------------------------------------
# Dashboard metrics
# ------------------------------------------------------------
df = orders_dataframe()

if not df.empty:
    total = len(df)
    pending = int((df["Status"] == "Pending").sum())
    progress = int((df["Status"] == "In Progress").sum())
    completed = int((df["Status"] == "Completed").sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Orders", total)
    c2.metric("Pending", pending)
    c3.metric("In Progress", progress)
    c4.metric("Completed", completed)

st.divider()

# ------------------------------------------------------------
# Filters
# ------------------------------------------------------------
header_col, undo_col, redo_col = st.columns([5, 1, 1])

with header_col:
    st.subheader("🔎 Orders")

with undo_col:
    if st.button(
        "↶ Undo",
        key="orders_undo_btn",
        use_container_width=True,
        disabled=not st.session_state["orders_undo_stack"],
        help="Undo the last order action.",
    ):
        if undo_order_action():
            st.rerun()

with redo_col:
    if st.button(
        "↷ Redo",
        key="orders_redo_btn",
        use_container_width=True,
        disabled=not st.session_state["orders_redo_stack"],
        help="Redo the last undone order action.",
    ):
        if redo_order_action():
            st.rerun()

c1, c2 = st.columns([1, 2])

# Tracked ourselves in plain session_state entries (separate from the
# widgets' own internal keys) and fed back in via `index=`/`value=` on
# every run. This is deliberate: Streamlit's own automatic widget-state
# restore for these two widgets was found to not survive the Undo/Redo
# buttons' internal st.rerun() call, so we don't rely on it — these plain
# session_state values persist correctly across that rerun regardless.
STATUS_FILTER_OPTIONS = STATUSES + ["All"]
st.session_state.setdefault("orders_status_filter_value", STATUS_FILTER_OPTIONS[0])
st.session_state.setdefault("orders_search_value", "")


def _sync_status_filter_value():
    st.session_state["orders_status_filter_value"] = st.session_state[
        "orders_status_filter_widget"
    ]


def _sync_search_value():
    st.session_state["orders_search_value"] = st.session_state[
        "orders_search_widget"
    ]


with c1:
    status_filter = st.selectbox(
        "Filter by Status",
        STATUS_FILTER_OPTIONS,
        index=STATUS_FILTER_OPTIONS.index(
            st.session_state["orders_status_filter_value"]
        ),
        key="orders_status_filter_widget",
        on_change=_sync_status_filter_value,
    )

with c2:
    search = st.text_input(
        "Search",
        value=st.session_state["orders_search_value"],
        placeholder="Search item name or supplier...",
        key="orders_search_widget",
        on_change=_sync_search_value,
    )

filtered = df.copy()

if not filtered.empty:
    if status_filter != "All":
        filtered = filtered[filtered["Status"] == status_filter]

    if search.strip():
        q = search.strip().lower()
        mask = (
            filtered["Item Name"].str.lower().str.contains(q, na=False)
            | filtered["Supplier"].str.lower().str.contains(q, na=False)
        )
        filtered = filtered[mask]

    # Newest orders first, oldest last.
    filtered = filtered.sort_values(
        by="Order Date", ascending=False, kind="stable"
    ).reset_index(drop=True)

# ------------------------------------------------------------
# Main order table — select one or more rows to act on them
# ------------------------------------------------------------
if filtered.empty:
    st.info("No orders match your filters.")
else:
    display_df = filtered.copy()
    display_df["Price"] = display_df["Price"].map(lambda x: f"₹{x:,.2f}")
    # Display-only: collapse the full alert text down to a single emoji,
    # or a blank cell when there's no active alert. The underlying alert
    # logic (get_order_alert / get_alerts) is untouched.
    display_df["Alert"] = display_df["Alert"].map(lambda a: "🚨" if a else "")
    # Display-only: dd-mm-yyyy instead of the stored ISO format. Sorting
    # above already happened on the ISO values, so this doesn't affect it.
    for date_col in ("Order Date", "Expected Delivery", "Reminder Date"):
        display_df[date_col] = display_df[date_col].map(format_display_date)

    st.caption(
        "Tip: Use the checkboxes on each row to select one or more orders "
        "(or the header checkbox to select every visible row), then use the "
        "action buttons that appear below the table. Deleted orders can be "
        "brought back with ↶ Undo."
    )

    selection_event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=420,
        on_select="rerun",
        selection_mode="multi-row",
        key="orders_table_select",
        column_config={
            "Alert": st.column_config.TextColumn("Alert", width="small"),
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Item Name": st.column_config.TextColumn("Item Name"),
            "Supplier": st.column_config.TextColumn("Supplier"),
            "Quantity": st.column_config.TextColumn("Quantity"),
            "Order Date": st.column_config.TextColumn("Order Date", width="small"),
            "Expected Delivery": st.column_config.TextColumn(
                "Expected Delivery", width="small"
            ),
            "Price": st.column_config.TextColumn("Price"),
            "Status": st.column_config.TextColumn("Status"),
            "Reminder Date": st.column_config.TextColumn(
                "Reminder Date", width=120
            ),
            # Sized to comfortably fit about 30 characters on one line at
            # normal table font size, instead of being truncated.
            "Reminder Note": st.column_config.TextColumn(
                "Reminder Note", width=260
            ),
        },
    )

    # Pull the selected rows out of the selection event. Streamlit returns
    # this as a dict-like object: {"selection": {"rows": [...]}}.
    if isinstance(selection_event, dict):
        selected_positions = selection_event.get("selection", {}).get("rows", [])
    else:
        selected_positions = getattr(
            getattr(selection_event, "selection", None), "rows", []
        ) or []

    selected_order_ids = []
    for pos in selected_positions:
        if 0 <= pos < len(display_df):
            selected_order_ids.append(int(display_df.iloc[pos]["ID"]))
    # Preserve the grid's own order but drop any accidental duplicates.
    selected_order_ids = list(dict.fromkeys(selected_order_ids))

    # If the selection changed (rows added/removed/cleared), drop any
    # in-flight confirmation tied to a different set of rows, and drop an
    # in-progress edit unless it's still the one-and-only selected row.
    if selected_order_ids != st.session_state["_last_selected_order_ids"]:
        pending = st.session_state.get("pending_action")
        if not pending or set(pending.get("order_ids", [])) != set(selected_order_ids):
            st.session_state["pending_action"] = None
        editing_id = st.session_state.get("editing_order_id")
        if editing_id is not None and selected_order_ids != [editing_id]:
            st.session_state["editing_order_id"] = None
        st.session_state["_last_selected_order_ids"] = selected_order_ids

    st.session_state["selected_order_ids"] = selected_order_ids

    pending = st.session_state.get("pending_action")
    editing_order_id = st.session_state.get("editing_order_id")
    selected_count = len(selected_order_ids)

    # Sized so each button's own label fits on one line without wrapping,
    # while still leaving them comfortably on a single row.
    ACTION_BTN_WIDTHS = [1, 1.3, 2.2, 1.7, 2.8]
    BULK_ACTION_BTN_WIDTHS = [1.4, 2.3, 1.8, 3.5]

    if selected_count > 0 and not (pending or (editing_order_id is not None)):
        if selected_count == 1:
            st.markdown(f"**1 order selected** — #{selected_order_ids[0]}")
        else:
            st.markdown(f"**{selected_count} orders selected**")

    if pending and set(pending.get("order_ids", [])) == set(selected_order_ids) and selected_order_ids:
        # ------------------------------------------------------------
        # Two-step confirmation for Edit / Delete / Mark as Complete /
        # Cancel Order — applies to every selected order at once (Edit
        # only ever targets a single order, since it's a per-row form).
        # ------------------------------------------------------------
        order_ids = pending["order_ids"]
        action_type = pending["type"]
        step = pending["step"]
        count = len(order_ids)
        order_word = "order" if count == 1 else "orders"
        id_list_text = ", ".join(f"#{oid}" for oid in order_ids)

        verbs = {
            "edit": "edit",
            "delete": "permanently delete",
            "complete": "mark as Completed",
            "cancel": "mark as Cancelled",
        }
        verb = verbs[action_type]

        if step == 1:
            st.warning(
                f"Are you sure you want to {verb} {count} {order_word} "
                f"({id_list_text})?"
            )
            yes_col, no_col, _sp = st.columns([1, 1, 8])
            with yes_col:
                if st.button(
                    "Yes, continue",
                    key=f"confirm1_yes_{action_type}",
                    use_container_width=True,
                ):
                    st.session_state["pending_action"]["step"] = 2
                    st.rerun()
            with no_col:
                if st.button(
                    "Cancel",
                    key=f"confirm1_no_{action_type}",
                    use_container_width=True,
                ):
                    st.session_state["pending_action"] = None
                    st.rerun()

        elif step == 2:
            st.error(
                f"Final confirmation — this will {verb} {count} {order_word} "
                f"({id_list_text}). Proceed?"
            )
            yes_col, no_col, _sp = st.columns([1, 1, 8])
            with yes_col:
                if st.button(
                    "Yes, I'm sure",
                    key=f"confirm2_yes_{action_type}",
                    type="primary",
                    use_container_width=True,
                ):
                    if action_type == "delete":
                        for oid in order_ids:
                            # Snapshot the order's name/quantity before
                            # deleting it, so the history entry still
                            # reads correctly once the row is gone.
                            snap = get_order_by_id(oid)
                            name = snap["item_name"] if snap else f"Order #{oid}"
                            qty = snap["quantity"] if snap else ""
                            delete_order(oid)
                            log_history(
                                "Order Deleted",
                                name,
                                qty,
                                f"Order '{name}' (#{oid}) deleted.",
                            )
                        set_action_message(
                            f"Deleted {count} {order_word}.", "🗑️"
                        )
                        st.session_state["selected_order_ids"] = []
                        st.session_state["_last_selected_order_ids"] = []
                        st.session_state.pop("orders_table_select", None)
                    elif action_type == "complete":
                        for oid in order_ids:
                            snap = get_order_by_id(oid)
                            name = snap["item_name"] if snap else f"Order #{oid}"
                            qty = snap["quantity"] if snap else ""
                            update_status(oid, "Completed")
                            log_history(
                                "Order Marked as Complete",
                                name,
                                qty,
                                f"Order '{name}' (#{oid}) marked as Completed.",
                            )
                        set_action_message(
                            f"Marked {count} {order_word} as Completed.", "✅"
                        )
                    elif action_type == "cancel":
                        for oid in order_ids:
                            snap = get_order_by_id(oid)
                            name = snap["item_name"] if snap else f"Order #{oid}"
                            qty = snap["quantity"] if snap else ""
                            update_status(oid, "Cancelled")
                            log_history(
                                "Order Cancelled",
                                name,
                                qty,
                                f"Order '{name}' (#{oid}) cancelled.",
                            )
                        set_action_message(
                            f"Marked {count} {order_word} as Cancelled.", "🚫"
                        )
                    elif action_type == "edit":
                        st.session_state["editing_order_id"] = order_ids[0]

                    st.session_state["pending_action"] = None
                    st.rerun()
            with no_col:
                if st.button(
                    "Cancel",
                    key=f"confirm2_no_{action_type}",
                    use_container_width=True,
                ):
                    st.session_state["pending_action"] = None
                    st.rerun()

    elif (
        editing_order_id is not None
        and selected_order_ids == [editing_order_id]
    ):
        # ------------------------------------------------------------
        # Inline edit form for the selected row (appears after both
        # confirmations). Pressing Enter in a text field submits the
        # form automatically, the same as clicking Save. Editing is only
        # ever offered for a single selected order.
        # ------------------------------------------------------------
        order_record = get_order_by_id(editing_order_id)
        if order_record is None:
            st.session_state["editing_order_id"] = None
        else:
            st.markdown(f"##### ✏️ Editing Order #{editing_order_id}")

            with st.form(key=f"edit_form_{editing_order_id}", clear_on_submit=False):
                e_col1, e_col2 = st.columns(2)

                with e_col1:
                    new_item_name = st.text_input(
                        "Item Name", value=order_record["item_name"]
                    )
                    new_supplier = st.text_input(
                        "Supplier Name", value=order_record["supplier_name"] or ""
                    )
                    new_quantity = st.text_input(
                        "Quantity", value=str(order_record["quantity"])
                    )
                    new_price = st.number_input(
                        "Price",
                        value=float(order_record["price"]),
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                    )

                with e_col2:
                    new_order_date = st.date_input(
                        "Date of Order",
                        value=date.fromisoformat(order_record["order_date"]),
                        format="DD-MM-YYYY",
                    )
                    new_end_date = st.date_input(
                        "Expected Delivery Date",
                        value=date.fromisoformat(order_record["end_date"]),
                        format="DD-MM-YYYY",
                    )
                    current_status = order_record["status"]
                    status_index = (
                        STATUSES.index(current_status)
                        if current_status in STATUSES
                        else 0
                    )
                    new_status = st.selectbox(
                        "Order Status", STATUSES, index=status_index
                    )
                    default_reminder = (
                        date.fromisoformat(order_record["reminder_date"])
                        if order_record["reminder_date"]
                        else new_end_date
                    )
                    new_reminder_date = st.date_input(
                        "Reminder Date", value=default_reminder, format="DD-MM-YYYY"
                    )

                new_reminder_note = st.text_input(
                    "Reminder Note", value=order_record["reminder_note"] or ""
                )

                save_submitted = st.form_submit_button(
                    "💾 Save (press Enter or click here)",
                    type="primary",
                    use_container_width=True,
                )

            cancel_clicked = st.button(
                "✖️ Cancel Edit", key=f"cancel_edit_{editing_order_id}"
            )

            if save_submitted:
                if not new_item_name.strip():
                    st.error("Item Name is required.")
                elif not str(new_quantity).strip():
                    st.error("Quantity is required.")
                elif new_end_date < new_order_date:
                    st.error(
                        "Expected Delivery Date cannot be before Date of Order."
                    )
                else:
                    edit_order(
                        editing_order_id,
                        new_item_name,
                        new_supplier,
                        new_quantity,
                        new_order_date,
                        new_end_date,
                        new_price,
                        new_status,
                        new_reminder_date,
                        new_reminder_note,
                    )
                    log_history(
                        "Order Edited",
                        new_item_name.strip(),
                        str(new_quantity).strip(),
                        f"Order '{new_item_name.strip()}' (#{editing_order_id}) edited.",
                    )
                    set_action_message(f"Order #{editing_order_id} updated.", "✏️")
                    st.session_state["editing_order_id"] = None
                    st.rerun()

            if cancel_clicked:
                st.session_state["editing_order_id"] = None
                st.rerun()

    elif selected_order_ids:
        # ------------------------------------------------------------
        # Default state for selected row(s): the action buttons. Edit is
        # only offered when exactly one order is selected; Delete, Mark
        # as Complete, and Cancel Order apply to every selected order.
        # ------------------------------------------------------------
        if selected_count == 1:
            edit_col, delete_col, complete_col, cancel_col, _spacer = st.columns(
                ACTION_BTN_WIDTHS
            )

            with edit_col:
                if st.button(
                    "✏️ Edit",
                    key="edit_btn_selected",
                    use_container_width=True,
                ):
                    st.session_state["pending_action"] = {
                        "order_ids": selected_order_ids,
                        "type": "edit",
                        "step": 1,
                    }
                    st.rerun()
        else:
            delete_col, complete_col, cancel_col, _spacer = st.columns(
                BULK_ACTION_BTN_WIDTHS
            )

        with delete_col:
            if st.button(
                "🗑️ Delete",
                key="delete_btn_selected",
                use_container_width=True,
            ):
                st.session_state["pending_action"] = {
                    "order_ids": selected_order_ids,
                    "type": "delete",
                    "step": 1,
                }
                st.rerun()

        with complete_col:
            if st.button(
                "✅ Mark as Complete",
                key="complete_btn_selected",
                use_container_width=True,
            ):
                st.session_state["pending_action"] = {
                    "order_ids": selected_order_ids,
                    "type": "complete",
                    "step": 1,
                }
                st.rerun()

        with cancel_col:
            if st.button(
                "🚫 Cancel Order",
                key="cancel_btn_selected",
                use_container_width=True,
            ):
                st.session_state["pending_action"] = {
                    "order_ids": selected_order_ids,
                    "type": "cancel",
                    "step": 1,
                }
                st.rerun()

# ------------------------------------------------------------
# Export
# ------------------------------------------------------------
if not df.empty:
    st.divider()
    csv_export_df = df.copy()
    for date_col in ("Order Date", "Expected Delivery", "Reminder Date"):
        csv_export_df[date_col] = csv_export_df[date_col].map(format_display_date)
    csv_data = csv_export_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Export Orders to CSV",
        data=csv_data,
        file_name=f"orders_{date.today().isoformat()}.csv",
        mime="text/csv",
    )

st.divider()
st.caption("🔒 Local-only storage: orders are stored in supplier_orders.db next to this application.")

# Render the latest successful action as a bottom-left popup.
show_action_message()