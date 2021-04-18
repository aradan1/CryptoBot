# CryptoBot
### Bot designed to track Cryptocurrencies on Telegram.

Commands are:
- /start     -> Begin running in that telegram chatgroup.
- /help      -> Display command information (this information).
- /display   -> Replies the name of the tracked cryptos in that chat group.
- /snapshot  -> Show current state of the cryptos being tracked.
- /track X   -> If X exists, add to tracked cryptos.
- /drop X    -> Drop X cryptocurrency from tracked list, if not in it tell the user.

(X in those last 2 cases has to be the abreviation of it's name, ex: Bitcoin would be "BTC")

To beging running locally you need to have a "Telegram" and a "Nomics" token, and place the first in a file called "TOKEN_TEL" and the second one in a file called "TOKEN_CRYPTO" (or change where you get your tokens from)
