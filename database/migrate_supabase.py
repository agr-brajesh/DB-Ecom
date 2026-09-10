"""
Supabase PostgreSQL Migration Runner
Connects to Supabase on region ap-southeast-2 and applies database/supabase_migration.sql
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load .env
load_dotenv()

SQL_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "supabase_migration.sql")
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
PROJECT_REF = "kxipulbczlqfenntmqzv"
DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")

if not DB_PASSWORD:
    print("[!] Error: SUPABASE_DB_PASSWORD not found in .env")
    exit(1)

# Supabase ap-southeast-2 host
HOST = "aws-0-ap-southeast-2.pooler.supabase.com"
USER = f"postgres.{PROJECT_REF}"
PORT = 5432  # Session pooler for clean DDL execution

print("=" * 65)
print(" EXECUTING REMOTE SUPABASE MIGRATION")
print("=" * 65)
print(f"[*] Connecting to {HOST}:{PORT}...")
print(f"[*] Target Tenant: {USER}")

try:
    conn = psycopg2.connect(
        host=HOST,
        port=PORT,
        user=USER,
        password=DB_PASSWORD,
        dbname="postgres",
        connect_timeout=15,
        sslmode="require"
    )
    conn.autocommit = True
    cursor = conn.cursor()
    print("[+] Connected to Supabase PostgreSQL database successfully!")

    print(f"[*] Reading migration script: {SQL_FILE_PATH}...")
    with open(SQL_FILE_PATH, "r", encoding="utf-8") as f:
        sql_script = f.read()

    print("[*] Applying schema, tables, triggers, views, RLS policies, and seed data...")
    cursor.execute(sql_script)
    print("[+] Migration executed successfully!")

    # Verify tables created
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\n[+] Verified Tables in Supabase ({len(tables)} created):")
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t};")
        cnt = cursor.fetchone()[0]
        print(f"    - {t}: {cnt} rows")

    # Verify views created
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.views 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    views = [row[0] for row in cursor.fetchall()]
    print(f"\n[+] Verified Analytical Views in Supabase ({len(views)} created):")
    for v in views:
        print(f"    - {v}")

    cursor.close()
    conn.close()
    print("\n" + "=" * 65)
    print(" ALL MIGRATIONS HAVE BEEN PUSHED TO SUPABASE SUCCESSFULLY!")
    print("=" * 65)

except Exception as e:
    print(f"\n[!] Migration failed with error: {e}")
    exit(1)
