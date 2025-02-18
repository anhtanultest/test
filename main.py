import json
import schedule
import time
import asyncio
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, CallbackContext
import threading
from flask import Flask

# Thay token và chat ID của bạn vào đây
TOKEN = "token"
CHAT_ID = "chat_id"
DATA_FILE = "tasks.json"

bot = Bot(token=TOKEN)

# Flask server để giữ bot sống
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running 🚀"

# Tải dữ liệu từ file JSON
def load_tasks():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Lưu dữ liệu vào file JSON
def save_tasks(tasks):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)

# Xử lý tin nhắn nhập task trong ngày
async def add_task(update: Update, context: CallbackContext):
    user_id = str(update.message.chat_id)
    task = update.message.text

    tasks = load_tasks()
    weekday = time.strftime("%A")  # Lấy ngày hiện tại (Monday, Tuesday,...)

    if user_id not in tasks:
        tasks[user_id] = {}

    if weekday not in tasks[user_id]:
        tasks[user_id][weekday] = []

    tasks[user_id][weekday].append(task)
    save_tasks(tasks)

    await update.message.reply_text(f"✅ Đã lưu task: {task}")

# Nhắc nhập task vào 16h từ thứ 2 đến thứ 6
async def remind_to_add_tasks():
    message = "⏳ Đến giờ rồi! Hãy nhập các task bạn đã làm hôm nay nhé."
    await bot.send_message(chat_id=CHAT_ID, text=message)

# Gửi báo cáo vào 16h30 thứ 6
async def send_weekly_report():
    tasks = load_tasks()
    if CHAT_ID not in tasks:
        return

    message = "📋 Báo cáo công việc tuần này:\n\n"
    for day, task_list in tasks[CHAT_ID].items():
        message += f"📅 {day}:\n"
        for task in task_list:
            message += f"- {task}\n"
        message += "\n"

    await bot.send_message(chat_id=CHAT_ID, text=message)
    print("✅ Đã gửi báo cáo tuần!")

    # Xóa dữ liệu sau khi gửi báo cáo
    tasks[CHAT_ID] = {}
    save_tasks(tasks)

# HÀM TRUNG GIAN (để chạy async function trong schedule)
def remind_to_add_tasks_sync():
    asyncio.run(remind_to_add_tasks())

def send_weekly_report_sync():
    asyncio.run(send_weekly_report())

# Lên lịch nhắc nhở vào các ngày cụ thể
schedule.every().monday.at("16:00").do(remind_to_add_tasks_sync)
schedule.every().tuesday.at("16:00").do(remind_to_add_tasks_sync)
schedule.every().wednesday.at("16:00").do(remind_to_add_tasks_sync)
schedule.every().thursday.at("16:00").do(remind_to_add_tasks_sync)
schedule.every().friday.at("16:00").do(remind_to_add_tasks_sync)
schedule.every().friday.at("16:30").do(send_weekly_report_sync)

# Chạy scheduler liên tục
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)  # Kiểm tra mỗi phút

# Chạy bot Telegram
def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_task))

    print("Starting bot...")
    application.run_polling(drop_pending_updates=True)

# Chạy tất cả trong các luồng riêng biệt
def main():
    # Chạy scheduler trong một thread phụ
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    # Chạy Flask trong một thread phụ
    flask_thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True)
    flask_thread.start()

    # Chạy bot Telegram trong main thread (để tránh lỗi asyncio)
    run_bot()

if __name__ == "__main__":
    main()
