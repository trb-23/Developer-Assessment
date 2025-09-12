@echo off
python3 -m venv venv
call venv\Scripts\activate.bat
python3 -m pip install --upgrade pip
pip install -r requirements.txt
python3 main.py
pause