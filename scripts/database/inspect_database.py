"""
Comprehensive database inspection script
Shows tables, schemas, and row counts
"""
import sqlite3

db_path = "anc_system.db"

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 70)
print(f"DATABASE INSPECTION: {db_path}")
print("=" * 70)

# Get all tables (excluding sqlite internal tables)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
tables = cursor.fetchall()

print(f"\nTotal user tables: {len(tables)}\n")

for table_name_tuple in tables:
    table_name = table_name_tuple[0]

    print(f"\n{'─' * 70}")
    print(f"TABLE: {table_name}")
    print('─' * 70)

    # Get table schema
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()

    print("\nColumns:")
    for col in columns:
        col_id, name, col_type, not_null, default, pk = col
        pk_marker = " [PRIMARY KEY]" if pk else ""
        null_marker = " NOT NULL" if not_null else ""
        default_marker = f" DEFAULT {default}" if default else ""
        print(f"  {name:<25} {col_type:<15}{pk_marker}{null_marker}{default_marker}")

    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    row_count = cursor.fetchone()[0]
    print(f"\nRow count: {row_count}")

    # Show foreign keys if any
    cursor.execute(f"PRAGMA foreign_key_list({table_name});")
    fks = cursor.fetchall()
    if fks:
        print("\nForeign Keys:")
        for fk in fks:
            fk_id, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
            print(f"  {from_col} -> {ref_table}({to_col}) ON DELETE {on_delete}")

# Get indexes
print(f"\n{'─' * 70}")
print("INDEXES")
print('─' * 70)
cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';")
indexes = cursor.fetchall()
if indexes:
    for idx_name, tbl_name in indexes:
        print(f"  {idx_name:<40} on table: {tbl_name}")
else:
    print("  No user-defined indexes")

print("\n" + "=" * 70)

conn.close()
