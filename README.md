# COMMON SETUP
Follow https://developers.google.com/workspace/guides/get-started and save your service_account credentials in .service_account.json
```
cp .service_account.json ~/.service_account.json
echo 'TELEGRAM_API_TOKEN="<YOUR_TOKEN>"' > .env
echo 'TELEGRAM_LIST_OF_ADMIN_IDS="<COMMA_SEPARATED_LIST_OF_TELEGRAM_USER_IDS>"' >> .env
echo 'GOOGLE_SPREADSHEET_ID="<YOUR_SPREADSHEET_ID>"' >> .env
echo 'GOOGLE_RANGE_NAME="A1:C2"' >> .env
echo 'GOOGLE_APPLICATION_CREDENTIALS_PATH="~/.service_account.json"' >> .env
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

## DEBUG mode
During development, *build & run* might be an overkill to do on every code change. In order to avoid rebuilding the image every time, there is a Makefile target to mount  mount local bot folder inside the container.
```
make debug && docker container logs unitedforu-bot -f
```

# RUNNING WITHOUT CONTAINERS
## SETUP
```
python3 -m venv venv
. venv/bin/activate
pip install python-telegram-bot
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```
## RUN
```
python bot-unitedforu/main.py
```
