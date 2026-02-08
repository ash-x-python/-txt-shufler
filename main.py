import os
import random
import re
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Flask app for Render's port binding
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is running!", 200

# --- SHUFFLING LOGIC ---

def shuffle_options(options_list):
    """Shuffles options and ensures the checkmark moves with the text."""
    random.shuffle(options_list)
    return options_list

def process_content(text):
    # Split into blocks based on common question starts or double newlines
    # This is a simplified regex; complex formats require specific parsers
    blocks = re.split(r'\n(?=Q\d+|[0-9]+\.)', text.strip())
    
    shuffled_blocks = []
    prev_correct_indices = [] # Stores 0, 1, 2, 3 for a, b, c, d

    # Shuffle the order of blocks entirely
    random.shuffle(blocks)

    for block in blocks:
        lines = block.split('\n')
        question_text = []
        options = []
        explanation = []
        
        # Simple extraction logic
        for line in lines:
            if re.match(r'^[\(\[ ]?[A-Ea-e][\.\)\-] ', line.strip()) or "✅" in line:
                options.append(line)
            elif "Ex:" in line or "Explanation:" in line or "व्याख्या" in line:
                explanation.append(line)
            else:
                question_text.append(line)

        # Shuffle options within the block
        if len(options) >= 2:
            # Logic to avoid same position as previous 3
            attempts = 0
            original_options = options.copy()
            while attempts < 10:
                random.shuffle(options)
                # Find current index of ✅
                current_idx = next(i for i, s in enumerate(options) if "✅" in s)
                if current_idx not in prev_correct_indices[-3:]:
                    prev_correct_indices.append(current_idx)
                    break
                attempts += 1
        
        # Reconstruct block
        new_block = "\n".join(question_text) + "\n" + "\n".join(options) + "\n" + "\n".join(explanation)
        shuffled_blocks.append(new_block)

    return "\n\n" + "\n\n".join(shuffled_blocks)

# --- BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a .txt file and use /shufflext to randomize it.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_path = f"temp_{update.message.chat_id}.txt"
    await file.download_to_drive(file_path)
    context.user_data['last_file'] = file_path
    await update.message.reply_text("File received! Use /shufflext to process.")

async def shuffle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_path = context.user_data.get('last_file')
    if not file_path:
        await update.message.reply_text("Please upload a .txt file first.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    processed_text = process_content(content)
    output_path = f"shuffled_{update.message.chat_id}.txt"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(processed_text)

    await update.message.reply_document(document=open(output_path, 'rb'), filename="shuffled_questions.txt")
    
    # Cleanup
    os.remove(file_path)
    os.remove(output_path)
    context.user_data['last_file'] = None

# --- MAIN ---

if __name__ == '__main__':
    # Start Flask in background
    import threading
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))).start()

    TOKEN = "8520855840:AAGeUrC0tIFqTKIi-hwLWrrEpHgbtzsk2SU" # Use env variables for production
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("shufflext", shuffle_command))
    application.add_handler(MessageHandler(filters.Document.FileExtension("txt"), handle_document))
    
    application.run_polling()
