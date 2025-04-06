# main.py
from config import *
import discord
from discord.ext import commands
import asyncio # <--- Перевір, чи імпортовано asyncio
import aiomysql
import os
import logging
import traceback # <--- Імпортуємо traceback для деталей помилки

print("--- [main] Скрипт запущено ---")

# --- Налаштування логування ---
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger = logging.getLogger('discord')
logging.getLogger('aiomysql').setLevel(logging.DEBUG)
logging.getLogger('aiomysql').addHandler(handler) # Додати той самий обробник
logger.setLevel(logging.DEBUG) # <--- Встановлюємо DEBUG для максимуму інформації
logger.addHandler(handler)

# -----------------------------


class MySuperBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        print("--- [MySuperBot] __init__ початок ---")
        super().__init__(*args, **kwargs)
        self.db_pool = None
        print("--- [MySuperBot] __init__ кінець ---")

    async def setup_hook(self):
        print("--- [MySuperBot] setup_hook ПОЧАТОК ---") # <--- Чи дійдемо сюди?

        # --- Створення пулу ---
        print("--- [setup_hook] Спроба створити пул mysql... ---")
        try:
            self.db_pool = await aiomysql.create_pool(
                host=db_host, port=db_port,
                user=db_user, password=db_password, db=db_name,
                minsize=1, maxsize=10, autocommit=True
            )
            print("--- [setup_hook] Пул mysql УСПІШНО створено! ---")
        except Exception as e:
            print(f"!!! [setup_hook] КРИТИЧНА ПОМИЛКА створення пулу: {e}")
            print("!!! [setup_hook] Бот не може працювати без бази даних. Зупиняємось.")
            await self.close()
            return

        # --- Завантаження когів ---
        print("--- [setup_hook] Починаємо завантаження когів ---")
        cogs_dir = './cogs'
        try:
            if not os.path.isdir(cogs_dir):
                print(f"!!! [setup_hook] ПОМИЛКА: папка '{cogs_dir}' не знайдена!")
                return
            initial_extensions = [f'cogs.{filename[:-3]}' for filename in os.listdir(cogs_dir) if filename.endswith('.py')]
            print(f"--- [setup_hook] Знайдені коги: {initial_extensions} ---")
        except Exception as e:
            print(f"!!! [setup_hook] ПОМИЛКА при отриманні списку когів: {e}")
            return

        load_errors = False
        for extension in initial_extensions:
            # --- Детальна діагностика перед завантаженням ---
            print("-" * 20) # роздільник для ясності
            print(f"--- [setup_hook] Готуємось завантажити: {extension} ---")
            try:
                load_method = self.load_extension # отримуємо посилання на метод
                is_coro_func = asyncio.iscoroutinefunction(load_method) # перевіряємо
                print(f"--- [DIAG] тип self.load_extension: {type(load_method)}")
                print(f"--- [DIAG] asyncio.iscoroutinefunction: {is_coro_func}") # <--- КЛЮЧОВИЙ ДРУК

                # Додаткова перевірка (на всяк випадок)
                if not is_coro_func:
                     print(f"!!! [setup_hook] УВАГА: {extension} - load_extension НЕ є корутинною функцією! Пропускаємо await.")
                     # Спробуємо викликати синхронно, якщо iscoroutinefunction = False (хоча це дивно)
                     # self.load_extension(extension) # або просто пропустити/видати помилку
                     raise TypeError(f"load_extension is not a coroutine function for {extension}") # Краще видати помилку тут

                # Якщо це корутинна функція, викликаємо з await
                print(f"--- [setup_hook] Спроба: await self.load_extension({extension}) ---")
                await self.load_extension(extension)
                print(f"--- [setup_hook] УСПІХ: {extension} завантажено ---")

            except TypeError as e:
                 print(f"!!! [setup_hook] TypeError при завантаженні {extension}: {e}")
                 traceback.print_exc() # Друкуємо повний traceback
                 load_errors = True
            except Exception as e:
                print(f"!!! [setup_hook] Інша ПОМИЛКА при завантаженні {extension}: {type(e).__name__} - {e}")
                traceback.print_exc() # Друкуємо повний traceback
                load_errors = True
            print("-" * 20) # роздільник

        print("--- [setup_hook] Завершено цикл завантаження когів ---")
        if load_errors:
            print("!!! [setup_hook] Були помилки під час завантаження когів!")
        else:
            print("--- [setup_hook] Всі знайдені коги завантажено успішно.")
        print("--- [MySuperBot] setup_hook КІНЕЦЬ ---")

        # --- СИНХРОНІЗАЦІЯ КОМАНД (ГЛОБАЛЬНО - ТІЛЬКИ ДЛЯ ДІАГНОСТИКИ!) ---
        print("--- [setup_hook] Починаємо ГЛОБАЛЬНУ синхронізацію команд... ---")
        try:
            # Викликаємо sync() без аргументу guild
            synced = await self.tree.sync()
            # Зверни увагу: len(synced) тут покаже кількість УСІХ глобальних команд бота
            print(f"--- [setup_hook] Глобально синхронізовано {len(synced)} команд. Оновлення в Discord може тривати до години! ---")
        except Exception as e:
            print(f"!!! [setup_hook] Помилка ГЛОБАЛЬНОЇ синхронізації: {e}")
            # import traceback
            # traceback.print_exc() # Розкоментуй для деталей помилки
        # --- Кінець блоку синхронізації ---

        print("--- [MySuperBot] setup_hook КІНЕЦЬ ---")
        
    async def on_ready(self):
        print(f'--- !!! ON_READY: бот {self.user} готовий !!! ---')
        if self.db_pool:
            print("--- [on_ready] Пул бази даних існує.")
        else:
            print("--- [on_ready] УВАГА! Пул бази даних = None.")
        print('------')

    async def close(self):
         # Очистка при завершенні роботи бота
         if self.db_pool:
             print("--- [close] Закриваємо пул з'єднань mysql...")
             self.db_pool.close()
             await self.db_pool.wait_closed()
             print("--- [close] Пул з'єднань mysql закрито.")
         await super().close()


# --- Ініціалізація та запуск ---
print("--- [main] Налаштування інтентів... ---")
intents = discord.Intents.default()
intents.members = True
intents.message_content = True # або інші потрібні інтенти

print("--- [main] Створення екземпляра MySuperBot... ---")
bot = MySuperBot(command_prefix=PREFIX, intents=intents)

print("--- [main] Виклик bot.run(TOKEN)... ---")
try:
    bot.run(TOKEN)
except Exception as e:
    print(f"!!! [main] ПОМИЛКА під час bot.run(): {e}")
    traceback.print_exc()

print("--- [main] Скрипт завершив роботу (після bot.run) ---") # Цей рядок зазвичай не виконується