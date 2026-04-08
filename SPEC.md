# Cocktail Database Management Software Specification

## Overview
A desktop/web application for managing a cocktail database with two main interfaces for viewing and managing alcohol inventory and cocktail recipes.

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

## Functional Requirements

### Tab 1: Alcohol Inventory Management

#### View Mode
- Display all alcohol entries in a table/grid format
- Columns: Brand, Base_Liquor, Type, ABV, Country, Price, Taste, Substitute, Availability
- Sortable columns
- Search/filter functionality by any field
- Pagination for large datasets (66 current records)

#### Add/Edit Mode
- Form with all 9 fields from alcohol_inventory table
- Required fields: Brand, Base_Liquor, Type
- Optional fields: ABV, Country, Price, Taste, Substitute, Availability
- Validation:
  - ABV must be numeric
  - Price must be in valid currency format
  - Availability must be "Yes" or "No"
- Save button to insert/update record
- Cancel button to discard changes
- Delete option for existing entries

### Tab 2: Cocktail Recipe Management

#### View Mode
- Display all cocktail entries in a table/card format
- Key columns: Cocktail_Name, Base_spirit_1, Brand1, Rating_overall, Difficulty, Prep_Time
- Expandable rows to show full details (Ingredients, Notes, etc.)
- Sortable by rating, difficulty, prep time
- Search/filter by name, base spirit, brand
- Pagination for large datasets (103 current records)

#### Add/Edit Mode
- Form with all 17 fields from cocktail_notes table
- Required fields: Cocktail_Name, Ingredients
- Optional fields: All others
- Auto-populate DatetimeAdded with current timestamp for new entries
- Validation:
  - Ratings must be numeric
  - Prep_Time must be numeric
  - Difficulty must be 1-5
- Save button to insert/update record
- Cancel button to discard changes
- Delete option for existing entries

## Technical Requirements

### Technology Stack
- **Selected**: Python with PyQt5 (desktop app)
  - Modern, professional UI framework
  - Cross-platform compatibility
  - Rich widget set for tables, forms, and dialogs
  - Compatible with Python 3.7+
  - Requires pip install: `pip install PyQt5`

### Database Connection
- SQLite database: `cocktail_database.db`
- Use Python `sqlite3` module
- Connection pooling for performance
- Error handling for database operations

### UI Layout
- Tabbed interface with 2 main tabs
- Tab 1: "Alcohol Inventory"
- Tab 2: "Cocktail Recipes"
- Each tab has View and Add/Edit modes
- Responsive design

## Non-Functional Requirements
- Fast query response (< 1 second for typical operations)
- Data persistence (SQLite)
- User-friendly interface
- Input validation
- Error handling and user feedback

## Future Enhancements
- Export data to CSV
- Import data from CSV
- Cocktail search based on available ingredients
- Rating trends over time
- Print-friendly recipe cards
