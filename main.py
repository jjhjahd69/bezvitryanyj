from config import *
import discord
from discord.ext import commands
from discord.utils import get
import sqlite3
import os

# Підключення усіх потрібних дозволів
intents = discord.Intents.default()
intents.message_content = True

# Ініціалізація об'єкту бота
bot = commands.Bot(command_prefix=PREFIX, intents=intents)


# Ініціалізація когів
for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        try:
            bot.load_extension(f'cogs.{filename[:-3]}')  # Завантажуємо всі .py файли
        except Exception as e:
            print(f'Не вдалося завантажити {filename}: {e}')


bot.run(TOKEN)