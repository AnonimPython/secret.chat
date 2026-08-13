@echo off
rem ============================================================================
rem  build_windows.bat — запасная сборка SecretChat.exe через PyInstaller
rem  build_windows.bat — fallback build of SecretChat.exe with PyInstaller
rem ============================================================================
rem  зачем запасной вариант: основной способ — Nuitka (build_windows_nuitka.bat),
rem  он компилирует в нативный код и меньше триггерит антивирусы. PyInstaller
rem  оставлен как запасной, если Nuitka не установится или не соберётся.
rem  why a fallback: the main way is Nuitka (build_windows_nuitka.bat), which
rem  compiles into native code and triggers fewer antiviruses. PyInstaller is
rem  kept as a fallback when Nuitka cannot be installed or built.
rem
rem  требования: Python 3.10+ в PATH (компилятор не нужен — PyInstaller упаковывает)
rem
rem  использование: build_windows.bat
rem  результат:     dist\SecretChat.exe  (один файл, без консоли)

setlocal
if not exist .venv-build python -m venv .venv-build
.venv-build\Scripts\python.exe -m pip install --upgrade pip
.venv-build\Scripts\python.exe -m pip install -r requirements.txt
.venv-build\Scripts\python.exe -m pip install pyinstaller
.venv-build\Scripts\python.exe -m PyInstaller --clean --noconfirm secretchat.spec
if exist dist\SecretChat.exe (
    echo [OK] done: dist\SecretChat.exe
) else (
    echo [!] build finished, look for the exe inside dist\
)
endlocal
