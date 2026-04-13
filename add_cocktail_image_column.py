import sqlite3

# Connect to the database
conn = sqlite3.connect('cocktail_database.db')
cursor = conn.cursor()

# Check if image_path column exists
cursor.execute("PRAGMA table_info(cocktail_notes)")
columns = [col[1] for col in cursor.fetchall()]

if 'image_path' not in columns:
    # Add image_path column
    cursor.execute("ALTER TABLE cocktail_notes ADD COLUMN image_path TEXT")
    print("Added image_path column to cocktail_notes table")
else:
    print("image_path column already exists in cocktail_notes table")

conn.commit()
conn.close()
