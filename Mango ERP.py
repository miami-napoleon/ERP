import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
DB_FILE = "mango_v4.json"

# --- BACKEND (LOGIC) ---
class Database:
    def __init__(self):
        self.data = {}
        self.load_db()

    def load_db(self):
        if not os.path.exists(DB_FILE):
            self.data = {
                "products": {},
                "history": []
            }
            # Add a demo product if empty
            self.add_product("Heirloom Tomato", "Vegetable")
        else:
            with open(DB_FILE, "r") as f:
                self.data = json.load(f)

    def save_db(self):
        with open(DB_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    def add_product(self, name, category):
        if name in self.data["products"]:
            return False, "Product already exists!"
        
        # Auto-assign emoji based on category
        icon = "📦"
        if category == "Fruit": icon = "🍎"
        elif category == "Vegetable": icon = "🥦"
        elif category == "Dairy": icon = "🥛"
        elif category == "Meat": icon = "🥩"
        
        self.data["products"][name] = {
            "category": category,
            "icon": icon,
            "base_unit": "lbs",
            "pool": 0.0,
            "known_units": {
                "Standard Crate": 20.0,
                "Small Box": 10.0
            }
        }
        self.save_db()
        return True, "Success"

    def get_product(self, name):
        return self.data["products"].get(name)

    def update_pool(self, product_name, qty, unit_name, unit_weight, action):
        product = self.data["products"][product_name]
        total_lbs = float(qty) * float(unit_weight)
        
        if action == "IN":
            product["pool"] += total_lbs
        elif action == "OUT":
            if product["pool"] < total_lbs:
                return False, f"Not enough stock! (Need {total_lbs} lbs, Have {product['pool']:.1f} lbs)"
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
            "pool_after": product["pool"]
        })
        self.save_db()
        return True, f"Success! {action} {total_lbs} lbs"

# --- FRONTEND (UI) ---
class MangoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MangoClub v4.0 (Mac Fix)")
        self.geometry("400x700")
        self.db = Database()
        
        # Main Container - Light Grey Background
        self.container = tk.Frame(self, bg="#ecf0f1")
        self.container.pack(fill="both", expand=True)
        
        self.show_home_screen()

    def clear_screen(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    # === 1. HOME SCREEN ===
    def show_home_screen(self):
        self.clear_screen()
        
        # Header
        header = tk.Frame(self.container, bg="#2c3e50", height=80)
        header.pack(fill="x")
        tk.Label(header, text="🥭 MangoClub Inventory", bg="#2c3e50", fg="white", font=("Arial", 18, "bold")).place(x=20, y=25)

        # "Add Product" Button
        # FIX: Text is black so it is visible on Mac. highlightbackground adds color border.
        btn_add = tk.Button(self.container, text="+ New Product", bg="#27ae60", fg="black", 
                            highlightbackground="#27ae60", font=("Arial", 14, "bold"),
                            command=self.show_add_product_screen)
        btn_add.pack(pady=15, padx=20, fill="x")

        # Scrollable List
        list_frame = tk.Frame(self.container, bg="#ecf0f1")
        list_frame.pack(fill="both", expand=True, padx=10)
        
        products = sorted(list(self.db.data["products"].keys()))
        
        if not products:
            tk.Label(list_frame, text="No products yet.", bg="#ecf0f1", fg="#7f8c8d").pack(pady=20)

        for p_name in products:
            p_data = self.db.get_product(p_name)
            
            # Card UI
            card = tk.Frame(list_frame, bg="white", pady=10, padx=10, relief="raised", bd=1)
            card.pack(fill="x", pady=5)
            
            # Icon + Name
            tk.Label(card, text=f"{p_data['icon']} {p_name}", bg="white", fg="#2c3e50", font=("Arial", 14, "bold")).pack(anchor="w")
            
            # Pool Amount
            tk.Label(card, text=f"{p_data['pool']:.1f} lbs available", bg="white", fg="#7f8c8d", font=("Arial", 11)).pack(anchor="w")
            
            # Click Bindings
            card.bind("<Button-1>", lambda e, p=p_name: self.show_product_hub(p))
            for child in card.winfo_children():
                child.bind("<Button-1>", lambda e, p=p_name: self.show_product_hub(p))

    # === 2. ADD PRODUCT SCREEN ===
    def show_add_product_screen(self):
        self.clear_screen()
        tk.Label(self.container, text="Create New Product", font=("Arial", 16, "bold"), bg="#ecf0f1", fg="#2c3e50").pack(pady=20)
        
        form = tk.Frame(self.container, bg="white", padx=20, pady=20)
        form.pack(fill="x", padx=20)
        
        tk.Label(form, text="Product Name", bg="white", fg="#2c3e50").pack(anchor="w")
        ent_name = tk.Entry(form, font=("Arial", 12), bg="#f8f9fa", fg="black")
        ent_name.pack(fill="x", pady=5)
        
        tk.Label(form, text="Category", bg="white", fg="#2c3e50").pack(anchor="w", pady=(10,0))
        cat_var = tk.StringVar(value="Vegetable")
        ttk.Combobox(form, textvariable=cat_var, values=["Fruit", "Vegetable", "Dairy", "Meat"], state="readonly").pack(fill="x", pady=5)
        
        def save():
            name = ent_name.get()
            if not name: return messagebox.showerror("Error", "Name required")
            success, msg = self.db.add_product(name, cat_var.get())
            if success: self.show_home_screen()
            else: messagebox.showerror("Error", msg)

        tk.Button(self.container, text="Save Product", bg="#2980b9", fg="black", highlightbackground="#2980b9", font=("Arial", 12, "bold"), command=save).pack(fill="x", padx=20, pady=20)
        tk.Button(self.container, text="Cancel", bg="#95a5a6", fg="black", highlightbackground="#95a5a6", font=("Arial", 12), command=self.show_home_screen).pack(fill="x", padx=20)

    # === 3. PRODUCT HUB ===
    def show_product_hub(self, product_name):
        self.clear_screen()
        p_data = self.db.get_product(product_name)
        
        # Header
        header = tk.Frame(self.container, bg="white", pady=20, relief="raised", bd=1)
        header.pack(fill="x")
        tk.Label(header, text=p_data['icon'], font=("Arial", 40), bg="white").pack()
        tk.Label(header, text=product_name, font=("Arial", 20, "bold"), bg="white", fg="#2c3e50").pack()
        tk.Label(header, text=f"{p_data['pool']:.2f} lbs", font=("Arial", 28, "bold"), fg="#27ae60", bg="white").pack()

        # Action Buttons
        btn_frame = tk.Frame(self.container, bg="#ecf0f1", pady=20)
        btn_frame.pack(fill="x", padx=20)
        
        # FIX: Text is BLACK. 'highlightbackground' sets the border color on Mac.
        tk.Button(btn_frame, text="📥 Harvest (IN)", bg="#27ae60", fg="black", highlightbackground="#27ae60",
                  font=("Arial", 14, "bold"), height=2,
                  command=lambda: self.show_transaction(product_name, "IN")).pack(fill="x", pady=5)
        
        tk.Button(btn_frame, text="📤 Sell (OUT)", bg="#c0392b", fg="black", highlightbackground="#c0392b",
                  font=("Arial", 14, "bold"), height=2,
                  command=lambda: self.show_transaction(product_name, "OUT")).pack(fill="x", pady=5)
        
        tk.Button(btn_frame, text="📜 View History", bg="#3498db", fg="black", highlightbackground="#3498db",
                  font=("Arial", 12),
                  command=lambda: self.show_history(product_name)).pack(fill="x", pady=5)

        tk.Button(self.container, text="Back to List", bg="#95a5a6", fg="black", highlightbackground="#95a5a6",
                  font=("Arial", 12),
                  command=self.show_home_screen).pack(side="bottom", fill="x", pady=20, padx=20)

    # === 4. TRANSACTION SCREEN ===
    def show_transaction(self, product_name, action):
        self.clear_screen()
        p_data = self.db.get_product(product_name)
        
        color = "#27ae60" if action == "IN" else "#c0392b"
        action_title = "Harvesting" if action == "IN" else "Selling"
        
        # Banner Header
        tk.Label(self.container, text=f"{action_title} {product_name}", bg=color, fg="white", font=("Arial", 16, "bold"), pady=15).pack(fill="x")

        form = tk.Frame(self.container, bg="white", padx=20, pady=20)
        form.pack(fill="both", expand=True, padx=10, pady=10)

        # Qty Input
        tk.Label(form, text="How many?", bg="white", fg="#2c3e50", font=("Arial", 12, "bold")).pack(anchor="w")
        ent_qty = tk.Entry(form, font=("Arial", 18), bg="#f8f9fa", fg="black", highlightthickness=1)
        ent_qty.pack(fill="x", pady=5)

        # Unit Selector
        tk.Label(form, text="Unit Type", bg="white", fg="#2c3e50", font=("Arial", 12, "bold")).pack(anchor="w", pady=(15, 0))
        
        # Format units nicely
        formatted_units = []
        raw_units_map = {} 
        for u_name, u_weight in p_data["known_units"].items():
            display_str = f"{u_name} ({u_weight} lbs)"
            formatted_units.append(display_str)
            raw_units_map[display_str] = u_name
            
        formatted_units.append("+ Create New Unit...")
        
        unit_var = tk.StringVar()
        dropdown = ttk.Combobox(form, textvariable=unit_var, values=formatted_units, state="readonly", font=("Arial", 12))
        dropdown.pack(fill="x", pady=5)
        dropdown.current(0)

        # Dynamic Form for New Units
        new_unit_frame = tk.Frame(form, bg="#ecf0f1", bd=1, relief="solid", padx=10, pady=10)
        tk.Label(new_unit_frame, text="Define New Unit:", bg="#ecf0f1", fg="#2c3e50", font=("Arial", 10, "bold")).pack(anchor="w")
        tk.Label(new_unit_frame, text="Name (e.g., Red Bucket)", bg="#ecf0f1", fg="#2c3e50").pack(anchor="w")
        ent_new_name = tk.Entry(new_unit_frame, bg="white", fg="black")
        ent_new_name.pack(fill="x")
        tk.Label(new_unit_frame, text="Weight of ONE (lbs)", bg="#ecf0f1", fg="#2c3e50").pack(anchor="w")
        ent_new_weight = tk.Entry(new_unit_frame, bg="white", fg="black")
        ent_new_weight.pack(fill="x")

        def toggle_new_unit_form(*args):
            if unit_var.get() == "+ Create New Unit...":
                new_unit_frame.pack(fill="x", pady=10)
            else:
                new_unit_frame.pack_forget()
        unit_var.trace_add("write", toggle_new_unit_form)

        # Submit Logic
        def submit():
            qty = ent_qty.get()
            selection = unit_var.get()
            unit_name_final = ""
            weight = 0.0

            if not qty: return messagebox.showerror("Error", "Enter Quantity")

            if selection == "+ Create New Unit...":
                unit_name_final = ent_new_name.get()
                w_str = ent_new_weight.get()
                if not unit_name_final or not w_str: return messagebox.showerror("Error", "Fill details")
                try: weight = float(w_str)
                except ValueError: return messagebox.showerror("Error", "Weight must be number")
            else:
                unit_name_final = raw_units_map[selection]
                weight = p_data["known_units"][unit_name_final]

            success, msg = self.db.update_pool(product_name, qty, unit_name_final, weight, action)
            if success:
                messagebox.showinfo("Done", msg)
                self.show_product_hub(product_name)
            else:
                messagebox.showerror("Error", msg)

        # Buttons - Black Text for Visibility
        tk.Button(form, text="Confirm", bg=color, fg="black", highlightbackground=color, font=("Arial", 14, "bold"), height=2, command=submit).pack(side="bottom", fill="x")
        tk.Button(form, text="Cancel", bg="#95a5a6", fg="black", highlightbackground="#95a5a6", font=("Arial", 12), command=lambda: self.show_product_hub(product_name)).pack(side="bottom", fill="x", pady=5)

    # === 5. HISTORY SCREEN ===
    def show_history(self, product_name):
        self.clear_screen()
        
        # Header - Blue
        tk.Label(self.container, text=f"History: {product_name}", bg="#3498db", fg="white", font=("Arial", 16, "bold"), pady=15).pack(fill="x")

        # List Area
        list_frame = tk.Frame(self.container, bg="#ecf0f1")
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(list_frame, bg="#ecf0f1")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#ecf0f1")

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Logs
        logs = [x for x in self.db.data["history"] if x["product"] == product_name]
        
        if not logs:
            tk.Label(scrollable_frame, text="No history yet.", bg="#ecf0f1", fg="#7f8c8d").pack(pady=20)
        
        for log in logs:
            card = tk.Frame(scrollable_frame, bg="white", pady=10, padx=10)
            card.pack(fill="x", pady=5, padx=5)
            
            color = "#27ae60" if log["action"] == "IN" else "#c0392b"
            tk.Label(card, text=log["action"], fg=color, bg="white", font=("Arial", 12, "bold"), width=4).pack(side="left")
            
            mid = tk.Frame(card, bg="white")
            mid.pack(side="left", fill="both", expand=True, padx=10)
            tk.Label(mid, text=log["qty_display"], bg="white", fg="black", font=("Arial", 11, "bold")).pack(anchor="w")
            tk.Label(mid, text=log["timestamp"], bg="white", fg="gray", font=("Arial", 9)).pack(anchor="w")
            
            sign = "+" if log["action"] == "IN" else "-"
            tk.Label(card, text=f"{sign}{log['weight_change']:.1f} lbs", bg="white", fg="black", font=("Arial", 11)).pack(side="right")

        tk.Button(self.container, text="Back", bg="#95a5a6", fg="black", highlightbackground="#95a5a6", font=("Arial", 12),
                  command=lambda: self.show_product_hub(product_name)).pack(fill="x", padx=20, pady=20)

if __name__ == "__main__":
    app = MangoApp()
    app.mainloop()