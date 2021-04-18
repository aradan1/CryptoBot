
# coding: utf-8
#!/usr/bin/env python
# pylint: disable=C0116

import requests
import json

import logging

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


"""
Simple Bot to track cryptocurrencies pricing every hour.
"""
class CryptoBot:

    instance = None
    
    def __init__(self, path="chats_db"):
        assert CryptoBot.instance is None
        CryptoBot.instance = self
        
        self.updater = None
        self.path = path


    def __enter__(self):
        return self
    

    def __exit__(self, type, value, tb):
        self.stop()


    def start(self, token):

        # Recover the data from users
        try:
            with open(self.path) as f:
                self.db = json.load(f)
                print(self.db)
        except IOError:
            self.db = {}

        """Run bot."""
        # Create the Updater and pass it your bot's token.
        self.updater = Updater(token)

        # Get the dispatcher to register handlers
        self.dispatcher = self.updater.dispatcher

        # /start     -> Begin running in that server
        # /help      -> Display command information
        # /display   -> Display currently tracked cryptos
        # /snapshot  -> Show current state of the cryptos being tracked
        # /track X   -> Call X cryptocurrency, if posible add to tracked cryptos
        # /drop X    -> Drop X cryptocurrency from current list, if not in it tell the user
        self.dispatcher.add_handler(CommandHandler("start",    self.comm_start))
        self.dispatcher.add_handler(CommandHandler("help",     self.comm_help))
        self.dispatcher.add_handler(CommandHandler("display",  self.comm_display))
        self.dispatcher.add_handler(CommandHandler("snapshot", self.comm_snapshot))
        self.dispatcher.add_handler(CommandHandler("track",    self.comm_track))
        self.dispatcher.add_handler(CommandHandler("drop",     self.comm_drop))

        # Start the Bot
        self.updater.start_polling()

        # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
        # SIGABRT. This should be used most of the time, since start_polling() is
        # non-blocking and will stop the bot gracefully.
        self.updater.idle()


    def stop(self):
        if self.updater:
            self.updater.stop()

        with open(self.path,'wt') as f:
            json.dump(self.db, f)


    # Define a few command handlers. These usually take the two arguments update and
    # context. Error handlers also receive the raised TelegramError object in error.
    def comm_start(self, update: Update, context: CallbackContext):
        chat_id = update.message.chat_id
        print("chat id: "+str(chat_id))
        self.db[str(chat_id)] = "BTC,ETH,BNB,ADA"
        self.comm_help(update, context)
        self.set_routine(update, context)


    def comm_help(self, update: Update, _: CallbackContext):
        update.message.reply_text(("/display - Shows all currently tracked cryptos\n"
                                   "/snapshot - Shows current market price of currently tracking cryptos\n"
                                   "/track X - Track X cryptocurrency (must be in abreviated form)\n"
                                   "/drop X - Stop tracking X if already being tracked"))


    def comm_display(self, update: Update, _: CallbackContext):
        chat_id = update.message.chat_id
        if str(chat_id) not in self.db:
            update.message.reply_text("type /start to initialize tracking")
            return

        reply = self.db[str(chat_id)]
        if not reply:
            reply = "Nothing being tracked."
        update.message.reply_text(reply)


    def comm_track(self, update: Update, context: CallbackContext):
        chat_id = update.message.chat_id
        if str(chat_id) not in self.db:
            update.message.reply_text("type /start to initialize tracking")
            return

        try:
            # args[0] should contain the cryptocurrency to be tracked
            crypto = str(context.args[0])
            self.db[str(chat_id)] = self.db[str(chat_id)] + "," + crypto

            text = crypto + ' added to the watchlist!'
            update.message.reply_text(text)
        except IndexError:
            update.message.reply_text("Uso: /track <cryptomoneda>")


    def comm_drop(self, update: Update, context: CallbackContext):
        chat_id = update.message.chat_id
        if str(chat_id) not in self.db:
            update.message.reply_text("type /start to initialize tracking")
            return

        try:        
            # args[0] should contain the cryptocurrency to be removed
            crypto = str(context.args[0])

            l = self.db[str(chat_id)].split(",")
            if crypto in l: l.remove(crypto)

            self.db[str(chat_id)] = ",".join(l)

            text = crypto + ' removed from the watchlist!'
            update.message.reply_text(text)
        except IndexError:
            update.message.reply_text("Uso: /drop <cryptomoneda>")



    def comm_snapshot(self, update: Update, _: CallbackContext):
        chat_id = update.message.chat_id
        if str(chat_id) not in self.db:
            update.message.reply_text("type /start to initialize tracking")
            return

        reply = self.show_prices(chat_id)
        update.message.reply_text(reply)


    def set_routine(self, update: Update, context: CallbackContext):
        """Add a job to the queue."""
        chat_id = update.message.chat_id
        try:
            # every 1 hora (60s*60min)
            interval = 60*60

            job_removed = self.remove_job_if_exists(str(chat_id), context)
            context.job_queue.run_repeating(self.check_prices, interval, context=chat_id, name=str(chat_id))

            text = 'Task successfully set!'
            if job_removed:
                text += ' Old task was removed.'
            update.message.reply_text(text)

        except (IndexError):
            update.message.reply_text('Usage: /set <seconds>')


    def remove_job_if_exists(self, name: str, context: CallbackContext):
        """Remove job with given name. Returns whether job was removed."""
        current_jobs = context.job_queue.get_jobs_by_name(name)
        if not current_jobs:
            return False
        for job in current_jobs:
            job.schedule_removal()
        return True


    def unset(self, update: Update, context: CallbackContext):
        """Remove the job."""
        chat_id = update.message.chat_id
        job_removed = self.remove_job_if_exists(str(chat_id), context)
        text = 'Task successfully cancelled!' if job_removed else 'You have no active Task.'
        update.message.reply_text(text)


    def check_prices(self, context: CallbackContext):
        """Displays the current pricing of the cryptos"""
        job = context.job
        chat_id = job.context

        """Send the message."""
        context.bot.send_message(chat_id, text=show_prices(chat_id))


    def show_prices(self, chat_id):
        """Ensures consistent formating when displaying crypto pricing"""
        if self.db[str(chat_id)]:
            json_data = self.collect_data(self.db[str(chat_id)])
            ms = []
            for obj in json_data:
                s = ["{} was {:.3f}€ at {}".format(obj['currency'], float(obj['price']), obj['price_date']),
                "1h_: {:7.3f}% {:.4f}".format(float(obj['1h']['price_change_pct'])*100, float(obj['1h']['price_change'])),
                "1d_: {:7.3f}% {:.4f}".format(float(obj['1d']['price_change_pct'])*100, float(obj['1d']['price_change'])),
                "7d_: {:7.3f}% {:.4f}".format(float(obj['7d']['price_change_pct'])*100, float(obj['7d']['price_change'])),
                "30d: {:7.3f}% {:.4f}".format(float(obj['30d']['price_change_pct'])*100, float(obj['30d']['price_change']))]
                
                ms.append("\n".join(s))

            """return the message."""
            return "\n\n".join(ms)
        
        return "No cryptos being tracked. Add some to the watchlist with /track"



    def collect_data(self, ids, interval="1h,1d,7d,30d,365d,ytd"):
        """Call Nomics API to check cryptocurrencies pricing"""
        tokenCrypto = open('TOKEN_CRYPTO').read().strip()

        url = "https://api.nomics.com/v1/currencies/ticker?key={}&ids={}&interval={}&convert=EUR&per-page=100&page=1"

        new_url = url.format(tokenCrypto, ids, interval)

        json = requests.get(new_url)

        try:
            json_data = json.json()
        except ValueError:
            print("Response content is not valid JSON")

        return json_data



if __name__ == '__main__':


    with CryptoBot() as bot:
        #test
        print("Running...")

        bot.start(open('TOKEN_TEL').read().strip())