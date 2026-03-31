import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def check_env_vars():
    required_vars = ["TELEGRAM_BOT_TOKEN", "SUPABASE_URL", "SUPABASE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    print("✅ Environment variables check passed.")
    return True


def check_supabase_connection():
    try:
        from config import supabase

        checks = [
            ("users", "user_id,lang"),
            ("user_states", "user_id,state_name,state_data"),
            ("notes", "id,user_id,content"),
            ("reminders", "id,user_id,chat_id,message,time"),
            ("ai_usage", "user_id,usage_date,usage_count"),
            ("metro_favorites", "user_id,station_id,direction_id"),
            ("tool_usage", "user_id,tool_name,action"),
        ]

        for table_name, columns in checks:
            supabase.table(table_name).select(columns).limit(1).execute()

        print("✅ Supabase connection successful.")
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False


def check_imports():
    try:
        import main  # noqa: F401

        print("✅ Main module import successful.")
        return True
    except Exception as e:
        print(f"❌ Main module import failed: {e}")
        return False


if __name__ == "__main__":
    print("🔍 Starting Health Check...")
    env_ok = check_env_vars()
    if env_ok:
        db_ok = check_supabase_connection()
        import_ok = check_imports()

        if env_ok and db_ok and import_ok:
            print("🚀 System is ready for startup!")
            sys.exit(0)
        else:
            print("⚠️ System has issues. Check logs above.")
            sys.exit(1)
    else:
        print("🛑 Critical environment configuration error.")
        sys.exit(1)
