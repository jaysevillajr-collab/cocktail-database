from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QLineEdit, 
                             QFormLayout, QDialog, QComboBox, QMessageBox, 
                             QFileDialog, QScrollArea)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QDoubleValidator, QIntValidator
from database import DatabaseManager
import os
from PIL import Image


class AlcoholDialog(QDialog):
    """Dialog for adding/editing alcohol records."""
    
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.data = data or {}
        self.setWindowTitle("Add Alcohol" if not data else "Edit Alcohol")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.image_path = self.data.get('image_path', '')
        self.init_ui()
        self.load_existing_image()
        # Trigger validation for existing data
        self.validate_abv_input(self.abv_edit.text())
        self.validate_price_input(self.price_edit.text())
    
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
        self.abv_edit.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.abv_edit.textChanged.connect(self.validate_abv_input)
        layout.addRow("ABV:", self.abv_edit)
        
        # Country (optional)
        self.country_edit = QLineEdit(self.data.get('Country', ''))
        layout.addRow("Country:", self.country_edit)
        
        # Price (optional)
        self.price_edit = QLineEdit(self.data.get('Price_NZD_700ml', ''))
        self.price_edit.setPlaceholderText("$0.00")
        self.price_edit.textChanged.connect(self.validate_price_input)
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
        
        # Image upload
        image_layout = QHBoxLayout()
        self.upload_button = QPushButton("Upload Image")
        self.upload_button.clicked.connect(self.upload_image)
        self.remove_image_button = QPushButton("Remove Image")
        self.remove_image_button.clicked.connect(self.remove_image)
        image_layout.addWidget(self.upload_button)
        image_layout.addWidget(self.remove_image_button)
        layout.addRow("Image:", image_layout)
        
        # Image preview
        self.image_label = QLabel()
        self.image_label.setFixedSize(200, 200)
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setText("No image")
        layout.addRow("Preview:", self.image_label)
        
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
    
    def validate_abv_input(self, text):
        """Validate ABV input in real-time."""
        if text and not text.replace('.', '').isdigit():
            self.abv_edit.setStyleSheet("background-color: #ffcccc;")
        else:
            self.abv_edit.setStyleSheet("")
    
    def validate_price_input(self, text):
        """Validate Price input in real-time."""
        if text and not (text.startswith('$') or text.replace('.', '').replace(',', '').isdigit()):
            self.price_edit.setStyleSheet("background-color: #ffcccc;")
        else:
            self.price_edit.setStyleSheet("")
    
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
            'Availability': self.availability_combo.currentText(),
            'image_path': self.image_path
        }
        
        self.accept()
    
    def upload_image(self):
        """Upload and process image for alcohol."""
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            self.process_image(file_path)
    
    def process_image(self, file_path):
        """Process image: resize to 512x512 and save to images/liquors/."""
        try:
            # Create directory if it doesn't exist
            os.makedirs('images/liquors', exist_ok=True)
            
            # Get brand, base_liquor, and type for filename
            brand = self.brand_edit.text().strip() or 'unknown'
            base_liquor = self.base_liquor_combo.currentText().strip() or 'unknown'
            liquor_type = self.type_edit.text().strip() or 'unknown'
            
            # Create safe filename
            safe_brand = brand.replace(' ', '_').replace('/', '_').replace('\\', '_')
            safe_base = base_liquor.replace(' ', '_').replace('/', '_').replace('\\', '_')
            safe_type = liquor_type.replace(' ', '_').replace('/', '_').replace('\\', '_')
            filename = f"{safe_brand}_{safe_base}_{safe_type}.jpg"
            save_path = os.path.join('images/liquors', filename)
            
            # Open and resize image
            img = Image.open(file_path)
            img = img.resize((512, 512), Image.Resampling.LANCZOS)
            img.save(save_path, 'JPEG', quality=85)
            
            self.image_path = save_path
            self.update_preview(save_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to process image: {e}")
    
    def remove_image(self):
        """Remove uploaded image."""
        self.image_path = ''
        self.image_label.clear()
        self.image_label.setText("No image")
    
    def load_existing_image(self):
        """Load existing image if available."""
        if self.image_path and os.path.exists(self.image_path):
            self.update_preview(self.image_path)
    
    def update_preview(self, image_path):
        """Update image preview label."""
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)


class AlcoholInfoDialog(QDialog):
    """Dialog for displaying alcohol information (read-only)."""
    
    def __init__(self, parent=None, data=None, parent_tab=None):
        super().__init__(parent)
        self.data = data or {}
        self.parent_tab = parent_tab
        self.setWindowTitle("Alcohol Information")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.init_ui()
        self.load_image()
    
    def init_ui(self):
        layout = QFormLayout()
        
        # Brand
        brand_label = QLabel(self.data.get('Brand', ''))
        layout.addRow("Brand:", brand_label)
        
        # Base_Liquor
        base_liquor_label = QLabel(self.data.get('Base_Liquor', ''))
        layout.addRow("Base Liquor:", base_liquor_label)
        
        # Type
        type_label = QLabel(self.data.get('Type', ''))
        layout.addRow("Type:", type_label)
        
        # ABV
        abv_label = QLabel(self.data.get('ABV', ''))
        layout.addRow("ABV:", abv_label)
        
        # Country
        country_label = QLabel(self.data.get('Country', ''))
        layout.addRow("Country:", country_label)
        
        # Price
        price_label = QLabel(self.data.get('Price_NZD_700ml', ''))
        layout.addRow("Price (NZD 700ml):", price_label)
        
        # Taste
        taste_label = QLabel(self.data.get('Taste', ''))
        layout.addRow("Taste:", taste_label)
        
        # Substitute
        substitute_label = QLabel(self.data.get('Substitute', ''))
        layout.addRow("Substitute:", substitute_label)
        
        # Availability
        availability_label = QLabel(self.data.get('Availability', ''))
        layout.addRow("Availability:", availability_label)
        
        # Image preview
        self.image_label = QLabel()
        self.image_label.setFixedSize(200, 200)
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setText("No image")
        layout.addRow("Image:", self.image_label)
        
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
    
    def load_image(self):
        """Load image if available."""
        image_path = self.data.get('image_path', '')
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
    
    def edit_item(self):
        """Edit the current item."""
        self.accept()
        # Find the row in the parent table
        brand = self.data.get('Brand', '')
        for row in range(self.parent_tab.table.rowCount()):
            if self.parent_tab.table.item(row, 0).text() == brand:
                self.parent_tab.table.selectRow(row)
                self.parent_tab.edit_alcohol()
                break
    
    def delete_item(self):
        """Delete the current item."""
        self.accept()
        # Find the row in the parent table
        brand = self.data.get('Brand', '')
        for row in range(self.parent_tab.table.rowCount()):
            if self.parent_tab.table.item(row, 0).text() == brand:
                self.parent_tab.table.selectRow(row)
                self.parent_tab.delete_alcohol()
                break


class AlcoholTab(QWidget):
    """Tab for managing alcohol inventory."""
    
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
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            'Brand', 'Base Liquor', 'Type', 'ABV', 'Country', 
            'Price', 'Taste', 'Substitute', 'Availability', 'Image Path'
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.show_alcohol_info)
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
            self.table.setItem(row, 9, QTableWidgetItem(item.get('image_path', '')))
        
        self.table.resizeColumnsToContents()
    
    def add_log(self, action):
        """Add an action to the log with timestamp."""
        from datetime import datetime
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
                self.add_log(f"Added alcohol: {dialog.result_data['Brand']}")
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
            'Availability': self.table.item(selected_row, 8).text(),
            'image_path': self.table.item(selected_row, 9).text() if self.table.columnCount() > 9 else ''
        }
        
        dialog = AlcoholDialog(self, data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.db.update_alcohol(brand, dialog.result_data):
                QMessageBox.information(self, "Success", "Alcohol updated successfully")
                self.add_log(f"Edited alcohol: {dialog.result_data['Brand']}")
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
        
        # First confirmation
        reply1 = QMessageBox.question(
            self, 'Confirm Delete',
            f'Are you sure you want to delete "{brand}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply1 != QMessageBox.StandardButton.Yes:
            return
        
        # Second confirmation
        reply2 = QMessageBox.question(
            self, 'Confirm Delete',
            f'Are you REALLY sure you want to delete "{brand}"? This action cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply2 == QMessageBox.StandardButton.Yes:
            if self.db.delete_alcohol(brand):
                QMessageBox.information(self, "Success", "Alcohol deleted successfully")
                self.add_log(f"Deleted alcohol: {brand}")
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete alcohol")
    
    def show_alcohol_info(self, row, column):
        """Show alcohol information dialog when row is double-clicked."""
        # Get current data from table
        brand = self.table.item(row, 0).text()
        data = {
            'Brand': brand,
            'Base_Liquor': self.table.item(row, 1).text(),
            'Type': self.table.item(row, 2).text(),
            'ABV': self.table.item(row, 3).text(),
            'Country': self.table.item(row, 4).text(),
            'Price_NZD_700ml': self.table.item(row, 5).text(),
            'Taste': self.table.item(row, 6).text(),
            'Substitute': self.table.item(row, 7).text(),
            'Availability': self.table.item(row, 8).text(),
            'image_path': self.table.item(row, 9).text() if self.table.columnCount() > 9 else ''
        }
        
        dialog = AlcoholInfoDialog(self, data, parent_tab=self)
        dialog.exec()
