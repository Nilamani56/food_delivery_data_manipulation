import os
import random
import csv
from datetime import datetime, timedelta

# ---- 1. CONFIGURATION PARAMETERS ----
TOTAL_ORDERS = 10_000_000
NUM_USERS = 800_000
NUM_RESTAURANTS = 25_000
BATCH_SIZE = 500_000

CITIES = ["Bengaluru", "Mumbai", "Delhi NCR", "Hyderabad", "Pune", "Chennai", "Kolkata", "Ahmedabad"]
CUISINES = ["North Indian", "South Indian", "Biryani", "Indo-Chinese", "Street Food", "Mughlai", "Fast Food/Desserts"]

# Indian Contextual Names
FIRST_NAMES = ["Aarav", "Vihaan", "Vivaan", "Ananya", "Diya", "Priya", "Rohan", "Rahul", "Aditya", "Sai", "Sneha", "Vikram", "Neha", "Arjun", "Karan"]
LAST_NAMES = ["Sharma", "Patel", "Das", "Reddy", "Joshi", "Nair", "Kumar", "Singh", "Mehta", "Iyer", "Rao", "Gupta", "Choudhury"]

MENU_TEMPLATES = {
    "North Indian": [("Paneer Butter Masala", 320, True), ("Garlic Naan", 60, True), ("Dal Makhani", 280, True), ("Butter Chicken", 380, False)],
    "South Indian": [("Masala Dosa", 120, True), ("Idli Sambar", 80, True), ("Filter Coffee", 60, True), ("Chicken Chettinad", 340, False)],
    "Biryani": [("Veg Dum Biryani", 260, True), ("Chicken Dum Biryani", 320, False), ("Mutton Biryani", 450, False), ("Raita", 40, True)],
    "Indo-Chinese": [("Veg Hakka Noodles", 220, True), ("Chilli Chicken", 290, False), ("Manchow Soup", 140, True), ("Spring Rolls", 180, True)],
    "Street Food": [("Pav Bhaji", 140, True), ("Pani Puri", 70, True), ("Samosa Chat", 90, True), ("Vada Pav", 50, True)],
    "Mughlai": [("Chicken Tikka Masala", 360, False), ("Tandoori Roti", 40, True), ("Kadhai Paneer", 310, True), ("Mutton Korma", 480, False)],
    "Fast Food/Desserts": [("Margherita Pizza", 299, True), ("Burger Combo", 249, False), ("Gulab Jamun", 80, True), ("Chocolate Brownie", 150, True)]
}

print("🚀 Starting 10-Million Row Dataset Generation Pipeline...")

# ---- 2. GENERATE CORE MASTER TABLES ----
# Users
users = []
for i in range(1, NUM_USERS + 1):
    uid = f"USR{i:06d}"
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    city = random.choice(CITIES)
    users.append([uid, name, f"{name.lower().replace(' ', '.')}@example.com", f"+91 {random.randint(60000, 99999)} {random.randint(10000, 99999)}", f"Flat {random.randint(101, 909)}, Area {random.randint(1, 25)}", city, (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 700))).strftime("%Y-%m-%d")])

# Restaurants & Menu Items
restaurants = []
menu_items = []
item_counter = 1
restaurant_menu_map = {} # Quick lookup map for order generation

for r_idx in range(1, NUM_RESTAURANTS + 1):
    rid = f"RES{r_idx:05d}"
    cuisine = random.choice(CUISINES)
    city = random.choice(CITIES)
    restaurants.append([rid, f"The Indian {cuisine} Kitchen {r_idx}", cuisine, round(random.uniform(3.5, 4.9), 1), city, "Active"])
    
    restaurant_menu_map[rid] = []
    # Inject items based on chosen cuisine
    for dish_name, base_price, is_veg in MENU_TEMPLATES[cuisine]:
        it_id = f"ITM{item_counter:07d}"
        # Inject minor price variations per restaurant
        final_price = float(base_price + random.randint(-20, 50))
        menu_items.append([it_id, rid, dish_name, "Main/Side", final_price, is_veg])
        restaurant_menu_map[rid].append({"id": it_id, "price": final_price})
        item_counter += 1

# Save Master Tables Immediately to free up operational RAM
def save_csv(filename, headers, rows):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"✅ Saved {filename}")

save_csv("users.csv", ["user_id", "name", "email", "phone", "address", "city", "joined_at"], users)
save_csv("restaurants.csv", ["restaurant_id", "name", "cuisine", "rating", "city", "status"], restaurants)
save_csv("menu_items.csv", ["item_id", "restaurant_id", "item_name", "category", "price", "is_vegetarian"], menu_items)

# Free up Python memory
del users
del menu_items

# ---- 3. GENERATE HIGH VOLUME TRANSACTIONAL TABLES IN BATCH CHUNKS ----
order_headers = ["order_id", "user_id", "restaurant_id", "total_amount", "payment_mode", "order_status", "ordered_at"]
order_items_headers = ["order_item_id", "order_id", "item_id", "quantity", "price_per_unit"]

with open("orders.csv", "w", newline="", encoding="utf-8") as f_ord, \
     open("order_items.csv", "w", newline="", encoding="utf-8") as f_items:
     
    ord_writer = csv.writer(f_ord)
    item_writer = csv.writer(f_items)
    
    ord_writer.writerow(order_headers)
    item_writer.writerow(order_items_headers)
    
    order_id_counter = 1
    order_item_id_counter = 1
    start_date = datetime(2026, 1, 1)
    
    # Process transactions in loop blocks to maintain minimal streaming memory overhead
    for batch_num in range(TOTAL_ORDERS // BATCH_SIZE):
        batch_orders = []
        batch_order_items = []
        
        for _ in range(BATCH_SIZE):
            oid = f"ORD{order_id_counter:08d}"
            uid = f"USR{random.randint(1, NUM_USERS):06d}"
            rid = f"RES{random.randint(1, NUM_RESTAURANTS):05d}"
            
            # Select random menu options mapped to this active restaurant
            available_items = restaurant_menu_map[rid]
            num_dishes = random.randint(1, 3)
            selected_dishes = random.sample(available_items, min(num_dishes, len(available_items)))
            
            order_total = 0.0
            for dish in selected_dishes:
                qty = random.randint(1, 2)
                item_cost = dish["price"]
                order_total += item_cost * qty
                
                batch_order_items.append([f"OI{order_item_id_counter:09d}", oid, dish["id"], qty, item_cost])
                order_item_id_counter += 1
            
            # Timestamp scaling across 2026
            order_time = start_date + timedelta(seconds=random.randint(0, 31536000))
            pmode = random.choices(["UPI", "Credit/Debit Card", "Net Banking", "Cash on Delivery"], weights=[65, 20, 5, 10])[0]
            status = random.choices(["Delivered", "Cancelled", "Returned"], weights=[92, 6, 2])[0]
            
            batch_orders.append([oid, uid, rid, round(order_total, 2), pmode, status, order_time.strftime("%Y-%m-%d %H:%M:%S")])
            order_id_counter += 1
            
        ord_writer.writerows(batch_orders)
        item_writer.writerows(batch_order_items)
        print(f"📈 Streamed batch {batch_num + 1}/{(TOTAL_ORDERS // BATCH_SIZE)} ({order_id_counter - 1} total orders processed)")

print("✨ Successfully completed generating all files with 10 Million orders locally!")
