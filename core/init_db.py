"""Initialize the SQLite database."""

from core.db import init_db, DB_PATH

def main() -> None:
    init_db()
    print(f"Database ready at: {DB_PATH}")

if __name__ == "__main__":
    main()
