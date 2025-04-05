#!/bin/bash

# Константи

# !!! УВАГА: Залиш bot_service_name порожнім (""), якщо при оновленні
# !!! репозиторію НЕ ТРЕБА перезапускати сервіс systemd.
bot_service_name=""
bot_repository_link="https://github.com/jjhjahd69/bezvitryanyj.git"
start_file="main.py"

handle_error() {
  local exit_code=$?
  echo "Cталася помилка в рядку $1 з кодом $exit_code"
  exit $exit_code
}

trap 'handle_error $LINENO' ERR

if [ -f "$start_file" ]; then
    echo 'Стартовий файл існує, у клонуванні репозиторію немає потреби.'
else
    echo 'Починаю копіювання репозиторію'

    echo "Оновлення коду з git..."
    git clone "$bot_repository_link"
    echo 'Репозиторій копійований'

    echo 'Відбувається вихід з скрипту, подальші дії непотрібні.'
    echo "Видалення цього скрипта запуску ('$0')..."
    rm "$0"
    exit
fi

if [ -n "$bot_service_name" ]; then
    echo "Зупинка сервісу '$bot_service_name'..."
    sudo systemctl stop "$bot_service_name"

    echo "Оновлення коду з git..."
    git pull 

    echo "Запуск сервісу '$bot_service_name'..."
    sudo systemctl start "$bot_service_name"

else
    echo "Оновлення коду з git (без перезапуску сервісу)..."
    git pull
fi

echo "Скрипт успішно завершив роботу."
exit 0