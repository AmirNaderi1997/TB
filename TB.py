from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from web3 import Web3
import random
import os

# === CONFIGURATION ===
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
PRIVATE_KEY = "YOUR_WALLET_PRIVATE_KEY"
SENDER_ADDRESS = "YOUR_WALLET_ADDRESS"
TOKEN_CONTRACT = "YOUR_ERC20_TOKEN_CONTRACT_ADDRESS"
INFURA_URL = "https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID"

# Reward amount per correct answer
REWARD_AMOUNT = 10  # tokens

# Connect to Web3
web3 = Web3(Web3.HTTPProvider(INFURA_URL))
contract_abi = [...]  # Paste the ABI of your token here
token_contract = web3.eth.contract(address=Web3.toChecksumAddress(TOKEN_CONTRACT), abi=contract_abi)

# === QUIZ QUESTIONS ===
QUESTIONS = [
    {"q": "What does BTC stand for?", "a": "bitcoin"},
    {"q": "What is the native token of Ethereum?", "a": "ether"},
    {"q": "What is the maximum supply of Bitcoin?", "a": "21000000"},
]

user_state = {}

# === BOT COMMANDS ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎮 Welcome to the Crypto Quiz Game!\nType /quiz to start a question.")

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = random.choice(QUESTIONS)
    user_state[update.message.chat_id] = question
    await update.message.reply_text(f"❓ Question: {question['q']}\nReply with your answer.")

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in user_state:
        await update.message.reply_text("❗ Please start with /quiz")
        return

    correct_answer = user_state[chat_id]['a'].lower()
    if update.message.text.strip().lower() == correct_answer:
        await update.message.reply_text("✅ Correct! Please send your wallet address to receive tokens.")
        user_state[chat_id]['answered'] = True
    else:
        await update.message.reply_text("❌ Incorrect. Try /quiz again.")
        user_state.pop(chat_id)

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in user_state and user_state[chat_id].get('answered'):
        wallet = update.message.text.strip()
        try:
            if Web3.isAddress(wallet):
                tx_hash = send_token(wallet, REWARD_AMOUNT)
                await update.message.reply_text(f"🎉 Sent {REWARD_AMOUNT} tokens!\nTx: {tx_hash}")
                user_state.pop(chat_id)
            else:
                await update.message.reply_text("⚠️ Invalid wallet address.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    else:
        await update.message.reply_text("❗ Answer a quiz first using /quiz.")

# === SEND TOKEN ===

def send_token(to_address, amount):
    nonce = web3.eth.get_transaction_count(SENDER_ADDRESS)
    tx = token_contract.functions.transfer(
        Web3.toChecksumAddress(to_address),
        web3.to_wei(amount, 'ether')
    ).build_transaction({
        'chainId': 1,
        'gas': 100000,
        'gasPrice': web3.to_wei('20', 'gwei'),
        'nonce': nonce,
    })
    signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return web3.to_hex(tx_hash)

# === MAIN ===

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("quiz", quiz))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
app.add_handler(MessageHandler(filters.Regex(r"^0x[a-fA-F0-9]{40}$"), handle_wallet))

print("Bot is running...")
app.run_polling()
