@echo off
setlocal
rem yayinla.bat - tek komutla guncelleme yayinla (Windows makinede calisir).
rem
rem   yayinla.bat "Cevrimdisina dusme duzeltildi"
rem
rem Sirasiyla: git pull -> C++ motor -> PyInstaller -> sunucuya yayin.
rem Yonetici anahtari ve imza anahtari ..\ReleaseSystem\backend\ altinda
rem oldugu icin yalnizca bu makineden yayinlanabilir; Mac'te calismaz.

cd /d "%~dp0"

set "NOTES=%~1"
if "%NOTES%"=="" set "NOTES=Hata duzeltmeleri"

if not exist "..\ReleaseSystem\backend\.env" (
    echo HATA: ..\ReleaseSystem\backend\.env yok. Yonetici anahtari bu dosyadan okunur.
    exit /b 1
)

echo [1/4] Depo guncelleniyor...
git pull --ff-only
if errorlevel 1 ( echo HATA: git pull basarisiz. & exit /b 1 )

echo [2/4] C++ planlama motoru...
python tools\build_scheduler.py
if errorlevel 1 ( echo HATA: motor derlenemedi. & exit /b 1 )

echo [3/4] Paket (PyInstaller)...
pyinstaller Chenkron.spec --noconfirm
if errorlevel 1 ( echo HATA: PyInstaller basarisiz. & exit /b 1 )

echo [4/4] Sunucuya yayin...
python publish_update.py --notes "%NOTES%"
if errorlevel 1 ( echo HATA: yayin basarisiz. & exit /b 1 )

echo.
echo Yayin tamam. Durum:
python publish_update.py --status
endlocal
