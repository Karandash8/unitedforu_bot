import os
import logging
from datetime import datetime
from typing import Dict

from telegram import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
TELEGRAM_LIST_OF_ADMIN_IDS = os.getenv("TELEGRAM_LIST_OF_ADMIN_IDS")
STORE_SHEET_ID = os.getenv("STORE_SHEET_ID")
STORE_SHEET_RANGE = os.getenv("STORE_SHEET_RANGE")
INFO_SHEET_ID = os.getenv("INFO_SHEET_ID")
FAQ_SHEET_ID = os.getenv("FAQ_SHEET_ID")
SHEET_CREDENTIALS_PATH = os.getenv("SHEET_CREDENTIALS_PATH")

ADMINS_ONLINE = []

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

reply_keyboard = [
    ['Ask for help', 'Get information', 'FAQ'],
    ['Done'],
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

# main states
MAIN_MENU = range(3)

# ASK_FOR_HELP substates
GETTING_LOCATION, GETTING_NUMBER_OF_PEOPLE, GETTING_BELONGINGS, FINISHING_SUBCONV, DONE_SUBCONV = range(3, 8)
substate_data = {
    GETTING_LOCATION: {
        "text": "Where are you?",
        "markup": None,
    },
    GETTING_NUMBER_OF_PEOPLE: {
        "text": "How many are you?",
        "markup": None,
    },
    GETTING_BELONGINGS: {
        "text": "Do you have necessary clothes with you?",
        "markup": None,
    },
    FINISHING_SUBCONV: {
        "text": "Thank you for the information",
        "markup": markup,
    },
}

def start(update: Update, context: CallbackContext) -> int:
    """Start the conversation and ask user for input."""
    logger.info(">> func start")

    update.message.reply_text(
        "Hi! I am UnitedForU bot. How can I help?",
        reply_markup=markup,
    )

    return MAIN_MENU

def register_admin(update: Update, context: CallbackContext) -> int:
    logger.info(">> func register_admin")

    list_of_admin_ids = TELEGRAM_LIST_OF_ADMIN_IDS.split(',') if TELEGRAM_LIST_OF_ADMIN_IDS else []
    list_of_admin_ids = map(int, list_of_admin_ids)
    user_id = update.effective_user.id

    if user_id in list_of_admin_ids:
        ADMINS_ONLINE.append(user_id)

        update.message.reply_text(
            "You logged in as an admin.",
            reply_markup=markup,
    )

    return MAIN_MENU

def ask_for_help_start(update: Update, context: CallbackContext) -> int:
    """The user wants to ask for help. Child conversation gathers all necessary info"""
    logger.info(">> func ask_for_help_start")

    text = 'Please give us some information.'
    update.message.reply_text(text)

    context.user_data['substate'] = GETTING_LOCATION
    write_substate_text(context.user_data['substate'], update, context)

    return context.user_data['substate']

def get_information(update: Update, context: CallbackContext) -> int:
    logger.info(">> func get_information")
    data = read_spreadsheet(INFO_SHEET_ID, 'Sheet1')
    text = "Information.\n"
    for elem in data[1:]:
        text += elem[1] + "\n"

    update.message.reply_text(text, reply_markup=markup)
    return MAIN_MENU

def faq(update: Update, context: CallbackContext) -> int:
    logger.info(">> func faq")
    data = read_spreadsheet(FAQ_SHEET_ID, 'Sheet1')
    text = "FAQ.\n"
    for elem in data[1:]:
        text += elem[1] + "\n"

    update.message.reply_text(text, reply_markup=markup)
    return MAIN_MENU

def write_substate_text(substate: int, update: Update, context: CallbackContext):
    text = substate_data[context.user_data['substate']]['text']
    update.message.reply_text(text, reply_markup=substate_data[context.user_data['substate']]['markup'])

def handle_reply(update: Update, context: CallbackContext) -> int:
    logger.info(">> func handle_reply {}".format(context.user_data['substate']))

    if "qa" not in context.user_data:
        context.user_data['qa'] = {}
    
    context.user_data['qa'][substate_data[context.user_data['substate']]['text']] = update.message.text

    context.user_data['substate'] += 1
    write_substate_text(context.user_data['substate'], update, context)

    if context.user_data['substate'] < FINISHING_SUBCONV:
        return context.user_data['substate']
    else: 
        return ask_for_help_finish(update, context)

def ask_for_help_finish(update: Update, context: CallbackContext) -> int:
    logger.info(">> func ask_for_help_finish")

    chat = update['message']['chat']
    values = {
        'first_name'    : chat['first_name'],
        'last_name'     : chat['last_name'],
        'telegram_id'   : chat['id'],
        'time'          : datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    values.update(context.user_data['qa'])

    store_in_spreadsheet(STORE_SHEET_ID, STORE_SHEET_RANGE, values)
    inform_admins(update)

    return DONE_SUBCONV

def inform_admins(update: Update):
    logger.info(">> func inform_admins")
    for admin_id in ADMINS_ONLINE:
        update.message.bot.send_message(chat_id=admin_id, text="New request for help was added.")

def dict_to_cells(map):
    values = [[], []]
    for k,v in map.items():
        values[0].append(k)
        values[1].append(v)
    return values

def get_sheet_service():
    creds = service_account.Credentials.from_service_account_file(os.path.expanduser(SHEET_CREDENTIALS_PATH))
    service = build('sheets', 'v4', credentials=creds)
    return service

'''
Issue 1: range_name doesn't seem to make any effect if set incorrectly. New values are always appended starting from the first empty row.
Issue 2: If there is an empty row in the middle of the spreadsheet, new values are added starting from that empty row (might override what is in the next rows).
'''
def store_in_spreadsheet(spreadsheet_id, range_name, values):
    logger.info(">> func store_in_spreadsheet")
    try:
        service = get_sheet_service()
        body = {
            'values': dict_to_cells(_values)
        }
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption="USER_ENTERED", body=body).execute()

        logger.info(f"{(result.get('updates').get('updatedCells'))} cells appended.")
        return result

    except HttpError as error:
        print(f"An error occurred: {error}")
        return error

def read_spreadsheet(spreadsheet_id, range_name):
    logger.info(">> func read_spreadsheet")
    try:
        service = get_sheet_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])
        return values

    except HttpError as error:
        print(f"An error occurred: {error}")
        return {}

def done(update: Update, context: CallbackContext) -> int:
    """Display the gathered info and end the conversation."""
    logger.info(">> func done")
    
    return ConversationHandler.END

def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(token=TELEGRAM_API_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    ask_for_help_conv = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.regex('^Ask for help$'), ask_for_help_start),
        ],
        states={
            GETTING_LOCATION: [
                MessageHandler(Filters.text, handle_reply)
            ],
            GETTING_NUMBER_OF_PEOPLE: [
                MessageHandler(Filters.text, handle_reply)
            ],
            GETTING_BELONGINGS: [
                MessageHandler(Filters.text, handle_reply),
            ],
        },
        fallbacks=[MessageHandler(Filters.text, ask_for_help_finish)],
        map_to_parent={
            DONE_SUBCONV: MAIN_MENU
        }
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [
                ask_for_help_conv,
                MessageHandler(Filters.regex('^Get information$'), get_information),
                MessageHandler(Filters.regex('^FAQ$'), faq),
                CommandHandler('admin', register_admin),
            ],
        },
        fallbacks=[MessageHandler(Filters.regex('^Done$'), done)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
