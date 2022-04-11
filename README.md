# SETUP
```
python3 -m venv venv
. venv/bin/activate
pip install python-telegram-bot
echo 'API_TOKEN="<YOUR_TOKEN>"' >> .env
export $(grep -v '^#' .env | xargs)
```
# RUN
```
python bot-unitedforu/main.py
```