import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st


# ------------------------------------------------------------
# Page configuration
# ------------------------------------------------------------
st.set_page_config(
    page_title="Inventory",
    page_icon="📦",
    layout="wide",
)

APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = APP_DIR / "supplier_orders.db"


# ------------------------------------------------------------
# Styling
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Page spacing — comfortable, centered reading width on desktop */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* Page title + caption a little more polished */
    h1 {
        font-weight: 800 !important;
        letter-spacing: -0.01em;
    }

    [data-testid="stCaptionContainer"] {
        color: #94a3b8 !important;
    }

    /* Raw material names */
    .inventory-material-name button {
        min-height: 52px !important;
        font-size: 24px !important;
        font-weight: 750 !important;
        text-align: left !important;
        border-radius: 8px !important;
    }

    /* Type rows */
    .inventory-type-name {
        font-size: 17px !important;
        font-weight: 500 !important;
        padding: 8px 0 8px 34px;
        min-height: 42px;
        display: flex;
        align-items: center;
        color: #e5e7eb;
    }

    /* Table header — sits above the first material row like a proper
       spreadsheet header instead of a plain text row. */
    .inventory-header {
        font-size: 12.5px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #94a3b8;
        padding: 6px 0 12px 0;
    }

    /* Small colored badge around each stock figure so it reads at a
       glance, instead of plain unstyled text in a table cell. */
    .inventory-stock-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        background: rgba(148, 163, 184, 0.12);
        font-weight: 600;
        font-size: 14px;
    }

    /* Slightly tighter action buttons */
    .inventory-actions button {
        font-size: 15px !important;
    }

    /* Keep delete buttons compact */
    .inventory-delete button {
        min-width: 52px !important;
    }

    /* Edit (✏️) buttons on the left of every material/type name — sized
       so the icon is never clipped by its narrow column. */
    .inventory-edit-btn button {
        min-width: 44px !important;
        min-height: 44px !important;
        padding: 0 !important;
        font-size: 19px !important;
        line-height: 1 !important;
        border-radius: 8px !important;
    }

    /* General button polish across the page — rounded corners and a
       touch more breathing room, purely cosmetic. */
    .stButton button,
    .stFormSubmitButton button {
        border-radius: 8px !important;
    }

    /* Card-style container used for the summary metrics and for each
       raw material's grouped block (st.container(border=True)). */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        border-color: #263042 !important;
    }

    /* Popover panels (Add Type / Add Stock / Remove Stock / Delete
       confirmations) get the same rounded, elevated card treatment. */
    div[data-baseweb="popover"] [data-testid="stPopoverBody"] {
        border-radius: 12px !important;
    }

    /* Bottom-left inventory action popup */
    .inventory-action-toast {
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
        animation: inventoryToastIn 0.25s ease-out;
    }

    @keyframes inventoryToastIn {
        from {
            opacity: 0;
            transform: translateY(12px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* Make summary metrics clean */
    [data-testid="stMetricValue"] {
        font-weight: 700;
    }

    [data-testid="stMetricLabel"] {
        font-weight: 600;
        color: #94a3b8 !important;
    }

    /* Subtler row dividers between materials, and a soft highlight on
       hover for the raw-material toggle buttons so the table feels more
       interactive without changing what any control does. */
    hr {
        margin: 0.6rem 0 !important;
        border-color: #263042 !important;
    }

    .inventory-material-name button:hover {
        background-color: rgba(59, 130, 246, 0.08) !important;
        border-color: #3b82f6 !important;
    }

    /* Horizontal scrollbar for the inventory table. The inner block is
       given a minimum width wide enough to fit every column comfortably;
       on any viewport narrower than that, the container below scrolls
       left/right instead of squeezing the columns. The direct-child
       combinator here is deliberate: it targets only the single outer
       wrapper block for the whole table, not the per-column blocks
       nested inside each row (which must stay their normal width). */
    .st-key-inventory_table_scroll {
        overflow-x: auto;
        overflow-y: visible;
        padding-bottom: 14px;
    }

    .st-key-inventory_table_scroll > div[data-testid="stVerticalBlock"] {
        min-width: 1100px;
    }

    /* Make that horizontal scrollbar big, colored, and impossible to
       miss — instead of the thin, near-invisible browser default. */
    .st-key-inventory_table_scroll {
        scrollbar-width: auto;
        scrollbar-color: #3b82f6 #1e293b;
    }

    .st-key-inventory_table_scroll::-webkit-scrollbar {
        height: 14px;
    }

    .st-key-inventory_table_scroll::-webkit-scrollbar-track {
        background: #1e293b;
        border-radius: 999px;
    }

    .st-key-inventory_table_scroll::-webkit-scrollbar-thumb {
        background-color: #3b82f6;
        border-radius: 999px;
        border: 2px solid #1e293b;
    }

    .st-key-inventory_table_scroll::-webkit-scrollbar-thumb:hover {
        background-color: #2563eb;
    }

    /* Add Stock ("+") and Remove Stock ("−") buttons: big, bold, clearly
       colored symbol buttons instead of small text-labelled ones. The
       substring attribute selector matches every row's unique key
       (inv_add_stock_btn_<id> / inv_remove_stock_btn_<id>) at once. */
    [class*="st-key-inv_add_stock_btn_"] button {
        background-color: #16a34a !important;
        border-color: #15803d !important;
        color: #ffffff !important;
        font-size: 22px !important;
        font-weight: 800 !important;
        line-height: 1 !important;
        min-height: 44px !important;
        border-radius: 8px !important;
    }

    [class*="st-key-inv_add_stock_btn_"] button:hover {
        background-color: #15803d !important;
        border-color: #166534 !important;
    }

    [class*="st-key-inv_remove_stock_btn_"] button {
        background-color: #dc2626 !important;
        border-color: #b91c1c !important;
        color: #ffffff !important;
        font-size: 22px !important;
        font-weight: 800 !important;
        line-height: 1 !important;
        min-height: 44px !important;
        border-radius: 8px !important;
    }

    [class*="st-key-inv_remove_stock_btn_"] button:hover {
        background-color: #b91c1c !important;
        border-color: #991b1b !important;
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
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_inventory_db():
    """
    Creates the new 2-level inventory structure.

    Level 1: Raw Material
    Level 2: Type

    Existing data from the previous 3-level system is flattened so
    stock is not silently lost:
        Material > Subpart > Variant
    becomes:
        Material > "Subpart — Variant"
    """
    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # New simple two-level type table.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            stock REAL NOT NULL DEFAULT 0,
            unit TEXT NOT NULL DEFAULT 'units',
            unit_cost REAL NOT NULL DEFAULT 0,
            low_stock_threshold REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (material_id) REFERENCES inventory_materials(id)
                ON DELETE CASCADE,
            UNIQUE(material_id, name)
        )
        """
    )

    # --------------------------------------------------------
    # Stock history
    # --------------------------------------------------------
    # Older versions of this project used a column named
    # `variant_id`. The current 2-level inventory uses `type_id`.
    #
    # SQLite CREATE TABLE IF NOT EXISTS does NOT change an
    # already-existing table, so simply creating the table again
    # would leave the old schema in place. Detect that situation
    # and replace the old history table safely.
    # --------------------------------------------------------
    transaction_exists = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name='inventory_stock_transactions'
        """
    ).fetchone()

    if transaction_exists:
        transaction_columns = [
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(inventory_stock_transactions)"
            ).fetchall()
        ]

        if "type_id" not in transaction_columns:
            conn.execute(
                """
                ALTER TABLE inventory_stock_transactions
                RENAME TO inventory_stock_transactions_old
                """
            )

            conn.execute(
                """
                CREATE TABLE inventory_stock_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type_id INTEGER NOT NULL,
                    quantity_added REAL NOT NULL,
                    note TEXT DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (type_id) REFERENCES inventory_types(id)
                        ON DELETE CASCADE
                )
                """
            )

            # Old transaction history referenced the old 3-level
            # variant IDs. The actual current stock is already stored
            # in inventory_types, so old history is not copied into
            # the new table rather than risking incorrect type mapping.
            conn.execute(
                "DROP TABLE inventory_stock_transactions_old"
            )
        else:
            # Make sure the existing table has the expected schema.
            pass
    else:
        conn.execute(
            """
            CREATE TABLE inventory_stock_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_id INTEGER NOT NULL,
                quantity_added REAL NOT NULL,
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (type_id) REFERENCES inventory_types(id)
                    ON DELETE CASCADE
            )
            """
        )

    # --------------------------------------------------------
    # One-time migration from the previous 3-level tables.
    # --------------------------------------------------------
    old_subparts = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name='inventory_subparts'
        """
    ).fetchone()

    old_variants = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name='inventory_variants'
        """
    ).fetchone()

    migration_done = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name='inventory_2level_migration'
        """
    ).fetchone()

    if old_subparts and old_variants and not migration_done:
        variant_columns = [
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(inventory_variants)"
            ).fetchall()
        ]

        # Previous versions may have used either:
        #   subpart_id only
        # or:
        #   material_id + subpart_id
        if "subpart_id" in variant_columns:
            rows = conn.execute(
                """
                SELECT
                    v.id,
                    COALESCE(v.material_id, s.material_id) AS material_id,
                    s.name AS subpart_name,
                    v.name,
                    v.spec,
                    v.stock,
                    v.unit,
                    v.unit_cost,
                    v.low_stock_threshold
                FROM inventory_variants v
                LEFT JOIN inventory_subparts s
                    ON s.id = v.subpart_id
                """
            ).fetchall()

            for row in rows:
                material_id = row["material_id"]
                if material_id is None:
                    continue

                subpart_name = (row["subpart_name"] or "").strip()
                variant_name = (row["name"] or "").strip()

                # Preserve the hierarchy information in the type name.
                if subpart_name:
                    if variant_name:
                        type_name = f"{subpart_name} — {variant_name}"
                    else:
                        type_name = subpart_name
                else:
                    type_name = variant_name

                if not type_name:
                    continue

                # Avoid collisions while preserving the old stock.
                base_name = type_name
                counter = 2
                while conn.execute(
                    """
                    SELECT 1 FROM inventory_types
                    WHERE material_id=? AND name=?
                    """,
                    (material_id, type_name),
                ).fetchone():
                    type_name = f"{base_name} ({counter})"
                    counter += 1

                conn.execute(
                    """
                    INSERT INTO inventory_types
                    (material_id, name, stock, unit, unit_cost, low_stock_threshold)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        material_id,
                        type_name,
                        float(row["stock"] or 0),
                        (row["unit"] or "units").strip(),
                        float(row["unit_cost"] or 0),
                        float(row["low_stock_threshold"] or 0),
                    ),
                )

        conn.execute(
            """
            CREATE TABLE inventory_2level_migration (
                id INTEGER PRIMARY KEY CHECK (id=1),
                migrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "INSERT INTO inventory_2level_migration (id) VALUES (1)"
        )

    # Shared permanent activity log used by the History page. Also created
    # in app.py — CREATE TABLE IF NOT EXISTS makes this safe either way,
    # since both pages point at the same supplier_orders.db file.
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


def get_materials():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT *
            FROM inventory_materials
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()


def get_types(material_id):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT *
            FROM inventory_types
            WHERE material_id=?
            ORDER BY name COLLATE NOCASE
            """,
            (material_id,),
        ).fetchall()


def capture_inventory_state():
    """Capture all editable inventory data for undo/redo."""
    with get_connection() as conn:
        return {
            "inventory_materials": [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM inventory_materials ORDER BY id"
                ).fetchall()
            ],
            "inventory_types": [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM inventory_types ORDER BY id"
                ).fetchall()
            ],
            "inventory_stock_transactions": [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM inventory_stock_transactions ORDER BY id"
                ).fetchall()
            ],
        }


def restore_inventory_state(snapshot):
    """Restore an inventory snapshot without creating a new history entry."""
    with get_connection() as conn:
        # Delete children first because foreign keys are enabled.
        conn.execute("DELETE FROM inventory_stock_transactions")
        conn.execute("DELETE FROM inventory_types")
        conn.execute("DELETE FROM inventory_materials")

        for row in snapshot["inventory_materials"]:
            conn.execute(
                """
                INSERT INTO inventory_materials
                (id, name, created_at)
                VALUES (?, ?, ?)
                """,
                (row["id"], row["name"], row["created_at"]),
            )

        for row in snapshot["inventory_types"]:
            conn.execute(
                """
                INSERT INTO inventory_types
                (id, material_id, name, stock, unit, unit_cost,
                 low_stock_threshold, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["material_id"],
                    row["name"],
                    row["stock"],
                    row["unit"],
                    row["unit_cost"],
                    row["low_stock_threshold"],
                    row["created_at"],
                ),
            )

        for row in snapshot["inventory_stock_transactions"]:
            conn.execute(
                """
                INSERT INTO inventory_stock_transactions
                (id, type_id, quantity_added, note, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["type_id"],
                    row["quantity_added"],
                    row["note"],
                    row["created_at"],
                ),
            )

        # Keep AUTOINCREMENT counters ahead of restored IDs.
        for table in (
            "inventory_materials",
            "inventory_types",
            "inventory_stock_transactions",
        ):
            max_id = conn.execute(
                f"SELECT COALESCE(MAX(id), 0) FROM {table}"
            ).fetchone()[0]

            conn.execute(
                "DELETE FROM sqlite_sequence WHERE name=?",
                (table,),
            )

            if max_id:
                conn.execute(
                    """
                    INSERT INTO sqlite_sequence (name, seq)
                    VALUES (?, ?)
                    """,
                    (table, max_id),
                )

        conn.commit()


def record_history(before_state):
    """Store a successful pre-change state and clear the redo branch."""
    st.session_state.setdefault("inventory_undo_stack", [])
    st.session_state.setdefault("inventory_redo_stack", [])

    st.session_state["inventory_undo_stack"].append(before_state)

    # Once a new action happens after undo, the old redo branch is invalid.
    st.session_state["inventory_redo_stack"].clear()


def undo_inventory_action():
    undo_stack = st.session_state.setdefault("inventory_undo_stack", [])
    redo_stack = st.session_state.setdefault("inventory_redo_stack", [])

    if not undo_stack:
        return False

    current_state = capture_inventory_state()
    previous_state = undo_stack.pop()

    restore_inventory_state(previous_state)
    redo_stack.append(current_state)

    set_action_message("Undid the last inventory action.", "↶")
    return True


def redo_inventory_action():
    undo_stack = st.session_state.setdefault("inventory_undo_stack", [])
    redo_stack = st.session_state.setdefault("inventory_redo_stack", [])

    if not redo_stack:
        return False

    current_state = capture_inventory_state()
    next_state = redo_stack.pop()

    restore_inventory_state(next_state)
    undo_stack.append(current_state)

    set_action_message("Redid the last inventory action.", "↷")
    return True


def add_material(name):
    before_state = capture_inventory_state()

    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO inventory_materials (name) VALUES (?)",
                (name.strip(),),
            )
            conn.commit()
    except Exception:
        raise

    record_history(before_state)


def add_type(
    material_id,
    name,
    unit,
    unit_cost,
    low_stock_threshold,
):
    before_state = capture_inventory_state()

    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO inventory_types
                (material_id, name, unit, unit_cost, low_stock_threshold)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    material_id,
                    name.strip(),
                    unit.strip() or "units",
                    float(unit_cost),
                    float(low_stock_threshold),
                ),
            )
            conn.commit()
    except Exception:
        raise

    record_history(before_state)


def add_stock(type_id, quantity, note):
    before_state = capture_inventory_state()

    try:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE inventory_types
                SET stock = stock + ?
                WHERE id=?
                """,
                (float(quantity), type_id),
            )

            conn.execute(
                """
                INSERT INTO inventory_stock_transactions
                (type_id, quantity_added, note)
                VALUES (?, ?, ?)
                """,
                (type_id, float(quantity), note.strip()),
            )

            conn.commit()
    except Exception:
        raise

    record_history(before_state)


def delete_material(material_id):
    before_state = capture_inventory_state()

    try:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM inventory_materials WHERE id=?",
                (material_id,),
            )
            conn.commit()
    except Exception:
        raise

    record_history(before_state)


def delete_type(type_id):
    before_state = capture_inventory_state()

    try:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM inventory_types WHERE id=?",
                (type_id,),
            )
            conn.commit()
    except Exception:
        raise

    record_history(before_state)


def edit_material(material_id, name):
    """Update a raw material's name only — this table has no stock/unit/
    unit_cost fields of its own (those live on inventory_types)."""
    before_state = capture_inventory_state()

    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE inventory_materials SET name = ? WHERE id = ?",
                (name.strip(), material_id),
            )
            conn.commit()
    except Exception:
        raise

    record_history(before_state)


def edit_type(type_id, name, stock, unit, unit_cost):
    """Update a type's (subtype's) name, current stock, unit, and unit
    cost in place — same row/id, no new row, no history rows touched."""
    before_state = capture_inventory_state()

    try:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE inventory_types
                SET name = ?, stock = ?, unit = ?, unit_cost = ?
                WHERE id = ?
                """,
                (
                    name.strip(),
                    float(stock),
                    unit.strip() or "units",
                    float(unit_cost),
                    type_id,
                ),
            )
            conn.commit()
    except Exception:
        raise

    record_history(before_state)


def remove_stock(type_id, quantity, note):
    """Reduce stock for a type and record the removal."""
    before_state = capture_inventory_state()

    try:
        with get_connection() as conn:
            current = conn.execute(
                "SELECT stock FROM inventory_types WHERE id=?",
                (type_id,),
            ).fetchone()

            if current is None:
                raise ValueError("Type not found.")

            current_stock = float(current["stock"])
            quantity = float(quantity)

            if quantity > current_stock:
                raise ValueError(
                    f"Cannot remove {format_number(quantity)}. "
                    f"Only {format_number(current_stock)} is currently in stock."
                )

            conn.execute(
                """
                UPDATE inventory_types
                SET stock = stock - ?
                WHERE id=?
                """,
                (quantity, type_id),
            )

            conn.execute(
                """
                INSERT INTO inventory_stock_transactions
                (type_id, quantity_added, note)
                VALUES (?, ?, ?)
                """,
                (
                    type_id,
                    -quantity,
                    note.strip() or "Stock removed",
                ),
            )

            conn.commit()
    except Exception:
        raise

    record_history(before_state)



def format_number(value):
    value = float(value)

    if value.is_integer():
        return f"{int(value):,}"

    return f"{value:,.2f}".rstrip("0").rstrip(".")


def stock_summary(types):
    """
    Aggregate a raw material's stock without incorrectly combining
    different units.

    Example:
        1,250 meters
    or:
        50 spools + 6 rolls
    """
    if not types:
        return "—"

    by_unit = {}

    for item in types:
        unit = (item["unit"] or "units").strip()
        by_unit[unit] = by_unit.get(unit, 0) + float(item["stock"])

    return " + ".join(
        f"{format_number(quantity)} {unit}"
        for unit, quantity in by_unit.items()
    )


def inventory_counts():
    with get_connection() as conn:
        materials = conn.execute(
            "SELECT COUNT(*) FROM inventory_materials"
        ).fetchone()[0]

        total_types = conn.execute(
            "SELECT COUNT(*) FROM inventory_types"
        ).fetchone()[0]

        low = conn.execute(
            """
            SELECT COUNT(*)
            FROM inventory_types
            WHERE stock > 0
              AND low_stock_threshold > 0
              AND stock <= low_stock_threshold
            """
        ).fetchone()[0]

        out = conn.execute(
            """
            SELECT COUNT(*)
            FROM inventory_types
            WHERE stock <= 0
            """
        ).fetchone()[0]

    return materials, total_types, low, out


def state_key(material_id):
    return f"inventory_material_open_{material_id}"


def toggle_material(material_id):
    key = state_key(material_id)
    st.session_state[key] = not st.session_state.get(key, False)


def set_action_message(message, icon="✅"):
    st.session_state["inventory_action_message"] = f"{icon}  {message}"


def show_action_message():
    message = st.session_state.pop("inventory_action_message", None)

    if message:
        st.markdown(
            f'<div class="inventory-action-toast">{message}</div>',
            unsafe_allow_html=True,
        )


# ------------------------------------------------------------
# Initialize
# ------------------------------------------------------------
init_inventory_db()


# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
st.session_state.setdefault("inventory_undo_stack", [])
st.session_state.setdefault("inventory_redo_stack", [])

top_left, top_right = st.columns([2.5, 1.5])

with top_left:
    st.title("📦 Inventory")
    st.caption("Manage your raw materials and track available stock.")

with top_right:
    undo_col, redo_col = st.columns(2)

    with undo_col:
        if st.button(
            "↶ Undo",
            use_container_width=True,
            disabled=not st.session_state["inventory_undo_stack"],
            help="Undo the last inventory action.",
        ):
            if undo_inventory_action():
                st.rerun()

    with redo_col:
        if st.button(
            "Redo ↷",
            use_container_width=True,
            disabled=not st.session_state["inventory_redo_stack"],
            help="Redo the last undone inventory action.",
        ):
            if redo_inventory_action():
                st.rerun()

# ------------------------------------------------------------
# Toolbar — search and "Add Raw Material" grouped together so related
# controls sit next to each other instead of stacked on their own lines.
# ------------------------------------------------------------
with st.container(border=True):
    toolbar_search, toolbar_add = st.columns([3, 1])

    with toolbar_search:
        search = st.text_input(
            "Search",
            placeholder="🔎 Search materials or types...",
            label_visibility="collapsed",
        )

    with toolbar_add:
        with st.popover("＋ Add Raw Material", use_container_width=True):
            st.markdown("### Add Raw Material")

            with st.form("add_material_form", clear_on_submit=True):
                material_name = st.text_input(
                    "Raw Material Name *",
                    placeholder="e.g. Wire, Beads & Stones, Clasps & Hooks",
                )

                save_material = st.form_submit_button(
                    "Save Raw Material",
                    type="primary",
                    use_container_width=True,
                )

            if save_material:
                if not material_name.strip():
                    st.error("Raw Material Name is required.")
                else:
                    try:
                        add_material(material_name)
                        set_action_message(
                            f"Raw material “{material_name.strip()}” added."
                        )
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("That raw material already exists.")


# ------------------------------------------------------------
# Summary cards
# ------------------------------------------------------------
total_materials, total_types, low_stock, out_of_stock = inventory_counts()

c1, c2, c3, c4 = st.columns(4)

with c1:
    with st.container(border=True):
        st.metric("Total Materials", total_materials)

with c2:
    with st.container(border=True):
        st.metric("Total Stock Items", total_types)

with c3:
    with st.container(border=True):
        st.metric("Low Stock Items", low_stock)

with c4:
    with st.container(border=True):
        st.metric("Out of Stock", out_of_stock)

st.divider()


# ------------------------------------------------------------
# Search helper
# ------------------------------------------------------------
def material_matches(material, types, query):
    if not query.strip():
        return True

    q = query.strip().lower()

    if q in material["name"].lower():
        return True

    return any(q in item["name"].lower() for item in types)


# ------------------------------------------------------------
# Table
# ------------------------------------------------------------
# ------------------------------------------------------------
# Horizontally scrollable table area — everything from the header
# row through the last material/type row lives inside this bordered,
# horizontally-scrolling container so all columns can be reached by
# sliding left/right, without altering any of the table's own logic.
# ------------------------------------------------------------
with st.container(key="inventory_table_scroll"):
    header = st.columns([4.0, 1.55, 1.05, 1.45, 1.85, 1.15])

    header[0].markdown(
        '<div class="inventory-header">Item / Type</div>',
        unsafe_allow_html=True,
    )
    header[1].markdown(
        '<div class="inventory-header">Current Stock</div>',
        unsafe_allow_html=True,
    )
    header[2].markdown(
        '<div class="inventory-header">Unit</div>',
        unsafe_allow_html=True,
    )
    header[3].markdown(
        '<div class="inventory-header">Unit Cost (₹)</div>',
        unsafe_allow_html=True,
    )
    header[4].markdown(
        '<div class="inventory-header">Actions</div>',
        unsafe_allow_html=True,
    )
    header[5].markdown(
        '<div class="inventory-header">Delete</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    materials = get_materials()

    if not materials:
        st.info(
            "No raw materials yet. Click **＋ Add Raw Material** to create your first one."
        )
    else:
        shown_any = False

        for material in materials:
            material_id = material["id"]
            types = get_types(material_id)

            if not material_matches(material, types, search):
                continue

            shown_any = True
            is_open = st.session_state.get(
                state_key(material_id),
                False,
            )

            # ----------------------------------------------------
            # Raw material row
            # ----------------------------------------------------
            row = st.columns([4.0, 1.55, 1.05, 1.45, 1.85, 1.15])

            with row[0]:
                edit_col, name_col = st.columns([0.8, 5.2])

                with edit_col:
                    st.markdown(
                        '<div class="inventory-edit-btn">',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "✏️",
                        key=f"material_edit_{material_id}",
                        help="Edit this raw material",
                        use_container_width=True,
                    ):
                        st.session_state[f"editing_material_{material_id}"] = (
                            not st.session_state.get(
                                f"editing_material_{material_id}", False
                            )
                        )
                        st.session_state[f"confirm_material_{material_id}"] = False
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

                with name_col:
                    st.markdown(
                        '<div class="inventory-material-name">',
                        unsafe_allow_html=True,
                    )

                    arrow = "▼" if is_open else "▶"

                    if st.button(
                        f"{arrow}  {material['name']}",
                        key=f"material_toggle_{material_id}",
                        use_container_width=True,
                    ):
                        toggle_material(material_id)
                        st.rerun()

                    st.markdown("</div>", unsafe_allow_html=True)

            # Raw-material stock is intentionally left blank.
            # Stock is tracked only at the Type level.
            row[1].write("—")
            row[2].write("—")
            row[3].write("—")

            # Raw material action: add a type directly under it.
            with row[4].popover(
                "＋ Add Type",
                use_container_width=True,
            ):
                st.markdown(f"### Add Type to {material['name']}")

                with st.form(
                    f"add_type_form_{material_id}",
                    clear_on_submit=True,
                ):
                    type_name = st.text_input(
                        "Type Name *",
                        placeholder="e.g. Copper Wire",
                    )

                    unit = st.text_input(
                        "Unit *",
                        value="pieces",
                        placeholder="e.g. meters, pieces, rolls",
                    )

                    unit_cost = st.number_input(
                        "Unit Cost (₹)",
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                    )

                    threshold = st.number_input(
                        "Low Stock Alert At",
                        min_value=0.0,
                        step=1.0,
                        value=0.0,
                        help="Set to 0 to disable the low-stock alert.",
                    )

                    save_type = st.form_submit_button(
                        "Save Type",
                        type="primary",
                        use_container_width=True,
                    )

                if save_type:
                    if not type_name.strip():
                        st.error("Type Name is required.")
                    elif not unit.strip():
                        st.error("Unit is required.")
                    else:
                        try:
                            add_type(
                                material_id,
                                type_name,
                                unit,
                                unit_cost,
                                threshold,
                            )
                            set_action_message(
                                f"Type “{type_name.strip()}” added to "
                                f"{material['name']}."
                            )
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error(
                                "That type already exists under this raw material."
                            )

            # Raw material delete.
            with row[5].popover(
                "🗑️",
                use_container_width=True,
            ):
                st.markdown(f"### Delete {material['name']}?")
                st.warning(
                    "This will delete the raw material, all its types, "
                    "and their stock history."
                )

                if st.button(
                    "Yes, Delete",
                    key=f"delete_material_{material_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    delete_material(material_id)
                    set_action_message(
                        f"Raw material “{material['name']}” deleted.",
                        "🗑️",
                    )
                    st.rerun()

            # ----------------------------------------------------
            # Edit raw material (name only — see edit_material() note)
            # ----------------------------------------------------
            if st.session_state.get(f"editing_material_{material_id}", False):
                with st.container(border=True):
                    st.markdown(f"**✏️ Edit Raw Material — {material['name']}**")

                    if not st.session_state.get(
                        f"confirm_material_{material_id}", False
                    ):
                        new_material_name = st.text_input(
                            "Name",
                            value=material["name"],
                            key=f"edit_material_name_{material_id}",
                        )

                        save_col, cancel_col = st.columns(2)
                        with save_col:
                            if st.button(
                                "Save",
                                key=f"save_material_{material_id}",
                                type="primary",
                                use_container_width=True,
                            ):
                                if not new_material_name.strip():
                                    st.error("Name is required.")
                                else:
                                    st.session_state[
                                        f"pending_material_name_{material_id}"
                                    ] = new_material_name
                                    st.session_state[
                                        f"confirm_material_{material_id}"
                                    ] = True
                                    st.rerun()
                        with cancel_col:
                            if st.button(
                                "Cancel",
                                key=f"cancel_material_edit_{material_id}",
                                use_container_width=True,
                            ):
                                st.session_state[
                                    f"editing_material_{material_id}"
                                ] = False
                                st.rerun()
                    else:
                        st.warning("Are you sure you want to save these changes?")
                        pending_name = st.session_state.get(
                            f"pending_material_name_{material_id}", material["name"]
                        )
                        confirm_col, cancel2_col = st.columns(2)
                        with confirm_col:
                            if st.button(
                                "Confirm & Save",
                                key=f"confirm_material_save_{material_id}",
                                type="primary",
                                use_container_width=True,
                            ):
                                edit_material(material_id, pending_name)
                                set_action_message(
                                    f"Raw material “{pending_name.strip()}” updated.",
                                    "✏️",
                                )
                                st.session_state[
                                    f"editing_material_{material_id}"
                                ] = False
                                st.session_state[
                                    f"confirm_material_{material_id}"
                                ] = False
                                st.rerun()
                        with cancel2_col:
                            if st.button(
                                "Cancel",
                                key=f"cancel_material_confirm_{material_id}",
                                use_container_width=True,
                            ):
                                st.session_state[
                                    f"confirm_material_{material_id}"
                                ] = False
                                st.session_state[
                                    f"editing_material_{material_id}"
                                ] = False
                                st.rerun()

            # ----------------------------------------------------
            # Type rows
            # ----------------------------------------------------
            if is_open:
                if not types:
                    empty = st.columns([4.0, 1.55, 1.05, 1.45, 1.85, 1.15])
                    empty[0].markdown(
                        '<div class="inventory-type-name">↳ No types yet — use ＋ Add Type above.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    for item in types:
                        type_id = item["id"]

                        type_row = st.columns(
                            [4.0, 1.55, 1.05, 1.45, 1.85, 1.15]
                        )

                        with type_row[0]:
                            type_edit_col, type_name_col = st.columns([0.9, 5.1])

                            with type_edit_col:
                                st.markdown(
                                    '<div class="inventory-edit-btn">',
                                    unsafe_allow_html=True,
                                )
                                if st.button(
                                    "✏️",
                                    key=f"type_edit_{type_id}",
                                    help="Edit this type",
                                    use_container_width=True,
                                ):
                                    st.session_state[
                                        f"editing_type_{type_id}"
                                    ] = not st.session_state.get(
                                        f"editing_type_{type_id}", False
                                    )
                                    st.session_state[f"confirm_type_{type_id}"] = False
                                    st.rerun()
                                st.markdown("</div>", unsafe_allow_html=True)

                            with type_name_col:
                                st.markdown(
                                    f'<div class="inventory-type-name">↳ {item["name"]}</div>',
                                    unsafe_allow_html=True,
                                )

                        stock_text = (
                            f"{format_number(item['stock'])}"
                        )

                        if item["stock"] <= 0:
                            stock_text = "🔴 " + stock_text
                        elif (
                            item["low_stock_threshold"] > 0
                            and item["stock"] <= item["low_stock_threshold"]
                        ):
                            stock_text = "🟠 " + stock_text

                        type_row[1].markdown(
                            f'<span class="inventory-stock-badge">{stock_text}</span>',
                            unsafe_allow_html=True,
                        )
                        type_row[2].write(item["unit"])
                        type_row[3].write(
                            f"₹{float(item['unit_cost']):,.2f}"
                        )

                        # Add Stock + Remove Stock
                        with type_row[4]:
                            action_add, action_remove = st.columns(2)

                            with action_add:
                                with st.container(
                                    key=f"inv_add_stock_btn_{type_id}"
                                ):
                                    with st.popover(
                                        "＋",
                                        use_container_width=True,
                                        help=f"Add Stock — {item['name']}",
                                    ):
                                        st.markdown(f"### Add Stock — {item['name']}")
                                        st.caption(
                                            f"Current stock: "
                                            f"{format_number(item['stock'])} "
                                            f"{item['unit']}"
                                        )

                                        with st.form(
                                            f"stock_form_{type_id}",
                                            clear_on_submit=True,
                                        ):
                                            quantity = st.number_input(
                                                f"Quantity to add ({item['unit']})",
                                                min_value=0.01,
                                                value=1.0,
                                                step=1.0,
                                            )

                                            note = st.text_input(
                                                "Note",
                                                placeholder="e.g. Received from supplier",
                                            )

                                            add_button = st.form_submit_button(
                                                "Add to Stock",
                                                type="primary",
                                                use_container_width=True,
                                            )

                                        if add_button:
                                            add_stock(
                                                type_id,
                                                quantity,
                                                note,
                                            )
                                            log_history(
                                                "Stock Added",
                                                item["name"],
                                                format_number(quantity),
                                                f"Added {format_number(quantity)} "
                                                f"{item['unit']} to {item['name']}.",
                                            )
                                            set_action_message(
                                                f"Added {format_number(quantity)} "
                                                f"to {item['name']}."
                                            )
                                            st.rerun()

                            with action_remove:
                                with st.container(
                                    key=f"inv_remove_stock_btn_{type_id}"
                                ):
                                    with st.popover(
                                        "−",
                                        use_container_width=True,
                                        help=f"Remove Stock — {item['name']}",
                                    ):
                                        st.markdown(f"### Remove Stock — {item['name']}")
                                        st.caption(
                                            f"Current stock: "
                                            f"{format_number(item['stock'])} "
                                            f"{item['unit']}"
                                        )

                                        with st.form(
                                            f"remove_stock_form_{type_id}",
                                            clear_on_submit=True,
                                        ):
                                            current_stock = float(item["stock"])

                                            # If there is no stock, don't create an invalid
                                            # number input (Streamlit requires value <= max_value).
                                            remove_max = current_stock if current_stock > 0 else 0.01
                                            remove_default = min(1.0, remove_max)

                                            remove_quantity = st.number_input(
                                                f"Quantity to remove ({item['unit']})",
                                                min_value=0.01,
                                                max_value=remove_max,
                                                value=remove_default,
                                                step=1.0,
                                                disabled=current_stock <= 0,
                                            )

                                            remove_note = st.text_input(
                                                "Reason / Note",
                                                placeholder="e.g. Used for production",
                                            )

                                            remove_button = st.form_submit_button(
                                                "Remove from Stock",
                                                type="primary",
                                                use_container_width=True,
                                            )

                                        if remove_button:
                                            if current_stock <= 0:
                                                st.error("There is no stock to remove.")
                                            else:
                                                try:
                                                    remove_stock(
                                                        type_id,
                                                        remove_quantity,
                                                        remove_note,
                                                    )
                                                    log_history(
                                                        "Stock Removed",
                                                        item["name"],
                                                        format_number(remove_quantity),
                                                        f"Removed "
                                                        f"{format_number(remove_quantity)} "
                                                        f"{item['unit']} from {item['name']}.",
                                                    )
                                                    set_action_message(
                                                        f"Removed "
                                                        f"{format_number(remove_quantity)} "
                                                        f"from {item['name']}."
                                                    )
                                                    st.rerun()
                                                except ValueError as exc:
                                                    st.error(str(exc))

                        # Delete type
                        with type_row[5].popover(
                            "🗑️",
                            use_container_width=True,
                        ):
                            st.markdown(f"### Delete {item['name']}?")

                            if st.button(
                                "Yes, Delete",
                                key=f"delete_type_{type_id}",
                                type="primary",
                                use_container_width=True,
                            ):
                                delete_type(type_id)
                                set_action_message(
                                    f"Type “{item['name']}” deleted.",
                                    "🗑️",
                                )
                                st.rerun()

                        # ----------------------------------------------------
                        # Edit type (subtype) — Name, Current Stock, Unit,
                        # Unit Cost. Existing stock-transaction history rows
                        # are untouched; this only updates this one row.
                        # ----------------------------------------------------
                        if st.session_state.get(
                            f"editing_type_{type_id}", False
                        ):
                            with st.container(border=True):
                                st.markdown(
                                    f"**✏️ Edit Type — {item['name']}**"
                                )

                                if not st.session_state.get(
                                    f"confirm_type_{type_id}", False
                                ):
                                    et_col1, et_col2 = st.columns(2)
                                    with et_col1:
                                        new_type_name = st.text_input(
                                            "Name",
                                            value=item["name"],
                                            key=f"edit_type_name_{type_id}",
                                        )
                                        new_type_stock = st.number_input(
                                            "Current Stock",
                                            value=float(item["stock"]),
                                            step=1.0,
                                            key=f"edit_type_stock_{type_id}",
                                        )
                                    with et_col2:
                                        new_type_unit = st.text_input(
                                            "Unit",
                                            value=item["unit"],
                                            key=f"edit_type_unit_{type_id}",
                                        )
                                        new_type_cost = st.number_input(
                                            "Unit Cost (₹)",
                                            value=float(item["unit_cost"]),
                                            min_value=0.0,
                                            step=0.01,
                                            format="%.2f",
                                            key=f"edit_type_cost_{type_id}",
                                        )

                                    save_col, cancel_col = st.columns(2)
                                    with save_col:
                                        if st.button(
                                            "Save",
                                            key=f"save_type_{type_id}",
                                            type="primary",
                                            use_container_width=True,
                                        ):
                                            if not new_type_name.strip():
                                                st.error("Name is required.")
                                            elif not new_type_unit.strip():
                                                st.error("Unit is required.")
                                            else:
                                                st.session_state[
                                                    f"pending_type_edit_{type_id}"
                                                ] = {
                                                    "name": new_type_name,
                                                    "stock": new_type_stock,
                                                    "unit": new_type_unit,
                                                    "unit_cost": new_type_cost,
                                                }
                                                st.session_state[
                                                    f"confirm_type_{type_id}"
                                                ] = True
                                                st.rerun()
                                    with cancel_col:
                                        if st.button(
                                            "Cancel",
                                            key=f"cancel_type_edit_{type_id}",
                                            use_container_width=True,
                                        ):
                                            st.session_state[
                                                f"editing_type_{type_id}"
                                            ] = False
                                            st.rerun()
                                else:
                                    st.warning(
                                        "Are you sure you want to save these changes?"
                                    )
                                    pending_type = st.session_state.get(
                                        f"pending_type_edit_{type_id}",
                                        {
                                            "name": item["name"],
                                            "stock": item["stock"],
                                            "unit": item["unit"],
                                            "unit_cost": item["unit_cost"],
                                        },
                                    )
                                    confirm_col, cancel2_col = st.columns(2)
                                    with confirm_col:
                                        if st.button(
                                            "Confirm & Save",
                                            key=f"confirm_type_save_{type_id}",
                                            type="primary",
                                            use_container_width=True,
                                        ):
                                            edit_type(
                                                type_id,
                                                pending_type["name"],
                                                pending_type["stock"],
                                                pending_type["unit"],
                                                pending_type["unit_cost"],
                                            )
                                            set_action_message(
                                                f"“{pending_type['name'].strip()}” updated.",
                                                "✏️",
                                            )
                                            st.session_state[
                                                f"editing_type_{type_id}"
                                            ] = False
                                            st.session_state[
                                                f"confirm_type_{type_id}"
                                            ] = False
                                            st.rerun()
                                    with cancel2_col:
                                        if st.button(
                                            "Cancel",
                                            key=f"cancel_type_confirm_{type_id}",
                                            use_container_width=True,
                                        ):
                                            st.session_state[
                                                f"confirm_type_{type_id}"
                                            ] = False
                                            st.session_state[
                                                f"editing_type_{type_id}"
                                            ] = False
                                            st.rerun()

            st.divider()

        if not shown_any:
            st.info("No materials or types match your search.")


st.caption(
    "Inventory data is stored in supplier_orders.db beside the application."
)

# Render the latest successful action as a bottom-left popup.
show_action_message()