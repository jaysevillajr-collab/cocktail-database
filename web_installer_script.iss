[Setup]
AppName=Cocktail Database Web App
AppVersion=1.0
DefaultDirName={autopf}\CocktailDatabaseWeb
DefaultGroupName=Cocktail Database Web App
OutputDir=Output
OutputBaseFilename=CocktailDatabaseWebInstaller
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Files]
Source: "web\backend\dist\CocktailWebBackend.exe"; DestDir: "{app}\web\backend"; Flags: ignoreversion
Source: "web\launch_web_app.ps1"; DestDir: "{app}\web"; Flags: ignoreversion
Source: "web\stop_web_app.ps1"; DestDir: "{app}\web"; Flags: ignoreversion
Source: "web\Launch Web App.cmd"; DestDir: "{app}\web"; Flags: ignoreversion
Source: "web\Stop Web App.cmd"; DestDir: "{app}\web"; Flags: ignoreversion
Source: "web\frontend\dist\*"; DestDir: "{app}\web\frontend\dist"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "cocktail_database.db"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "images\*"; DestDir: "{app}\images"; Flags: ignoreversion onlyifdoesntexist recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Launch Cocktail Database Web App"; Filename: "{app}\web\Launch Web App.cmd"
Name: "{group}\Stop Cocktail Database Web App"; Filename: "{app}\web\Stop Web App.cmd"
Name: "{autodesktop}\Cocktail Database Web App"; Filename: "{app}\web\Launch Web App.cmd"

[Run]
Filename: "{app}\web\Launch Web App.cmd"; Description: "Launch Cocktail Database Web App"; Flags: nowait postinstall skipifsilent
