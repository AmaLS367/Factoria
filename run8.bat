@echo off
chcp 65001 >nul
title Parts Info Collector - Автоматический сбор данных

echo  PARTS INFO COLLECTOR - ЗАПУСК

:: Проверка Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python не найден. Установите Python 3.9 или выше.
    pause
    exit /b
)

:: Запуск основного скрипта
echo [INFO] Запуск main.py...
python main.py --profile user-data-8

echo.
echo [DONE] Обработка завершена. Результат: results\output.xlsx
pause
