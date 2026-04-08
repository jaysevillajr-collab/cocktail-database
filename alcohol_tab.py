from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QLineEdit, 
                             QFormLayout, QDialog, QComboBox, QMessageBox)
from PyQt5.QtCore import Qt
from database import DatabaseManager


class AlcoholDialog(QDialog):
    """Dialog for adding/editing alcohol records."""
    
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.data = data or {}
        self.setWindowTitle("Add Alcohol" if not data else "Edit Alcohol")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.init_ui()
    
    def init_ui(self):
        layout = QFormLayout()
        
        # Brand (required)
        self.brand_edit = QLineEdit(self.data.get('Brand', ''))
        layout.addRow("Brand*:", self.brand_edit)
        
        # Base_Liquor (required)
        self.base_liquor_combo = QComboBox()
        self.base_liquor_combo.setEditable(True)
        self.base_liquor_combo.addItems(['Gin', 'Rum', 'Whisky', 'Vodka', 'Tequila', 
                                         'Mezcal', 'Liqueur', 'Brandy'])
        self.base_liquor_combo.setCurrentText(self.data.get('Base_Liquor', ''))
        layout.addRow("Base Liquor*:", self.base_liquor_combo)
        
        # Type (required)
        self.type_edit = QLineEdit(self.data.get('Type', ''))
        layout.addRow("Type*:", self.type_edit)
        
        # ABV (optional)
        self.abv_edit = QLineEdit(self.data.get('ABV', ''))
        layout.addRow("ABV:", self.abv_edit)
        
        # Country (optional)
        self.country_edit = QLineEdit(self.data.get('Country', ''))
        layout.addRow("Country:", self.country_edit)
        
        # Price (optional)
        self.price_edit = QLineEdit(self.data.get('Price_NZD_700ml', ''))
        layout.addRow("Price (NZD 700ml):", self.price_edit)
        
        # Taste (optional)
        self.taste_edit = QLineEdit(self.data.get('Taste', ''))
        layout.addRow("Taste:", self.taste_edit)
        
        # Substitute (optional)
        self.substitute_edit = QLineEdit(self.data.get('Substitute', ''))
        layout.addRow("Substitute:", self.substitute_edit)
        
        # Availability (optional)
        self.availability_combo = QComboBox()
        self.availability_combo.addItems(['Yes', 'No'])
        self.availability_combo.setCurrentText(self.data.get('Availability', 'Yes'))
        layout.addRow("Availability:", self.availability_combo)
        
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
    
    def validate_and_save(self):
        """Validate input and save."""
        brand = self.brand_edit.text().strip()
        base_liquor = self.base_liquor_combo.currentText().strip()
        liquor_type = self.type_edit.text().strip()
        
        # Required fields validation
        if not brand:
            QMessageBox.warning(self, "Validation Error", "Brand is required")
            return
        if not base_liquor:
            QMessageBox.warning(self, "Validation Error", "Base Liquor is required")
            return
        if not liquor_type:
            QMessageBox.warning(self, "Validation Error", "Type is required")
            return
        
        # Numeric validation for ABV
        abv = self.abv_edit.text().strip()
        if abv and not abv.replace('.', '').isdigit():
            QMessageBox.warning(self, "Validation Error", "ABV must be numeric")
            return
        
        # Price validation (should start with $ or be numeric)
        price = self.price_edit.text().strip()
        if price and not (price.startswith('$') or price.replace('.', '').replace(',', '').isdigit()):
            QMessageBox.warning(self, "Validation Error", "Price must be in valid format (e.g., $49.99)")
            return
        
        # Build data dictionary
        self.result_data = {
            'Brand': brand,
            'Base_Liquor': base_liquor,
            'Type': liquor_type,
            'ABV': abv,
            'Country': self.country_edit.text().strip(),
            'Price_NZD_700ml': price,
            'Taste': self.taste_edit.text().strip(),
            'Substitute': self.substitute_edit.text().strip(),
            'Availability': self.availability_combo.currentText()
        }
        
        self.accept()


class AlcoholTab(QWidget):
    """Tab for managing alcohol inventory."""
    
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by any field...")
        self.search_edit.textChanged.connect(self.filter_data)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        
        # Buttons
        self.add_button = QPushButton("Add Alcohol")
        self.add_button.clicked.connect(self.add_alcohol)
        self.edit_button = QPushButton("Edit Alcohol")
        self.edit_button.clicked.connect(self.edit_alcohol)
        self.delete_button = QPushButton("Delete Alcohol")
        self.delete_button.clicked.connect(self.delete_alcohol)
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
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            'Brand', 'Base Liquor', 'Type', 'ABV', 'Country', 
            'Price', 'Taste', 'Substitute', 'Availability'
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        
        layout.addLayout(search_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)
    
    def load_data(self):
        """Load data from database into table."""
        data = self.db.get_all_alcohol()
        self.populate_table(data)
    
    def populate_table(self, data):
        """Populate table with data."""
        self.table.setRowCount(len(data))
        
        for row, item in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(item.get('Brand', '')))
            self.table.setItem(row, 1, QTableWidgetItem(item.get('Base_Liquor', '')))
            self.table.setItem(row, 2, QTableWidgetItem(item.get('Type', '')))
            self.table.setItem(row, 3, QTableWidgetItem(item.get('ABV', '')))
            self.table.setItem(row, 4, QTableWidgetItem(item.get('Country', '')))
            self.table.setItem(row, 5, QTableWidgetItem(item.get('Price_NZD_700ml', '')))
            self.table.setItem(row, 6, QTableWidgetItem(item.get('Taste', '')))
            self.table.setItem(row, 7, QTableWidgetItem(item.get('Substitute', '')))
            self.table.setItem(row, 8, QTableWidgetItem(item.get('Availability', '')))
        
        self.table.resizeColumnsToContents()
    
    def filter_data(self):
        """Filter table data based on search text."""
        search_text = self.search_edit.text().lower()
        data = self.db.get_all_alcohol()
        
        filtered_data = []
        for item in data:
            # Search in all fields
            if any(search_text in str(value).lower() for value in item.values()):
                filtered_data.append(item)
        
        self.populate_table(filtered_data)
    
    def add_alcohol(self):
        """Open dialog to add new alcohol."""
        dialog = AlcoholDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.db.add_alcohol(dialog.result_data):
                QMessageBox.information(self, "Success", "Alcohol added successfully")
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", "Failed to add alcohol")
    
    def edit_alcohol(self):
        """Open dialog to edit selected alcohol."""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Warning", "Please select an alcohol to edit")
            return
        
        # Get current data from table
        brand = self.table.item(selected_row, 0).text()
        data = {
            'Brand': brand,
            'Base_Liquor': self.table.item(selected_row, 1).text(),
            'Type': self.table.item(selected_row, 2).text(),
            'ABV': self.table.item(selected_row, 3).text(),
            'Country': self.table.item(selected_row, 4).text(),
            'Price_NZD_700ml': self.table.item(selected_row, 5).text(),
            'Taste': self.table.item(selected_row, 6).text(),
            'Substitute': self.table.item(selected_row, 7).text(),
            'Availability': self.table.item(selected_row, 8).text()
        }
        
        dialog = AlcoholDialog(self, data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.db.update_alcohol(brand, dialog.result_data):
                QMessageBox.information(self, "Success", "Alcohol updated successfully")
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", "Failed to update alcohol")
    
    def delete_alcohol(self):
        """Delete selected alcohol."""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Warning", "Please select an alcohol to delete")
            return
        
        brand = self.table.item(selected_row, 0).text()
        reply = QMessageBox.question(
            self, 'Confirm Delete',
            f'Are you sure you want to delete "{brand}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.db.delete_alcohol(brand):
                QMessageBox.information(self, "Success", "Alcohol deleted successfully")
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete alcohol")
