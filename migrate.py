# migrate.py — run once: python migrate.py
import sqlite3

conn = sqlite3.connect("vidora.db")
cur = conn.cursor()

migrations = [
    "ALTER TABLE users ADD COLUMN plan VARCHAR DEFAULT 'free'",
    "ALTER TABLE users ADD COLUMN razorpay_customer_id VARCHAR",
    "ALTER TABLE users ADD COLUMN razorpay_subscription_id VARCHAR",
    "ALTER TABLE users ADD COLUMN subscription_status VARCHAR DEFAULT 'inactive'",
    "ALTER TABLE users ADD COLUMN videos_used_this_period INTEGER DEFAULT 0",
    "ALTER TABLE users ADD COLUMN period_start DATETIME",
]

for m in migrations:
    try:
        cur.execute(m)
        print("OK:", m)
    except sqlite3.OperationalError as e:
        print("SKIP:", m, "-", e)

conn.commit()
conn.close()