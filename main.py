import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

from database import DatabaseManager
from alcohol_tab import AlcoholTab
from cocktail_tab import CocktailTab


class CocktailDatabaseApp(QMainWindow):
    """Main application window for the Cocktail Database Manager."""
    
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.db.connect()
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Cocktail Database Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget with tabbed interface
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Tab 1: Alcohol Inventory
        self.alcohol_tab = AlcoholTab(self.db)
        self.tab_widget.addTab(self.alcohol_tab, "Alcohol Inventory")
        
        # Tab 2: Cocktail Recipes
        self.cocktail_tab = CocktailTab(self.db)
        self.tab_widget.addTab(self.cocktail_tab, "Cocktail Recipes")
        
        layout.addWidget(self.tab_widget)
    
    def closeEvent(self, event):
        """Handle window close event - close database connection."""
        self.db.close()
        event.accept()


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    
    window = CocktailDatabaseApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
