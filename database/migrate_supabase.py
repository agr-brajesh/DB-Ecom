"""
Supabase PostgreSQL Migration Executor
Executes database/supabase_migration.sql against your remote Supabase database.
"""

import os
import sys
from dotenv import load_dotenv

# Load .env
load_dotenv()

SQL_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "supabase_migration.sql")
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
PROJECT_REF = SUPABASE_URL.replace("https://", "").replace(".supabase.co", "").strip()

DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD") or os.getenv("DATABASE_PASSWORD")
DATABASE_URL = os.getenv("DATABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def print_manual_instructions():
    print("\n" + "=" * 65)
    print(" HOW TO APPLY THE MIGRATION TO SUPABASE (1-CLICK)")
    print("=" * 65)
    print("Supabase client publishable keys (sb_publishable_...) do not have")
    print("permission to execute DDL (CREATE TABLE).")
    print("\nTo apply the migration in 5 seconds:")
    print(f"1. Open your Supabase Dashboard SQL Editor:")
    print(f"   -> https://supabase.com/dashboard/project/{PROJECT_REF}/sql/new")
    print("2. Copy all contents from:")
    print(f"   -> database/supabase_migration.sql")
    print("3. Paste into the SQL Editor and click 'RUN'.")
    print("\n-------------------------------------------------------------")
    print("OR AUTOMATE IT VIA TERMINAL:")
    print("Add your database password to your .env file:")
    print("   SUPABASE_DB_PASSWORD=your_database_password_here")
    print("Then re-run: python database/migrate_supabase.py")
    print("=" * 65 + "\n")

def run_migration_with_psycopg():
    try:
        import psycopg2
    except ImportError:
        print("[!] psycopg2 not found. Install it with: pip install psycopg2-binary")
        return False

    conn_string = DATABASE_URL
    if not conn_string and DB_PASSWORD:
        # Standard Supabase transaction pooler URL
        conn_string = f"postgresql://postgres.{PROJECT_REF}:{DB_PASSWORD}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

    if not conn_string:
        return False

    print(f"[*] Connecting to Supabase PostgreSQL at {PROJECT_REF}...")
    try:
        with open(SQL_FILE_PATH, "r", encoding="utf-8") as f:
            sql_content = f.read()

        conn = psycopg2.connect(conn_string, connect_timeout=15)
        conn.autocommit = True
        cursor = conn.cursor()
        print("[*] Applying supabase_migration.sql...")
        cursor.execute(sql_content)
        cursor.close()
        conn.close()
        print("[SUCCESS] Schema migrated successfully to remote Supabase PostgreSQL!")
        return True
    except Exception as e:
        print(f"[!] PostgreSQL Migration Error: {e}")
        return False

if __name__ == "__main__":
    if DB_PASSWORD or DATABASE_URL:
        success = run_migration_with_psycopg()
        if not success:
            print_manual_instructions()
    else:
        print_manual_instructions()
