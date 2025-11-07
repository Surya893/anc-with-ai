"""
Quick script to list all tables in the SQLite database
"""
import sqlite3

db_path = "anc_system.db"

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Query to get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")

tables = cursor.fetchall()

print(f"Tables in {db_path}:")
print("=" * 50)
for table in tables:
    print(f"  - {table[0]}")

print("\n" + "=" * 50)
print(f"Total tables: {len(tables)}")

conn.close()
