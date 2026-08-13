@echo off
rem ============================================================================
rem  build_windows_nuitka.bat — сборка SecretChat.exe через Nuitka
rem  build_windows_nuitka.bat — build SecretChat.exe with Nuitka
rem ============================================================================
rem  зачем: Nuitka компилирует Python в нативный код, без распаковки в temp
rem  и без UPX — такие exe антивирусы помечают заметно реже, чем PyInstaller.
rem  why: Nuitka compiles Python into native code, no temp extraction and no
rem  UPX — antiviruses flag such exes far less often than PyInstaller ones.
rem
rem  требования (requirements):
rem    • Python 3.10+ в PATH
rem    • компилятор C на выбор:
rem         - Visual Studio Build Tools (рекомендуется)
rem           https://visualstudio.microsoft.com/ru/downloads/ -> Build Tools
rem           поставь компонент «Средства сборки C++» / MSVC
rem         - либо MinGW-w64, тогда собери так:
rem           build_windows_nuitka.bat mingw
rem
rem  использование (usage):
rem    build_windows_nuitka.bat            -> dist\SecretChat\SecretChat.exe (папка, меньше всего AV)
rem    build_windows_nuitka.bat onefile    -> dist\SecretChat.exe (один файл)
rem    build_windows_nuitka.bat mingw      -> собрать через MinGW вместо MSVC
rem
rem  результат:
rem    - standalone: dist\SecretChat\SecretChat.exe
rem    - onefile:    dist\SecretChat.exe

setlocal

set MODE=standalone
set EXTRA=
if /i "%1"=="onefile" set MODE=onefile
if /i "%1"=="mingw" set EXTRA=--mingw64

echo [*] creating/updating build venv...
if not exist .venv-build python -m venv .venv-build
.venv-build\Scripts\python.exe -m pip install --upgrade pip
.venv-build\Scripts\python.exe -m pip install -r requirements.txt
.venv-build\Scripts\python.exe -m pip install nuitka zstandard

echo [*] building (%MODE%)...
if "%MODE%"=="onefile" (
    .venv-build\Scripts\python.exe -m nuitka ^
        --onefile ^
        --enable-plugin=pyside6 ^
        --include-qt-plugins=all ^
        --include-package=cryptography ^
        --include-package-data=cryptography ^
        --nofollow-import-to=tkinter ^
        --windows-console-mode=disable ^
        --output-dir=dist_nuitka ^
        --output-filename=SecretChat ^
        --company-name="SecretChat" ^
        --product-name="SecretChat" ^
        --file-version=1.0.0 ^
        --product-version=1.0.0 ^
        --assume-yes-for-downloads ^
        %EXTRA% ^
        main.py
    if exist dist_nuitka\SecretChat.exe (
        if not exist dist mkdir dist
        copy /y dist_nuitka\SecretChat.exe dist\SecretChat.exe >nul
        echo [OK] done: dist\SecretChat.exe
    ) else (
        echo [!] build finished, look for the exe inside dist_nuitka\
    )
) else (
    .venv-build\Scripts\python.exe -m nuitka ^
        --standalone ^
        --enable-plugin=pyside6 ^
        --include-qt-plugins=all ^
        --include-package=cryptography ^
        --include-package-data=cryptography ^
        --nofollow-import-to=tkinter ^
        --windows-console-mode=disable ^
        --output-dir=dist_nuitka ^
        --output-filename=SecretChat ^
        --company-name="SecretChat" ^
        --product-name="SecretChat" ^
        --file-version=1.0.0 ^
        --product-version=1.0.0 ^
        --assume-yes-for-downloads ^
        %EXTRA% ^
        main.py
    if exist dist_nuitka\main.dist\SecretChat.exe (
        if not exist dist mkdir dist
        if exist dist\SecretChat rmdir /s /q dist\SecretChat
        move /y dist_nuitka\main.dist dist\SecretChat >nul
        echo [OK] done: dist\SecretChat\SecretChat.exe
    ) else (
        echo [!] build finished, look for the folder inside dist_nuitka\
    )
)

echo.
echo  подсказка: папка (standalone) триггерит антивирусы меньше, чем один файл
echo  tip: a folder (standalone) triggers antiviruses less than a single file
endlocal
