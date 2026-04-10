"""
ContextShield — Telegram Bot (Professional Chat UI with Grok Integration)
=========================================================================
Features:
- Professional Chat UI with beautiful formatting
- ContextShield API integration for security analysis
- Grok API integration for safe prompt execution
- Smart decision making based on risk levels
- Beautiful response templates
"""

import os
import sys
import uuid
import logging
import httpx
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatAction

# Load environment variables
load_dotenv()

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("contextshield.telegram")

# =============================================================================
# CONFIGURATION (from .env)
# =============================================================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CONTEXTSHIELD_API_URL = os.getenv("CONTEXTSHIELD_API_URL", "http://localhost:8000")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

FLAG_THRESHOLD = float(os.getenv("FLAG_THRESHOLD", "0.55"))
HIGH_RISK_THRESHOLD = float(os.getenv("HIGH_RISK_THRESHOLD", "0.7"))

# =============================================================================
# UI TEMPLATES - Professional Chat Design
# =============================================================================

# Welcome Messages
WELCOME_MESSAGES = [
    "🛡️ <b>ContextShield Security Bot</b>\n\n"
    "Welcome to the Intelligent Protection System!\n"
    "Send any message and the bot will analyze and execute it securely 🔒",

    "🤖 <b>How It Works:</b>\n\n"
    "1️⃣ <b>Security Analysis</b> - Scans your message\n"
    "2️⃣ <b>Decision Making</b> - Safe / Warning / Block\n"
    "3️⃣ <b>Execution</b> - Executes safe messages via Grok AI",

    "💡 <b>Commands:</b>\n"
    "/start - Start the bot\n"
    "/help - Get help\n"
    "/stats - View analysis statistics\n"
    "/status - System status"
]

def get_welcome_message():
    """Get a formatted welcome message with buttons"""
    keyboard = [
        [InlineKeyboardButton("🔒 Security Analysis", callback_data="info_security"),
         InlineKeyboardButton("🤖 AI Execution", callback_data="info_ai")],
        [InlineKeyboardButton("📊 Statistics", callback_data="stats"),
         InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return WELCOME_MESSAGES[0], reply_markup

# Security Analysis Messages
def msg_scanning():
    """Beautiful scanning animation"""
    animations = [
        "🔍 <b>Security Analysis in Progress...</b>\n\n"
        "┌──────────────────────────────┐\n"
        "│ ▓▓▓▓▓░░░░░░░░░░░░░░░░░ 20% │\n"
        "└──────────────────────────────┘\n"
        "<i>Analyzing core intent...</i>",

        "🔍 <b>Security Analysis in Progress...</b>\n\n"
        "┌──────────────────────────────┐\n"
        "│ ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░ 50% │\n"
        "└──────────────────────────────┘\n"
        "<i>Checking for injection attempts...</i>",

        "🔍 <b>Security Analysis in Progress...</b>\n\n"
        "┌──────────────────────────────┐\n"
        "│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░ 80% │\n"
        "└──────────────────────────────┘\n"
        "<i>Analyzing neural risk factors...</i>"
    ]
    return animations

def msg_analysis_complete(result):
    """Beautiful analysis result display"""
    decision = result.get("decision", "SAFE")
    risk = result.get("final_risk", 0.0)
    
    # Risk meter visualization
    risk_bar = generate_risk_meter(risk)
    
    if decision == "SAFE":
        return (
            f"✅ <b>MESSAGE SAFE</b>\n\n"
            f"📊 <b>Security Report:</b>\n"
            f"{risk_bar}\n\n"
            f"┌─ <b>Analysis Details:</b>\n"
            f"│ 🎯 Risk Level: <code>{risk:.1%}</code>\n"
            f"│ 🛡️ Status: <b>✅ SAFE</b>\n"
            f"│ 📝 Category: <code>{result.get('dominant', 'General')}</code>\n"
            f"└─────────────────\n\n"
            f"🚀 <i>Executing via Grok AI...</i>"
        )
    
    elif decision == "BLOCK":
        triggered = result.get("triggered", [])
        threats = "\n".join(f"  ⚠️  <code>{r}</code>" for r in triggered)
        return (
            f"🚫 <b>THREAT DETECTED</b>\n\n"
            f"📊 <b>Security Report:</b>\n"
            f"{risk_bar}\n\n"
            f"┌─ <b>Threat Analysis:</b>\n"
            f"│ 🎯 Risk Level: <code>{risk:.1%}</code>\n"
            f"│ 🛡️ Status: <b>🚫 BLOCKED</b>\n"
            f"│ ⚡ Threats Found: <code>{len(triggered)}</code>\n"
            f"└─────────────────\n\n"
            f"🔥 <b>Detection Details:</b>\n"
            f"{threats}\n\n"
            f"❌ <i>Message blocked for security reasons.</i>"
        )
    
    elif decision == "FLAG":
        return (
            f"⚠️ <b>CAUTION - FLAGGED</b>\n\n"
            f"📊 <b>Security Report:</b>\n"
            f"{risk_bar}\n\n"
            f"┌─ <b>Risk Assessment:</b>\n"
            f"│ 🎯 Risk Level: <code>{risk:.1%}</code>\n"
            f"│ 🛡️ Status: <b>⚠️ FLAGGED</b>\n"
            f"│ ⚡ Threshold: <code>{FLAG_THRESHOLD:.1%}</code>\n"
            f"└─────────────────\n\n"
            f"{'🟡 <i>Moderate risk - checking execution policy...</i>' if risk < HIGH_RISK_THRESHOLD else '🔴 <i>High risk - execution blocked!</i>'}"
        )
    
    return "❓ Unknown analysis result."

def generate_risk_meter(risk):
    """Generate a visual risk meter"""
    filled = int(risk * 20)
    empty = 20 - filled
    
    if risk < 0.3:
        color = "🟢"
    elif risk < 0.55:
        color = "🟡"
    elif risk < 0.7:
        color = "🟠"
    else:
        color = "🔴"
    
    bar = f"{color}" * filled + "⚪" * empty
    return f"┌────────────────────┐\n│ {bar} │\n└────────────────────┘"

# Groq AI Response Templates
def msg_grok_thinking():
    """Groq AI processing message"""
    return (
        "🧠 <b>Llama AI Processing...</b>\n\n"
        "┌─────────────────────────────┐\n"
        "│ 💭 Analyzing prompt...      │\n"
        "│ 🔄 Generating response...   │\n"
        "│ ✨ Formatting output...     │\n"
        "└─────────────────────────────┘"
    )

def msg_grok_response(response_text):
    """Beautiful Groq AI response formatting"""
    timestamp = datetime.now().strftime("%H:%M:%S")

    return (
        f"🤖 <b>Llama AI Response</b>\n"
        f"<i>Generated at {timestamp}</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{response_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <b>Powered by ContextShield + Groq</b>"
    )

# Error Messages
def msg_error_connection():
    """Connection error with professional formatting"""
    return (
        "🔌 <b>CONNECTION ERROR</b>\n\n"
        "┌─ <b>System Status:</b>\n"
        "│ ❌ ContextShield API: Unreachable\n"
        "│ ❌ Groq AI: Not accessed\n"
        "└─────────────────\n\n"
        "💡 <i>Please ensure both services are running:</i>\n"
        "  • <code>uvicorn api:app --reload</code>\n"
        "  • <code>Groq API key configured</code>"
    )

def msg_grok_error():
    """Groq API error"""
    return (
        "🤖 <b>Llama AI Error</b>\n\n"
        "┌─ <b>AI Service Status:</b>\n"
        "│ ❌ Groq API: Error encountered\n"
        "│ ✅ Security Analysis: Passed\n"
        "└─────────────────\n\n"
        "💡 <i>Your message is safe, but AI execution failed.</i>\n"
        "Please try again later."
    )

# Stats and Info
STATS_DATA = {"total_analyzed": 0, "safe": 0, "blocked": 0, "flagged": 0}

def msg_stats():
    """Professional statistics display"""
    total = STATS_DATA["total_analyzed"]
    safe = STATS_DATA["safe"]
    blocked = STATS_DATA["blocked"]
    flagged = STATS_DATA["flagged"]
    
    safe_pct = f"{(safe/total)*100:.1f}%" if total > 0 else "0%"
    blocked_pct = f"{(blocked/total)*100:.1f}%" if total > 0 else "0%"
    flagged_pct = f"{(flagged/total)*100:.1f}%" if total > 0 else "0%"
    
    return (
        f"📊 <b>ContextShield Statistics</b>\n\n"
        f"┌─ <b>Analysis Summary:</b>\n"
        f"│ 📝 Total Analyzed: <b>{total}</b>\n"
        f"│ ✅ Safe: <b>{safe}</b> ({safe_pct})\n"
        f"│ 🚫 Blocked: <b>{blocked}</b> ({blocked_pct})\n"
        f"│ ⚠️ Flagged: <b>{flagged}</b> ({flagged_pct})\n"
        f"└─────────────────\n\n"
        f"🛡️ <i>Keeping your conversations safe!</i>"
    )

def msg_system_status():
    """System status display"""
    return (
        "⚙️ <b>System Status</b>\n\n"
        "┌─ <b>Service Health:</b>\n"
        f"│ 🔒 ContextShield API: <code>{CONTEXTSHIELD_API_URL}</code>\n"
        f"│ 🤖 Groq AI: <code>{GROQ_MODEL}</code>\n"
        f"│ 📊 Flag Threshold: <code>{FLAG_THRESHOLD:.1%}</code>\n"
        f"│ 🚨 High Risk Threshold: <code>{HIGH_RISK_THRESHOLD:.1%}</code>\n"
        "└─────────────────\n\n"
        "✅ <i>All systems operational</i>"
    )

# =============================================================================
# SERVER COMMUNICATION
# =============================================================================

async def call_contextshield_api(text: str) -> dict | None:
    """Send prompt to ContextShield API for analysis"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{CONTEXTSHIELD_API_URL}/analyze",
                json={"text": text},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        logger.error(f"Cannot connect to ContextShield API at {CONTEXTSHIELD_API_URL}")
        return None
    except Exception as e:
        logger.error(f"ContextShield API Error: {e}")
        return None

async def call_groq_api(prompt: str) -> str | None:
    """Execute prompt via Groq API (Llama models)"""
    if not GROQ_API_KEY or GROQ_API_KEY == "your-groq-api-key-here":
        logger.error("Groq API key not configured")
        return None
    
    logger.info(f"Calling Groq API with model: {GROQ_MODEL}")
    logger.debug(f"Prompt: {prompt[:100]}...")
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful AI assistant integrated with ContextShield security system. Provide clear, concise, and helpful responses."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
            )
            
            # Log status code for debugging
            logger.info(f"Groq API Response Status: {resp.status_code}")
            
            resp.raise_for_status()
            data = resp.json()
            
            # Log full response for debugging
            logger.debug(f"Groq API Response: {data}")
            
            # Extract response from Groq
            if "choices" in data and len(data["choices"]) > 0:
                response_text = data["choices"][0]["message"]["content"]
                logger.info(f"Groq API Success - Response length: {len(response_text)}")
                return response_text
            else:
                logger.error(f"Unexpected Groq response structure: {data}")
                return None
                
    except httpx.HTTPStatusError as e:
        logger.error(f"Groq API HTTP Error: {e.response.status_code}")
        logger.error(f"Groq API Error Response: {e.response.text}")
        return None
    except httpx.TimeoutException:
        logger.error("Groq API request timed out")
        return None
    except Exception as e:
        logger.error(f"Groq API Unexpected Error: {type(e).__name__} - {e}")
        return None

# =============================================================================
# HANDLERS
# =============================================================================

async def process_prompt(update: Update, text: str):
    """Main prompt processing with professional UI"""
    # Update stats
    STATS_DATA["total_analyzed"] += 1
    
    # Send initial scanning message with animation
    scanning_msgs = msg_scanning()
    
    # Send first scanning message
    scan_msg = await update.message.reply_text(
        scanning_msgs[0], 
        parse_mode=ParseMode.HTML
    )
    
    # Show typing action
    await update.message.chat.send_action(ChatAction.TYPING)
    await asyncio.sleep(1)
    
    # Update to second scanning message
    await scan_msg.edit_text(
        scanning_msgs[1], 
        parse_mode=ParseMode.HTML
    )
    await update.message.chat.send_action(ChatAction.TYPING)
    await asyncio.sleep(1)
    
    # Update to third scanning message
    await scan_msg.edit_text(
        scanning_msgs[2], 
        parse_mode=ParseMode.HTML
    )
    
    # Call ContextShield API
    result = await call_contextshield_api(text)
    
    # Edit to show analysis result
    await scan_msg.delete()
    
    if not result:
        await update.message.reply_text(
            msg_error_connection(), 
            parse_mode=ParseMode.HTML
        )
        STATS_DATA["total_analyzed"] -= 1  # Don't count failed analyses
        return
    
    decision = result.get("decision", "SAFE")
    risk = result.get("final_risk", 0.0)
    
    # Update stats
    if decision == "SAFE":
        STATS_DATA["safe"] += 1
    elif decision == "BLOCK":
        STATS_DATA["blocked"] += 1
    elif decision == "FLAG":
        STATS_DATA["flagged"] += 1
    
    # Send analysis result
    await update.message.reply_text(
        msg_analysis_complete(result), 
        parse_mode=ParseMode.HTML
    )
    
    # Decision making
    if decision == "SAFE":
        # Execute via Groq
        await execute_via_groq(update, text)

    elif decision == "BLOCK":
        # Block completely
        await update.message.reply_text(
            "🚫 <b>Execution Blocked</b>\n\n"
            "❌ This message contains security threats.\n"
            "🛡️ ContextShield prevented execution.\n"
            "📊 Review the analysis report above.",
            parse_mode=ParseMode.HTML
        )

    elif decision == "FLAG":
        # Check risk level
        if risk >= HIGH_RISK_THRESHOLD:
            # High risk - block
            await update.message.reply_text(
                "🔴 <b>High Risk - Execution Blocked</b>\n\n"
                f"⚠️ Risk Level: <code>{risk:.1%}</code>\n"
                f"🚨 Threshold: <code>{HIGH_RISK_THRESHOLD:.1%}</code>\n\n"
                "🛡️ Message flagged as high risk.\n"
                "❌ Execution prevented for security.",
                parse_mode=ParseMode.HTML
            )
        else:
            # Moderate risk - allow with warning
            await update.message.reply_text(
                "🟡 <b>Moderate Risk - Executing with Caution</b>\n\n"
                f"⚠️ Risk Level: <code>{risk:.1%}</code>\n"
                f"✅ Below high risk threshold.\n\n"
                "🚀 Proceeding with Groq AI execution...",
                parse_mode=ParseMode.HTML
            )
            await execute_via_groq(update, text)

async def execute_via_groq(update: Update, prompt: str):
    """Execute prompt via Groq AI with beautiful UI"""
    # Send Groq thinking message
    groq_msg = await update.message.reply_text(
        msg_grok_thinking(),
        parse_mode=ParseMode.HTML
    )

    await update.message.chat.send_action(ChatAction.TYPING)

    # Call Groq API
    response = await call_groq_api(prompt)

    await groq_msg.delete()

    if response:
        # Send beautiful Groq response
        await update.message.reply_text(
            msg_grok_response(response),
            parse_mode=ParseMode.HTML
        )
    else:
        # Groq error
        await update.message.reply_text(
            msg_grok_error(),
            parse_mode=ParseMode.HTML
        )

async def cmd_start(update: Update, ctx):
    """Handle /start command"""
    welcome_text, reply_markup = get_welcome_message()
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def cmd_help(update: Update, ctx):
    """Handle /help command"""
    help_text = (
        "📖 <b>ContextShield Help</b>\n\n"
        "<b>How it works:</b>\n"
        "1️⃣ Send any message\n"
        "2️⃣ Bot analyzes it for security threats\n"
        "3️⃣ If safe, executes via Grok AI\n"
        "4️⃣ If blocked, shows threat details\n\n"
        "<b>Commands:</b>\n"
        "/start - Initialize the bot\n"
        "/help - Show this help\n"
        "/stats - View analysis statistics\n"
        "/status - Check system status\n\n"
        "<b>Security Levels:</b>\n"
        "✅ SAFE - Executes normally\n"
        "⚠️ FLAG - May execute if risk is low\n"
        "🚫 BLOCK - Always blocked"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def cmd_stats(update: Update, ctx):
    """Handle /stats command"""
    await update.message.reply_text(
        msg_stats(),
        parse_mode=ParseMode.HTML
    )

async def cmd_status(update: Update, ctx):
    """Handle /status command"""
    await update.message.reply_text(
        msg_system_status(),
        parse_mode=ParseMode.HTML
    )

async def button_callback(update: Update, ctx):
    """Handle inline button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "info_security":
        text = (
            "🔒 <b>Security Analysis</b>\n\n"
            "ContextShield uses 4 AI agents:\n\n"
            "1️⃣ <b>Semantic Analyzer</b>\n"
            "   Analyzes meaning and intent\n\n"
            "2️⃣ <b>Injection Detector</b>\n"
            "   Detects prompt injection attacks\n\n"
            "3️⃣ <b>Neural Classifier</b>\n"
            "   Classifies threat categories\n\n"
            "4️⃣ <b>Decision Agent</b>\n"
            "   Makes final security decision"
        )
    elif data == "info_ai":
        text = (
            "🤖 <b>AI Execution (Groq)</b>\n\n"
            "When a message is deemed SAFE:\n\n"
            "✅ Your prompt is sent to Groq AI\n"
            "✅ Llama generates a helpful response\n"
            "✅ Response is beautifully formatted\n\n"
            "<b>Model:</b> " + GROQ_MODEL + "\n"
            "<b>Temperature:</b> 0.7\n"
            "<b>Max Tokens:</b> 2000"
        )
    elif data == "stats":
        text = msg_stats()
    elif data == "settings":
        text = (
            "⚙️ <b>Current Settings</b>\n\n"
            f"📊 Flag Threshold: <code>{FLAG_THRESHOLD:.1%}</code>\n"
            f"🚨 High Risk Threshold: <code>{HIGH_RISK_THRESHOLD:.1%}</code>\n"
            f"🤖 Groq Model: <code>{GROQ_MODEL}</code>\n\n"
            "💡 These can be configured in .env file"
        )
    else:
        text = "❓ Unknown option"
    
    await query.edit_message_text(text, parse_mode=ParseMode.HTML)

async def handle_message(update: Update, ctx):
    """Handle incoming messages"""
    if update.message.text:
        await process_prompt(update, update.message.text)

# =============================================================================
# MAIN
# =============================================================================

async def run_bot():
    """Initialize and run the bot"""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        return
    
    logger.info("Starting ContextShield Telegram Bot...")
    logger.info(f"ContextShield API: {CONTEXTSHIELD_API_URL}")
    logger.info(f"Groq Model: {GROQ_MODEL}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Force delete webhook to avoid conflicts
    logger.info("Cleaning up webhook...")
    await app.bot.delete_webhook(drop_pending_updates=True)
    
    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Bot is ready! Send /start to begin.")
    
    # Start the bot
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Bot shutting down...")

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
