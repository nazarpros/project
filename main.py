import os
import asyncio
import subprocess
import tempfile
from aiogram import Bot, Dispatcher, types
import openai

# Токены берем из переменных окружения Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")          # НЕ вставляй сюда токен напрямую
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # НЕ вставляй сюда ключ напрямую

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

openai.api_key = OPENAI_API_KEY

# Функция запуска Python-кода
def run_code(code):
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            filename = f.name

        result = subprocess.run(
            ["python", filename],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout or result.stderr
    except Exception as e:
        return str(e)

# Обработчик сообщений
@dp.message()
async def vibe_code(message: types.Message):
    user_text = message.text

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты пишешь только Python код без объяснений."},
            {"role": "user", "content": user_text}
        ]
    )

    code = response["choices"][0]["message"]["content"]
    code = code.replace("```python", "").replace("```", "")
    output = run_code(code)

    await message.answer(
        f"💻 Код:\n```python\n{code}\n```\n\n📤 Результат:\n{output}",
        parse_mode="Markdown"
    )

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
