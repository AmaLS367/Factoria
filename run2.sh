#!/bin/bash
echo -e "\033]0;Parts Info Collector - Автоматический сбор данных\007"

echo "   PARTS INFO COLLECTOR - ЗАПУСК"

# Проверка Python
python3 --version >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[ERROR] Python не найден. Установите Python 3.9 или выше."
    read -p "Нажмите Enter для продолжения..."
    exit 1
fi

# Запуск основного скрипта
echo "[INFO] Запуск main.py..."
python3 main.py --profile user-data-2

echo
echo "[DONE] Обработка завершена. Результат: results/output.xlsx"
read -p "Нажмите Enter для продолжения..."