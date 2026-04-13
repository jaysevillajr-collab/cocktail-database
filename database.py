import sqlite3
from typing import List, Dict, Optional, Tuple
import os
import json

class DatabaseManager:
    """Manages SQLite database connections and operations for the cocktail database."""
    
    def __init__(self, db_path: str = 'cocktail_database.db', backup_db_path: Optional[str] = None):
        self.db_path = db_path
        self.backup_db_path = backup_db_path
        self.conn = None
        self.backup_conn = None
        
    def connect(self):
        """Establish database connection."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
            
            # Connect to backup database if configured
            if self.backup_db_path and os.path.exists(self.backup_db_path):
                self.backup_conn = sqlite3.connect(self.backup_db_path)
                self.backup_conn.row_factory = sqlite3.Row
            return True
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            return False
    
    def close(self):
        """Close database connections."""
        if self.conn:
            self.conn.close()
            self.conn = None
        if self.backup_conn:
            self.backup_conn.close()
            self.backup_conn = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def get_record_counts(self, db_conn=None):
        """Get record counts from both tables for comparison."""
        conn = db_conn if db_conn else self.conn
        if not conn:
            return {'alcohol_inventory': 0, 'cocktail_notes': 0}
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM alcohol_inventory")
            alcohol_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM cocktail_notes")
            cocktail_count = cursor.fetchone()[0]
            return {'alcohol_inventory': alcohol_count, 'cocktail_notes': cocktail_count}
        except sqlite3.Error as e:
            print(f"Error getting record counts: {e}")
            return {'alcohol_inventory': 0, 'cocktail_notes': 0}
    
    def set_backup_path(self, backup_path: str):
        """Set or update the backup database path."""
        self.backup_db_path = backup_path
        # Reconnect to backup if path is valid
        if backup_path and os.path.exists(backup_path):
            if self.backup_conn:
                self.backup_conn.close()
            self.backup_conn = sqlite3.connect(backup_path)
            self.backup_conn.row_factory = sqlite3.Row
    
    # Alcohol Inventory Operations
    def get_all_alcohol(self) -> List[Dict]:
        """Retrieve all alcohol inventory records."""
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM alcohol_inventory")
        return [dict(row) for row in cursor.fetchall()]
    
    def add_alcohol(self, data: Dict) -> bool:
        """Add a new alcohol record."""
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            cursor.execute(
                f"INSERT INTO alcohol_inventory ({columns}) VALUES ({placeholders})",
                list(data.values())
            )
            self.conn.commit()
            
            # Sync to backup if configured
            if self.backup_conn:
                try:
                    cursor = self.backup_conn.cursor()
                    cursor.execute(
                        f"INSERT INTO alcohol_inventory ({columns}) VALUES ({placeholders})",
                        list(data.values())
                    )
                    self.backup_conn.commit()
                except sqlite3.Error as e:
                    print(f"Error syncing to backup: {e}")
            
            return True
        except sqlite3.Error as e:
            print(f"Error adding alcohol: {e}")
            self.conn.rollback()
            return False
    
    def update_alcohol(self, brand: str, data: Dict) -> bool:
        """Update an existing alcohol record by brand."""
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
            cursor.execute(
                f"UPDATE alcohol_inventory SET {set_clause} WHERE Brand = ?",
                list(data.values()) + [brand]
            )
            self.conn.commit()
            
            # Sync to backup if configured
            if self.backup_conn:
                try:
                    cursor = self.backup_conn.cursor()
                    cursor.execute(
                        f"UPDATE alcohol_inventory SET {set_clause} WHERE Brand = ?",
                        list(data.values()) + [brand]
                    )
                    self.backup_conn.commit()
                except sqlite3.Error as e:
                    print(f"Error syncing to backup: {e}")
            
            return True
        except sqlite3.Error as e:
            print(f"Error updating alcohol: {e}")
            self.conn.rollback()
            return False
    
    def delete_alcohol(self, brand: str) -> bool:
        """Delete an alcohol record by brand."""
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM alcohol_inventory WHERE Brand = ?", (brand,))
            self.conn.commit()
            
            # Sync to backup if configured
            if self.backup_conn:
                try:
                    cursor = self.backup_conn.cursor()
                    cursor.execute("DELETE FROM alcohol_inventory WHERE Brand = ?", (brand,))
                    self.backup_conn.commit()
                except sqlite3.Error as e:
                    print(f"Error syncing to backup: {e}")
            
            return True
        except sqlite3.Error as e:
            print(f"Error deleting alcohol: {e}")
            self.conn.rollback()
            return False
    
    # Cocktail Notes Operations
    def get_all_cocktails(self) -> List[Dict]:
        """Retrieve all cocktail records."""
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM cocktail_notes")
        return [dict(row) for row in cursor.fetchall()]
    
    def add_cocktail(self, data: Dict) -> bool:
        """Add a new cocktail record."""
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            cursor.execute(
                f"INSERT INTO cocktail_notes ({columns}) VALUES ({placeholders})",
                list(data.values())
            )
            self.conn.commit()
            
            # Sync to backup if configured
            if self.backup_conn:
                try:
                    cursor = self.backup_conn.cursor()
                    cursor.execute(
                        f"INSERT INTO cocktail_notes ({columns}) VALUES ({placeholders})",
                        list(data.values())
                    )
                    self.backup_conn.commit()
                except sqlite3.Error as e:
                    print(f"Error syncing to backup: {e}")
            
            return True
        except sqlite3.Error as e:
            print(f"Error adding cocktail: {e}")
            self.conn.rollback()
            return False
    
    def update_cocktail(self, cocktail_name: str, data: Dict) -> bool:
        """Update an existing cocktail record by name."""
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
            cursor.execute(
                f"UPDATE cocktail_notes SET {set_clause} WHERE Cocktail_Name = ?",
                list(data.values()) + [cocktail_name]
            )
            self.conn.commit()
            
            # Sync to backup if configured
            if self.backup_conn:
                try:
                    cursor = self.backup_conn.cursor()
                    cursor.execute(
                        f"UPDATE cocktail_notes SET {set_clause} WHERE Cocktail_Name = ?",
                        list(data.values()) + [cocktail_name]
                    )
                    self.backup_conn.commit()
                except sqlite3.Error as e:
                    print(f"Error syncing to backup: {e}")
            
            return True
        except sqlite3.Error as e:
            print(f"Error updating cocktail: {e}")
            self.conn.rollback()
            return False
    
    def delete_cocktail(self, cocktail_name: str) -> bool:
        """Delete a cocktail record by name."""
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM cocktail_notes WHERE Cocktail_Name = ?", (cocktail_name,))
            self.conn.commit()
            
            # Sync to backup if configured
            if self.backup_conn:
                try:
                    cursor = self.backup_conn.cursor()
                    cursor.execute("DELETE FROM cocktail_notes WHERE Cocktail_Name = ?", (cocktail_name,))
                    self.backup_conn.commit()
                except sqlite3.Error as e:
                    print(f"Error syncing to backup: {e}")
            
            return True
        except sqlite3.Error as e:
            print(f"Error deleting cocktail: {e}")
            self.conn.rollback()
            return False
