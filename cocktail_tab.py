from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QLineEdit, 
                             QFormLayout, QDialog, QComboBox, QMessageBox, QTextEdit, 
                             QShortcut, QMenu, QCompleter, QSplitter, QScrollArea)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QDoubleValidator, QIntValidator, QKeySequence
from datetime import datetime
from database import DatabaseManager
import os


class StarRatingWidget(QWidget):
    """Clickable star rating widget."""
    
    def __init__(self, parent=None, rating=0.0, max_rating=10.0):
        super().__init__(parent)
        self.rating = rating
        self.max_rating = max_rating
        self.stars_per_rating = max_rating / 10  # 5 stars for 10 rating
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setSpacing(2)
        
        self.star_labels = []
        for i in range(5):
            label = QLabel("☆")
            label.setStyleSheet("font-size: 24px; cursor: pointer;")
            label.mousePressEvent = lambda event, idx=i: self.on_star_click(idx)
            layout.addWidget(label)
            self.star_labels.append(label)
        
        layout.addStretch()
        self.setLayout(layout)
        self.update_display()
    
    def update_display(self):
        """Update the star display based on current rating."""
        filled_stars = int((self.rating / self.max_rating) * 5)
        for i, label in enumerate(self.star_labels):
            if i < filled_stars:
                label.setText("★")
            else:
                label.setText("☆")
    
    def on_star_click(self, star_index):
        """Handle star click to set rating."""
        new_rating = ((star_index + 1) / 5) * self.max_rating
        self.rating = round(new_rating, 1)
        self.update_display()
    
    def get_rating(self):
        """Get the current rating."""
        return self.rating
    
    def set_rating(self, rating):
        """Set the rating."""
        self.rating = rating
        self.update_display()


class CocktailDialog(QDialog):
    """Dialog for adding/editing cocktail records."""
    
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.data = data or {}
        self.setWindowTitle("Add Cocktail" if not data else "Edit Cocktail")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.init_ui()
        # Trigger validation for existing data
        self.validate_prep_time_input(self.prep_time_edit.text())
        # Add fade-in animation
        self.fade_in()
    
    def fade_in(self):
        """Add fade-in animation to the dialog."""
        self.setWindowOpacity(0.0)
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(200)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()
    
    def fade_out_and_close(self):
        """Fade out animation before closing."""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(150)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.finished.connect(self.accept)
        self.animation.start()
    
    def init_ui(self):
        layout = QFormLayout()
        
        # Cocktail_Name (required)
        self.name_edit = QLineEdit(self.data.get('Cocktail_Name', ''))
        layout.addRow("Cocktail Name*:", self.name_edit)
        
        # Ingredients (required)
        self.ingredients_edit = QTextEdit()
        self.ingredients_edit.setPlainText(self.data.get('Ingredients', ''))
        self.ingredients_edit.setMaximumHeight(100)
        layout.addRow("Ingredients*:", self.ingredients_edit)
        
        # Ratings
        ratings_layout = QVBoxLayout()
        
        jason_layout = QHBoxLayout()
        jason_layout.addWidget(QLabel("Jason:"))
        self.rating_jason_widget = StarRatingWidget(self, float(self.data.get('Rating_Jason', 0)), 10.0)
        jason_layout.addWidget(self.rating_jason_widget)
        jason_layout.addWidget(QLabel(f"({self.data.get('Rating_Jason', '0')})"))
        ratings_layout.addLayout(jason_layout)
        
        jaime_layout = QHBoxLayout()
        jaime_layout.addWidget(QLabel("Jaime:"))
        self.rating_jaime_widget = StarRatingWidget(self, float(self.data.get('Rating_Jaime', 0)), 10.0)
        jaime_layout.addWidget(self.rating_jaime_widget)
        jaime_layout.addWidget(QLabel(f"({self.data.get('Rating_Jaime', '0')})"))
        ratings_layout.addLayout(jaime_layout)
        
        overall_layout = QHBoxLayout()
        overall_layout.addWidget(QLabel("Overall:"))
        self.rating_overall_widget = StarRatingWidget(self, float(self.data.get('Rating_overall', 0)), 10.0)
        overall_layout.addWidget(self.rating_overall_widget)
        overall_layout.addWidget(QLabel(f"({self.data.get('Rating_overall', '0')})"))
        ratings_layout.addLayout(overall_layout)
        
        layout.addRow("Ratings:", ratings_layout)
        
        # Base Spirit 1
        base1_layout = QHBoxLayout()
        self.base_spirit1_combo = QComboBox()
        self.base_spirit1_combo.setEditable(True)
        self.base_spirit1_combo.addItems(['Gin', 'Rum', 'Whisky', 'Vodka', 'Tequila', 
                                           'Mezcal', 'Liqueur', 'Brandy', 'Amaretto'])
        self.base_spirit1_combo.setCurrentText(self.data.get('Base_spirit_1', ''))
        
        # Add auto-complete
        spirits = ['Gin', 'Rum', 'Whisky', 'Vodka', 'Tequila', 'Mezcal', 'Liqueur', 'Brandy', 'Amaretto']
        completer1 = QCompleter(spirits)
        completer1.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.base_spirit1_combo.setCompleter(completer1)
        
        self.type1_edit = QLineEdit(self.data.get('Type1', ''))
        self.brand1_edit = QLineEdit(self.data.get('Brand1', ''))
        base1_layout.addWidget(QLabel("Base:"))
        base1_layout.addWidget(self.base_spirit1_combo)
        base1_layout.addWidget(QLabel("Type:"))
        base1_layout.addWidget(self.type1_edit)
        base1_layout.addWidget(QLabel("Brand:"))
        base1_layout.addWidget(self.brand1_edit)
        layout.addRow("Base Spirit 1:", base1_layout)
        
        # Base Spirit 2 (optional)
        base2_layout = QHBoxLayout()
        self.base_spirit2_combo = QComboBox()
        self.base_spirit2_combo.setEditable(True)
        self.base_spirit2_combo.addItems(['', 'Gin', 'Rum', 'Whisky', 'Vodka', 'Tequila', 
                                           'Mezcal', 'Liqueur', 'Brandy', 'Amaretto'])
        self.base_spirit2_combo.setCurrentText(self.data.get('Base_spirit_2', ''))
        
        # Add auto-complete
        completer2 = QCompleter(['', 'Gin', 'Rum', 'Whisky', 'Vodka', 'Tequila', 
                                 'Mezcal', 'Liqueur', 'Brandy', 'Amaretto'])
        completer2.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.base_spirit2_combo.setCompleter(completer2)
        
        self.type2_edit = QLineEdit(self.data.get('Type2', ''))
        self.brand2_edit = QLineEdit(self.data.get('Brand2', ''))
        base2_layout.addWidget(QLabel("Base:"))
        base2_layout.addWidget(self.base_spirit2_combo)
        base2_layout.addWidget(QLabel("Type:"))
        base2_layout.addWidget(self.type2_edit)
        base2_layout.addWidget(QLabel("Brand:"))
        base2_layout.addWidget(self.brand2_edit)
        layout.addRow("Base Spirit 2:", base2_layout)
        
        # Citrus
        self.citrus_edit = QLineEdit(self.data.get('Citrus', ''))
        layout.addRow("Citrus:", self.citrus_edit)
        
        # Garnish
        self.garnish_edit = QLineEdit(self.data.get('Garnish', ''))
        layout.addRow("Garnish:", self.garnish_edit)
        
        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlainText(self.data.get('Notes', ''))
        self.notes_edit.setMaximumHeight(80)
        layout.addRow("Notes:", self.notes_edit)
        
        # Prep Time and Difficulty
        meta_layout = QHBoxLayout()
        self.prep_time_edit = QLineEdit(self.data.get('Prep_Time', ''))
        self.prep_time_edit.setValidator(QIntValidator(0, 999))
        self.prep_time_edit.textChanged.connect(self.validate_prep_time_input)
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(['', '1', '2', '3', '4', '5'])
        self.difficulty_combo.setCurrentText(self.data.get('Difficulty', ''))
        meta_layout.addWidget(QLabel("Prep Time (min):"))
        meta_layout.addWidget(self.prep_time_edit)
        meta_layout.addWidget(QLabel("Difficulty (1-5):"))
        meta_layout.addWidget(self.difficulty_combo)
        layout.addRow("Meta:", meta_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.validate_and_save)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addRow(button_layout)
        self.setLayout(layout)
    
    def validate_prep_time_input(self, text):
        """Validate prep time input in real-time."""
        if text and not text.isdigit():
            self.prep_time_edit.setStyleSheet("background-color: #ffcccc;")
        else:
            self.prep_time_edit.setStyleSheet("")
    
    def validate_and_save(self):
        """Validate input and save."""
        name = self.name_edit.text().strip()
        ingredients = self.ingredients_edit.toPlainText().strip()
        
        # Required fields validation
        if not name:
            QMessageBox.warning(self, "Validation Error", "Cocktail Name is required")
            return
        if not ingredients:
            QMessageBox.warning(self, "Validation Error", "Ingredients are required")
            return
        
        # Numeric validation for prep time
        prep_time = self.prep_time_edit.text().strip()
        if prep_time and not prep_time.isdigit():
            QMessageBox.warning(self, "Validation Error", "Prep Time must be numeric")
            return
        
        # Build data dictionary
        self.result_data = {
            'Cocktail_Name': name,
            'Ingredients': ingredients,
            'Rating_Jason': str(self.rating_jason_widget.get_rating()),
            'Rating_Jaime': str(self.rating_jaime_widget.get_rating()),
            'Rating_overall': str(self.rating_overall_widget.get_rating()),
            'Base_spirit_1': self.base_spirit1_combo.currentText().strip(),
            'Type1': self.type1_edit.text().strip(),
            'Brand1': self.brand1_edit.text().strip(),
            'Base_spirit_2': self.base_spirit2_combo.currentText().strip(),
            'Type2': self.type2_edit.text().strip(),
            'Brand2': self.brand2_edit.text().strip(),
            'Citrus': self.citrus_edit.text().strip(),
            'Garnish': self.garnish_edit.text().strip(),
            'Notes': self.notes_edit.toPlainText().strip(),
            'DatetimeAdded': self.data.get('DatetimeAdded', datetime.now().strftime('%d/%m/%Y %H:%M')),
            'Prep_Time': prep_time,
            'Difficulty': self.difficulty_combo.currentText()
        }
        
        self.accept()


class CocktailInfoDialog(QDialog):
    """Dialog for displaying cocktail information (read-only)."""
    
    def __init__(self, parent=None, data=None, parent_tab=None):
        super().__init__(parent)
        self.data = data or {}
        self.parent_tab = parent_tab
        self.setWindowTitle("Cocktail Information")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.init_ui()
        self.fade_in()
    
    def fade_in(self):
        """Add fade-in animation to the dialog."""
        self.setWindowOpacity(0.0)
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(200)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()
    
    def fade_out_and_close(self):
        """Fade out animation before closing."""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(150)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.finished.connect(self.accept)
        self.animation.start()
    
    def init_ui(self):
        layout = QFormLayout()
        
        # Cocktail Name
        name_label = QLabel(self.data.get('Cocktail_Name', ''))
        layout.addRow("Cocktail Name:", name_label)
        
        # Ingredients
        ingredients_label = QLabel(self.data.get('Ingredients', ''))
        ingredients_label.setWordWrap(True)
        layout.addRow("Ingredients:", ingredients_label)
        
        # Ratings
        ratings_layout = QHBoxLayout()
        ratings_layout.addWidget(QLabel(f"Jason: {self.data.get('Rating_Jason', '')}"))
        ratings_layout.addWidget(QLabel(f"Jaime: {self.data.get('Rating_Jaime', '')}"))
        ratings_layout.addWidget(QLabel(f"Overall: {self.data.get('Rating_overall', '')}"))
        layout.addRow("Ratings:", ratings_layout)
        
        # Base Spirit 1
        base1_label = QLabel(f"{self.data.get('Base_spirit_1', '')} - {self.data.get('Type1', '')} - {self.data.get('Brand1', '')}")
        layout.addRow("Base Spirit 1:", base1_label)
        
        # Base Spirit 2
        base2_label = QLabel(f"{self.data.get('Base_spirit_2', '')} - {self.data.get('Type2', '')} - {self.data.get('Brand2', '')}")
        layout.addRow("Base Spirit 2:", base2_label)
        
        # Citrus
        citrus_label = QLabel(self.data.get('Citrus', ''))
        layout.addRow("Citrus:", citrus_label)
        
        # Garnish
        garnish_label = QLabel(self.data.get('Garnish', ''))
        layout.addRow("Garnish:", garnish_label)
        
        # Notes
        notes_label = QLabel(self.data.get('Notes', ''))
        notes_label.setWordWrap(True)
        layout.addRow("Notes:", notes_label)
        
        # Prep Time and Difficulty
        meta_label = QLabel(f"Prep Time: {self.data.get('Prep_Time', '')} min | Difficulty: {self.data.get('Difficulty', '')}/5")
        layout.addRow("Meta:", meta_label)
        
        # Date Added
        date_label = QLabel(self.data.get('DatetimeAdded', ''))
        layout.addRow("Date Added:", date_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete")
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        if self.parent_tab:
            self.edit_button.clicked.connect(lambda: self.edit_item())
            self.delete_button.clicked.connect(lambda: self.delete_item())
        else:
            self.edit_button.setEnabled(False)
            self.delete_button.setEnabled(False)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.close_button)
        layout.addRow(button_layout)
        
        self.setLayout(layout)
    
    def edit_item(self):
        """Edit the current item."""
        self.accept()
        # Find the row in the parent table
        name = self.data.get('Cocktail_Name', '')
        for row in range(self.parent_tab.table.rowCount()):
            if self.parent_tab.table.item(row, 0).text() == name:
                self.parent_tab.table.selectRow(row)
                self.parent_tab.edit_cocktail()
                break
    
    def delete_item(self):
        """Delete the current item."""
        self.accept()
        # Find the row in the parent table
        name = self.data.get('Cocktail_Name', '')
        for row in range(self.parent_tab.table.rowCount()):
            if self.parent_tab.table.item(row, 0).text() == name:
                self.parent_tab.table.selectRow(row)
                self.parent_tab.delete_cocktail()
                break


class CocktailTab(QWidget):
    """Tab for managing cocktail recipes."""
    
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.action_logs = []
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name, base spirit, or brand...")
        self.search_edit.textChanged.connect(self.filter_data)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        
        # Buttons
        self.add_button = QPushButton("Add Cocktail")
        self.add_button.clicked.connect(self.add_cocktail)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_data)
        self.split_view_button = QPushButton("Split View")
        self.split_view_button.setCheckable(True)
        self.split_view_button.clicked.connect(self.toggle_split_view)
        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self.export_data)
        self.favorites_button = QPushButton("⭐ Favorites")
        self.favorites_button.setCheckable(True)
        self.favorites_button.clicked.connect(self.toggle_favorites_filter)
        self.favorites = set()
        self.load_favorites()
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.split_view_button)
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.favorites_button)
        button_layout.addStretch()
        
        # Filter chips
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Quick Filters:"))
        self.all_filter = QPushButton("All")
        self.all_filter.setCheckable(True)
        self.all_filter.setChecked(True)
        self.all_filter.clicked.connect(lambda: self.apply_filter('all'))
        filter_layout.addWidget(self.all_filter)
        
        self.high_rating_filter = QPushButton("High Rating (8+)")
        self.high_rating_filter.setCheckable(True)
        self.high_rating_filter.clicked.connect(lambda: self.apply_filter('high_rating'))
        filter_layout.addWidget(self.high_rating_filter)
        
        self.medium_rating_filter = QPushButton("Medium Rating (6-7)")
        self.medium_rating_filter.setCheckable(True)
        self.medium_rating_filter.clicked.connect(lambda: self.apply_filter('medium_rating'))
        filter_layout.addWidget(self.medium_rating_filter)
        
        self.low_rating_filter = QPushButton("Low Rating (<6)")
        self.low_rating_filter.setCheckable(True)
        self.low_rating_filter.clicked.connect(lambda: self.apply_filter('low_rating'))
        filter_layout.addWidget(self.low_rating_filter)
        
        filter_layout.addStretch()
        
        # Create splitter for split view
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'Name', 'Base Spirit', 'Brand', 'Rating', 'Difficulty', 'Prep Time'
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.show_cocktail_info)
        self.table.setSortingEnabled(True)
        self.table.itemSelectionChanged.connect(self.update_status_bar)
        self.table.itemSelectionChanged.connect(self.update_details_panel)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Add table to splitter
        self.splitter.addWidget(self.table)
        
        # Details panel (initially hidden)
        self.details_panel = QScrollArea()
        self.details_panel.setWidgetResizable(True)
        self.details_panel.setMaximumWidth(400)
        self.details_panel.setHidden(True)
        self.details_label = QLabel("Select an item to view details")
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet("padding: 10px;")
        self.details_panel.setWidget(self.details_label)
        self.splitter.addWidget(self.details_panel)
        
        # Set initial splitter sizes (table takes all space initially)
        self.splitter.setSizes([1000, 0])
        
        # Keyboard shortcuts
        self.shortcut_new = QShortcut(QKeySequence("Ctrl+N"), self)
        self.shortcut_new.activated.connect(self.add_cocktail)
        self.shortcut_edit = QShortcut(QKeySequence("Ctrl+E"), self)
        self.shortcut_edit.activated.connect(self.edit_cocktail)
        self.shortcut_delete = QShortcut(QKeySequence("Delete"), self)
        self.shortcut_delete.activated.connect(self.delete_cocktail)
        self.shortcut_refresh = QShortcut(QKeySequence("F5"), self)
        self.shortcut_refresh.activated.connect(self.load_data)
        
        layout.addLayout(search_layout)
        layout.addLayout(button_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self.splitter, stretch=1)  # Give table more space
        
        # Log display with scroll area
        log_label = QLabel("Recent Actions:")
        self.log_display = QLabel()
        self.log_display.setStyleSheet("background-color: #f0f0f0; border: 1px solid gray; padding: 5px;")
        self.log_display.setWordWrap(True)
        self.update_log_display()
        
        self.log_scroll = QScrollArea()
        self.log_scroll.setWidget(self.log_display)
        self.log_scroll.setWidgetResizable(True)
        self.log_scroll.setMaximumHeight(100)
        
        layout.addWidget(log_label)
        layout.addWidget(self.log_scroll)
        self.setLayout(layout)
    
    def load_data(self):
        """Load data from database into table."""
        data = self.db.get_all_cocktails()
        self.current_data = data  # Store current data for filtering
        self.populate_table(data)
        self.update_status_bar()
    
    def update_status_bar(self):
        """Update status bar with current table information."""
        try:
            total_items = self.table.rowCount()
            selected_items = len(self.table.selectedItems()) > 0
            selection_text = "1 selected" if selected_items else "No selection"
            
            # Update parent window status bar if available
            parent = self.parent()
            while parent and not isinstance(parent, QMainWindow):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'status_bar'):
                parent.status_bar.showMessage(f"Cocktail Recipes - Total: {total_items} | {selection_text}")
        except Exception as e:
            # Silently fail if status bar update fails
            pass
    
    def toggle_split_view(self):
        """Toggle between normal and split view."""
        if self.split_view_button.isChecked():
            self.details_panel.setHidden(False)
            self.splitter.setSizes([600, 400])
        else:
            self.details_panel.setHidden(True)
            self.splitter.setSizes([1000, 0])
    
    def export_data(self):
        """Export current table data to CSV."""
        import csv
        from PyQt5.QtWidgets import QFileDialog
        
        # Get current data from table
        data = []
        for row in range(self.table.rowCount()):
            row_data = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_data.append(item.text() if item else '')
            data.append(row_data)
        
        # Get headers
        headers = []
        for col in range(self.table.columnCount()):
            headers.append(self.table.horizontalHeaderItem(col).text())
        
        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Cocktail Data", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(data)
                QMessageBox.information(self, "Success", "Data exported successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")
    
    def load_favorites(self):
        """Load favorites from JSON file."""
        import json
        favorites_file = "cocktail_favorites.json"
        if os.path.exists(favorites_file):
            try:
                with open(favorites_file, 'r') as f:
                    self.favorites = set(json.load(f))
            except Exception:
                self.favorites = set()
    
    def save_favorites(self):
        """Save favorites to JSON file."""
        import json
        favorites_file = "cocktail_favorites.json"
        try:
            with open(favorites_file, 'w') as f:
                json.dump(list(self.favorites), f)
        except Exception as e:
            print(f"Failed to save favorites: {e}")
    
    def toggle_favorites_filter(self):
        """Toggle favorites filter."""
        if self.favorites_button.isChecked():
            # Show only favorites
            filtered_data = [item for item in self.current_data if item.get('Cocktail_Name', '') in self.favorites]
            self.populate_table(filtered_data)
        else:
            # Show all
            self.populate_table(self.current_data)
    
    def toggle_favorite(self, cocktail_name):
        """Toggle favorite status for an item."""
        if cocktail_name in self.favorites:
            self.favorites.remove(cocktail_name)
        else:
            self.favorites.add(cocktail_name)
        self.save_favorites()
    
    def update_details_panel(self):
        """Update details panel with selected item information."""
        if not self.split_view_button.isChecked():
            return
        
        selected_row = self.table.currentRow()
        if selected_row < 0:
            self.details_label.setText("Select an item to view details")
            return
        
        # Get item data from current_data based on the selected row
        try:
            # Find the corresponding item in current_data
            name = self.table.item(selected_row, 0).text()
            item = next((d for d in self.current_data if d.get('Cocktail_Name', '') == name), None)
            
            if item:
                details_text = f"<b>Cocktail Name:</b> {item.get('Cocktail_Name', '')}<br><br>"
                details_text += f"<b>Ingredients:</b><br>{item.get('Ingredients', '')}<br><br>"
                details_text += f"<b>Ratings:</b><br>"
                details_text += f"  - Jason: {item.get('Rating_Jason', '')}<br>"
                details_text += f"  - Jaime: {item.get('Rating_Jaime', '')}<br>"
                details_text += f"  - Overall: {item.get('Rating_overall', '')}<br><br>"
                details_text += f"<b>Base Spirit 1:</b> {item.get('Base_spirit_1', '')} - {item.get('Type1', '')} - {item.get('Brand1', '')}<br>"
                if item.get('Base_spirit_2', ''):
                    details_text += f"<b>Base Spirit 2:</b> {item.get('Base_spirit_2', '')} - {item.get('Type2', '')} - {item.get('Brand2', '')}<br>"
                details_text += f"<b>Citrus:</b> {item.get('Citrus', '')}<br>"
                details_text += f"<b>Garnish:</b> {item.get('Garnish', '')}<br>"
                details_text += f"<b>Notes:</b><br>{item.get('Notes', '')}<br><br>"
                details_text += f"<b>Prep Time:</b> {item.get('Prep_Time', '')} min<br>"
                details_text += f"<b>Difficulty:</b> {item.get('Difficulty', '')}/5"
                
                self.details_label.setText(details_text)
            else:
                self.details_label.setText("Error loading details")
        except Exception as e:
            self.details_label.setText("Error loading details")
    
    def apply_filter(self, filter_type):
        """Apply filter to the table data."""
        # Update button states
        self.all_filter.setChecked(filter_type == 'all')
        self.high_rating_filter.setChecked(filter_type == 'high_rating')
        self.medium_rating_filter.setChecked(filter_type == 'medium_rating')
        self.low_rating_filter.setChecked(filter_type == 'low_rating')
        
        # Filter data
        if filter_type == 'all':
            filtered_data = self.current_data
        else:
            filtered_data = []
            for item in self.current_data:
                try:
                    rating = float(item.get('Rating_overall', 0))
                    if filter_type == 'high_rating' and rating >= 8.0:
                        filtered_data.append(item)
                    elif filter_type == 'medium_rating' and 6.0 <= rating < 8.0:
                        filtered_data.append(item)
                    elif filter_type == 'low_rating' and rating < 6.0:
                        filtered_data.append(item)
                except ValueError:
                    pass
        
        self.populate_table(filtered_data)
    
    def show_context_menu(self, position):
        """Show context menu at the clicked position."""
        item = self.table.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        info_action = menu.addAction("View Info")
        menu.addSeparator()
        favorite_action = menu.addAction("⭐ Toggle Favorite")
        menu.addSeparator()
        refresh_action = menu.addAction("Refresh")
        
        action = menu.exec(self.table.viewport().mapToGlobal(position))
        
        if action == edit_action:
            self.edit_cocktail()
        elif action == delete_action:
            self.delete_cocktail()
        elif action == info_action:
            self.show_cocktail_info(item.row(), item.column())
        elif action == favorite_action:
            cocktail_name = self.table.item(item.row(), 0).text()
            self.toggle_favorite(cocktail_name)
        elif action == refresh_action:
            self.load_data()
    
    def populate_table(self, data):
        """Populate table with data."""
        self.table.setRowCount(len(data))
        
        search_text = self.search_edit.text().lower()
        
        for row, item in enumerate(data):
            name_item = QTableWidgetItem(item.get('Cocktail_Name', ''))
            spirit_item = QTableWidgetItem(item.get('Base_spirit_1', ''))
            brand_item = QTableWidgetItem(item.get('Brand1', ''))
            
            # Highlight matching cells if search is active
            if search_text:
                for table_item in [name_item, spirit_item, brand_item]:
                    if search_text in table_item.text().lower():
                        table_item.setBackground(Qt.GlobalColor.cyan)
                        table_item.setForeground(Qt.GlobalColor.black)
            
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, spirit_item)
            self.table.setItem(row, 2, brand_item)
            
            # Color-coded rating badge
            rating_item = QTableWidgetItem(item.get('Rating_overall', ''))
            try:
                rating = float(item.get('Rating_overall', 0))
                if rating >= 8.0:
                    rating_item.setBackground(Qt.GlobalColor.darkGreen)
                    rating_item.setForeground(Qt.GlobalColor.white)
                elif rating >= 6.0:
                    rating_item.setBackground(Qt.GlobalColor.yellow)
                    rating_item.setForeground(Qt.GlobalColor.black)
                elif rating >= 4.0:
                    rating_item.setBackground(Qt.GlobalColor.darkYellow)
                    rating_item.setForeground(Qt.GlobalColor.white)
                else:
                    rating_item.setBackground(Qt.GlobalColor.red)
                    rating_item.setForeground(Qt.GlobalColor.white)
            except ValueError:
                pass
            self.table.setItem(row, 3, rating_item)
            
            self.table.setItem(row, 4, QTableWidgetItem(item.get('Difficulty', '')))
            self.table.setItem(row, 5, QTableWidgetItem(item.get('Prep_Time', '')))
        
        self.table.resizeColumnsToContents()
    
    def add_log(self, action):
        """Add an action to the log with timestamp."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.action_logs.append(f"{timestamp} - {action}")
        # Keep only last 3 actions
        if len(self.action_logs) > 3:
            self.action_logs = self.action_logs[-3:]
        self.update_log_display()
    
    def update_log_display(self):
        """Update the log display with recent actions."""
        if self.action_logs:
            self.log_display.setText("\n".join(self.action_logs))
        else:
            self.log_display.setText("No recent actions")
    
    def filter_data(self):
        """Filter table data based on search text."""
        search_text = self.search_edit.text().lower()
        data = self.db.get_all_cocktails()
        
        filtered_data = []
        for item in data:
            # Search in key fields
            searchable_fields = [
                item.get('Cocktail_Name', ''),
                item.get('Base_spirit_1', ''),
                item.get('Brand1', ''),
                item.get('Base_spirit_2', ''),
                item.get('Brand2', '')
            ]
            if any(search_text in str(value).lower() for value in searchable_fields):
                filtered_data.append(item)
        
        self.populate_table(filtered_data)
    
    def add_cocktail(self):
        """Open dialog to add new cocktail."""
        dialog = CocktailDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.db.add_cocktail(dialog.result_data):
                QMessageBox.information(self, "Success", "Cocktail added successfully")
                self.add_log(f"Added cocktail: {dialog.result_data['Cocktail_Name']}")
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", "Failed to add cocktail")
    
    def edit_cocktail(self):
        """Open dialog to edit selected cocktail."""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a cocktail to edit")
            return
        
        # Get current data from table - need to fetch full data from DB
        name = self.table.item(selected_row, 0).text()
        all_cocktails = self.db.get_all_cocktails()
        data = next((c for c in all_cocktails if c.get('Cocktail_Name') == name), None)
        
        if not data:
            QMessageBox.critical(self, "Error", "Could not find cocktail data")
            return
        
        dialog = CocktailDialog(self, data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.db.update_cocktail(name, dialog.result_data):
                QMessageBox.information(self, "Success", "Cocktail updated successfully")
                self.add_log(f"Edited cocktail: {dialog.result_data['Cocktail_Name']}")
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", "Failed to update cocktail")
    
    def delete_cocktail(self):
        """Delete selected cocktail."""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a cocktail to delete")
            return
        
        name = self.table.item(selected_row, 0).text()
        
        # First confirmation
        reply1 = QMessageBox.question(
            self, 'Confirm Delete',
            f'Are you sure you want to delete "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply1 != QMessageBox.StandardButton.Yes:
            return
        
        # Second confirmation
        reply2 = QMessageBox.question(
            self, 'Confirm Delete',
            f'Are you REALLY sure you want to delete "{name}"? This action cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply2 == QMessageBox.StandardButton.Yes:
            if self.db.delete_cocktail(name):
                QMessageBox.information(self, "Success", "Cocktail deleted successfully")
                self.add_log(f"Deleted cocktail: {name}")
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete cocktail")
    
    def show_cocktail_info(self, row, column):
        """Show cocktail information dialog when row is double-clicked."""
        # Check if row is valid
        if row < 0 or row >= self.table.rowCount():
            return
        
        # Get cocktail name from table with error handling
        try:
            name_item = self.table.item(row, 0)
            if not name_item:
                return
            name = name_item.text()
            
            # Fetch full data from database
            all_cocktails = self.db.get_all_cocktails()
            data = next((c for c in all_cocktails if c.get('Cocktail_Name') == name), None)
            
            if not data:
                QMessageBox.critical(self, "Error", "Could not find cocktail data")
                return
            
            dialog = CocktailInfoDialog(self, data, parent_tab=self)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load cocktail information: {str(e)}")
