[Setup]
AppName=Cocktail Database Manager
AppVersion=1.0
DefaultDirName={autopf}\CocktailDatabase
DefaultGroupName=Cocktail Database Manager
OutputBaseFilename=CocktailDatabaseInstaller
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\CocktailDatabase.exe

[Files]
Source: "dist\CocktailDatabase.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "cocktail_database.db"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "alcohol_favorites.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "cocktail_favorites.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "images\*"; DestDir: "{app}\images"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Cocktail Database Manager"; Filename: "{app}\CocktailDatabase.exe"
Name: "{group}\Uninstall Cocktail Database Manager"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Cocktail Database Manager"; Filename: "{app}\CocktailDatabase.exe"

[Run]
Filename: "{app}\CocktailDatabase.exe"; Description: "Launch Cocktail Database Manager"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\images"
