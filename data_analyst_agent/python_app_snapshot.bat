@echo off
setlocal enabledelayedexpansion

:: Python Project Snapshot Script
:: Creates a comprehensive snapshot of your Python project
echo ========================================
echo Python Project Snapshot Generator
echo ========================================
echo.

:: Create snapshot directory with timestamp
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%-%MM%-%DD%_%HH%-%Min%-%Sec%"

set "snapshot_dir=python_snapshot_%timestamp%"
mkdir "%snapshot_dir%"

echo Creating snapshot in: %snapshot_dir%
echo.

:: Create main snapshot file
set "snapshot_file=%snapshot_dir%\project_snapshot.txt"

echo Python Project Snapshot > "%snapshot_file%"
echo Generated on: %date% %time% >> "%snapshot_file%"
echo Directory: %cd% >> "%snapshot_file%"
echo ======================================== >> "%snapshot_file%"
echo. >> "%snapshot_file%"

:: 1. System Information
echo [1/10] Gathering system information...
echo SYSTEM INFORMATION >> "%snapshot_file%"
echo ================== >> "%snapshot_file%"
systeminfo | findstr /C:"OS Name" /C:"OS Version" /C:"System Type" /C:"Total Physical Memory" >> "%snapshot_file%"
echo. >> "%snapshot_file%"

:: 2. Python Interpreter Information
echo [2/10] Capturing Python interpreter details...
echo PYTHON INTERPRETER >> "%snapshot_file%"
echo ================== >> "%snapshot_file%"
python --version >> "%snapshot_file%" 2>&1
echo Python executable location: >> "%snapshot_file%"
where python >> "%snapshot_file%" 2>&1
echo. >> "%snapshot_file%"

echo Python configuration: >> "%snapshot_file%"
python -c "import sys; print('Python version:', sys.version)" >> "%snapshot_file%" 2>&1
python -c "import sys; print('Python executable:', sys.executable)" >> "%snapshot_file%" 2>&1
python -c "import sys; print('Python path:', sys.path)" >> "%snapshot_file%" 2>&1
python -c "import platform; print('Platform:', platform.platform())" >> "%snapshot_file%" 2>&1
echo. >> "%snapshot_file%"

:: 3. Virtual Environment Information
echo [3/10] Checking virtual environment...
echo VIRTUAL ENVIRONMENT >> "%snapshot_file%"
echo =================== >> "%snapshot_file%"
if defined VIRTUAL_ENV (
    echo Virtual Environment: %VIRTUAL_ENV% >> "%snapshot_file%"
) else (
    echo No virtual environment detected >> "%snapshot_file%"
)

if defined CONDA_DEFAULT_ENV (
    echo Conda Environment: %CONDA_DEFAULT_ENV% >> "%snapshot_file%"
    conda info --envs >> "%snapshot_file%" 2>&1
)
echo. >> "%snapshot_file%"

:: 4. Installed Packages
echo [4/10] Listing installed packages...
echo INSTALLED PACKAGES >> "%snapshot_file%"
echo ================== >> "%snapshot_file%"
pip list >> "%snapshot_file%" 2>&1
echo. >> "%snapshot_file%"

echo INSTALLED PACKAGES (DETAILED) >> "%snapshot_file%"
echo ============================== >> "%snapshot_file%"
pip list --verbose >> "%snapshot_file%" 2>&1
echo. >> "%snapshot_file%"

:: 5. Requirements and Dependencies
echo [5/10] Capturing requirements and dependencies...
echo REQUIREMENTS >> "%snapshot_file%"
echo ============ >> "%snapshot_file%"

:: Check if requirements.txt exists
if exist requirements.txt (
    echo Found requirements.txt: >> "%snapshot_file%"
    type requirements.txt >> "%snapshot_file%"
    copy requirements.txt "%snapshot_dir%\" >nul
) else (
    echo No requirements.txt found >> "%snapshot_file%"
    echo Generating requirements from current environment: >> "%snapshot_file%"
    pip freeze > "%snapshot_dir%\generated_requirements.txt"
    type "%snapshot_dir%\generated_requirements.txt" >> "%snapshot_file%"
)
echo. >> "%snapshot_file%"

:: 6. Dependency Tree
echo [6/10] Generating dependency tree...
echo DEPENDENCY TREE >> "%snapshot_file%"
echo =============== >> "%snapshot_file%"
pip show --verbose pip >> "%snapshot_file%" 2>&1
echo. >> "%snapshot_file%"

:: Try to use pipdeptree if available
pip show pipdeptree >nul 2>&1
if %errorlevel% equ 0 (
    echo Detailed dependency tree: >> "%snapshot_file%"
    pipdeptree >> "%snapshot_file%" 2>&1
) else (
    echo pipdeptree not installed, installing temporarily... >> "%snapshot_file%"
    pip install pipdeptree >nul 2>&1
    if %errorlevel% equ 0 (
        pipdeptree >> "%snapshot_file%" 2>&1
        pipdeptree --json > "%snapshot_dir%\dependency_tree.json"
    ) else (
        echo Could not install pipdeptree >> "%snapshot_file%"
    )
)
echo. >> "%snapshot_file%"

:: 7. Project Structure
echo [7/10] Mapping project structure...
echo PROJECT STRUCTURE >> "%snapshot_file%"
echo ================= >> "%snapshot_file%"
tree /F /A >> "%snapshot_file%" 2>&1
echo. >> "%snapshot_file%"

:: 8. Python Files Analysis
echo [8/10] Analyzing Python files...
echo PYTHON FILES ANALYSIS >> "%snapshot_file%"
echo ===================== >> "%snapshot_file%"
echo Python files in project: >> "%snapshot_file%"
dir /S *.py >> "%snapshot_file%" 2>&1
echo. >> "%snapshot_file%"

:: 9. Configuration Files
echo [9/10] Capturing configuration files...
echo CONFIGURATION FILES >> "%snapshot_file%"
echo =================== >> "%snapshot_file%"

:: Common config files to capture
set "config_files=setup.py setup.cfg pyproject.toml tox.ini pytest.ini .env environment.yml conda.yml Pipfile Pipfile.lock poetry.lock requirements-dev.txt requirements-test.txt"

for %%f in (%config_files%) do (
    if exist "%%f" (
        echo. >> "%snapshot_file%"
        echo Found %%f: >> "%snapshot_file%"
        echo ---------------------------------------- >> "%snapshot_file%"
        type "%%f" >> "%snapshot_file%"
        copy "%%f" "%snapshot_dir%\" >nul
    )
)
echo. >> "%snapshot_file%"

:: 10. Additional Information
echo [10/10] Gathering additional information...
echo ADDITIONAL INFORMATION >> "%snapshot_file%"
echo ====================== >> "%snapshot_file%"

:: Git information (if available)
if exist .git (
    echo Git repository information: >> "%snapshot_file%"
    git --version >> "%snapshot_file%" 2>&1
    git status >> "%snapshot_file%" 2>&1
    git log --oneline -10 >> "%snapshot_file%" 2>&1
    git remote -v >> "%snapshot_file%" 2>&1
) else (
    echo No Git repository found >> "%snapshot_file%"
)
echo. >> "%snapshot_file%"

:: Environment variables related to Python
echo Python-related environment variables: >> "%snapshot_file%"
set | findstr /I python >> "%snapshot_file%"
set | findstr /I conda >> "%snapshot_file%"
set | findstr /I pip >> "%snapshot_file%"
echo. >> "%snapshot_file%"

:: Create a summary file
echo Creating summary files...
set "summary_file=%snapshot_dir%\snapshot_summary.txt"
echo PROJECT SNAPSHOT SUMMARY > "%summary_file%"
echo ======================== >> "%summary_file%"
echo Snapshot created: %date% %time% >> "%summary_file%"
echo Project directory: %cd% >> "%summary_file%"
echo Python version: >> "%summary_file%"
python --version >> "%summary_file%" 2>&1
echo Total Python files: >> "%summary_file%"
for /f %%i in ('dir /S *.py 2^>nul ^| find "File(s)" ^| find /V "Dir(s)"') do echo %%i >> "%summary_file%"
echo. >> "%summary_file%"

:: Create a batch file to recreate environment
echo Creating environment recreation script...
set "recreate_file=%snapshot_dir%\recreate_environment.bat"
echo @echo off > "%recreate_file%"
echo :: Script to recreate Python environment >> "%recreate_file%"
echo :: Generated on %date% %time% >> "%recreate_file%"
echo. >> "%recreate_file%"
echo echo Recreating Python environment... >> "%recreate_file%"
if exist requirements.txt (
    echo pip install -r requirements.txt >> "%recreate_file%"
) else (
    echo pip install -r generated_requirements.txt >> "%recreate_file%"
)
echo echo Environment recreation complete! >> "%recreate_file%"

:: Final summary
echo.
echo ========================================
echo Snapshot creation completed!
echo ========================================
echo Snapshot directory: %snapshot_dir%
echo Main snapshot file: %snapshot_file%
echo Summary file: %summary_file%
echo Recreation script: %recreate_file%
echo.
echo Files included:
echo - project_snapshot.txt (complete project information)
echo - snapshot_summary.txt (quick overview)
echo - recreate_environment.bat (environment recreation script)
if exist requirements.txt (
    echo - requirements.txt (copied from project)
) else (
    echo - generated_requirements.txt (generated from current environment)
)
if exist "%snapshot_dir%\dependency_tree.json" (
    echo - dependency_tree.json (detailed dependency information)
)
echo.
echo You can now archive the '%snapshot_dir%' folder to preserve
echo your complete Python project snapshot.
echo.
pause