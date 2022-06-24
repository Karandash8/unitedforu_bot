import os
import logging
from datetime import datetime
from typing import Dict

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
    filters
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

async def start(update: Update, context: CallbackContext) -> int:
    """Start the conversation and ask user for input."""
    logger.info(">> func start")

    await update.message.reply_text(resource['hello'], reply_markup=markup)
    return MAIN_MENU

async def register_admin(update: Update, context: CallbackContext) -> int:
    logger.info(">> func register_admin")

    list_of_admin_ids = TELEGRAM_LIST_OF_ADMIN_IDS.split(',') if TELEGRAM_LIST_OF_ADMIN_IDS else []
    list_of_admin_ids = map(int, list_of_admin_ids)
    user_id = update.effective_user.id

    if user_id in list_of_admin_ids:
        ADMINS_ONLINE.append(user_id)
        await update.message.reply_text("You logged in as an admin.", reply_markup=markup)

    return MAIN_MENU

async def ask_for_help_start(update: Update, context: CallbackContext) -> int:
    """The user wants to ask for help. Child conversation gathers all necessary info"""
    logger.info(">> func ask_for_help_start")

    query = update.callback_query
    await query.answer()
    await query.message.reply_text(resource['give_info'], parse_mode='html')
    context.user_data['substate'] = ids[0]

    reply_keyboard = [
        [ InlineKeyboardButton(resource['yes'], callback_data='yes'),
          InlineKeyboardButton(resource['no'], callback_data='no')
        ],
        [ InlineKeyboardButton(resource['back'], callback_data='back') ]
    ]
    yes_no_markup = InlineKeyboardMarkup(reply_keyboard)
    await write_substate_text(context.user_data['substate'], query.message, yes_no_markup)
    return context.user_data['substate']

async def get_information(update: Update, context: CallbackContext) -> int:
    logger.info(">> func get_information")
    data = read_spreadsheet(LOAD_SHEET_ID, INFO_SHEET_RANGE)
    text = resource['info'] + ".\n"
    for elem in data:
        text += elem[1] + "\n"

    query = update.callback_query
    await query.answer()
    await query.message.reply_text(text, reply_markup=markup, parse_mode='html')
    return MAIN_MENU

async def faq(update: Update, context: CallbackContext) -> int:
    logger.info(">> func faq")
    data = read_spreadsheet(LOAD_SHEET_ID, FAQ_SHEET_RANGE)
    text = resource['faq'] + ".\n"
    for elem in data[1:]:
        text += f"/{elem[0]} - {elem[1]}\n"

    query = update.callback_query
    await query.answer()
    await query.message.reply_text(text, reply_markup=markup, parse_mode='html')
    return MAIN_MENU

def get_faq_commands(faqs):
    commands = []
    for elem in faqs[1:]:
        text = elem[2]
        async def handler(update: Update, context: CallbackContext, text=text) -> int:
            await update.message.reply_text(text, reply_markup=markup, parse_mode='html')
            return MAIN_MENU

        commands.append(CommandHandler(elem[0], handler))
    return commands

async def write_substate_text(substate: int, message, markup=None):
    text = substate_data[substate]['text']
    await message.reply_text(text,
        reply_markup=markup if markup else substate_data[substate]['markup'])

async def handle_callback(update: Update, context: CallbackContext) -> int:
    logger.info(">> func handle_callback {}".format(context.user_data['substate']))

    query = update.callback_query
    await query.answer()
    if (query.data == 'back') or \
        (context.user_data['substate'] == ids[0] and query.data != 'yes'):
        context.user_data['substate'] = ids[-1]
        await query.message.reply_text(resource['back_msg'],
                    reply_markup=substate_data[context.user_data['substate']]['markup'])
        return DONE_SUBCONV

    context.user_data['substate'] += 1
    await write_substate_text(context.user_data['substate'], query.message)
    return context.user_data['substate']

async def handle_reply(update: Update, context: CallbackContext) -> int:
    logger.info(">> func handle_reply {}".format(context.user_data['substate']))

    if "qa" not in context.user_data:
        context.user_data['qa'] = {}
    context.user_data['qa'][substate_data[context.user_data['substate']]['text']] = update.message.text

    context.user_data['substate'] += 1
    await write_substate_text(context.user_data['substate'], update.message)

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
    reply_keyboard = [
        [ InlineKeyboardButton(resource['back'], callback_data='back') ]
    ]
    back_markup = InlineKeyboardMarkup(reply_keyboard)

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
        [ InlineKeyboardButton(resource['ask_help'], callback_data='ask_help') ],
        [ InlineKeyboardButton(resource['faq'], callback_data='faq') ],
        [ InlineKeyboardButton(resource['info'], callback_data='info') ]
    ]
    global markup
    markup = InlineKeyboardMarkup(reply_keyboard)

    questions = read_spreadsheet(LOAD_SHEET_ID, QUESTIONS_SHEET_RANGE)
    global ids
    ids = get_ids(questions, 2)
    logger.info(ids)

    global substate_data
    substate_data = get_states(questions, ids)
    logger.info(substate_data)

    application = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()

    ask_for_help_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(ask_for_help_start, "^ask_help$")
        ],
        states = { id : [ MessageHandler(filters.TEXT, handle_reply) ] for id in ids },
        fallbacks=[ CallbackQueryHandler(handle_callback) ],
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
                CallbackQueryHandler(get_information, "^info$"),
                CallbackQueryHandler(faq, "^faq$"),
                CommandHandler('admin', register_admin),
               *faq_commands
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == '__main__':
    main()
