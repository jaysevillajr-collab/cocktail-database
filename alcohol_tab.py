from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QLineEdit, 
                             QFormLayout, QDialog, QComboBox, QMessageBox, 
                             QFileDialog, QScrollArea, QShortcut, QMenu, QCompleter, QSplitter, QGridLayout, QFrame)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QMimeData, QUrl
from PyQt5.QtGui import QPixmap, QDoubleValidator, QIntValidator, QKeySequence, QDragEnterEvent, QDropEvent
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
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
        self.setAcceptDrops(True)
        self.image_path = self.data.get('image_path', '')
        self.create_image_folders()
        self.init_ui()
        self.load_existing_image()
        # Trigger validation for existing data
        self.validate_abv_input(self.abv_edit.text())
        self.validate_price_input(self.price_edit.text())
        # Add fade-in animation
        self.fade_in()
    
    def create_image_folders(self):
        """Create image folders if they don't exist."""
        os.makedirs('images/liquors', exist_ok=True)
    
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
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event for image files."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path and os.path.exists(file_path):
                    # Check if it's an image file by trying to open it
                    try:
                        img = Image.open(file_path)
                        # Copy image to images/liquors folder
                        brand = self.brand_edit.text() if self.brand_edit.text() else 'temp'
                        base_liquor = self.base_liquor_combo.currentText() if self.base_liquor_combo.currentText() else 'unknown'
                        liquor_type = self.type_edit.text() if self.type_edit.text() else 'unknown'
                        
                        # Create safe filename
                        safe_brand = brand.replace(' ', '_').replace('/', '_').replace('\\', '_')
                        safe_base = base_liquor.replace(' ', '_').replace('/', '_').replace('\\', '_')
                        safe_type = liquor_type.replace(' ', '_').replace('/', '_').replace('\\', '_')
                        filename = f"{safe_brand}_{safe_base}_{safe_type}.jpg"
                        save_path = os.path.join('images/liquors', filename)
                        
                        # Resize image
                        img = img.resize((512, 512), Image.Resampling.LANCZOS)
                        img.save(save_path, 'JPEG', quality=85)
                        
                        self.image_path = save_path
                        self.load_existing_image()
                        break
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to process dropped image: {e}")
                        continue
        event.acceptProposedAction()
    
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
        
        # Add auto-complete with existing values from database
        completer = QCompleter(['Gin', 'Rum', 'Whisky', 'Vodka', 'Tequila', 
                                'Mezcal', 'Liqueur', 'Brandy'])
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.base_liquor_combo.setCompleter(completer)
        
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
        self.availability_combo.addItems(['Available', 'Limited', 'Unavailable'])
        self.availability_combo.setCurrentText(self.data.get('Availability', 'Available'))
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
    
    # Country code mapping for flag API
    COUNTRY_CODES = {
        'Scotland': 'gb-sct',
        'England': 'gb-eng',
        'Wales': 'gb-wls',
        'Northern Ireland': 'gb-nir',
        'United States': 'us',
        'USA': 'us',
        'United Kingdom': 'gb',
        'UK': 'gb',
        'Japan': 'jp',
        'Mexico': 'mx',
        'France': 'fr',
        'Germany': 'de',
        'Italy': 'it',
        'Spain': 'es',
        'Ireland': 'ie',
        'Canada': 'ca',
        'Australia': 'au',
        'New Zealand': 'nz',
        'Sweden': 'se',
        'Norway': 'no',
        'Denmark': 'dk',
        'Netherlands': 'nl',
        'Belgium': 'be',
        'Austria': 'at',
        'Switzerland': 'ch',
        'Poland': 'pl',
        'Czech Republic': 'cz',
        'Hungary': 'hu',
        'Romania': 'ro',
        'Bulgaria': 'bg',
        'Greece': 'gr',
        'Turkey': 'tr',
        'Russia': 'ru',
        'China': 'cn',
        'India': 'in',
        'Brazil': 'br',
        'Argentina': 'ar',
        'Chile': 'cl',
        'Colombia': 'co',
        'Peru': 'pe',
        'Cuba': 'cu',
        'Jamaica': 'jm',
        'Haiti': 'ht',
        'Dominican Republic': 'do',
        'Puerto Rico': 'pr',
        'Philippines': 'ph',
        'Thailand': 'th',
        'Vietnam': 'vn',
        'Indonesia': 'id',
        'Malaysia': 'my',
        'Singapore': 'sg',
        'South Korea': 'kr',
        'Taiwan': 'tw',
        'Hong Kong': 'hk',
        'South Africa': 'za',
        'Portugal': 'pt',
        'Finland': 'fi',
        'Iceland': 'is',
        'Estonia': 'ee',
        'Latvia': 'lv',
        'Lithuania': 'lt',
        'Ukraine': 'ua',
        'Belarus': 'by',
        'Kazakhstan': 'kz',
        'Georgia': 'ge',
        'Armenia': 'am',
        'Azerbaijan': 'az',
        'Israel': 'il',
        'Lebanon': 'lb',
        'Jordan': 'jo',
        'Egypt': 'eg',
        'Morocco': 'ma',
        'Tunisia': 'tn',
        'Algeria': 'dz',
        'Kenya': 'ke',
        'Nigeria': 'ng',
        'Ghana': 'gh',
        'Ethiopia': 'et',
    }
    
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.action_logs = []
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self.on_flag_loaded)
        self.init_ui()
        self.create_image_folders()
        self.load_data()
    
    def create_image_folders(self):
        """Create image folders if they don't exist."""
        os.makedirs('images/liquors', exist_ok=True)
        os.makedirs('images/flags', exist_ok=True)
    
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
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_data)
        self.split_view_button = QPushButton("Split View")
        self.split_view_button.setCheckable(True)
        self.split_view_button.clicked.connect(self.toggle_split_view)
        self.view_toggle_button = QPushButton("Gallery View")
        self.view_toggle_button.setCheckable(True)
        self.view_toggle_button.clicked.connect(self.toggle_view)
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
        button_layout.addWidget(self.view_toggle_button)
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
        
        self.available_filter = QPushButton("Available")
        self.available_filter.setCheckable(True)
        self.available_filter.clicked.connect(lambda: self.apply_filter('available'))
        filter_layout.addWidget(self.available_filter)
        
        self.limited_filter = QPushButton("Limited")
        self.limited_filter.setCheckable(True)
        self.limited_filter.clicked.connect(lambda: self.apply_filter('limited'))
        filter_layout.addWidget(self.limited_filter)
        
        self.unavailable_filter = QPushButton("Unavailable")
        self.unavailable_filter.setCheckable(True)
        self.unavailable_filter.clicked.connect(lambda: self.apply_filter('unavailable'))
        filter_layout.addWidget(self.unavailable_filter)
        
        filter_layout.addStretch()
        
        # Create stacked widget for view switching
        from PyQt5.QtWidgets import QStackedWidget
        self.view_stack = QStackedWidget()
        
        # Create splitter for split view (for table view)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
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
        
        # Container widget for details panel
        self.details_container = QWidget()
        self.details_layout = QVBoxLayout(self.details_container)
        self.details_layout.setContentsMargins(0, 0, 0, 0)
        
        # Images container (horizontal layout for side-by-side)
        self.images_container = QWidget()
        self.images_layout = QHBoxLayout(self.images_container)
        self.images_layout.setContentsMargins(0, 5, 0, 5)
        self.images_layout.setSpacing(10)
        
        # Flag label
        self.flag_label = QLabel()
        self.flag_label.setMaximumSize(180, 120)
        self.flag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.flag_label.setStyleSheet("border: none;")
        self.images_layout.addWidget(self.flag_label)
        
        # Alcohol image label
        self.alcohol_image_label = QLabel()
        self.alcohol_image_label.setMaximumSize(180, 120)
        self.alcohol_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.alcohol_image_label.setStyleSheet("border: none;")
        self.images_layout.addWidget(self.alcohol_image_label)
        
        self.details_layout.addWidget(self.images_container)
        
        # Text label (with solid background for readability)
        self.details_label = QLabel("Select an item to view details")
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet("padding: 15px; background-color: white; color: #333333; border-radius: 0px;")
        self.details_layout.addWidget(self.details_label)
        
        self.details_panel.setWidget(self.details_container)
        self.splitter.addWidget(self.details_panel)
        
        # Set initial splitter sizes (table takes all space initially)
        self.splitter.setSizes([1000, 0])
        
        # Add splitter to view stack (table view)
        self.view_stack.addWidget(self.splitter)
        
        # Create gallery view
        self.gallery_scroll = QScrollArea()
        self.gallery_scroll.setWidgetResizable(True)
        self.gallery_widget = QWidget()
        self.gallery_layout = QGridLayout()
        self.gallery_widget.setLayout(self.gallery_layout)
        self.gallery_scroll.setWidget(self.gallery_widget)
        
        # Add gallery to view stack
        self.view_stack.addWidget(self.gallery_scroll)
        
        # Keyboard shortcuts
        self.shortcut_new = QShortcut(QKeySequence("Ctrl+N"), self)
        self.shortcut_new.activated.connect(self.add_alcohol)
        self.shortcut_edit = QShortcut(QKeySequence("Ctrl+E"), self)
        self.shortcut_edit.activated.connect(self.edit_alcohol)
        self.shortcut_delete = QShortcut(QKeySequence("Delete"), self)
        self.shortcut_delete.activated.connect(self.delete_alcohol)
        self.shortcut_refresh = QShortcut(QKeySequence("F5"), self)
        self.shortcut_refresh.activated.connect(self.load_data)
        
        layout.addLayout(search_layout)
        layout.addLayout(button_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self.view_stack, stretch=1)  # Give table more space
        
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
        data = self.db.get_all_alcohol()
        self.current_data = data  # Store current data for filtering
        self.populate_table(data)
        self.populate_gallery(data)
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
                parent.status_bar.showMessage(f"Alcohol Inventory - Total: {total_items} | {selection_text}")
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
    
    def on_flag_loaded(self, reply):
        """Handle flag image download completion."""
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                # Scale pixmap to fit the flag label
                scaled_pixmap = pixmap.scaled(
                    120,
                    100,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.flag_label.setPixmap(scaled_pixmap)
        reply.deleteLater()
    
    def update_details_panel(self):
        """Update details panel with selected item information."""
        if not self.split_view_button.isChecked():
            self.flag_label.clear()
            self.alcohol_image_label.clear()
            return
        
        selected_row = self.table.currentRow()
        if selected_row < 0:
            self.details_label.setText("Select an item to view details")
            self.flag_label.clear()
            self.alcohol_image_label.clear()
            return
        
        # Get item data from table directly to ensure it matches the current view
        try:
            brand = self.table.item(selected_row, 0).text()
            base_liquor = self.table.item(selected_row, 1).text()
            type_val = self.table.item(selected_row, 2).text()
            abv = self.table.item(selected_row, 3).text()
            country = self.table.item(selected_row, 4).text()
            price = self.table.item(selected_row, 5).text()
            taste = self.table.item(selected_row, 6).text()
            substitute = self.table.item(selected_row, 7).text()
            availability = self.table.item(selected_row, 8).text()
            image_path = self.table.item(selected_row, 9).text() if self.table.columnCount() > 9 else ''
            
            details_text = f"<b>Brand:</b> {brand}<br>"
            details_text += f"<b>Base Liquor:</b> {base_liquor}<br>"
            details_text += f"<b>Type:</b> {type_val}<br>"
            details_text += f"<b>ABV:</b> {abv}<br>"
            details_text += f"<b>Country:</b> {country}<br>"
            details_text += f"<b>Price:</b> {price}<br>"
            details_text += f"<b>Taste:</b> {taste}<br>"
            details_text += f"<b>Substitute:</b> {substitute}<br>"
            details_text += f"<b>Availability:</b> {availability}"
            self.details_label.setText(details_text)
            
            # Clear previous images
            self.flag_label.clear()
            self.alcohol_image_label.clear()
            
            # Check what images are available
            has_flag = bool(self.COUNTRY_CODES.get(country, ''))
            has_alcohol_image = bool(image_path and os.path.exists(image_path))
            
            # Handle image display based on availability
            if has_flag and has_alcohol_image:
                # Show both side by side
                country_code = self.COUNTRY_CODES.get(country, '')
                flag_url = f"https://flagcdn.com/w320/{country_code}.png"
                # Download and save flag to images/flags folder
                flag_filename = f"flag_{country_code}.png"
                flag_path = os.path.join('images/flags', flag_filename)
                if not os.path.exists(flag_path):
                    import urllib.request
                    urllib.request.urlretrieve(flag_url, flag_path)
                # Load flag from local file
                pixmap = QPixmap(flag_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        180,
                        120,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.flag_label.setPixmap(scaled_pixmap)
                
                # Load alcohol image
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        180,
                        120,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.alcohol_image_label.setPixmap(scaled_pixmap)
                
                # Reset sizes for side-by-side
                self.flag_label.setMaximumSize(180, 120)
                self.alcohol_image_label.setMaximumSize(180, 120)
                self.images_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.flag_label.show()
                self.alcohol_image_label.show()
            elif has_flag:
                # Show only flag centered
                country_code = self.COUNTRY_CODES.get(country, '')
                flag_url = f"https://flagcdn.com/w320/{country_code}.png"
                # Download and save flag to images/flags folder
                flag_filename = f"flag_{country_code}.png"
                flag_path = os.path.join('images/flags', flag_filename)
                if not os.path.exists(flag_path):
                    import urllib.request
                    urllib.request.urlretrieve(flag_url, flag_path)
                # Load flag from local file
                pixmap = QPixmap(flag_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        250,
                        150,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.flag_label.setPixmap(scaled_pixmap)
                self.flag_label.setMaximumSize(250, 150)
                self.alcohol_image_label.hide()
                self.images_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            elif has_alcohol_image:
                # Show only alcohol image centered
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        250,
                        150,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.alcohol_image_label.setPixmap(scaled_pixmap)
                    self.alcohol_image_label.setMaximumSize(250, 150)
                    self.flag_label.hide()
                self.images_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                # Hide both
                self.flag_label.hide()
                self.alcohol_image_label.hide()
                
            # Reset visibility for next selection
            self.flag_label.show()
            self.alcohol_image_label.show()
            self.flag_label.setMaximumSize(180, 120)
            self.alcohol_image_label.setMaximumSize(180, 120)
            
        except Exception as e:
            self.details_label.setText("Error loading details")
            self.flag_label.clear()
            self.alcohol_image_label.clear()
    
    def toggle_view(self):
        """Toggle between table and gallery view."""
        if self.view_toggle_button.isChecked():
            self.view_stack.setCurrentIndex(1)  # Gallery view
            self.view_toggle_button.setText("Table View")
        else:
            self.view_stack.setCurrentIndex(0)  # Table view
            self.view_toggle_button.setText("Gallery View")
    
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
            self, "Export Alcohol Data", "", "CSV Files (*.csv);;All Files (*)"
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
        favorites_file = "alcohol_favorites.json"
        if os.path.exists(favorites_file):
            try:
                with open(favorites_file, 'r') as f:
                    self.favorites = set(json.load(f))
            except Exception:
                self.favorites = set()
    
    def save_favorites(self):
        """Save favorites to JSON file."""
        import json
        favorites_file = "alcohol_favorites.json"
        try:
            with open(favorites_file, 'w') as f:
                json.dump(list(self.favorites), f)
        except Exception as e:
            print(f"Failed to save favorites: {e}")
    
    def toggle_favorites_filter(self):
        """Toggle favorites filter."""
        if self.favorites_button.isChecked():
            # Show only favorites
            filtered_data = [item for item in self.current_data if item.get('Brand', '') in self.favorites]
            self.populate_table(filtered_data)
            self.populate_gallery(filtered_data)
        else:
            # Show all
            self.populate_table(self.current_data)
            self.populate_gallery(self.current_data)
    
    def toggle_favorite(self, brand):
        """Toggle favorite status for an item."""
        if brand in self.favorites:
            self.favorites.remove(brand)
        else:
            self.favorites.add(brand)
        self.save_favorites()
    
    def populate_gallery(self, data):
        """Populate gallery with thumbnail images."""
        # Clear existing gallery items
        for i in reversed(range(self.gallery_layout.count())):
            self.gallery_layout.itemAt(i).widget().setParent(None)
        
        # Add thumbnails to gallery
        for row, item in enumerate(data):
            # Create thumbnail frame
            frame = QFrame()
            frame.setFrameStyle(QFrame.Shape.Box)
            frame.setStyleSheet("border: 1px solid #ccc; border-radius: 5px; padding: 5px;")
            
            frame_layout = QVBoxLayout()
            
            # Image label
            image_label = QLabel()
            image_label.setFixedSize(150, 150)
            image_path = item.get('image_path', '')
            
            if image_path and os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                scaled_pixmap = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                image_label.setPixmap(scaled_pixmap)
            else:
                image_label.setText("No Image")
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                image_label.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;")
            
            frame_layout.addWidget(image_label)
            
            # Brand label
            brand_label = QLabel(item.get('Brand', ''))
            brand_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            brand_label.setStyleSheet("font-weight: bold; font-size: 12px;")
            frame_layout.addWidget(brand_label)
            
            # Base liquor label
            liquor_label = QLabel(item.get('Base_Liquor', ''))
            liquor_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            liquor_label.setStyleSheet("font-size: 10px; color: #666;")
            frame_layout.addWidget(liquor_label)
            
            frame.setLayout(frame_layout)
            
            # Add to grid layout (4 columns)
            col = row % 4
            row_grid = row // 4
            self.gallery_layout.addWidget(frame, row_grid, col)
        
        self.gallery_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    
    def apply_filter(self, filter_type):
        """Apply filter to the table data."""
        # Update button states
        self.all_filter.setChecked(filter_type == 'all')
        self.available_filter.setChecked(filter_type == 'available')
        self.limited_filter.setChecked(filter_type == 'limited')
        self.unavailable_filter.setChecked(filter_type == 'unavailable')
        
        # Filter data
        if filter_type == 'all':
            filtered_data = self.current_data
        else:
            filtered_data = []
            for item in self.current_data:
                availability = item.get('Availability', '').lower()
                # Handle both old (yes/no) and new (available/limited/unavailable) values
                if filter_type == 'available':
                    if 'available' in availability or 'yes' in availability:
                        filtered_data.append(item)
                elif filter_type == 'limited':
                    if 'limited' in availability or 'low' in availability:
                        filtered_data.append(item)
                elif filter_type == 'unavailable':
                    if 'unavailable' in availability or 'out' in availability or 'no' in availability:
                        filtered_data.append(item)
        
        self.populate_table(filtered_data)
        self.populate_gallery(filtered_data)
    
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
        brand = item.row() >= 0 and self.table.item(item.row(), 0) and self.table.item(item.row(), 0).text()
        favorite_action = menu.addAction("⭐ Toggle Favorite")
        menu.addSeparator()
        refresh_action = menu.addAction("Refresh")
        
        action = menu.exec(self.table.viewport().mapToGlobal(position))
        
        if action == edit_action:
            self.edit_alcohol()
        elif action == delete_action:
            self.delete_alcohol()
        elif action == info_action:
            self.show_alcohol_info(item.row(), item.column())
        elif action == favorite_action:
            brand = self.table.item(item.row(), 0).text()
            self.toggle_favorite(brand)
        elif action == refresh_action:
            self.load_data()
    
    def populate_table(self, data):
        """Populate table with data."""
        self.table.setRowCount(len(data))
        
        search_text = self.search_edit.text().lower()
        
        for row, item in enumerate(data):
            brand_item = QTableWidgetItem(item.get('Brand', ''))
            base_liquor_item = QTableWidgetItem(item.get('Base_Liquor', ''))
            type_item = QTableWidgetItem(item.get('Type', ''))
            abv_item = QTableWidgetItem(item.get('ABV', ''))
            country_item = QTableWidgetItem(item.get('Country', ''))
            price_item = QTableWidgetItem(item.get('Price_NZD_700ml', ''))
            taste_item = QTableWidgetItem(item.get('Taste', ''))
            substitute_item = QTableWidgetItem(item.get('Substitute', ''))
            image_path = item.get('image_path', '')
            
            # Highlight matching cells if search is active
            if search_text:
                for table_item in [brand_item, base_liquor_item, type_item, abv_item, country_item, price_item, taste_item, substitute_item]:
                    if search_text in table_item.text().lower():
                        table_item.setBackground(Qt.GlobalColor.cyan)
                        table_item.setForeground(Qt.GlobalColor.black)
            
            # Set tooltip for all items based on image availability
            if image_path and os.path.exists(image_path):
                tooltip_text = f"<img src='{image_path}' width='200' height='200'>"
            else:
                country = item.get('Country', '')
                country_code = self.COUNTRY_CODES.get(country, '')
                if country_code:
                    # Download flag to images/flags folder
                    import urllib.request
                    flag_url = f"https://flagcdn.com/w320/{country_code}.png"
                    try:
                        flag_filename = f"flag_{country_code}.png"
                        flag_path = os.path.join('images/flags', flag_filename)
                        
                        # Only download if not already cached
                        if not os.path.exists(flag_path):
                            urllib.request.urlretrieve(flag_url, flag_path)
                        
                        tooltip_text = f"<img src='{flag_path}' width='200' height='150'>"
                    except Exception:
                        # Fallback to just country name if download fails
                        tooltip_text = f"Country: {country}"
                else:
                    tooltip_text = ""
            
            # Apply tooltip to all items
            for table_item in [brand_item, base_liquor_item, type_item, abv_item, country_item, price_item, taste_item, substitute_item]:
                if tooltip_text:
                    table_item.setToolTip(tooltip_text)
            
            self.table.setItem(row, 0, brand_item)
            self.table.setItem(row, 1, base_liquor_item)
            self.table.setItem(row, 2, type_item)
            self.table.setItem(row, 3, abv_item)
            self.table.setItem(row, 4, country_item)
            self.table.setItem(row, 5, price_item)
            self.table.setItem(row, 6, taste_item)
            self.table.setItem(row, 7, substitute_item)
            
            # Color-coded availability
            availability = item.get('Availability', '').lower()
            availability_item = QTableWidgetItem(item.get('Availability', ''))
            if 'available' in availability:
                availability_item.setBackground(Qt.GlobalColor.green)
                availability_item.setForeground(Qt.GlobalColor.white)
            elif 'limited' in availability or 'low' in availability:
                availability_item.setBackground(Qt.GlobalColor.yellow)
                availability_item.setForeground(Qt.GlobalColor.black)
            elif 'unavailable' in availability or 'out' in availability:
                availability_item.setBackground(Qt.GlobalColor.red)
                availability_item.setForeground(Qt.GlobalColor.white)
            self.table.setItem(row, 8, availability_item)
            
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
        # Check if row is valid
        if row < 0 or row >= self.table.rowCount():
            return
        
        # Get current data from table with error handling
        try:
            brand_item = self.table.item(row, 0)
            if not brand_item:
                return
            brand = brand_item.text()
            
            data = {
                'Brand': brand,
                'Base_Liquor': self.table.item(row, 1).text() if self.table.item(row, 1) else '',
                'Type': self.table.item(row, 2).text() if self.table.item(row, 2) else '',
                'ABV': self.table.item(row, 3).text() if self.table.item(row, 3) else '',
                'Country': self.table.item(row, 4).text() if self.table.item(row, 4) else '',
                'Price_NZD_700ml': self.table.item(row, 5).text() if self.table.item(row, 5) else '',
                'Taste': self.table.item(row, 6).text() if self.table.item(row, 6) else '',
                'Substitute': self.table.item(row, 7).text() if self.table.item(row, 7) else '',
                'Availability': self.table.item(row, 8).text() if self.table.item(row, 8) else '',
                'image_path': self.table.item(row, 9).text() if self.table.columnCount() > 9 and self.table.item(row, 9) else ''
            }
            
            dialog = AlcoholInfoDialog(self, data, parent_tab=self)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load alcohol information: {str(e)}")
