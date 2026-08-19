@echo off
set JAVA_HOME=C:\Program Files\Microsoft\jdk-17.0.20.8-hotspot
set ANDROID_HOME=D:\AndroidSdk
set ANDROID_SDK_ROOT=D:\AndroidSdk
set GRADLE_USER_HOME=D:\gradle-home
cd /d "%~dp0"
python make_icons.py
python android\copy_web.py
python android\make_launcher_icons.py
cd android
call gradlew.bat assembleRelease --no-daemon
if errorlevel 1 exit /b 1
copy /Y app\build\outputs\apk\release\app-release.apk "%~dp0GitVidX.apk"
echo.
echo Built: %~dp0GitVidX.apk
