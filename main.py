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
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 15px; color: #1a1a1a;")
        main_layout.addWidget(title_label)
        
        # Create scroll areas for each statistics section
        # Alcohol statistics scroll area
        alcohol_scroll = QScrollArea()
        alcohol_scroll.setWidgetResizable(True)
        alcohol_scroll.setMaximumHeight(300)
        self.alcohol_stats_label = QLabel()
        self.alcohol_stats_label.setWordWrap(True)
        self.alcohol_stats_label.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(0, 0, 0, 0.2);
            border-radius: 16px;
            padding: 20px;
            color: #1a1a1a;
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
            background-color: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(0, 0, 0, 0.2);
            border-radius: 16px;
            padding: 20px;
            color: #1a1a1a;
        """)
        cocktail_scroll.setWidget(self.cocktail_stats_label)
        main_layout.addWidget(cocktail_scroll)
        
        main_layout.addStretch()
        self.setLayout(main_layout)
    
    def update_theme(self, dark_mode):
        """Update dashboard theme based on dark mode with glassmorphism."""
        if dark_mode:
            bg_color = "rgba(0, 0, 0, 0.6)"
            border_color = "rgba(255, 255, 255, 0.2)"
            text_color = "#f0f0f0"
        else:
            bg_color = "rgba(255, 255, 255, 0.7)"
            border_color = "rgba(0, 0, 0, 0.2)"
            text_color = "#1a1a1a"
        
        style = f"""
            background-color: {bg_color}; 
            border: 1px solid {border_color}; 
            border-radius: 16px; 
            padding: 20px;
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
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget with tabbed interface
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with title and controls
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Cocktail Database")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Theme toggle button
        self.theme_button = QPushButton("🌙 Dark Mode")
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setFixedHeight(40)
        header_layout.addWidget(self.theme_button)
        
        # Custom theme button
        self.custom_theme_button = QPushButton("🎨 Custom Theme")
        self.custom_theme_button.clicked.connect(self.show_custom_theme_dialog)
        self.custom_theme_button.setFixedHeight(40)
        header_layout.addWidget(self.custom_theme_button)
        
        # Settings button
        self.settings_button = QPushButton("⚙️ Settings")
        self.settings_button.clicked.connect(self.show_settings_menu)
        self.settings_button.setFixedHeight(40)
        header_layout.addWidget(self.settings_button)
        
        layout.addWidget(header_container)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        
        # Tab 1: Dashboard
        self.dashboard_tab = DashboardTab(self.db)
        self.tab_widget.addTab(self.dashboard_tab, "📊 Dashboard")
        
        # Tab 2: Alcohol Inventory
        self.alcohol_tab = AlcoholTab(self.db)
        self.tab_widget.addTab(self.alcohol_tab, "🍷 Alcohol Inventory")
        
        # Tab 3: Cocktail Recipes
        self.cocktail_tab = CocktailTab(self.db)
        self.tab_widget.addTab(self.cocktail_tab, "🍹 Cocktail Recipes")
        
        layout.addWidget(self.tab_widget, stretch=1)
        
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
        """Get the light theme stylesheet with glassmorphism."""
        return """
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f093fb, stop:1 #4facfe);
        }
        QWidget {
            background: transparent;
            color: white;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 11pt;
        }
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(102, 126, 234, 0.6), stop:1 rgba(118, 75, 162, 0.6));
            background-color: rgba(255, 255, 255, 0.4);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.4);
            border-radius: 12px;
            padding: 10px 20px;
            font-weight: bold;
            min-width: 100px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(102, 126, 234, 0.8), stop:1 rgba(118, 75, 162, 0.8));
            background-color: rgba(255, 255, 255, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.6);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(102, 126, 234, 1.0), stop:1 rgba(118, 75, 162, 1.0));
            background-color: rgba(255, 255, 255, 0.6);
        }
        QPushButton:checked {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(102, 126, 234, 0.9), stop:1 rgba(118, 75, 162, 0.9));
            background-color: rgba(255, 255, 255, 0.6);
            border: 2px solid rgba(102, 126, 234, 0.8);
        }
        QTableWidget {
            background-color: rgba(255, 255, 255, 0.6);
            alternate-background-color: rgba(255, 255, 255, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.4);
            border-radius: 16px;
            gridline-color: rgba(0, 0, 0, 0.1);
        }
        QTableWidget::item {
            padding: 8px;
            background-color: rgba(255, 255, 255, 0.6);
            color: #1a1a1a;
            border-radius: 4px;
        }
        QTableWidget::item:hover {
            background-color: rgba(102, 126, 234, 0.3);
            color: #1a1a1a;
        }
        QTableWidget::item:selected {
            background-color: rgba(102, 126, 234, 0.7);
            color: white;
        }
        QHeaderView::section {
            background-color: rgba(255, 255, 255, 0.7);
            color: #1a1a1a;
            padding: 8px;
            border: none;
            border-bottom: 1px solid rgba(0, 0, 0, 0.1);
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
            font-weight: bold;
        }
        QLineEdit {
            background-color: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            padding: 8px;
            color: #1a1a1a;
        }
        QLineEdit:focus {
            border: 2px solid rgba(102, 126, 234, 0.8);
            background-color: rgba(255, 255, 255, 0.85);
        }
        QLineEdit:hover {
            border: 1px solid rgba(102, 126, 234, 0.5);
        }
        QTextEdit {
            background-color: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            padding: 8px;
            color: #1a1a1a;
        }
        QTextEdit:focus {
            border: 2px solid rgba(102, 126, 234, 0.8);
            background-color: rgba(255, 255, 255, 0.85);
        }
        QTextEdit:hover {
            border: 1px solid rgba(102, 126, 234, 0.5);
        }
        QComboBox {
            background-color: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            padding: 8px;
            color: #1a1a1a;
        }
        QComboBox QAbstractItemView {
            background-color: rgba(255, 255, 255, 0.98);
            border: 1px solid rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            selection-background-color: rgba(102, 126, 234, 0.7);
        }
        QTabWidget::pane {
            border: 1px solid rgba(0, 0, 0, 0.2);
            border-radius: 16px;
            background-color: rgba(255, 255, 255, 0.5);
            top: -1px;
        }
        QTabBar::tab {
            background-color: rgba(255, 255, 255, 0.5);
            color: #1a1a1a;
            padding: 12px 24px;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            margin-right: 4px;
            border: 1px solid rgba(0, 0, 0, 0.1);
            border-bottom: none;
            min-width: 120px;
            font-weight: 500;
        }
        QTabBar::tab:selected {
            background-color: rgba(255, 255, 255, 0.8);
            color: #667eea;
            font-weight: bold;
            border: 1px solid rgba(0, 0, 0, 0.2);
            border-bottom: 1px solid rgba(255, 255, 255, 0.8);
        }
        QTabBar::tab:hover {
            background-color: rgba(255, 255, 255, 0.65);
        }
        QDialog {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(240, 147, 251, 0.3), stop:0.5 rgba(245, 87, 108, 0.3), stop:1 rgba(79, 172, 254, 0.3));
            background-color: rgba(255, 255, 255, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.4);
            border-radius: 16px;
            font-size: 9pt;
        }
        QLabel {
            color: white;
        }
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        QScrollBar:vertical {
            border: none;
            background: rgba(255, 255, 255, 0.1);
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f093fb, stop:1 #f5576c);
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f5576c, stop:1 #4facfe);
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
        QScrollBar:horizontal {
            border: none;
            background: rgba(255, 255, 255, 0.1);
            height: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f093fb, stop:1 #f5576c);
            min-width: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f5576c, stop:1 #4facfe);
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            border: none;
            background: none;
        }
        """
    
    def get_dark_theme(self):
        """Get the dark theme stylesheet with glassmorphism."""
        return """
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a1a2e, stop:1 #16213e);
        }
        QWidget {
            background: transparent;
            color: #f0f0f0;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 11pt;
        }
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(102, 126, 234, 0.7), stop:1 rgba(118, 75, 162, 0.7));
            background-color: rgba(0, 0, 0, 0.5);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 12px;
            padding: 10px 20px;
            font-weight: bold;
            min-width: 100px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(102, 126, 234, 0.9), stop:1 rgba(118, 75, 162, 0.9));
            background-color: rgba(0, 0, 0, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.5);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(102, 126, 234, 1.0), stop:1 rgba(118, 75, 162, 1.0));
            background-color: rgba(0, 0, 0, 0.7);
        }
        QPushButton:checked {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(102, 126, 234, 1.0), stop:1 rgba(118, 75, 162, 1.0));
            background-color: rgba(0, 0, 0, 0.7);
            border: 2px solid rgba(102, 126, 234, 0.9);
        }
        QTableWidget {
            background-color: rgba(0, 0, 0, 0.5);
            alternate-background-color: rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 16px;
            gridline-color: rgba(255, 255, 255, 0.1);
        }
        QTableWidget::item {
            padding: 8px;
            background-color: rgba(0, 0, 0, 0.5);
            color: #f0f0f0;
            border-radius: 4px;
        }
        QTableWidget::item:hover {
            background-color: rgba(102, 126, 234, 0.4);
            color: #f0f0f0;
        }
        QTableWidget::item:selected {
            background-color: rgba(102, 126, 234, 0.8);
            color: white;
        }
        QHeaderView::section {
            background-color: rgba(0, 0, 0, 0.6);
            color: #f0f0f0;
            padding: 8px;
            border: none;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
            font-weight: bold;
        }
        QLineEdit {
            background-color: rgba(0, 0, 0, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            padding: 8px;
            color: #f0f0f0;
        }
        QLineEdit:focus {
            border: 2px solid rgba(102, 126, 234, 0.9);
            background-color: rgba(0, 0, 0, 0.75);
        }
        QLineEdit:hover {
            border: 1px solid rgba(102, 126, 234, 0.6);
        }
        QTextEdit {
            background-color: rgba(0, 0, 0, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            padding: 8px;
            color: #f0f0f0;
        }
        QTextEdit:focus {
            border: 2px solid rgba(102, 126, 234, 0.9);
            background-color: rgba(0, 0, 0, 0.75);
        }
        QTextEdit:hover {
            border: 1px solid rgba(102, 126, 234, 0.6);
        }
        QComboBox {
            background-color: rgba(0, 0, 0, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            padding: 8px;
            color: #f0f0f0;
        }
        QComboBox QAbstractItemView {
            background-color: rgba(30, 30, 46, 0.98);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            selection-background-color: rgba(102, 126, 234, 0.8);
        }
        QTabWidget::pane {
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 16px;
            background-color: rgba(0, 0, 0, 0.5);
            top: -1px;
        }
        QTabBar::tab {
            background-color: rgba(0, 0, 0, 0.5);
            color: #f0f0f0;
            padding: 12px 24px;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            margin-right: 4px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-bottom: none;
            min-width: 120px;
            font-weight: 500;
        }
        QTabBar::tab:selected {
            background-color: rgba(0, 0, 0, 0.7);
            color: #667eea;
            font-weight: bold;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-bottom: 1px solid rgba(0, 0, 0, 0.7);
        }
        QTabBar::tab:hover {
            background-color: rgba(0, 0, 0, 0.6);
        }
        QDialog {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(26, 26, 46, 0.4), stop:1 rgba(22, 33, 62, 0.4));
            background-color: rgba(0, 0, 0, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 16px;
        }
        QLabel {
            color: #f0f0f0;
        }
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        QScrollBar:vertical {
            border: none;
            background: rgba(0, 0, 0, 0.3);
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: rgba(102, 126, 234, 0.6);
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background: rgba(102, 126, 234, 0.8);
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
        QScrollBar:horizontal {
            border: none;
            background: rgba(0, 0, 0, 0.3);
            height: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal {
            background: rgba(102, 126, 234, 0.6);
            min-width: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:horizontal:hover {
            background: rgba(102, 126, 234, 0.8);
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            border: none;
            background: none;
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
