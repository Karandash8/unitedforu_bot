# COMMON SETUP
```
echo 'API_TOKEN="<YOUR_TOKEN>"' >> .env
export $(grep -v '^#' .env | xargs)
```

# RUNNING INSIDE A CONTAINER
## BUILD 
```
make build
```
## RUN
```
make run
```

# RUNNING WITHOUT CONTAINERS
## SETUP
```
python3 -m venv venv
. venv/bin/activate
pip install python-telegram-bot
```
## RUN
```
python bot-unitedforu/main.py
```
