from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QLineEdit, 
                             QFormLayout, QDialog, QComboBox, QMessageBox, QTextEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from datetime import datetime
from database import DatabaseManager


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
        self.validate_rating_input(self.rating_jason_edit.text())
        self.validate_rating_input(self.rating_jaime_edit.text())
        self.validate_rating_input(self.rating_overall_edit.text())
        self.validate_prep_time_input(self.prep_time_edit.text())
    
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
        ratings_layout = QHBoxLayout()
        self.rating_jason_edit = QLineEdit(self.data.get('Rating_Jason', ''))
        self.rating_jason_edit.setValidator(QDoubleValidator(0.0, 10.0, 1))
        self.rating_jason_edit.textChanged.connect(self.validate_rating_input)
        self.rating_jaime_edit = QLineEdit(self.data.get('Rating_Jaime', ''))
        self.rating_jaime_edit.setValidator(QDoubleValidator(0.0, 10.0, 1))
        self.rating_jaime_edit.textChanged.connect(self.validate_rating_input)
        self.rating_overall_edit = QLineEdit(self.data.get('Rating_overall', ''))
        self.rating_overall_edit.setValidator(QDoubleValidator(0.0, 10.0, 1))
        self.rating_overall_edit.textChanged.connect(self.validate_rating_input)
        ratings_layout.addWidget(QLabel("Jason:"))
        ratings_layout.addWidget(self.rating_jason_edit)
        ratings_layout.addWidget(QLabel("Jaime:"))
        ratings_layout.addWidget(self.rating_jaime_edit)
        ratings_layout.addWidget(QLabel("Overall:"))
        ratings_layout.addWidget(self.rating_overall_edit)
        layout.addRow("Ratings:", ratings_layout)
        
        # Base Spirit 1
        base1_layout = QHBoxLayout()
        self.base_spirit1_combo = QComboBox()
        self.base_spirit1_combo.setEditable(True)
        self.base_spirit1_combo.addItems(['Gin', 'Rum', 'Whisky', 'Vodka', 'Tequila', 
                                           'Mezcal', 'Liqueur', 'Brandy', 'Amaretto'])
        self.base_spirit1_combo.setCurrentText(self.data.get('Base_spirit_1', ''))
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
    
    def validate_rating_input(self, text):
        """Validate rating input in real-time."""
        if text and not text.replace('.', '').isdigit():
            sender = self.sender()
            sender.setStyleSheet("background-color: #ffcccc;")
        else:
            sender = self.sender()
            sender.setStyleSheet("")
    
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
        
        # Numeric validation for ratings
        for field_name, field_value in [
            ("Jason's Rating", self.rating_jason_edit.text().strip()),
            ("Jaime's Rating", self.rating_jaime_edit.text().strip()),
            ("Overall Rating", self.rating_overall_edit.text().strip())
        ]:
            if field_value and not field_value.replace('.', '').isdigit():
                QMessageBox.warning(self, "Validation Error", f"{field_name} must be numeric")
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
            'Rating_Jason': self.rating_jason_edit.text().strip(),
            'Rating_Jaime': self.rating_jaime_edit.text().strip(),
            'Rating_overall': self.rating_overall_edit.text().strip(),
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
        self.edit_button = QPushButton("Edit Cocktail")
        self.edit_button.clicked.connect(self.edit_cocktail)
        self.delete_button = QPushButton("Delete Cocktail")
        self.delete_button.clicked.connect(self.delete_cocktail)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_data)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        
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
        
        layout.addLayout(search_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.table)
        
        # Log display
        log_label = QLabel("Recent Actions:")
        self.log_display = QLabel()
        self.log_display.setStyleSheet("background-color: #f0f0f0; border: 1px solid gray; padding: 5px;")
        self.log_display.setWordWrap(True)
        self.update_log_display()
        
        layout.addWidget(log_label)
        layout.addWidget(self.log_display)
        self.setLayout(layout)
    
    def load_data(self):
        """Load data from database into table."""
        data = self.db.get_all_cocktails()
        self.populate_table(data)
    
    def populate_table(self, data):
        """Populate table with data."""
        self.table.setRowCount(len(data))
        
        for row, item in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(item.get('Cocktail_Name', '')))
            self.table.setItem(row, 1, QTableWidgetItem(item.get('Base_spirit_1', '')))
            self.table.setItem(row, 2, QTableWidgetItem(item.get('Brand1', '')))
            self.table.setItem(row, 3, QTableWidgetItem(item.get('Rating_overall', '')))
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
        # Get cocktail name from table
        name = self.table.item(row, 0).text()
        
        # Fetch full data from database
        all_cocktails = self.db.get_all_cocktails()
        data = next((c for c in all_cocktails if c.get('Cocktail_Name') == name), None)
        
        if not data:
            QMessageBox.critical(self, "Error", "Could not find cocktail data")
            return
        
        dialog = CocktailInfoDialog(self, data, parent_tab=self)
        dialog.exec()
