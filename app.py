import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ----------------------------- DATABASE SETUP -----------------------------
DB_FILE = "fees.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Student table
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            total_fee REAL,
            paid_amount REAL,
            created_date TEXT
        )
    """)

    # Payments table
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            amount REAL,
            date TEXT,
            note TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    conn.commit()
    conn.close()

def execute_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()

    if fetch:
        data = c.fetchall()
        conn.close()
        return data

    conn.close()

# Initialize DB
init_db()


# ----------------------------- CRUD OPERATIONS -----------------------------
def add_student(name, email, phone, total_fee, initial_payment):
    created_date = datetime.now().strftime("%Y-%m-%d")
    execute_query(
        "INSERT INTO students (name, email, phone, total_fee, paid_amount, created_date) VALUES (?,?,?,?,?,?)",
        (name, email, phone, total_fee, initial_payment, created_date)
    )

    # Add initial payment
    if initial_payment > 0:
        student_id = get_last_student_id()
        add_payment_only(student_id, initial_payment, "Initial payment")

def get_last_student_id():
    data = execute_query("SELECT MAX(id) FROM students", fetch=True)
    return data[0][0]

def add_payment_only(student_id, amount, note):
    """Add payment record without updating student paid_amount"""
    date = datetime.now().strftime("%Y-%m-%d")
    execute_query("""
        INSERT INTO payments (student_id, amount, date, note)
        VALUES (?, ?, ?, ?)
    """, (student_id, amount, date, note))

def add_payment(student_id, amount, note):
    """Add payment and update student paid_amount"""
    date = datetime.now().strftime("%Y-%m-%d")

    execute_query("""
        INSERT INTO payments (student_id, amount, date, note)
        VALUES (?, ?, ?, ?)
    """, (student_id, amount, date, note))

    # Update student paid amount
    execute_query("""
        UPDATE students
        SET paid_amount = paid_amount + ?
        WHERE id = ?
    """, (amount, student_id))

def delete_student(student_id):
    execute_query("DELETE FROM payments WHERE student_id = ?", (student_id,))
    execute_query("DELETE FROM students WHERE id = ?", (student_id,))

def get_students():
    data = execute_query("SELECT * FROM students ORDER BY id DESC", fetch=True)
    return [{
        "id": d[0],
        "name": d[1],
        "email": d[2],
        "phone": d[3],
        "total_fee": d[4],
        "paid_amount": d[5],
        "created_date": d[6]
    } for d in data]

def get_payment_history(student_id):
    data = execute_query("""
        SELECT amount, date, note FROM payments 
        WHERE student_id = ? ORDER BY id DESC
    """, (student_id,), fetch=True)

    return [{"amount": d[0], "date": d[1], "note": d[2]} for d in data]


# ----------------------------- STATS -----------------------------
def get_statistics():
    stats = {}

    total_students = execute_query("SELECT COUNT(*) FROM students", fetch=True)[0][0]
    revenue = execute_query("SELECT SUM(paid_amount) FROM students", fetch=True)[0][0] or 0
    expected = execute_query("SELECT SUM(total_fee) FROM students", fetch=True)[0][0] or 0
    outstanding = expected - revenue

    stats["total_students"] = total_students
    stats["total_revenue"] = revenue
    stats["total_outstanding"] = outstanding
    stats["total_expected"] = expected
    return stats


# ----------------------------- STREAMLIT UI -----------------------------
st.set_page_config(page_title="Fee Management System", page_icon="💰", layout="wide")

# Custom CSS for better UI
st.markdown("""
    <style>
    .student-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #4CAF50;
        margin-bottom: 15px;
    }
    .pending-card {
        border-left: 4px solid #ff9800;
    }
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

st.title("💰 Student Fee Management System")
st.markdown("##### Manage student fees, track payments, and monitor outstanding balances")
st.markdown("---")

# ---- SIDEBAR: ADD STUDENT ----
with st.sidebar:
    st.header("➕ Add New Student")
    st.markdown("Fill in the details below to register a new student")

    with st.form("add_student", clear_on_submit=True):
        name = st.text_input("Student Name *", placeholder="Enter full name")
        email = st.text_input("Email", placeholder="student@example.com")
        phone = st.text_input("Phone", placeholder="+1 234 567 8900")
        total_fee = st.number_input("Total Fee ($) *", min_value=0.0, step=100.0)
        initial_payment = st.number_input("Initial Payment ($)", min_value=0.0, step=50.0)

        submitted = st.form_submit_button("✅ Add Student", use_container_width=True)
        
        if submitted:
            if not name or total_fee <= 0:
                st.error("⚠️ Name and Total Fee are required!")
            elif initial_payment > total_fee:
                st.error("⚠️ Initial payment cannot exceed total fee!")
            else:
                add_student(name, email, phone, total_fee, initial_payment)
                st.success(f"✅ {name} added successfully!")
                st.rerun()

# ---- STATISTICS ----
stats = get_statistics()

st.subheader("📊 Overview Dashboard")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="👥 Total Students", 
        value=stats["total_students"],
        delta=None
    )

with col2:
    st.metric(
        label="💵 Total Revenue", 
        value=f"${stats['total_revenue']:,.2f}"
    )

with col3:
    st.metric(
        label="⚠️ Outstanding", 
        value=f"${stats['total_outstanding']:,.2f}",
        delta=None,
        delta_color="inverse"
    )

with col4:
    collection_rate = (stats['total_revenue']/stats['total_expected']*100) if stats['total_expected'] > 0 else 0
    st.metric(
        label="📈 Collection Rate", 
        value=f"{collection_rate:.1f}%",
        delta=f"{collection_rate:.1f}%" if collection_rate > 0 else None
    )

st.markdown("---")

# ---- SEARCH & FILTER ----
col_search, col_filter = st.columns([3, 1])

with col_search:
    search_term = st.text_input("🔍 Search students by name", placeholder="Type to search...")

with col_filter:
    filter_option = st.selectbox("Filter by Status", ["All Students", "Fully Paid", "Pending Payment"])

students = get_students()

# Search
if search_term:
    students = [s for s in students if search_term.lower() in s["name"].lower()]

# Filter
if filter_option == "Fully Paid":
    students = [s for s in students if s["total_fee"] - s["paid_amount"] <= 0]
elif filter_option == "Pending Payment":
    students = [s for s in students if s["total_fee"] - s["paid_amount"] > 0]

st.subheader(f"📋 Students List ({len(students)} found)")

if not students:
    st.info("👋 No students found. Add a new student to get started!")
else:
    # ---- CARD VIEW ----
    for s in students:
        balance = s["total_fee"] - s["paid_amount"]
        status = "✅ Fully Paid" if balance <= 0 else "⏳ Pending"
        color = "green" if balance <= 0 else "orange"
        card_class = "student-card" if balance <= 0 else "student-card pending-card"

        with st.container():
            col_info, col_actions = st.columns([4, 1])

            with col_info:
                st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid {color};">
                        <h3 style="margin: 0 0 10px 0;">{s['name']}</h3>
                        <p style="margin: 5px 0;"><strong>📧 Email:</strong> {s['email'] or 'N/A'}</p>
                        <p style="margin: 5px 0;"><strong>📱 Phone:</strong> {s['phone'] or 'N/A'}</p>
                        <p style="margin: 5px 0;"><strong>📅 Registered:</strong> {s['created_date']}</p>
                        <hr style="margin: 10px 0;">
                        <p style="margin: 5px 0;"><strong>Total Fee:</strong> ${s['total_fee']:,.2f}</p>
                        <p style="margin: 5px 0;"><strong>Amount Paid:</strong> ${s['paid_amount']:,.2f}</p>
                        <p style="margin: 5px 0; font-size: 1.1em;"><strong>Balance:</strong> <span style="color: {color};">${balance:,.2f}</span></p>
                        <p style="margin: 10px 0 0 0; color: {color}; font-weight: bold;">{status}</p>
                    </div>
                """, unsafe_allow_html=True)

            with col_actions:
                st.write("")  # Spacing
                st.write("")  # Spacing
                
                # Payment button
                if balance > 0:
                    if st.button(f"💳 Add Payment", key=f"pay{s['id']}", use_container_width=True):
                        st.session_state[f"pay_now_{s['id']}"] = True

                # View history
                if st.button(f"📜 View History", key=f"view{s['id']}", use_container_width=True):
                    st.session_state[f"view_{s['id']}"] = True

                # Delete
                if st.button(f"🗑️ Delete", type="secondary", key=f"del{s['id']}", use_container_width=True):
                    if st.session_state.get(f"confirm_delete_{s['id']}", False):
                        delete_student(s['id'])
                        st.success("✅ Student deleted!")
                        st.session_state[f"confirm_delete_{s['id']}"] = False
                        st.rerun()
                    else:
                        st.session_state[f"confirm_delete_{s['id']}"] = True
                        st.warning("⚠️ Click again to confirm deletion")

        # Payment modal
        if st.session_state.get(f"pay_now_{s['id']}", False):
            with st.expander(f"💳 Add Payment for {s['name']}", expanded=True):
                with st.form(f"form_pay_{s['id']}"):
                    st.info(f"Outstanding balance: ${balance:,.2f}")
                    amt = st.number_input("Payment Amount ($)", min_value=0.01, max_value=float(balance), step=10.0)
                    note = st.text_input("Note (optional)", placeholder="e.g., Semester 1 payment")
                    
                    col_submit, col_cancel = st.columns(2)
                    
                    with col_submit:
                        submitted = st.form_submit_button("✅ Submit Payment", use_container_width=True)
                        if submitted:
                            add_payment(s["id"], amt, note)
                            st.success(f"✅ Payment of ${amt:,.2f} added!")
                            st.session_state[f"pay_now_{s['id']}"] = False
                            st.rerun()
                    
                    with col_cancel:
                        if st.form_submit_button("❌ Cancel", use_container_width=True):
                            st.session_state[f"pay_now_{s['id']}"] = False
                            st.rerun()

        # History modal
        if st.session_state.get(f"view_{s['id']}", False):
            with st.expander(f"📜 Payment History - {s['name']}", expanded=True):
                history = get_payment_history(s["id"])
                if not history:
                    st.info("ℹ️ No payment records found")
                else:
                    total_paid = sum(h['amount'] for h in history)
                    st.success(f"Total Payments Made: ${total_paid:,.2f}")
                    
                    for idx, h in enumerate(history, 1):
                        st.markdown(f"""
                            **Payment #{idx}**  
                            📅 Date: {h['date']}  
                            💵 Amount: ${h['amount']:,.2f}  
                            📝 Note: {h['note'] or 'N/A'}
                        """)
                        st.markdown("---")
                
                if st.button("✖️ Close", key=f"close{s['id']}", use_container_width=True):
                    st.session_state[f"view_{s['id']}"] = False
                    st.rerun()

        st.markdown("---")

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #888; padding: 20px;">
        <p>💰 Fee Management System | Powered by SQLite & Streamlit</p>
        <p style="font-size: 0.8em;">Secure • Reliable • Easy to Use</p>
    </div>
""", unsafe_allow_html=True)