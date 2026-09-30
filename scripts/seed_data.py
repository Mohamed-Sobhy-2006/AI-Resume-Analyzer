"""Create the database tables and insert sample jobs + learning resources:  python scripts/seed_data.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.seed_service import seed_database  # noqa: E402


def main():
    added = seed_database()
    print(f"Database ready. Added {added['jobs']} jobs and {added['learning_resources']} learning resources "
          "(0 means they already existed).")


if __name__ == "__main__":
    main()
