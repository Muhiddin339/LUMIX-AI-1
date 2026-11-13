import os
import logging
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from database import init_db, add_user, get_profile, add_points, top_users, save_daily, get_daily
from questions import SUBJECTS, QUESTIONS

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

TEXT = {
    "start": "🎓 LUMIX ACADEMY ga xush kelibsiz!\n\nTest ishlash uchun /quiz buyrug‘ini bosing.",
    "choose": "📚 Fanni tanlang:",
    "no_questions": "Bu fan uchun savollar hozircha mavjud emas.",
    "profile": "👤 Profilingiz\nBall: {points}\nIshlangan testlar: {played}",
    "top": "🏆 Eng yuqori natijalar:\n{rows}",
    "correct": "✅ To‘g‘ri! +10 ball",
    "wrong": "❌ Noto‘g‘ri. To‘g‘ri javob: {answer}",
    "daily_done": "Bugungi kunlik savolni allaqachon ishlagansiz. Ertaga yana keling!",
    "daily_prompt": "🌟 Kunlik savol:\n{question}",
    "daily_answer": "Kunlik savol javobi: {answer}",
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.full_name or user.first_name)
    await update.message.reply_text(TEXT["start"])

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(SUBJECTS[i], callback_data=f"subject:{i}")]
        for i in range(0, len(SUBJECTS), 2)
    ]
    # Two columns
    rows = []
    for i in range(0, len(SUBJECTS), 2):
        row = [InlineKeyboardButton(SUBJECTS[i], callback_data=f"subject:{i}")]
        if i + 1 < len(SUBJECTS):
            row.append(InlineKeyboardButton(SUBJECTS[i+1], callback_data=f"subject:{i+1}"))
        rows.append(row)
    await update.message.reply_text(TEXT["choose"], reply_markup=InlineKeyboardMarkup(rows))

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_profile(update.effective_user.id)
    await update.message.reply_text(TEXT["profile"].format(points=p["points"], played=p["played"]))

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = top_users()
    body = "\n".join(f"{i+1}. {name} — {points} ball" for i, (name, points) in enumerate(rows))
    await update.message.reply_text(TEXT["top"].format(rows=body or "Hozircha natijalar yo‘q."))

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    today = date.today().isoformat()
    if get_daily(uid, today):
        await update.message.reply_text(TEXT["daily_done"])
        return
    q = QUESTIONS["Matematika"][0]
    context.user_data["daily"] = {"question": q, "date": today}
    buttons = [[InlineKeyboardButton(a, callback_data=f"daily:{i}") for i, a in enumerate(q["options"])]]
    await update.message.reply_text(TEXT["daily_prompt"].format(question=q["question"]),
                                    reply_markup=InlineKeyboardMarkup(buttons))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("subject:"):
        idx = int(data.split(":")[1])
        subject = SUBJECTS[idx]
        questions = QUESTIONS.get(subject, [])
        if not questions:
            await query.edit_message_text(TEXT["no_questions"])
            return
        context.user_data["quiz"] = {"subject": subject, "index": 0, "score": 0}
        await send_question(query, context)
        return

    if data.startswith("answer:"):
        _, chosen = data.split(":")
        state = context.user_data.get("quiz")
        if not state:
            await query.edit_message_text("Test sessiyasi tugagan. /quiz ni bosing.")
            return
        q = QUESTIONS[state["subject"]][state["index"]]
        if int(chosen) == q["correct"]:
            state["score"] += 10
            add_points(query.from_user.id, 10)
            result = TEXT["correct"]
        else:
            result = TEXT["wrong"].format(answer=q["options"][q["correct"]])
        state["index"] += 1
        if state["index"] >= len(QUESTIONS[state["subject"]]):
            await query.edit_message_text(
                f"{result}\n\n🏁 Test tugadi!\nNatija: {state['score']} ball"
            )
            add_points(query.from_user.id, 0, played=1)
            context.user_data.pop("quiz", None)
        else:
            await query.edit_message_text(result)
            await send_question(query, context)
        return

    if data.startswith("daily:"):
        state = context.user_data.get("daily")
        if not state:
            await query.edit_message_text("Kunlik savol topilmadi. /daily ni bosing.")
            return
        q = state["question"]
        chosen = int(data.split(":")[1])
        correct = chosen == q["correct"]
        if correct:
            add_points(query.from_user.id, 10)
            result = "✅ To‘g‘ri! +10 ball"
        else:
            result = f"❌ To‘g‘ri javob: {q['options'][q['correct']]}"
        save_daily(query.from_user.id, state["date"])
        context.user_data.pop("daily", None)
        await query.edit_message_text(result)

async def send_question(query, context):
    state = context.user_data["quiz"]
    q = QUESTIONS[state["subject"]][state["index"]]
    text = f"📘 {state['subject']} — {state['index']+1}/{len(QUESTIONS[state['subject']])}\n\n{q['question']}"
    rows = [[InlineKeyboardButton(a, callback_data=f"answer:{i}")]
            for i, a in enumerate(q["options"])]
    await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(rows))

def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN secret/environment variable is missing.")
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CallbackQueryHandler(button_handler))
    logging.info("LUMIX ACADEMY started")
    app.run_polling()

if __name__ == "__main__":
    main()
