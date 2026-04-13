import sys
import os
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel, QScrollArea, QStatusBar, QColorDialog, QMenu, QFileDialog, QDialog, QMessageBox, QVBoxLayout as QVBoxLayout2
from PyQt5.QtCore import Qt

from database import DatabaseManager
from alcohol_tab import AlcoholTab
from cocktail_tab import CocktailTab


class DashboardTab(QWidget):
    """Dashboard tab showing statistics and insights."""
    
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_statistics()
    
    def init_ui(self):
        """Initialize the dashboard UI."""
        main_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("📊 Statistics Dashboard")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # Create scroll areas for each statistics section
        # Alcohol statistics scroll area
        alcohol_scroll = QScrollArea()
        alcohol_scroll.setWidgetResizable(True)
        alcohol_scroll.setMaximumHeight(300)
        self.alcohol_stats_label = QLabel()
        self.alcohol_stats_label.setWordWrap(True)
        self.alcohol_stats_label.setStyleSheet("""
            background-color: #f5f5f5; 
            border: 1px solid #d0d0d0; 
            border-radius: 8px; 
            padding: 15px;
            color: #333333;
        """)
        alcohol_scroll.setWidget(self.alcohol_stats_label)
        main_layout.addWidget(alcohol_scroll)
        
        # Cocktail statistics scroll area
        cocktail_scroll = QScrollArea()
        cocktail_scroll.setWidgetResizable(True)
        cocktail_scroll.setMaximumHeight(300)
        self.cocktail_stats_label = QLabel()
        self.cocktail_stats_label.setWordWrap(True)
        self.cocktail_stats_label.setStyleSheet("""
            background-color: #f5f5f5; 
            border: 1px solid #d0d0d0; 
            border-radius: 8px; 
            padding: 15px;
            color: #333333;
        """)
        cocktail_scroll.setWidget(self.cocktail_stats_label)
        main_layout.addWidget(cocktail_scroll)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
    
    def update_theme(self, dark_mode):
        """Update dashboard theme based on dark mode."""
        bg_color = "#2d2d2d" if dark_mode else "#f5f5f5"
        border_color = "#404040" if dark_mode else "#d0d0d0"
        text_color = "#e0e0e0" if dark_mode else "#333333"
        
        style = f"""
            background-color: {bg_color}; 
            border: 1px solid {border_color}; 
            border-radius: 8px; 
            padding: 15px;
            color: {text_color};
        """
        
        self.alcohol_stats_label.setStyleSheet(style)
        self.cocktail_stats_label.setStyleSheet(style)
    
    def load_statistics(self):
        """Load and display statistics."""
        # Alcohol statistics by country
        alcohols = self.db.get_all_alcohol()
        country_counts = {}
        for alcohol in alcohols:
            country = alcohol.get('Country', 'Unknown')
            country_counts[country] = country_counts.get(country, 0) + 1
        
        alcohol_text = "<b>🍹 Alcohol Inventory Statistics</b><br><br>"
        alcohol_text += f"Total Alcohols: {len(alcohols)}<br><br>"
        alcohol_text += "<b>By Country:</b><br>"
        for country, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True):
            alcohol_text += f"• {country}: {count}<br>"
        
        self.alcohol_stats_label.setText(alcohol_text)
        
        # Cocktail statistics by base spirit
        cocktails = self.db.get_all_cocktails()
        spirit_counts = {}
        for cocktail in cocktails:
            spirit = cocktail.get('Base_spirit_1', 'Unknown')
            spirit_counts[spirit] = spirit_counts.get(spirit, 0) + 1
        
        cocktail_text = "<b>🍸 Cocktail Recipe Statistics</b><br><br>"
        cocktail_text += f"Total Cocktails: {len(cocktails)}<br><br>"
        cocktail_text += "<b>By Base Spirit:</b><br>"
        for spirit, count in sorted(spirit_counts.items(), key=lambda x: x[1], reverse=True):
            cocktail_text += f"• {spirit}: {count}<br>"
        
        # Average ratings
        overall_ratings = [float(c.get('Rating_overall', 0)) for c in cocktails if c.get('Rating_overall')]
        if overall_ratings:
            avg_rating = sum(overall_ratings) / len(overall_ratings)
            cocktail_text += f"<br><b>Average Overall Rating:</b> {avg_rating:.1f}/10"
        
        self.cocktail_stats_label.setText(cocktail_text)


class CocktailDatabaseApp(QMainWindow):
    """Main application window for the Cocktail Database Manager."""
    
    def __init__(self):
        super().__init__()
        self.config = self.load_config()
        backup_db_path = self.get_backup_db_path()
        self.db = DatabaseManager(backup_db_path=backup_db_path)
        self.db.connect()
        self.dark_mode = False
        self.backup_enabled = bool(backup_db_path)
        
        # Check and setup backup on startup
        self.setup_backup_on_startup()
        
        self.init_ui()
        self.apply_theme()
        self.update_status_bar()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Cocktail Database Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget with tabbed interface
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Theme toggle button
        header_layout = QHBoxLayout()
        self.theme_button = QPushButton("🌙 Dark Mode")
        self.theme_button.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_button)
        
        # Custom theme button
        self.custom_theme_button = QPushButton("🎨 Custom Theme")
        self.custom_theme_button.clicked.connect(self.show_custom_theme_dialog)
        header_layout.addWidget(self.custom_theme_button)
        
        # Settings button
        self.settings_button = QPushButton("⚙️ Settings")
        self.settings_button.clicked.connect(self.show_settings_menu)
        header_layout.addWidget(self.settings_button)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Tab 1: Dashboard
        self.dashboard_tab = DashboardTab(self.db)
        self.tab_widget.addTab(self.dashboard_tab, "📊 Dashboard")
        
        # Tab 2: Alcohol Inventory
        self.alcohol_tab = AlcoholTab(self.db)
        self.tab_widget.addTab(self.alcohol_tab, "Alcohol Inventory")
        
        # Tab 3: Cocktail Recipes
        self.cocktail_tab = CocktailTab(self.db)
        self.tab_widget.addTab(self.cocktail_tab, "Cocktail Recipes")
        
        layout.addWidget(self.tab_widget)
        
        # Add status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.on_tab_changed(0)  # Initialize status bar
    
    def on_tab_changed(self, index):
        """Update status bar when tab changes."""
        if index == 0:
            self.status_bar.showMessage("Dashboard - Statistics Overview")
        elif index == 1:
            self.status_bar.showMessage(f"Alcohol Inventory - {self.alcohol_tab.table.rowCount()} items")
        elif index == 2:
            self.status_bar.showMessage(f"Cocktail Recipes - {self.cocktail_tab.table.rowCount()} items")
        self.update_status_bar()
    
    def load_config(self):
        """Load configuration from config.json."""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
        return {'backup_folder': ''}
    
    def save_config(self):
        """Save configuration to config.json."""
        try:
            with open('config.json', 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get_backup_db_path(self):
        """Get the backup database path from config."""
        backup_folder = self.config.get('backup_folder', '')
        if backup_folder and os.path.exists(backup_folder):
            return os.path.join(backup_folder, 'cocktail_database.db')
        return None
    
    def setup_backup_on_startup(self):
        """Check and setup backup on application startup."""
        backup_folder = self.config.get('backup_folder', '')
        
        # If backup folder not configured or not reachable, ask to select
        if not backup_folder or not os.path.exists(backup_folder):
            self.select_backup_folder()
        elif not os.path.exists(os.path.join(backup_folder, 'cocktail_database.db')):
            # Backup folder exists but database doesn't
            reply = QMessageBox.question(
                self,
                'Backup Database Missing',
                f'Backup folder exists at {backup_folder} but cocktail_database.db is not found.\n\n'
                'Would you like to select a different backup folder?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.select_backup_folder()
        else:
            # Both databases exist, compare record counts
            self.compare_and_choose_database()
            # Sync images folder on startup
            self.sync_images_folder()
    
    def select_backup_folder(self):
        """Show dialog to select backup folder."""
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setWindowTitle("Select Backup Folder")
        if dialog.exec():
            selected_folder = dialog.selectedFiles()[0]
            self.config['backup_folder'] = selected_folder
            self.save_config()
            
            # Reconnect database with new backup path
            backup_db_path = self.get_backup_db_path()
            self.db.set_backup_path(backup_db_path)
            self.backup_enabled = bool(backup_db_path)
            
            # Check if database exists in backup folder
            if backup_db_path and os.path.exists(backup_db_path):
                self.compare_and_choose_database()
            else:
                QMessageBox.information(
                    self,
                    'Backup Database Created',
                    f'Backup folder set to {selected_folder}.\n'
                    'Database will be synced to this location on save operations.'
                )
            
            # Sync images folder to backup
            self.sync_images_folder()
            
            self.update_status_bar()
    
    def compare_and_choose_database(self):
        """Compare local and backup databases and ask which to use if counts differ."""
        if not self.db.backup_conn:
            return
        
        local_counts = self.db.get_record_counts(self.db.conn)
        backup_counts = self.db.get_record_counts(self.db.backup_conn)
        
        if local_counts != backup_counts:
            dialog = QDialog(self)
            dialog.setWindowTitle('Database Sync Required')
            dialog.setMinimumWidth(500)
            layout = QVBoxLayout2(dialog)
            
            message = QLabel(
                'The local and backup databases have different record counts:\n\n'
                f'Local Database:\n'
                f'  Alcohol Inventory: {local_counts["alcohol_inventory"]} records\n'
                f'  Cocktail Recipes: {local_counts["cocktail_notes"]} records\n\n'
                f'Backup Database:\n'
                f'  Alcohol Inventory: {backup_counts["alcohol_inventory"]} records\n'
                f'  Cocktail Recipes: {backup_counts["cocktail_notes"]} records\n\n'
                'Which database would you like to use?'
            )
            layout.addWidget(message)
            
            button_layout = QHBoxLayout()
            use_local_btn = QPushButton('Use Local (Overwrite Backup)')
            use_backup_btn = QPushButton('Use Backup (Overwrite Local)')
            
            use_local_btn.clicked.connect(lambda: self.use_local_database(dialog))
            use_backup_btn.clicked.connect(lambda: self.use_backup_database(dialog))
            
            button_layout.addWidget(use_local_btn)
            button_layout.addWidget(use_backup_btn)
            layout.addLayout(button_layout)
            
            dialog.exec()
    
    def use_local_database(self, dialog):
        """Use local database and overwrite backup."""
        dialog.accept()
        QMessageBox.information(self, 'Database Synced', 'Using local database. Backup will be synced on save operations.')
    
    def use_backup_database(self, dialog):
        """Use backup database and overwrite local."""
        dialog.accept()
        # Copy backup database to local
        backup_db_path = self.db.backup_db_path
        if backup_db_path and os.path.exists(backup_db_path):
            import shutil
            shutil.copy2(backup_db_path, 'cocktail_database.db')
            QMessageBox.information(self, 'Database Synced', 'Using backup database. Local database has been overwritten.')
            # Reload data
            self.alcohol_tab.load_data()
            self.cocktail_tab.load_data()
            self.dashboard_tab.load_statistics()
    
    def update_status_bar(self):
        """Update status bar with current save location."""
        if self.backup_enabled:
            self.status_bar.showMessage('Saving to: Local + Backup')
        else:
            self.status_bar.showMessage('Saving to: Local only')
    
    def show_settings_menu(self):
        """Show settings menu to change backup location."""
        dialog = QDialog(self)
        dialog.setWindowTitle('Settings')
        dialog.setMinimumWidth(400)
        layout = QVBoxLayout2(dialog)
        
        # Current backup folder
        backup_folder = self.config.get('backup_folder', 'Not configured')
        backup_label = QLabel(f'Current Backup Folder: {backup_folder}')
        layout.addWidget(backup_label)
        
        # Change backup folder button
        change_backup_btn = QPushButton('Change Backup Folder')
        change_backup_btn.clicked.connect(lambda: [dialog.accept(), self.select_backup_folder()])
        layout.addWidget(change_backup_btn)
        
        # Sync images button
        if self.backup_enabled:
            sync_images_btn = QPushButton('Sync Images Now')
            sync_images_btn.clicked.connect(lambda: [self.sync_images_folder(), QMessageBox.information(self, 'Sync Complete', 'Images folder synced to backup location.')])
            layout.addWidget(sync_images_btn)
        
        dialog.exec()
    
    def sync_images_folder(self):
        """Sync images folder to backup location."""
        if not self.backup_enabled:
            return
        
        backup_folder = self.config.get('backup_folder', '')
        if not backup_folder or not os.path.exists(backup_folder):
            return
        
        import shutil
        images_source = 'images'
        images_dest = os.path.join(backup_folder, 'images')
        
        try:
            if os.path.exists(images_source):
                # Create destination directories if they don't exist
                for subfolder in ['liquors', 'flags', 'cocktails']:
                    dest_subfolder = os.path.join(images_dest, subfolder)
                    source_subfolder = os.path.join(images_source, subfolder)
                    os.makedirs(dest_subfolder, exist_ok=True)
                    
                    # Copy individual files to handle locked files
                    if os.path.exists(source_subfolder):
                        for filename in os.listdir(source_subfolder):
                            source_file = os.path.join(source_subfolder, filename)
                            dest_file = os.path.join(dest_subfolder, filename)
                            try:
                                if os.path.isfile(source_file):
                                    shutil.copy2(source_file, dest_file)
                            except Exception as e:
                                print(f"Skipping {filename}: {e}")
                
                print(f"Images synced to: {images_dest}")
        except Exception as e:
            print(f"Error syncing images: {e}")
    
    def show_custom_theme_dialog(self):
        """Show dialog to pick custom theme colors."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QLineEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Custom Theme")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Background color picker
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel("Background:"))
        self.bg_color_edit = QLineEdit("#f5f5f5")
        self.bg_color_edit.setReadOnly(True)
        bg_color_button = QPushButton("Choose Color")
        bg_color_button.clicked.connect(lambda: self.pick_color(self.bg_color_edit))
        bg_layout.addWidget(self.bg_color_edit)
        bg_layout.addWidget(bg_color_button)
        layout.addLayout(bg_layout)
        
        # Text color picker
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("Text:"))
        self.text_color_edit = QLineEdit("#333333")
        self.text_color_edit.setReadOnly(True)
        text_color_button = QPushButton("Choose Color")
        text_color_button.clicked.connect(lambda: self.pick_color(self.text_color_edit))
        text_layout.addWidget(self.text_color_edit)
        text_layout.addWidget(text_color_button)
        layout.addLayout(text_layout)
        
        # Button color picker
        button_layout = QHBoxLayout()
        button_layout.addWidget(QLabel("Button:"))
        self.button_color_edit = QLineEdit("#0078d4")
        self.button_color_edit.setReadOnly(True)
        button_color_button = QPushButton("Choose Color")
        button_color_button.clicked.connect(lambda: self.pick_color(self.button_color_edit))
        button_layout.addWidget(self.button_color_edit)
        button_layout.addWidget(button_color_button)
        layout.addLayout(button_layout)
        
        # Apply button
        apply_button = QPushButton("Apply Custom Theme")
        apply_button.clicked.connect(lambda: self.apply_custom_theme(dialog))
        layout.addWidget(apply_button)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def pick_color(self, color_edit):
        """Open color picker dialog."""
        color = QColorDialog.getColor()
        if color.isValid():
            color_edit.setText(color.name())
    
    def apply_custom_theme(self, dialog):
        """Apply custom theme colors."""
        bg_color = self.bg_color_edit.text()
        text_color = self.text_color_edit.text()
        button_color = self.button_color_edit.text()
        
        custom_stylesheet = f"""
        QMainWindow {{
            background-color: {bg_color};
        }}
        QWidget {{
            background-color: {bg_color};
            color: {text_color};
        }}
        QPushButton {{
            background-color: {button_color};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {button_color};
            opacity: 0.8;
        }}
        QTableWidget {{
            background-color: white;
            color: {text_color};
            border: 1px solid #ccc;
            gridline-color: #eee;
        }}
        QTableWidget::item {{
            padding: 5px;
        }}
        QTableWidget::item:selected {{
            background-color: {button_color};
            color: white;
        }}
        QLabel {{
            color: {text_color};
        }}
        QLineEdit, QComboBox {{
            background-color: white;
            color: {text_color};
            border: 1px solid #ccc;
            padding: 5px;
        }}
        """
        
        self.setStyleSheet(custom_stylesheet)
        self.alcohol_tab.setStyleSheet(custom_stylesheet)
        self.cocktail_tab.setStyleSheet(custom_stylesheet)
        self.dashboard_tab.update_theme(self.dark_mode)
        
        dialog.accept()
    
    def closeEvent(self, event):
        """Handle window close event - close database connection."""
        self.db.close()
        event.accept()
    
    def toggle_theme(self):
        """Toggle between dark and light themes."""
        self.dark_mode = not self.dark_mode
        self.theme_button.setText("☀️ Light Mode" if self.dark_mode else "🌙 Dark Mode")
        self.apply_theme()
    
    def apply_theme(self):
        """Apply the current theme to the application."""
        if self.dark_mode:
            stylesheet = self.get_dark_theme()
        else:
            stylesheet = self.get_light_theme()
        
        self.setStyleSheet(stylesheet)
        self.alcohol_tab.setStyleSheet(stylesheet)
        self.cocktail_tab.setStyleSheet(stylesheet)
        self.dashboard_tab.update_theme(self.dark_mode)
    
    def get_light_theme(self):
        """Get the light theme stylesheet."""
        return """
        QMainWindow {
            background-color: #f5f5f5;
        }
        QWidget {
            background-color: #f5f5f5;
            color: #333333;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 11pt;
        }
        QPushButton {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6fa8dc, stop:1 #4a90d9);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5a9cd0, stop:1 #3a80c9);
        }
        QPushButton:pressed {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4a90d9, stop:1 #2a70b9);
        }
        QTableWidget {
            background-color: white;
            alternate-background-color: #f8f8f8;
            border: 1px solid #d0d0d0;
            border-radius: 8px;
            gridline-color: #e0e0e0;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QTableWidget::item:hover {
            background-color: #e8f4ff;
        }
        QTableWidget::item:selected {
            background-color: #6fa8dc;
            color: white;
        }
        QHeaderView::section {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e8e8e8, stop:1 #d0d0d0);
            color: #333333;
            padding: 5px;
            border: none;
            border-bottom: 1px solid #c0c0c0;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-weight: bold;
        }
        QLineEdit {
            background-color: white;
            border: 1px solid #c0c0c0;
            border-radius: 6px;
            padding: 5px;
        }
        QLineEdit:focus {
            border: 2px solid #6fa8dc;
        }
        QTextEdit {
            background-color: white;
            border: 1px solid #c0c0c0;
            border-radius: 6px;
            padding: 5px;
        }
        QComboBox {
            background-color: white;
            border: 1px solid #c0c0c0;
            border-radius: 6px;
            padding: 5px;
        }
        QTabWidget::pane {
            border: 1px solid #d0d0d0;
            border-radius: 8px;
            background-color: white;
        }
        QTabBar::tab {
            background-color: #e8e8e8;
            color: #333333;
            padding: 8px 16px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: white;
            color: #6fa8dc;
            font-weight: bold;
        }
        QTabBar::tab:hover {
            background-color: #f0f0f0;
        }
        QDialog {
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f8f9fa, stop:1 #e9ecef);
        }
        QLabel {
            color: #333333;
        }
        """
    
    def get_dark_theme(self):
        """Get the dark theme stylesheet."""
        return """
        QMainWindow {
            background-color: #1e1e1e;
        }
        QWidget {
            background-color: #1e1e1e;
            color: #e0e0e0;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 11pt;
        }
        QPushButton {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4a90d9, stop:1 #2a70b9);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5aa0e9, stop:1 #3a80c9);
        }
        QPushButton:pressed {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3a80c9, stop:1 #1a60a9);
        }
        QTableWidget {
            background-color: #2d2d2d;
            alternate-background-color: #383838;
            border: 1px solid #404040;
            border-radius: 8px;
            gridline-color: #404040;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QTableWidget::item:hover {
            background-color: #3d4d5d;
        }
        QTableWidget::item:selected {
            background-color: #4a90d9;
            color: white;
        }
        QHeaderView::section {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #383838, stop:1 #282828);
            color: #e0e0e0;
            padding: 5px;
            border: none;
            border-bottom: 1px solid #404040;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-weight: bold;
        }
        QLineEdit {
            background-color: #2d2d2d;
            border: 1px solid #505050;
            border-radius: 6px;
            padding: 5px;
            color: #e0e0e0;
        }
        QLineEdit:focus {
            border: 2px solid #4a90d9;
        }
        QTextEdit {
            background-color: #2d2d2d;
            border: 1px solid #505050;
            border-radius: 6px;
            padding: 5px;
            color: #e0e0e0;
        }
        QComboBox {
            background-color: #2d2d2d;
            border: 1px solid #505050;
            border-radius: 6px;
            padding: 5px;
            color: #e0e0e0;
        }
        QTabWidget::pane {
            border: 1px solid #404040;
            border-radius: 8px;
            background-color: #2d2d2d;
        }
        QTabBar::tab {
            background-color: #383838;
            color: #e0e0e0;
            padding: 8px 16px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #2d2d2d;
            color: #4a90d9;
            font-weight: bold;
        }
        QTabBar::tab:hover {
            background-color: #404040;
        }
        QDialog {
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #252525, stop:1 #1e1e1e);
        }
        QLabel {
            color: #e0e0e0;
        }
        """


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    
    window = CocktailDatabaseApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
