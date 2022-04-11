import os
import logging
from typing import Dict

from telegram import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
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

# main states
CHOOSING, ASKING_FOR_HELP, TYPING_CHOICE = range(3)

# ASKING_FOR_HELP states
LOCATION, NUMBER_OF_PEOPLE, BELONGINGS, FINISHING, DONE = range(3, 8)
questions = {
    LOCATION: "Where are you?",
    NUMBER_OF_PEOPLE: "How many are you?",
    BELONGINGS: "Do you have necessary clothes with you?",
}

reply_keyboard = [
    ['Ask for help', 'Get information', 'FAQ'],
    ['Done'],
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


# def facts_to_str(user_data: Dict[str, str]) -> str:
#     """Helper function for formatting the gathered user info."""
#     facts = [f'{key} - {value}' for key, value in user_data.items()]
#     return "\n".join(facts).join(['\n', '\n'])


def start(update: Update, context: CallbackContext) -> int:
    """Start the conversation and ask user for input."""
    update.message.reply_text(
        "Hi! I am UnitedForU bot. How can I help?",
        reply_markup=markup,
    )

    return CHOOSING

def ask_for_help(update: Update, context: CallbackContext) -> int:
    """The user wants to ask for help. Child conversation gathers all necessary info"""

    # if 'substate' not in context.user_data:
    #     context.user_data['substate'] = LOCATION
    text = 'Please give us some information.'
    # else:
    #     context.user_data['substate'] += 1
    #     text = questions[context.user_data['substate']]
    
    update.message.reply_text(text)

    return ASKING_FOR_HELP

def get_information(update: Update, context: CallbackContext) -> int:
    return CHOOSING

def faq(update: Update, context: CallbackContext) -> int:
    return CHOOSING


def ask_for_help_start(update: Update, context: CallbackContext) -> int:
    context.user_data['substate'] = LOCATION

    return context.user_data['substate']

def ask_for_help_question(update: Update, context: CallbackContext) -> int:
    text = questions[context.user_data['substate']]
    context.user_data['substate'] += 1

    update.message.reply_text(text)

    return context.user_data['substate']

def ask_for_help_finish(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(f'Thank you for the information', reply_markup=markup)

    return DONE


# def regular_choice(update: Update, context: CallbackContext) -> int:
#     """Ask the user for info about the selected predefined choice."""
#     text = update.message.text
#     context.user_data['choice'] = text
#     update.message.reply_text(
#         f'Your {text.lower()}? Yes, I would love to hear about that!')

#     return TYPING_REPLY


# def custom_choice(update: Update, context: CallbackContext) -> int:
#     """Ask the user for a description of a custom category."""
#     update.message.reply_text(
#         'Alright, please send me the category first, for example "Most impressive skill"'
#     )

#     return TYPING_CHOICE


# def received_information(update: Update, context: CallbackContext) -> int:
#     """Store info provided by user and ask for the next category."""
#     user_data = context.user_data
#     text = update.message.text
#     category = user_data['choice']
#     user_data[category] = text
#     del user_data['choice']

#     update.message.reply_text(
#         "Neat! Just so you know, this is what you already told me:"
#         f"{facts_to_str(user_data)} You can tell me more, or change your opinion"
#         " on something.",
#         reply_markup=markup,
#     )

#     return CHOOSING


def done(update: Update, context: CallbackContext) -> int:
    """Display the gathered info and end the conversation."""
    user_data = context.user_data
    if 'choice' in user_data:
        del user_data['choice']

    # update.message.reply_text(
    #     f"I learned these facts about you: {facts_to_str(user_data)}Until next time!",
    #     reply_markup=ReplyKeyboardRemove(),
    # )

    user_data.clear()
    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(token=API_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [
                MessageHandler(Filters.regex('^Ask for help$'), ask_for_help),
                MessageHandler(Filters.regex('^Get information$'), get_information),
                MessageHandler(Filters.regex('^FAQ$'), faq),
            ],
            ASKING_FOR_HELP: [
                ConversationHandler(
                    entry_points=[
                        MessageHandler(Filters.regex('^kek$'), ask_for_help_start),
                    ],
                    states={
                        LOCATION: [
                            MessageHandler(
                                Filters.text, ask_for_help_question
                            )
                        ],
                        NUMBER_OF_PEOPLE: [
                            MessageHandler(
                                Filters.text, ask_for_help_question
                            )
                        ],
                        BELONGINGS: [
                            MessageHandler(
                                Filters.text, ask_for_help_question
                            )
                        ],
                        FINISHING: [
                            MessageHandler(
                                Filters.text, ask_for_help_finish
                            )
                        ],
                    },
                    fallbacks=[MessageHandler(Filters.text, ask_for_help_finish)],
                    map_to_parent={
                        DONE: CHOOSING
                    }
                ),
            ],
            # TYPING_CHOICE: [
            #     MessageHandler(
            #         Filters.text & ~(Filters.command | Filters.regex(
            #             '^Done$')), regular_choice
            #     )
            # ],
            # TYPING_REPLY: [
            #     MessageHandler(
            #         Filters.text & ~(Filters.command |
            #                          Filters.regex('^Done$')),
            #         received_information,
            #     )
            # ],
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
