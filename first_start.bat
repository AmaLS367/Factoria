@echo off
chcp 65001 >nul
title Parts Info Collector - Первый запуск (авторизация Gemini)

echo   FIRST START - НАСТРОЙКА ПРОЕКТА

:: Проверка Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python не найден. Установите Python 3.9 или выше.
    pause
    exit /b
)

:: Установка зависимостей
echo [INFO] Установка зависимостей...
pip install -r requirements.txt

:: Установка Playwright
echo [INFO] Установка Playwright...
playwright install

:: Запуск авторизации
echo [INFO] Открываю браузер для входа в Gemini...
python auth_gemini.py

echo.
echo [INFO] Всё готово. Теперь можно запускать start.bat
pause
