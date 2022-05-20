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
LOAD_SHEET_ID = os.getenv("LOAD_SHEET_ID")
SHEET_CREDENTIALS_PATH = os.getenv("SHEET_CREDENTIALS_PATH")

RESOURCE_SHEET_RANGE = 'Resource'
QUESTIONS_SHEET_RANGE = 'Questions'
INFO_SHEET_RANGE = 'Info'
FAQ_SHEET_RANGE = 'FAQ'

ADMINS_ONLINE = []

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# main states
MAIN_MENU, DONE_SUBCONV = range(2)

ids = []
substate_data = {}
resource = {}
markup = None

def start(update: Update, context: CallbackContext) -> int:
    """Start the conversation and ask user for input."""
    logger.info(">> func start")

    update.message.reply_text(resource['hello'], reply_markup=markup)
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
            reply_markup=markup)
    return MAIN_MENU

def ask_for_help_start(update: Update, context: CallbackContext) -> int:
    """The user wants to ask for help. Child conversation gathers all necessary info"""
    logger.info(">> func ask_for_help_start")

    update.message.reply_text(resource['give_info'])
    context.user_data['substate'] = ids[0]
    write_substate_text(context.user_data['substate'], update, context)
    return context.user_data['substate']

def get_information(update: Update, context: CallbackContext) -> int:
    logger.info(">> func get_information")
    data = read_spreadsheet(LOAD_SHEET_ID, INFO_SHEET_RANGE)
    text = resource['info'] + ".\n"
    for elem in data:
        text += elem[1] + "\n"

    update.message.reply_text(text, reply_markup=markup, parse_mode='html')
    return MAIN_MENU

def faq(update: Update, context: CallbackContext) -> int:
    logger.info(">> func faq")
    data = read_spreadsheet(LOAD_SHEET_ID, FAQ_SHEET_RANGE)
    text = resource['faq'] + ".\n"
    for elem in data[1:]:
        text += f"/{elem[0]} - {elem[1]}\n"

    update.message.reply_text(text, reply_markup=markup, parse_mode='html')
    return MAIN_MENU

def get_faq_commands(faqs):
    commands = [ CommandHandler('test', get_information) ]
    for elem in faqs[1:]:
        text = elem[2]
        def handler(update: Update, context: CallbackContext, text=text) -> int:
            update.message.reply_text(text, reply_markup=markup, parse_mode='html')
            return MAIN_MENU

        commands.append(CommandHandler(elem[0], handler))
    return commands

def write_substate_text(substate: int, update: Update, context: CallbackContext):
    text = substate_data[substate]['text']
    update.message.reply_text(text, reply_markup=substate_data[substate]['markup'])

def handle_reply(update: Update, context: CallbackContext) -> int:
    logger.info(">> func handle_reply {}".format(context.user_data['substate']))

    if update.message.text == resource['back']:
        context.user_data['substate'] = ids[-1]
        update.message.reply_text(resource['back_msg'],
                                  reply_markup=substate_data[context.user_data['substate']]['markup'])
        return DONE_SUBCONV

    if "qa" not in context.user_data:
        context.user_data['qa'] = {}
    
    context.user_data['qa'][substate_data[context.user_data['substate']]['text']] = update.message.text

    context.user_data['substate'] += 1
    write_substate_text(context.user_data['substate'], update, context)

    if context.user_data['substate'] < ids[-1]:
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
        'telegram_user' : f"https://t.me/{chat['username']}" if chat['username'] else "None",
        'time'          : datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    values.update(context.user_data['qa'])

    store_in_spreadsheet(STORE_SHEET_ID, values)
    inform_admins(update)
    return DONE_SUBCONV

def inform_admins(update: Update):
    logger.info(">> func inform_admins")
    for admin_id in ADMINS_ONLINE:
        update.message.bot.send_message(chat_id=admin_id, text="New request for help was added.")

def get_ids(questions, start):
    ids = []
    for question in questions:
        ids.append(start)
        start = start + 1
    return ids

def get_states(questions, ids):
    reply_keyboard = [[resource['back']]]
    back_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

    states = {}
    for index, id in enumerate(ids):
        states[id] = {
            "text": questions[index][0],
            "markup": back_markup if index < len(ids) - 1 else markup
        }
    return states

def dict_to_cell(map):
    values = [[], []]
    for k,v in map.items():
        values[0].append(k)
        values[1].append(v)
    return values

def get_sheet_service():
    creds = service_account.Credentials.from_service_account_file(os.path.expanduser(SHEET_CREDENTIALS_PATH))
    service = build('sheets', 'v4', credentials=creds)
    return service

def read_spreadsheet(spreadsheet_id, range_name='Sheet1'):
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

'''
Issue 1: If there is an empty row in the middle of the spreadsheet, new values are added starting from that empty row (might override what is in the next rows).
'''
def store_in_spreadsheet(spreadsheet_id, values, range_name='Sheet1'):
    logger.info(">> func store_in_spreadsheet")
    try:
        service = get_sheet_service()
        body = {
            'values': dict_to_cell(values)
        }
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption="USER_ENTERED", body=body).execute()

        logger.info(f"{(result.get('updates').get('updatedCells'))} cells appended.")
        return result

    except HttpError as error:
        print(f"An error occurred: {error}")
        return error

def done(update: Update, context: CallbackContext) -> int:
    """Display the gathered info and end the conversation."""
    logger.info(">> func done")
    
    return ConversationHandler.END

def back(update: Update, context: CallbackContext) -> int:
    logger.info(">> func back")
    return DONE_SUBCONV

def main() -> None:
    """Run the bot."""

    global resource
    cells = read_spreadsheet(LOAD_SHEET_ID, RESOURCE_SHEET_RANGE)
    resource = { cell[0] : cell[1] for cell in cells }
    logger.info(resource)

    reply_keyboard = [
        [resource['ask_help'], resource['faq'], resource['info']],
        [resource['done']],
    ]
    global markup
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

    questions = read_spreadsheet(LOAD_SHEET_ID, QUESTIONS_SHEET_RANGE)
    global ids
    ids = get_ids(questions, 2)
    logger.info(ids)

    global substate_data
    substate_data = get_states(questions, ids)
    logger.info(substate_data)

    # Create the Updater and pass it your bot's token.
    updater = Updater(token=TELEGRAM_API_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    ask_for_help_conv = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.regex(f"^{resource['ask_help']}$"), ask_for_help_start),
        ],
        states = { id : [ MessageHandler(Filters.text, handle_reply) ] for id in ids },
        fallbacks=[MessageHandler(Filters.text, ask_for_help_finish)],
        map_to_parent={
            DONE_SUBCONV: MAIN_MENU
        }
    )

    faqs = read_spreadsheet(LOAD_SHEET_ID, FAQ_SHEET_RANGE)
    faq_commands = get_faq_commands(faqs)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [
                ask_for_help_conv,
                MessageHandler(Filters.regex(f"^{resource['info']}$"), get_information),
                MessageHandler(Filters.regex(f"^{resource['faq']}$"), faq),
                CommandHandler('admin', register_admin),
                *faq_commands
            ],
        },
        fallbacks=[MessageHandler(Filters.regex(f"^{resource['done']}$"), done)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
