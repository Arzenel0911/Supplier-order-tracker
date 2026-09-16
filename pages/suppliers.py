import sqlite3
from datetime import date, datetime
from pathlib import Path

import streamlit as st

# ------------------------------------------------------------
# Page configuration
# ------------------------------------------------------------
st.set_page_config(
    page_title="Suppliers",
    page_icon="👥",
    layout="wide",
)

# Same project layout as inventory.py / history.py: this file lives in
# pages/, so the database sits one level up, next to app.py.
APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = APP_DIR / "supplier_orders.db"


# ------------------------------------------------------------
# Styling — dark, compact, premium, iPad-first. Scoped to this page only.
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1300px;
    }

    /* ---------- Header ---------- */
    h1 {
        font-weight: 800 !important;
        letter-spacing: -0.01em;
        font-size: 2.1rem !important;
        margin-bottom: 0.1rem !important;
    }

    [data-testid="stCaptionContainer"] {
        color: #94a3b8 !important;
        font-size: 15px !important;
        margin-top: 0 !important;
    }

    /* ---------- Search bar ---------- */
    .suppliers-search input {
        font-size: 16px !important;
        padding: 12px 16px !important;
        border-radius: 12px !important;
        background: #161d2b !important;
        border: 1px solid #263042 !important;
        height: 48px !important;
    }

    /* ---------- Generic buttons ---------- */
    .stButton button,
    .stFormSubmitButton button {
        border-radius: 10px !important;
        font-size: 15px !important;
    }

    /* ---------- Cards (bordered containers) ---------- */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px !important;
        border-color: #263042 !important;
        background: #141b28 !important;
    }

    /* Tight vertical rhythm between grid cards and sections */
    div[data-testid="element-container"]:has(> div[data-testid="stVerticalBlockBorderWrapper"]) {
        margin-bottom: 10px !important;
    }

    /* ---------- Supplier card button (arrow + name row) ---------- */
    .supplier-card-btn button {
        min-height: 46px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        text-align: left !important;
        border-radius: 10px !important;
        padding: 4px 14px !important;
        background: transparent !important;
        border: none !important;
    }

    .supplier-card-btn button:hover {
        background: rgba(59, 130, 246, 0.08) !important;
    }

    /* Count badges under each supplier card */
    .supplier-card-counts {
        display: flex;
        gap: 8px;
        padding: 0 12px 10px 12px;
        flex-wrap: wrap;
    }

    .supplier-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 13px;
        font-weight: 600;
        white-space: nowrap;
    }

    .supplier-badge-progress {
        background: rgba(59, 130, 246, 0.14);
        color: #93c5fd;
    }

    .supplier-badge-done {
        background: rgba(34, 197, 94, 0.14);
        color: #86efac;
    }

    /* ---------- Selected-supplier expanded panel ---------- */
    .supplier-panel-title {
        font-size: 20px;
        font-weight: 800;
        color: #f1f5f9;
    }

    .supplier-subview-btn button {
        min-height: 42px !important;
        font-size: 15.5px !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
    }

    /* ---------- Give button in the table ---------- */
    /* Wrapper centers the button in the row and matches the row's
       natural (text-cell) height, so it lines up with ID / Item Name /
       etc. in the same row instead of sitting taller/off-center. */
    .suppliers-give-btn {
        display: flex;
        align-items: center;
        min-height: 34px;
    }

    .suppliers-give-btn button {
        min-height: 34px !important;
        font-size: 14.5px !important;
        font-weight: 700 !important;
        background-color: #3b82f6 !important;
        border-color: #2563eb !important;
        color: #ffffff !important;
        border-radius: 9px !important;
        padding: 4px 10px !important;
        margin: 0 !important;
    }

    .suppliers-give-btn button:hover {
        background-color: #2563eb !important;
    }

    /* ---------- Compact table ---------- */
    .suppliers-table-header {
        font-size: 12.5px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #94a3b8;
        padding: 2px 4px 7px 4px;
        border-bottom: 2px solid #263042;
    }

    .suppliers-table-cell {
        display: flex;
        align-items: center;
        min-height: 34px;
        font-size: 14.5px;
        padding: 6px 4px;
        color: #e2e8f0;
        white-space: pre-line;
        line-height: 1.3;
    }

    /* Every column in each In Progress row — vertically center all
       cells against each other (this is what actually keeps the Give
       button lined up with the ID/Item Name/etc. text beside it,
       regardless of small height differences between a button and
       plain text), and remove Streamlit's own default gap between
       consecutive rows so they sit closer together. */
    .st-key-suppliers_inprogress_rows [data-testid="stHorizontalBlock"] {
        align-items: center !important;
        margin-bottom: 0 !important;
    }

    .st-key-suppliers_inprogress_rows [data-testid="element-container"] {
        margin-bottom: 0 !important;
    }

    /* ---------- Give dialog ---------- */
    .give-dialog-subtitle {
        color: #94a3b8;
        font-size: 14px;
        margin: -6px 0 14px 0;
    }

    .give-row-header {
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #94a3b8;
        padding-bottom: 6px;
        border-bottom: 1px solid #263042;
        margin-bottom: 4px;
    }

    .suppliers-give-available {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 8px;
        background: rgba(148, 163, 184, 0.12);
        font-size: 14.5px;
        font-weight: 700;
        color: #e2e8f0;
        white-space: nowrap;
    }

    /* Negative available stock reads clearly as a warning, still shown
       normally (never hidden or blocked). */
    .suppliers-give-available.negative {
        background: rgba(239, 68, 68, 0.14);
        color: #fca5a5;
    }

    /* ---------- Toast ---------- */
    .suppliers-action-toast {
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
        animation: suppliersToastIn 0.25s ease-out;
    }

    @keyframes suppliersToastIn {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# Database  (unchanged business logic — schema, queries, allocation
# math, and history logging are identical to before; only the
# presentation layer below this section was redesigned)
# ------------------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_suppliers_db():
    """Idempotent. This page reuses the existing orders / inventory /
    history tables as-is (same schema, same columns) and only adds the
    one genuinely new table this feature needs: order_raw_materials."""
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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_stock_transactions (
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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS order_raw_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            type_id INTEGER,
            quantity REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (material_id) REFERENCES inventory_materials(id),
            FOREIGN KEY (type_id) REFERENCES inventory_types(id)
        )
        """
    )
    conn.commit()
    conn.close()


def log_history(action_type, item_name, quantity, description):
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


def format_number(value):
    value = float(value)
    if value.is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def format_display_date(iso_string):
    if not iso_string:
        return ""
    try:
        return date.fromisoformat(iso_string).strftime("%d-%m-%Y")
    except (ValueError, TypeError):
        return iso_string


def get_all_supplier_names():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT DISTINCT supplier_name
        FROM orders
        WHERE TRIM(COALESCE(supplier_name, '')) != ''
        ORDER BY supplier_name COLLATE NOCASE
        """
    ).fetchall()
    conn.close()
    return [r["supplier_name"] for r in rows]


def get_orders_by_supplier_and_status(supplier_name, status):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM orders
        WHERE supplier_name = ? AND status = ?
        ORDER BY id DESC
        """,
        (supplier_name, status),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_orders_by_status(supplier_name, status):
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM orders WHERE supplier_name = ? AND status = ?",
        (supplier_name, status),
    ).fetchone()
    conn.close()
    return row["n"] if row else 0


def get_materials():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM inventory_materials ORDER BY name COLLATE NOCASE"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_types(material_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM inventory_types WHERE material_id = ? ORDER BY name COLLATE NOCASE",
        (material_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_order_allocations(order_id):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT orm.id, orm.order_id, orm.material_id, orm.type_id, orm.quantity,
               m.name AS material_name, t.name AS type_name, t.unit AS unit
        FROM order_raw_materials orm
        JOIN inventory_materials m ON m.id = orm.material_id
        LEFT JOIN inventory_types t ON t.id = orm.type_id
        WHERE orm.order_id = ?
        ORDER BY orm.id
        """,
        (order_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def format_allocations_display(allocations):
    if not allocations:
        return "—"
    parts = []
    for a in allocations:
        label = a["material_name"]
        if a.get("type_name"):
            label += f" ({a['type_name']})"
        qty_text = format_number(a["quantity"])
        unit = (a.get("unit") or "").strip()
        parts.append(f"{label}: {qty_text} {unit}".rstrip())
    return "\n".join(parts)


def save_order_allocation(order_id, new_rows):
    """Reverses any existing allocation for this order (returns that stock
    to Inventory), replaces the order's allocation with the new one
    (deducts stock — negative stock is allowed and never blocked), and
    records both movements in the EXISTING inventory_stock_transactions
    table plus the shared history_log. Runs as one transaction."""
    old_rows = get_order_allocations(order_id)

    conn = get_connection()
    order = conn.execute(
        "SELECT item_name FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    order_label = order["item_name"] if order else f"Order #{order_id}"

    try:
        for old in old_rows:
            if old["type_id"] is not None:
                conn.execute(
                    "UPDATE inventory_types SET stock = stock + ? WHERE id = ?",
                    (float(old["quantity"]), old["type_id"]),
                )
                conn.execute(
                    """
                    INSERT INTO inventory_stock_transactions
                    (type_id, quantity_added, note)
                    VALUES (?, ?, ?)
                    """,
                    (
                        old["type_id"],
                        float(old["quantity"]),
                        f"Reversed previous allocation for Order #{order_id} "
                        f"({order_label})",
                    ),
                )

        conn.execute(
            "DELETE FROM order_raw_materials WHERE order_id = ?", (order_id,)
        )

        for new in new_rows:
            conn.execute(
                """
                INSERT INTO order_raw_materials
                (order_id, material_id, type_id, quantity)
                VALUES (?, ?, ?, ?)
                """,
                (
                    order_id,
                    new["material_id"],
                    new["type_id"],
                    float(new["quantity"]),
                ),
            )
            conn.execute(
                "UPDATE inventory_types SET stock = stock - ? WHERE id = ?",
                (float(new["quantity"]), new["type_id"]),
            )
            conn.execute(
                """
                INSERT INTO inventory_stock_transactions
                (type_id, quantity_added, note)
                VALUES (?, ?, ?)
                """,
                (
                    new["type_id"],
                    -float(new["quantity"]),
                    f"Given to supplier for Order #{order_id} ({order_label})",
                ),
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    if old_rows:
        old_desc = "; ".join(
            f"{r['material_name']}"
            + (f" ({r['type_name']})" if r.get("type_name") else "")
            + f": {format_number(r['quantity'])}"
            for r in old_rows
        )
        log_history(
            "Raw Materials Returned",
            order_label,
            "",
            f"Reversed previous raw-material allocation for Order #{order_id} "
            f"({order_label}): {old_desc}.",
        )

    if new_rows:
        new_desc = "; ".join(
            f"{r['material_name']}"
            + (f" ({r['type_name']})" if r.get("type_name") else "")
            + f": {format_number(r['quantity'])}"
            for r in new_rows
        )
        log_history(
            "Raw Materials Given",
            order_label,
            "",
            f"Gave raw materials to supplier for Order #{order_id} "
            f"({order_label}): {new_desc}.",
        )


def set_action_message(message, icon="✅"):
    st.session_state["suppliers_action_message"] = f"{icon}  {message}"


def show_action_message():
    message = st.session_state.pop("suppliers_action_message", None)
    if message:
        st.markdown(
            f'<div class="suppliers-action-toast">{message}</div>',
            unsafe_allow_html=True,
        )


# ------------------------------------------------------------
# Give Raw Materials — a real, compact modal dialog (st.dialog) instead
# of an inline section, matching the "premium app" design goal. All the
# underlying data logic (pre-fill existing allocation, Available lookup,
# one-step confirm, save) is unchanged from before.
# ------------------------------------------------------------
@st.dialog("Give Raw Materials", width="large")
def give_dialog(order):
    order_id = order["id"]
    rows_key = f"give_rows_{order_id}"
    confirm_key = f"give_confirm_{order_id}"
    counter_key = f"give_row_counter_{order_id}"

    def _new_row(**overrides):
        """Every row gets a permanent, unique id (not its list position),
        used for widget keys. Widget values persist in Streamlit's
        session_state under their key regardless of position — so if
        keys were based on list index (0, 1, 2...), removing row 0 would
        make the row that used to be at index 1 render under key "...1",
        but the row now sitting at index 0 would pick up the *old*,
        stale widget value already stored under key "...0". A permanent
        uid avoids that entirely: each row's widgets always keep the
        same key for as long as that row exists, no matter what gets
        removed around it."""
        st.session_state.setdefault(counter_key, 0)
        uid = st.session_state[counter_key]
        st.session_state[counter_key] += 1
        row = {"uid": uid, "material_id": None, "type_id": None, "quantity": 0.0}
        row.update(overrides)
        return row

    if rows_key not in st.session_state:
        existing = get_order_allocations(order_id)
        if existing:
            st.session_state[rows_key] = [
                _new_row(
                    material_id=r["material_id"],
                    type_id=r["type_id"],
                    quantity=float(r["quantity"]),
                )
                for r in existing
            ]
        else:
            st.session_state[rows_key] = [_new_row()]

    materials = get_materials()
    material_options = [m["id"] for m in materials]
    material_labels = {m["id"]: m["name"] for m in materials}

    st.markdown(
        f'<div class="give-dialog-subtitle">Order #{order_id} · {order["item_name"]}</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.get(confirm_key, False):
        if not material_options:
            st.info(
                "No raw materials exist in Inventory yet. Add some on the "
                "Inventory page first."
            )
            if st.button("Close", use_container_width=True):
                st.session_state["give_dialog_order"] = None
                st.rerun()
            return

        rows = st.session_state[rows_key]

        header_cells = st.columns([1.7, 1.7, 1.2, 1.2, 0.5])
        for cell, label in zip(
            header_cells,
            ["Raw Material", "Subtype", "Available", "Give Qty", ""],
        ):
            cell.markdown(
                f'<div class="give-row-header">{label}</div>',
                unsafe_allow_html=True,
            )

        for idx in range(len(rows)):
            row_data = rows[idx]
            row_uid = row_data["uid"]
            rcol1, rcol2, rcol3, rcol4, rcol5 = st.columns(
                [1.7, 1.7, 1.2, 1.2, 0.5]
            )

            with rcol1:
                default_mat_id = row_data.get("material_id")
                mat_index = (
                    material_options.index(default_mat_id)
                    if default_mat_id in material_options
                    else 0
                )
                selected_mat_id = st.selectbox(
                    "Raw Material",
                    material_options,
                    index=mat_index,
                    format_func=lambda mid: material_labels.get(mid, "—"),
                    key=f"give_mat_{order_id}_{row_uid}",
                    label_visibility="collapsed",
                )

            with rcol2:
                types_for_mat = get_types(selected_mat_id)
                type_options = [t["id"] for t in types_for_mat]
                type_labels = {t["id"]: t["name"] for t in types_for_mat}
                default_type_id = row_data.get("type_id")
                type_index = (
                    type_options.index(default_type_id)
                    if default_type_id in type_options
                    else 0
                )
                if type_options:
                    selected_type_id = st.selectbox(
                        "Subtype",
                        type_options,
                        index=type_index,
                        format_func=lambda tid: type_labels.get(tid, "—"),
                        key=f"give_type_{order_id}_{row_uid}",
                        label_visibility="collapsed",
                    )
                else:
                    selected_type_id = None
                    st.caption("No subtypes yet.")

            with rcol3:
                # Always read straight from current Inventory — never
                # hard-coded, and it updates the instant the Material or
                # Subtype selection above changes.
                selected_type_row = next(
                    (t for t in types_for_mat if t["id"] == selected_type_id),
                    None,
                )
                if selected_type_row:
                    stock_val = float(selected_type_row["stock"])
                    available_text = (
                        f"{format_number(stock_val)} {selected_type_row['unit']}"
                    )
                    neg_class = " negative" if stock_val < 0 else ""
                else:
                    available_text = "—"
                    neg_class = ""
                st.markdown(
                    f'<div class="suppliers-give-available{neg_class}">'
                    f"{available_text}</div>",
                    unsafe_allow_html=True,
                )

            with rcol4:
                selected_qty = st.number_input(
                    "Quantity",
                    value=float(row_data.get("quantity") or 0.0),
                    min_value=0.0,
                    step=1.0,
                    key=f"give_qty_{order_id}_{row_uid}",
                    label_visibility="collapsed",
                )

            with rcol5:
                if st.button(
                    "✕",
                    key=f"give_remove_{order_id}_{row_uid}",
                    help="Remove this row",
                ):
                    rows.pop(idx)
                    if not rows:
                        rows.append(_new_row())
                    st.rerun()

            rows[idx] = {
                "uid": row_uid,
                "material_id": selected_mat_id,
                "type_id": selected_type_id,
                "quantity": selected_qty,
            }

        if st.button("+ Add another raw material", key=f"give_add_row_{order_id}"):
            rows.append(_new_row())
            st.rerun()

        save_col, cancel_col = st.columns(2)
        with cancel_col:
            if st.button(
                "Cancel", key=f"give_cancel_{order_id}", use_container_width=True
            ):
                st.session_state.pop(rows_key, None)
                st.session_state[confirm_key] = False
                st.session_state["give_dialog_order"] = None
                st.rerun()
        with save_col:
            if st.button(
                "Save",
                key=f"give_save_{order_id}",
                type="primary",
                use_container_width=True,
            ):
                error = None
                for r in rows:
                    # Quantity 0 means the user wants this row removed
                    # entirely — skip validation for it rather than
                    # blocking Save.
                    if not r["quantity"] or r["quantity"] <= 0:
                        continue
                    if not r["material_id"] or not r["type_id"]:
                        error = "Select a raw material and subtype for every row."
                        break
                if error:
                    st.error(error)
                else:
                    st.session_state[confirm_key] = True
                    st.rerun()

    else:
        st.warning("Are you sure you want to save these raw materials?")

        summary_lines = []
        for r in st.session_state[rows_key]:
            mat_name = material_labels.get(r["material_id"], "—")
            types_for_mat = get_types(r["material_id"])
            type_name = next(
                (t["name"] for t in types_for_mat if t["id"] == r["type_id"]), ""
            )
            unit = next(
                (t["unit"] for t in types_for_mat if t["id"] == r["type_id"]), ""
            )
            label = mat_name + (f" ({type_name})" if type_name else "")
            if not r["quantity"] or r["quantity"] <= 0:
                summary_lines.append(f"- {label}: will be removed")
            else:
                summary_lines.append(
                    f"- {label}: {format_number(r['quantity'])} {unit}"
                )
        st.markdown("\n".join(summary_lines))

        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button(
                "Confirm & Save",
                key=f"give_confirm_btn_{order_id}",
                type="primary",
                use_container_width=True,
            ):
                enriched_rows = []
                for r in st.session_state[rows_key]:
                    # Quantity 0 = remove this row. Simply excluding it
                    # here is what makes save_order_allocation's existing
                    # reverse-old/apply-new logic return any of its
                    # previous allocation to Inventory without a 0-qty
                    # row ever being (re)applied or stored.
                    if not r["quantity"] or r["quantity"] <= 0:
                        continue
                    types_for_mat = get_types(r["material_id"])
                    type_row = next(
                        (t for t in types_for_mat if t["id"] == r["type_id"]), None
                    )
                    enriched_rows.append(
                        {
                            "material_id": r["material_id"],
                            "material_name": material_labels.get(
                                r["material_id"], "—"
                            ),
                            "type_id": r["type_id"],
                            "type_name": type_row["name"] if type_row else "",
                            "unit": type_row["unit"] if type_row else "",
                            "quantity": r["quantity"],
                        }
                    )

                save_order_allocation(order_id, enriched_rows)
                set_action_message(
                    f"Raw materials saved for Order #{order_id}.", "📤"
                )
                st.session_state.pop(rows_key, None)
                st.session_state[confirm_key] = False
                st.session_state["give_dialog_order"] = None
                st.rerun()

        with cancel_col:
            if st.button(
                "Cancel",
                key=f"give_cancel_confirm_{order_id}",
                use_container_width=True,
            ):
                st.session_state[confirm_key] = False
                st.rerun()


# ------------------------------------------------------------
# In Progress table — Give | ID | Item Name | Qnt | Order Date |
# End Date | Raw Materials
# ------------------------------------------------------------
def render_in_progress_table(supplier_name):
    orders = get_orders_by_supplier_and_status(supplier_name, "In Progress")

    if not orders:
        st.info("No In Progress orders for this supplier.")
        return

    col_widths = [0.8, 0.5, 2.1, 0.8, 1.1, 1.1, 2.8]
    headers = [
        "Give", "ID", "Item Name", "Qnt", "Order Date", "End Date", "Raw Materials",
    ]

    # Wrapped in a keyed container so CSS below can vertically
    # center every cell in each row (fixes the Give button sitting
    # off-center) and tighten the gap between rows.
    with st.container(key="suppliers_inprogress_rows"):
        header_cells = st.columns(col_widths)
        for cell, label in zip(header_cells, headers):
            cell.markdown(
                f'<div class="suppliers-table-header">{label}</div>',
                unsafe_allow_html=True,
            )

        for order in orders:
            row_cells = st.columns(col_widths)

            with row_cells[0]:
                st.markdown('<div class="suppliers-give-btn">', unsafe_allow_html=True)
                if st.button(
                    "Give", key=f"give_open_{order['id']}", use_container_width=True
                ):
                    # Only set which order's dialog should be open here — the
                    # dialog itself is (re)opened by the page-level check near
                    # the bottom of the script on every rerun, which is what
                    # keeps it open across "+ Add another raw material",
                    # dropdown changes, Save, etc. Calling give_dialog(order)
                    # directly from this click handler was the bug: on any
                    # later rerun caused by something *inside* the dialog,
                    # this button's own condition is False again, so the
                    # dialog was never re-invoked and appeared to close itself.
                    st.session_state["give_dialog_order"] = order
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            row_cells[1].markdown(
                f'<div class="suppliers-table-cell">{order["id"]}</div>',
                unsafe_allow_html=True,
            )
            row_cells[2].markdown(
                f'<div class="suppliers-table-cell">{order["item_name"]}</div>',
                unsafe_allow_html=True,
            )
            row_cells[3].markdown(
                f'<div class="suppliers-table-cell">{order["quantity"]}</div>',
                unsafe_allow_html=True,
            )
            row_cells[4].markdown(
                f'<div class="suppliers-table-cell">'
                f'{format_display_date(order["order_date"])}</div>',
                unsafe_allow_html=True,
            )
            row_cells[5].markdown(
                f'<div class="suppliers-table-cell">'
                f'{format_display_date(order["end_date"])}</div>',
                unsafe_allow_html=True,
            )

            allocations = get_order_allocations(order["id"])
            row_cells[6].markdown(
                f'<div class="suppliers-table-cell">'
                f'{format_allocations_display(allocations)}</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div style="border-bottom:1px solid #1e293b; margin:4px 0 8px 0;"></div>',
                unsafe_allow_html=True,
            )


# ------------------------------------------------------------
# Completed table — Order ID | Item Name | Quantity | Order Date |
# Expt Delivery | Price  (read-only, exactly these columns)
# ------------------------------------------------------------
def render_completed_table(supplier_name):
    orders = get_orders_by_supplier_and_status(supplier_name, "Completed")

    if not orders:
        st.info("No Completed orders for this supplier.")
        return

    import pandas as pd

    display_rows = [
        {
            "Order ID": o["id"],
            "Item Name": o["item_name"],
            "Quantity": o["quantity"],
            "Order Date": format_display_date(o["order_date"]),
            "Expt Delivery": format_display_date(o["end_date"]),
            "Price": f"₹{float(o['price']):,.2f}",
        }
        for o in orders
    ]

    st.dataframe(
        pd.DataFrame(display_rows),
        use_container_width=True,
        hide_index=True,
        row_height=34,
    )


# ------------------------------------------------------------
# Page
# ------------------------------------------------------------
init_suppliers_db()

st.title("👥 Suppliers")
st.caption("Manage supplier orders and raw-material dispatch")

st.markdown('<div class="suppliers-search">', unsafe_allow_html=True)
search_query = st.text_input(
    "Search suppliers",
    placeholder="🔍  Search suppliers...",
    label_visibility="collapsed",
    key="suppliers_search",
)
st.markdown("</div>", unsafe_allow_html=True)

st.write("")

all_supplier_names = get_all_supplier_names()

if search_query.strip():
    _q = search_query.strip().lower()
    supplier_names = [s for s in all_supplier_names if _q in s.lower()]
else:
    supplier_names = all_supplier_names

st.session_state.setdefault("selected_supplier", None)
st.session_state.setdefault("give_dialog_order", None)

if not all_supplier_names:
    st.info(
        "No suppliers yet. Add an order with a Supplier Name on the Orders "
        "page and it will show up here automatically."
    )
elif not supplier_names:
    st.info("No suppliers found.")
else:
    selected_supplier = st.session_state["selected_supplier"]
    if selected_supplier not in supplier_names:
        selected_supplier = None

    def _render_supplier_card(name, is_selected):
        """The compact name+counts card. The arrow is a literal text
        prefix on the button label (never a separately-positioned
        decoration), so it always sits immediately before the name and
        never moves when the card expands."""
        in_progress_count = count_orders_by_status(name, "In Progress")
        completed_count = count_orders_by_status(name, "Completed")
        arrow = "⌄" if is_selected else "›"

        with st.container(border=True):
            st.markdown('<div class="supplier-card-btn">', unsafe_allow_html=True)
            if st.button(
                f"{arrow}  👤  {name}",
                key=f"card_{name}",
                use_container_width=True,
            ):
                st.session_state["selected_supplier"] = (
                    None if st.session_state["selected_supplier"] == name else name
                )
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(
                f'<div class="supplier-card-counts">'
                f'<span class="supplier-badge supplier-badge-progress">'
                f"🔵 {in_progress_count} In Progress</span>"
                f'<span class="supplier-badge supplier-badge-done">'
                f"✓ {completed_count} Done</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    def _render_expanded_content(name):
        """In Progress / Completed toggle + table (and, inside that
        table, the Give dialog for a specific order) — rendered directly
        under this supplier's own card, never at the bottom of the page."""
        st.write("")

        with st.container(border=True):
            in_progress_count = count_orders_by_status(name, "In Progress")
            completed_count = count_orders_by_status(name, "Completed")

            sub_col1, sub_col2, _sub_spacer = st.columns([1.4, 1.4, 3.2])
            current_view = st.session_state.get("supplier_view_active")

            with sub_col1:
                st.markdown(
                    '<div class="supplier-subview-btn">', unsafe_allow_html=True
                )
                if st.button(
                    f"🔵 In Progress ({in_progress_count})",
                    key="view_inprogress_active",
                    use_container_width=True,
                ):
                    st.session_state["supplier_view_active"] = (
                        None if current_view == "in_progress" else "in_progress"
                    )
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            with sub_col2:
                st.markdown(
                    '<div class="supplier-subview-btn">', unsafe_allow_html=True
                )
                if st.button(
                    f"✓ Completed ({completed_count})",
                    key="view_completed_active",
                    use_container_width=True,
                ):
                    st.session_state["supplier_view_active"] = (
                        None if current_view == "completed" else "completed"
                    )
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            active_view = st.session_state.get("supplier_view_active")
            if active_view == "in_progress":
                st.write("")
                render_in_progress_table(name)
            elif active_view == "completed":
                st.write("")
                render_completed_table(name)

        st.write("")

    # ---------------- Render suppliers, row by row ----------------
    # Compact cards are paired up 2-per-row exactly like before. The
    # moment we reach the selected supplier, any half-filled pair is
    # flushed first, then that supplier's card is rendered full-width
    # with its expanded content immediately underneath — never collected
    # separately and rendered at the end of the list. Pairing then
    # resumes normally for the suppliers that follow.
    pending_pair = []

    def _flush_pending_pair():
        if not pending_pair:
            return
        cols = st.columns(2)
        for i, pending_name in enumerate(pending_pair):
            with cols[i]:
                _render_supplier_card(pending_name, is_selected=False)
        pending_pair.clear()

    for supplier_name in supplier_names:
        if supplier_name == selected_supplier:
            _flush_pending_pair()
            _render_supplier_card(supplier_name, is_selected=True)
            _render_expanded_content(supplier_name)
        else:
            pending_pair.append(supplier_name)
            if len(pending_pair) == 2:
                _flush_pending_pair()

    _flush_pending_pair()

# ------------------------------------------------------------
# Keep the Give Raw Materials dialog open across reruns.
#
# st.dialog only renders when its decorated function is actually called
# during a script run — it does not automatically "remember" it was open
# on a previous run. This check runs on every single rerun of the page
# (regardless of what triggered it — a dropdown change, "+ Add another
# raw material", Save, etc.) and re-invokes give_dialog() using the order
# cached in session_state when "Give" was clicked, so the dialog never
# disappears on its own. It only closes when give_dialog_order is
# explicitly set back to None, which only happens on: the form's Cancel,
# Confirm & Save, or the "no materials" Close button inside give_dialog.
# ------------------------------------------------------------
_open_give_order = st.session_state.get("give_dialog_order")
if _open_give_order is not None:
    give_dialog(_open_give_order)

show_action_message()