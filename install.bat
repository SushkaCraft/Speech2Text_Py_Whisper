@echo off
chcp 65001
echo Создание виртуального окружения и его настройка...
python -m venv venv

call venv\Scripts\activate

pip install vosk flask sounddevice

echo Установка завершена.
echo Для запуска приложения выполните start.bat
pause
