@echo off
chcp 65001
cd %~dp0
venv\Scripts\activate
python app.py
pause
