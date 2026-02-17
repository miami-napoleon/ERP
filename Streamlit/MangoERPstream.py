import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# --- CONFIGURATION ---
DB_FILE = "mango_v5_web.json"
st.set_page_config(page_title="MangoClub Cloud", page_icon="🥭", layout="centered")

# --- BACKEND LOGIC (Cached Resource) ---
class Database:
    def __init__(self):
        self.data = {}
        self.load_db()

    def load_db(self):
        if not os.path.exists(DB_FILE):
            self.data = {
                "products": {},
                "history": [],
                "contacts": {} # {name: {type: 'Vendor'/'Customer'}}
            }
            # Demo Data
            self.add_product("Heirloom Tomato", "Vegetable")
            self.add_contact("Farm Supply Co", "Vendor")
            self.add_contact("Local Market", "Customer")
        else:
            with open(DB_FILE, "r") as f:
                self.data = json.load(f)
            # Migration for existing DBs
            if "contacts" not in self.data:
                self.data["contacts"] = {}

    def save_db(self):
        with open(DB_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    def add_product(self, name, category):
        if name in self.data["products"]:
            return False, "Product already exists!"
        
        icon = "📦"
        if category == "Fruit": icon = "🍎"
        elif category == "Vegetable": icon = "🥦"
        elif category == "Dairy": icon = "🥛"
        elif category == "Meat": icon = "🥩"
        
        self.data["products"][name] = {
            "category": category,
            "icon": icon,
            "pool": 0.0,
            "known_units": {
                "Standard Crate": 20.0,
                "Small Box": 10.0
            }
        }
        self.save_db()
        return True, "Success"

    def add_contact(self, name, type):
        if name in self.data["contacts"]:
            return False, "Contact already exists!"
        self.data["contacts"][name] = {"type": type}
        self.save_db()
        return True, "Contact Added"

    def update_pool(self, product_name, qty, unit_name, unit_weight, action, contact_name="Unspecified"):
        product = self.data["products"][product_name]
        total_lbs = float(qty) * float(unit_weight)
        
        if action == "IN":
            product["pool"] += total_lbs
        elif action == "OUT":
            if product["pool"] < total_lbs:
                return False, f"Not enough stock! (Need {total_lbs} lbs)"
            product["pool"] -= total_lbs

        # Learn the unit automatically
        product["known_units"][unit_name] = float(unit_weight)
        
        # Log History
        self.data["history"].insert(0, {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "product": product_name,
            "action": action,
            "qty_display": f"{qty} {unit_name}",
            "weight_change": total_lbs,
            "pool_after": product["pool"],
            "contact": contact_name
        })
        self.save_db()
        return True, f"Success! {action} {total_lbs:.1f} lbs"

# Initialize DB in Session State
if 'db' not in st.session_state:
    st.session_state.db = Database()

db = st.session_state.db

# --- NAVIGATION LOGIC ---
if 'current_view' not in st.session_state:
    st.session_state.current_view = "home"
if 'selected_product' not in st.session_state:
    st.session_state.selected_product = None

def navigate_to(view, product=None):
    st.session_state.current_view = view
    st.session_state.selected_product = product
    st.rerun()

# --- VIEW 1: HOME SCREEN ---
def render_home():
    st.title("🥭 MangoClub Inventory")
    
    # 1. Quick Add Product Section
    with st.expander("➕ Create New Product"):
        with st.form("add_product_form"):
            new_name = st.text_input("Product Name")
            new_cat = st.selectbox("Category", ["Fruit", "Vegetable", "Dairy", "Meat"])
            submitted = st.form_submit_button("Create Product")
            if submitted:
                if new_name:
                    success, msg = db.add_product(new_name, new_cat)
                    if success:
                        st.success(f"Added {new_name}!")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Name is required.")

    st.divider()

    # 1.5 Contact Management Button
    if st.button("👥 Manage Contacts"):
        navigate_to("contacts")

    st.divider()

    # 2. FILTER SECTION (New Feature)
    # Get unique categories from DB
    all_products = sorted(list(db.data["products"].keys()))
    
    if not all_products:
        st.info("No products yet. Add one above!")
        return

    # Extract categories dynamically
    categories = ["All Categories"] + sorted(list(set([db.data["products"][p]["category"] for p in all_products])))
    
    # Filter Widget
    col_filter, col_spacer = st.columns([2, 1])
    with col_filter:
        selected_cat = st.selectbox("🔍 Filter by Category:", categories)

    # 3. Apply Filter
    displayed_products = []
    if selected_cat == "All Categories":
        displayed_products = all_products
    else:
        displayed_products = [p for p in all_products if db.data["products"][p]["category"] == selected_cat]

    # 4. Render Grid
    if not displayed_products:
        st.caption("No products found in this category.")
    
    for p_name in displayed_products:
        p_data = db.data["products"][p_name]
        
        # Creating a clickable card-like row
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            st.markdown(f"## {p_data['icon']}")
        with col2:
            st.markdown(f"**{p_name}**")
            st.caption(f"{p_data['pool']:.1f} lbs available")
        with col3:
            if st.button("Manage", key=f"btn_{p_name}"):
                navigate_to("product", p_name)
        st.divider()

# --- VIEW 1.5: CONTACTS MANAGER ---
def render_contacts():
    st.title("👥 Contact Manager")
    if st.button("← Back to Home"):
        navigate_to("home")
    
    # Add New Contact
    with st.expander("➕ Add New Contact", expanded=True):
        with st.form("add_contact_form"):
            c_name = st.text_input("Contact Name/Entity")
            c_type = st.radio("Type", ["Vendor", "Customer"], horizontal=True)
            submitted = st.form_submit_button("Save Contact")
            if submitted:
                if c_name:
                    success, msg = db.add_contact(c_name, c_type)
                    if success:
                        st.success(f"Added {c_name}")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Name required")

    st.divider()
    
    # List Contacts
    st.subheader("Directory")
    contacts = db.data.get("contacts", {})
    if not contacts:
        st.info("No contacts yet.")
    else:
        # Separate by type for better viewing
        vendors = [name for name, info in contacts.items() if info["type"] == "Vendor"]
        customers = [name for name, info in contacts.items() if info["type"] == "Customer"]
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🏢 Vendors (Sources)")
            for v in vendors:
                st.markdown(f"- **{v}**")
        with c2:
             st.markdown("### 🛒 Customers (Destinations)")
             for c in customers:
                 st.markdown(f"- **{c}**")

# --- VIEW 2: PRODUCT HUB ---
def render_product():
    p_name = st.session_state.selected_product
    p_data = db.data["products"][p_name]
    
    # Top Bar
    if st.button("← Back to List"):
        navigate_to("home")
    
    st.title(f"{p_data['icon']} {p_name}")
    
    # Big Metrics
    st.metric(label="Current Inventory (Pool)", value=f"{p_data['pool']:.2f} lbs")
    
    # Tabs
    tab_harvest, tab_sell, tab_history, tab_chain = st.tabs(["📥 Harvest (IN)", "📤 Sell (OUT)", "📈 History", "🔗 Supply Chain"])
    
    # --- DYNAMIC FORM LOGIC ---
    # This uses the 'Reactive' approach (no st.form) so the New Unit fields appear instantly
    def render_transaction_form(tab, action):
        with tab:
            color = "green" if action == "IN" else "red"
            btn_label = "Confirm Harvest" if action == "IN" else "Confirm Sale"
            
            # --- Contact Selection ---
            contacts = db.data.get("contacts", {})
            contact_options = ["Unspecified"]
            
            if action == "IN":
                # Filter for Vendors
                contact_options += [name for name, info in contacts.items() if info["type"] == "Vendor"]
                contact_label = "Source (Vendor)"
            else:
                # Filter for Customers
                contact_options += [name for name, info in contacts.items() if info["type"] == "Customer"]
                contact_label = "Destination (Customer)"
                
            selected_contact = st.selectbox(contact_label, contact_options, key=f"contact_{action}")
            # -------------------------
            
            # 1. Standard Inputs
            c1, c2 = st.columns(2)
            qty = c1.number_input("Quantity", min_value=0.0, step=1.0, key=f"qty_{action}")
            
            unit_options = list(p_data["known_units"].keys()) + ["+ Create New Unit..."]
            display_options = [f"{u} ({p_data['known_units'][u]} lbs)" for u in p_data["known_units"]] + ["+ Create New Unit..."]
            
            # This triggers a rerun instantly when changed
            unit_selection = c2.selectbox("Unit Type", display_options, key=f"unit_{action}")
            
            # 2. Conditional Inputs (Show Only if Needed)
            new_u_name = None
            new_u_weight = 0.0
            
            if "+ Create New Unit..." in unit_selection:
                st.info("🆕 Define the new container below:")
                c3, c4 = st.columns(2)
                new_u_name = c3.text_input("Name (e.g., Red Bucket)", key=f"new_name_{action}")
                new_u_weight = c4.number_input("Weight of ONE (lbs)", min_value=0.0, step=0.1, key=f"new_weight_{action}")

            # 3. Action Button
            st.write("") # Spacer
            if st.button(btn_label, type="primary" if action=="IN" else "secondary", key=f"btn_{action}"):
                
                # Logic Execution
                final_unit_name = ""
                final_weight = 0.0
                
                if "+ Create New Unit..." in unit_selection:
                    if not new_u_name or new_u_weight <= 0:
                        st.error("Please fill out New Unit Name and Weight!")
                        return
                    final_unit_name = new_u_name
                    final_weight = new_u_weight
                else:
                    index = display_options.index(unit_selection)
                    final_unit_name = unit_options[index]
                    final_weight = p_data["known_units"][final_unit_name]
                
                
                if qty > 0:
                    success, msg = db.update_pool(p_name, qty, final_unit_name, final_weight, action, selected_contact)
                    if success:
                        st.toast(msg, icon="✅")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Quantity must be greater than 0")

    render_transaction_form(tab_harvest, "IN")
    render_transaction_form(tab_sell, "OUT")

    # --- TAB 3: HISTORY ---
    with tab_history:
        st.subheader("Inventory Trend")
        logs = [x for x in db.data["history"] if x["product"] == p_name]
        
        if logs:
            df = pd.DataFrame(logs)
            df = df.iloc[::-1]
            st.line_chart(df, x="timestamp", y="pool_after")
            
            st.divider()
            st.subheader("Transaction Log")
            for log in logs:
                icon = "🟢" if log["action"] == "IN" else "🔴"
                contact_info = log.get("contact", "Unspecified")
                contact_display = f"From: {contact_info}" if log["action"] == "IN" else f"To: {contact_info}"
                
                st.markdown(f"**{log['timestamp']}** | {icon} {log['action']} | {contact_display}")
                st.text(f"{log['qty_display']} ({log['weight_change']:.1f} lbs)")
                st.caption(f"Pool after: {log['pool_after']:.1f} lbs")
                st.divider()
        else:
            st.info("No history available yet.")

    # --- TAB 4: SUPPLY CHAIN ---
    with tab_chain:
        st.subheader("Supply Chain Visualization")
        render_supply_chain_sankey(p_name, p_data, db.data["history"])

def render_supply_chain_sankey(product_name, product_data, history):
    # Filter logs for this product
    logs = [x for x in history if x["product"] == product_name]
    
    if not logs:
        st.info("Not enough data to visualize supply chain.")
        return

    # Data Aggregation
    in_flows = {}  # Source -> Amount
    out_flows = {} # Destination -> Amount
    total_in = 0.0
    total_out = 0.0
    
    for log in logs:
        contact = log.get("contact", "Unspecified")
        weight = float(log["weight_change"])
        
        if log["action"] == "IN":
            in_flows[contact] = in_flows.get(contact, 0.0) + weight
            total_in += weight
        elif log["action"] == "OUT":
            out_flows[contact] = out_flows.get(contact, 0.0) + weight
            total_out += weight

    current_stock = product_data["pool"]
    
    # Balance Check
    # Total Available = Total IN ( + Initial if we tracked it, but assuming 0 for now)
    # Total Used = Total OUT + Current Stock
    # If Total IN < Total Used, we have an "Initial Stock" or "Unknown Source" mismatch
    
    balance_gap = (total_out + current_stock) - total_in
    if balance_gap > 0.1: # Threshold for float errors
        in_flows["Initial / Unknown"] = in_flows.get("Initial / Unknown", 0.0) + balance_gap

    # Node Setup
    # Indices: 
    # 0..N-1 : Vendors
    # N      : MangoClub Farm (Central Node)
    # N+1..M : Customers
    # M+1    : Current Stock
    
    labels = []
    source_indices = []
    target_indices = []
    values = []
    colors = []
    
    # 1. Vendors (Sources)
    vendor_map = {} # Name -> Index
    for v_name in in_flows:
        vendor_map[v_name] = len(labels)
        labels.append(v_name)
        colors.append("#66c2a5") # Tealish
        
    # 2. Central Node (Us)
    farm_idx = len(labels)
    labels.append("MangoClub Farm")
    colors.append("#fc8d62") # Orange-ish
    
    # 3. Customers (Destinations)
    customer_map = {} # Name -> Index
    for c_name in out_flows:
        customer_map[c_name] = len(labels)
        labels.append(c_name)
        colors.append("#8da0cb") # Blue-ish

    # 4. Current Stock (Sink)
    stock_idx = len(labels)
    labels.append(f"Current Stock ({current_stock:.1f} lbs)")
    colors.append("#e78ac3") # Pinkish
    
    # -- LINKS --
    
    # Vendors -> Farm
    for v_name, amount in in_flows.items():
        source_indices.append(vendor_map[v_name])
        target_indices.append(farm_idx)
        values.append(amount)
        
    # Farm -> Customers
    for c_name, amount in out_flows.items():
        source_indices.append(farm_idx)
        target_indices.append(customer_map[c_name])
        values.append(amount)
        
    # Farm -> Current Stock
    if current_stock > 0:
        source_indices.append(farm_idx)
        target_indices.append(stock_idx)
        values.append(current_stock)
        
    # Plot
    fig = go.Figure(data=[go.Sankey(
        node = dict(
          pad = 15,
          thickness = 20,
          line = dict(color = "black", width = 0.5),
          label = labels,
          color = colors
        ),
        link = dict(
          source = source_indices,
          target = target_indices,
          value = values
      ))])

    fig.update_layout(title_text=f"{product_name} Supply Chain Flow", font_size=12)
    st.plotly_chart(fig, use_container_width=True)

# --- MAIN APP ROUTER ---
if st.session_state.current_view == "home":
    render_home()
elif st.session_state.current_view == "contacts":
    render_contacts()
elif st.session_state.current_view == "product":
    render_product()