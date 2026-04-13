# Cocktail Database Manager

A desktop application for managing a cocktail database with two main interfaces for viewing and managing alcohol inventory and cocktail recipes.

## Features

### Alcohol Inventory Tab
- **View Mode**: Display all alcohol entries in a table format with sortable columns
- **Add/Edit Mode**: Form with validation for adding or editing alcohol records
- **Search/Filter**: Real-time search across all fields
- **Delete**: Remove alcohol entries with confirmation

### Cocktail Recipes Tab
- **View Mode**: Display all cocktail entries with key information (name, base spirit, brand, rating, difficulty, prep time)
- **Add/Edit Mode**: Form with validation for adding or editing cocktail recipes
- **Search/Filter**: Real-time search by name, base spirit, or brand
- **Delete**: Remove cocktail entries with confirmation

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Setup
1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Database Setup
The application uses SQLite database (`cocktail_database.db`) which should already exist in the project root with the following tables:
- `alcohol_inventory`: Alcohol inventory data (66 records)
- `cocktail_notes`: Cocktail recipe data (103 records)

## Usage

### Running the Application
```bash
python main.py
```

### Alcohol Inventory Management
1. Click the "Alcohol Inventory" tab
2. **View**: Browse the table of all alcohol entries
3. **Add**: Click "Add Alcohol" button to open the form
   - Required fields: Brand, Base Liquor, Type
   - Optional fields: ABV, Country, Price, Taste, Substitute, Availability
4. **Edit**: Select a row and click "Edit Alcohol"
5. **Delete**: Select a row and click "Delete Alcohol"
6. **Search**: Type in the search box to filter results

### Cocktail Recipe Management
1. Click the "Cocktail Recipes" tab
2. **View**: Browse the table of all cocktail entries
3. **Add**: Click "Add Cocktail" button to open the form
   - Required fields: Cocktail Name, Ingredients
   - Optional fields: Ratings, Base Spirits, Citrus, Garnish, Notes, Prep Time, Difficulty
4. **Edit**: Select a row and click "Edit Cocktail"
5. **Delete**: Select a row and click "Delete Cocktail"
6. **Search**: Type in the search box to filter results

## Database Schema

### alcohol_inventory Table
- **Brand** (TEXT): Brand name of the alcohol
- **Base_Liquor** (TEXT): Category (Gin, Rum, Whisky, Vodka, Tequila, Mezcal, Liqueur, Brandy)
- **Type** (TEXT): Specific type (London Dry, Aged Rum, Bourbon, etc.)
- **ABV** (TEXT): Alcohol by volume percentage
- **Country** (TEXT): Country of origin
- **Price_NZD_700ml** (TEXT): Price in NZD for 700ml bottle
- **Taste** (TEXT): Tasting notes and flavor profile
- **Substitute** (TEXT): Alternative brands that can be substituted
- **Availability** (TEXT): Yes/No availability status

### cocktail_notes Table
- **Cocktail_Name** (TEXT): Name of the cocktail
- **Ingredients** (TEXT): Full ingredient list with measurements
- **Rating_Jason** (TEXT): Jason's rating (numeric)
- **Rating_Jaime** (TEXT): Jaime's rating (numeric)
- **Rating_overall** (TEXT): Overall combined rating (numeric)
- **Base_spirit_1** (TEXT): Primary base spirit category
- **Type1** (TEXT): Primary spirit type
- **Brand1** (TEXT): Primary spirit brand
- **Base_spirit_2** (TEXT): Secondary base spirit category (optional)
- **Type2** (TEXT): Secondary spirit type (optional)
- **Brand2** (TEXT): Secondary spirit brand (optional)
- **Citrus** (TEXT): Citrus ingredients used
- **Garnish** (TEXT): Garnish used
- **Notes** (TEXT): Additional notes, tasting notes, edits
- **DatetimeAdded** (TEXT): Date/time when cocktail was added
- **Prep_Time** (TEXT): Preparation time in minutes
- **Difficulty** (TEXT): Difficulty level (1-5 scale)

## Project Structure
```
cocktail-database/
├── main.py              # Main application entry point
├── database.py          # Database connection and operations
├── alcohol_tab.py       # Alcohol inventory tab UI
├── cocktail_tab.py      # Cocktail recipes tab UI
├── requirements.txt     # Python dependencies
├── SPEC.md             # Detailed software specification
├── README.md           # This file
├── .gitignore          # Git ignore rules
└── cocktail_database.db # SQLite database
```

## Technology Stack
- **Language**: Python 3.7+
- **UI Framework**: PyQt5
- **Database**: SQLite
- **ORM**: sqlite3 (built-in)

## Validation Rules

### Alcohol Inventory
- **ABV**: Must be numeric
- **Price**: Must be in valid currency format (e.g., $49.99)
- **Availability**: Must be "Yes" or "No"

### Cocktail Recipes
- **Ratings**: Must be numeric
- **Prep Time**: Must be numeric
- **Difficulty**: Must be 1-5

## Troubleshooting

### Application won't start
- Ensure PyQt5 is installed: `pip install PyQt5`
- Check that `cocktail_database.db` exists in the project root
- Verify Python version is 3.7 or higher

### Database connection errors
- Ensure the database file is not corrupted
- Check file permissions on `cocktail_database.db`

### Import errors
- Make sure all Python files are in the same directory
- Reinstall dependencies: `pip install -r requirements.txt`

## Building an Installer

### Prerequisites
- Python 3.7 or higher
- Inno Setup 6 (or later) - Download from https://jrsoftware.org/isdl.php

### Build Instructions

#### Automated Build (Recommended)
Run one of the following scripts from the project root:

**Windows Batch:**
```bash
build_installer.bat
```

**PowerShell:**
```powershell
.\build_installer.ps1
```

These scripts will:
1. Install all dependencies from requirements.txt
2. Build the executable using PyInstaller
3. Create the installer using Inno Setup

The final installer will be located at: `Output\CocktailDatabaseInstaller.exe`

#### Manual Build
If you prefer to build manually:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Build the executable with PyInstaller:
   ```bash
   pyinstaller --clean cocktail_database.spec
   ```

3. Build the installer with Inno Setup:
   ```bash
   iscc installer_script.iss
   ```

The installer will be created in the `Output` folder.

### Distribution
The generated `CocktailDatabaseInstaller.exe` can be distributed to users. When installed, it will:
- Install the application to `C:\Program Files\CocktailDatabase` (or user-selected location)
- Create desktop and Start Menu shortcuts
- Include all necessary files (database, images, config)
- Provide uninstall functionality

## Future Enhancements
- Export data to CSV
- Import data from CSV
- Cocktail search based on available ingredients
- Rating trends over time
- Print-friendly recipe cards
- Backup/restore database functionality

## License
This project is for personal use.

## Version History
- **v1.0** - Initial release with PyQt5, alcohol inventory management, and cocktail recipe management
