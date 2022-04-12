import os
import logging
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

API_TOKEN = os.getenv("API_TOKEN")

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
    update.message.reply_text("INFORMATION", reply_markup=markup)
    return MAIN_MENU

def faq(update: Update, context: CallbackContext) -> int:
    logger.info(">> func faq")
    update.message.reply_text("FAQ", reply_markup=markup)
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

    update.message.reply_text('Here is what you told us:')
    for k,v in context.user_data['qa'].items():
        update.message.reply_text('{}: {}'.format(k, v))

    return DONE_SUBCONV

def done(update: Update, context: CallbackContext) -> int:
    """Display the gathered info and end the conversation."""
    logger.info(">> func done")
    
    return ConversationHandler.END

def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(token=API_TOKEN)

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
