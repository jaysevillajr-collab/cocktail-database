import sqlite3
import os

# Connect to the backup database
backup_db_path = "C:/Users/jsevilla/OneDrive/Cocktail App Data/cocktail_database.db"
if os.path.exists(backup_db_path):
    conn = sqlite3.connect(backup_db_path)
    cursor = conn.cursor()

    # Check if image_path column exists
    cursor.execute("PRAGMA table_info(cocktail_notes)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'image_path' not in columns:
        # Add image_path column
        cursor.execute("ALTER TABLE cocktail_notes ADD COLUMN image_path TEXT")
        print("Added image_path column to cocktail_notes table in backup database")
    else:
        print("image_path column already exists in cocktail_notes table in backup database")

    conn.commit()
    conn.close()
else:
    print("Backup database not found")
