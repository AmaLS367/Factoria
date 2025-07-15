#!/bin/bash
echo -e "\033]0;Parts Info Collector - Первый запуск (авторизация Gemini)\007"

echo "   FIRST START - НАСТРОЙКА ПРОЕКТА"

# Проверка Python
python3 --version >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[ERROR] Python не найден. Установите Python 3.9 или выше."
    read -p "Нажмите Enter для продолжения..."
    exit 1
fi

# Установка зависимостей
echo "[INFO] Установка зависимостей..."
pip install -r requirements.txt

# Установка Playwright
echo "[INFO] Установка Playwright..."
playwright install

# Запуск авторизации
echo "[INFO] Открываю браузер для входа в Gemini..."
python3 auth_gemini.py

echo
echo "[INFO] Всё готово. Теперь можно запускать start.sh"
read -p "Нажмите Enter для продолжения..."