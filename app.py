import os
import logging
import gspread
from dotenv import load_dotenv
from telegram.constants import ParseMode
from oauth2client.service_account import ServiceAccountCredentials
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ConversationHandler, ContextTypes
)
from datetime import datetime
import json

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds_env = os.getenv("GOOGLE_CREDENTIALS")
if google_creds_env:
    creds_dict = json.loads(google_creds_env)
else:
    with open("google_credentials.json") as f:
        creds_dict = json.load(f)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("CancelItNowDB").sheet1

# States for ConversationHandler
NAME, COST, PRIORITY = range(3)

# Priorities with colors
priority_buttons = [
    ("🔴 High", "High"),
    ("🟡 Medium", "Medium"),
    ("🟢 Low", "Low")
]

# Main menu keyboard
main_menu_kb = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("➕ Add Subscription", callback_data="add"),
        InlineKeyboardButton("📂 View Subscriptions", callback_data="view")
    ],
    [
        InlineKeyboardButton("❌ Cancel Subscription", callback_data="cancel"),
        InlineKeyboardButton("📈 View Benefits", callback_data="benefits")
    ],
[InlineKeyboardButton("❓ Help", callback_data="help"),InlineKeyboardButton("🚧 Upcoming features", callback_data="upcoming")],
    [InlineKeyboardButton("📤 Share ", callback_data="share")]
])

def insert_row(user_id, username, name="", cost="", priority="", status="active"):
    sheet.append_row([str(user_id), username or "", name, str(cost), priority, status])

def get_user_subs(user_id, include_cancelled=True):
    records = sheet.get_all_records()
    user_subs = []
    for i, row in enumerate(records):
        if str(row["user_id"]) == str(user_id) and row["name"]:  # Check name exists
            if row["status"].lower() == "active" or include_cancelled:
                row_num = i + 2
                user_subs.append({
                    "name": row["name"],
                    "cost": row["cost"],
                    "priority": row["priority"],
                    "status": row["status"].lower(),  # Add status
                    "row": row_num
                })
    return user_subs


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    sheet.append_row([str(user.id), user.username or "", "", "", "", "passive"])
    await update.message.reply_text("""Why keep paying for what you don’t use?\n✨ You’re not alone — over 80% of people lose money on unused subscriptions.\nWe are here to help you flip the script.\n\n
👋 Welcome to *CancelItNowBot* — your personal assistant for cutting subscription clutter.

✅ Track everything you're paying for  
🧠 Reflect on what's *actually* worth it  
❌ Cancel wasteful services in seconds  
💰 Feel lighter — mentally and financially


Let’s turn confusion into clarity.
Let’s simplify your life.
One subscription at a time.\n

Start below 👇\n""", parse_mode=ParseMode.MARKDOWN
    )
    await update.message.reply_text("Click the button below to get started:", reply_markup=main_menu_kb)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📍 What would you like to do now?", reply_markup=main_menu_kb)

async def unknown_response(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("🤔 Sorry, I didn’t understand that. Please try again.")
    await query.message.reply_text("📍 What would you like to do now?", reply_markup=main_menu_kb)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    await query.answer()
    data = query.data

    if data == "add":
        await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="📌 What subscription do you want to add?")
        return NAME


    elif data == "view":
        subs = get_user_subs(user.id)
        if not subs:
            await query.message.reply_text("📭 No subscriptions tracked yet.")
        else:
            active_subs = [s for s in subs if s['status'] == 'active']
            cancelled_subs = [s for s in subs if s['status'] == 'cancelled']
            
            msg = "📋 Your Subscription Dashboard:\n\n"
            
            # Active subscriptions
            if active_subs:
                msg += "<b>🟢 ACTIVE SUBSCRIPTIONS:</b>\n"
                for s in active_subs:
                    color = "🔴" if s['priority'] == 'High' else "🟡" if s['priority'] == 'Medium' else "🟢"
                    msg += (f"🔹 <b>{s['name']}</b>\n"
                           f"   💰 ${s['cost']:.2f} / month\n"
                           f"   🏷️ Priority: {color} {s['priority']}\n\n")
            
            # Cancelled subscriptions with strikethrough
            if cancelled_subs:
                msg += "\n<b>❌ CANCELLED (Your Wins!):</b>\n"
                total_saved = 0
                for s in cancelled_subs:
                    total_saved += float(s['cost'])
                    msg += f"<s>{s['name']} - ${s['cost']:.2f}/mo</s> ✅\n"
                
                msg += f"\n💪 <b>Total Monthly Savings: ${total_saved:.2f}</b>\n"
                msg += f"📈 <b>Yearly Savings: ${(total_saved * 12):.2f}</b>\n"
            
            msg += f"\n🧘 <i>Review. Reflect. You're already doing great.</i>\n"
            
            await query.message.reply_text(msg, parse_mode=ParseMode.HTML)
        
        await query.message.reply_text("📍 What would you like to do now?", reply_markup=main_menu_kb)


    elif data == "cancel":
        subs = get_user_subs(user.id)
        active_subs = [s for s in subs if s['status'] == 'active']  # Filter active only

        if not active_subs:
            await query.message.reply_text("📭 No active subscriptions to cancel.")
        else:
            kb = [[InlineKeyboardButton(f"{s['name']} | ${s['cost']} | {s['priority']}",
        callback_data=f"confirm_cancel:{s['row']}:{s['name']}:{s['cost']}"
    )]
    for s in active_subs]

            await query.message.reply_text("🔻 Select a subscription you want to cancel:", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("confirm_cancel"):
        _, row_index, name, cost = data.split(":")
        context.user_data['row_index'] = int(row_index)
        context.user_data['cancel_name'] = name
        context.user_data['cancel_cost'] = cost
        
        confirm_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Cancel", callback_data="do_cancel")],
            [InlineKeyboardButton("❌ No", callback_data="cancel_abort")],
        ])
        await query.message.reply_text(
            f"Are you sure you want to cancel '{name}' subscription?\n💸 It’s costing you ${cost} every month.",
            reply_markup=confirm_kb
        )

    elif data == "do_cancel":
        row = context.user_data['row_index']
        name = context.user_data['cancel_name']
        cost = float(context.user_data['cancel_cost'])
        sheet.update_cell(row, 6, "cancelled")
        await query.message.reply_text(
            f"✅ Subscription '{name}' has been cancelled.\n🎉 You just saved ${cost} monthly! That’s ${(cost * 12):.2f} per year! 💰\n\n💪 _Keep going — smarter money is your new normal._",parse_mode=ParseMode.MARKDOWN
        )
        await query.message.reply_text("📍 What would you like to do now?", reply_markup=main_menu_kb)

    elif data == "benefits":
        subs = get_user_subs(user.id)
        if not subs:
            await query.message.reply_text("📭 No subscriptions tracked yet.")
        else:
            active_subs = [s for s in subs if s['status'] == 'active']
            cancelled_subs = [s for s in subs if s['status'] == 'cancelled']
            
            active_total = sum(float(s['cost']) for s in active_subs) if active_subs else 0
            saved_total = sum(float(s['cost']) for s in cancelled_subs) if cancelled_subs else 0
            
            count = len(active_subs)
            high = sum(1 for s in active_subs if s['priority'] == 'High')
            medium = sum(1 for s in active_subs if s['priority'] == 'Medium')
            low = sum(1 for s in active_subs if s['priority'] == 'Low')
            
            await query.message.reply_text(
                f"📊 Your Subscription Snapshot:\n\n"
                f"<b>Active Subscriptions:</b>\n"
                f"• Total Active: {count}\n"
                f"• Monthly Spend: ${active_total:.2f}\n"
                f"• Yearly Spend: ${(active_total * 12):.2f}\n\n"
                f"<b>Priority Breakdown:</b>\n"
                f"🔴 High: {high}\n"
                f"🟡 Medium: {medium}\n"
                f"🟢 Low: {low}\n\n"
                f"<b>Your Savings:</b>\n"
                f"✅ Cancelled: {len(cancelled_subs)} subscriptions\n"
                f"💰 Monthly Saved: ${saved_total:.2f}\n"
                f"🎯 Yearly Saved: ${(saved_total * 12):.2f}\n\n"
                f"💡 <i>Think: what else can you cut to save more?</i>\n",
                parse_mode=ParseMode.HTML
            )
        await query.message.reply_text("📍 What would you like to do now?", reply_markup=main_menu_kb)


    elif data == "cancel_abort":
        cost = context.user_data.get("cancel_cost", "0")
        await query.message.reply_text(
        "😌 No worries.\n"
        "Your subscription is safe for now.\n\n"
        f"💡 It currently costs you *${cost} monthly*.\n"
        "\nTake your time to decide — I'm here whenever you're ready to optimize your expenses 💸💪",
        parse_mode=ParseMode.MARKDOWN
    )
        await query.message.reply_text("📍 What would you like to do now?", reply_markup=main_menu_kb)


    elif data == "menu":

        await query.message.reply_text("📍 What would you like to do now?", reply_markup=main_menu_kb)

    elif data == "help":
        await query.message.reply_text(
        "🤖 *CancelItNowBot Help Guide*\n\n"
        "Here's what I can do for you:\n\n"
        "🔹 *Add Subscription* – Add a new subscription and track the recurring cost\n"
        "🔹 *View Subscriptions* – See all your active services\n"
        "🔹 *Cancel Subscription* – Cancel a subscription\n"
        "🔹 *View Benefits* – Get insights into where your money goes\n\n"
        "I'm here to simplify your digital expenses and help you cut waste! 💸",
        parse_mode=ParseMode.MARKDOWN)
        await query.message.reply_text("📍 What would you like to do now?", reply_markup=main_menu_kb)

    elif data == "share":
        await query.message.reply_text(
        "❤️ Love CancelItNowBot?\n\n"
        "Invite your friends to manage their subscriptions too!\n"
        "Click below to share:\n"
        "https://t.me/cancelitnowbot")
        await query.message.reply_text("📍 What would you like to do now?",reply_markup=main_menu_kb)

    elif data == "upcoming":
    	await query.message.reply_text(
        "🚀 *Coming Soon to CancelItNowBot:*\n\n"
        "🌐 *Multilanguage Support* – Use the bot in your native language!\n"
        "🌐 *Multi Currency Support* – Log prices as per your local currency!\n"
        "🧠 *Smart Recommendations* – AI will suggest what to cancel or keep\n"
        "📅 *Reminder Alerts* – Monthly nudges before recurring payments\n"
        "📊 *Monthly Summary Reports* – Track your total savings & expenses\n"
        "👥 *Referral Rewards* – Invite friends, unlock perks!\n"
        "💳 *Budget Planning Tools* – Set monthly budgets & auto warnings\n"
        "🤝 *Exclusive Discounts* – Save more with partner deals\n"
        "🔒 *Private Mode* – Keep your subscriptions 100% private\n"
        "📥 *Import from Email* – Auto-detect subscriptions from receipts\n"
        "📌 *Custom Notes* – Add notes or cancellation deadlines per subscription\n\n"
        "We're just getting started — thank you for growing with us 💚",
        parse_mode=ParseMode.MARKDOWN)
    	await query.message.reply_text("📍 What would you like to do now?", reply_markup=main_menu_kb)


    return ConversationHandler.END

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("💰 How much does it cost you monthly?")
    return COST

async def get_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cost = float(update.message.text)
        if cost <= 0 or cost > 100000:
            raise ValueError
        context.user_data['cost'] = cost
        kb = [[InlineKeyboardButton(text, callback_data=f"priority:{val}")] for text, val in priority_buttons]
        await update.message.reply_text("""📊 How important is this to you?\n
_(Be honest — we won't judge)_\n""", reply_markup=InlineKeyboardMarkup(kb),parse_mode=ParseMode.MARKDOWN)
        return PRIORITY
    except ValueError:
        await update.message.reply_text("❗ Please enter a valid monthly cost (0.01–100000).")  # Updated message
        return COST

async def get_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    priority = query.data.split(":")[1]
    context.user_data['priority'] = priority

    u = query.from_user
    insert_row(u.id, u.username, context.user_data['name'], context.user_data['cost'], priority)

    await query.message.reply_text("✅ Subscription saved successfully!")
    await query.message.reply_text("📍 What would you like to do now?", reply_markup=main_menu_kb)

    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CallbackQueryHandler(handle_buttons)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            COST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_cost)],
            PRIORITY: [CallbackQueryHandler(get_priority, pattern="^priority:")]
        },
         fallbacks=[MessageHandler(filters.ALL, unknown_response)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_buttons))  # Handle buttons LAST
    app.add_handler(CommandHandler("menu", main_menu))

    app.run_polling()

if __name__ == '__main__':
    main()
