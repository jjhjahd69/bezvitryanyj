# main.py
from config import *
import discord
from discord.ext import commands
import asyncio # <--- Перевір, чи імпортовано asyncio
import aiomysql
import os
import logging
from discord import app_commands
from errors import *
import traceback # <--- Імпортуємо traceback для деталей помилки
from database_utils import DatabaseFuncs
from templates import *

print("--- [main] Скрипт запущено ---")

# --- Налаштування логування ---
logging.basicConfig(
    level=logging.DEBUG,
    filename='discord.log',
    filemode='w',  # 'a' — append, 'w' — перезаписувати кожен раз
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)
# ------------------------------------------

class MySuperBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        logging.debug("--- [MySuperBot] __init__ початок ---")
        super().__init__(*args, **kwargs)
        self.db_pool = None
        self.db_utils: DatabaseFuncs | None = None
        logging.debug("--- [MySuperBot] __init__ кінець ---")

    async def setup_hook(self):
        logging.debug("--- [MySuperBot] setup_hook ПОЧАТОК ---") 

        # --- Створення пулу ---
        logging.debug("--- [setup_hook] Спроба створити пул mysql... ---")
        try:
            self.db_pool = await aiomysql.create_pool(
                host=db_host, port=db_port,
                user=db_user, password=db_password, db=db_name,
                minsize=1, maxsize=10, autocommit=True
            )
            if self.db_pool: # Додаткова перевірка не завадить
                self.db_utils = DatabaseFuncs(self.db_pool) # Передаємо сюди створений пул
                logging.debug("--- [setup_hook] Екземпляр DatabaseFuncs УСПІШНО створено! ---")
            else:
                logging.critical("!!! [setup_hook] db_pool не було створено, DatabaseFuncs не може бути ініціалізовано.")
                await self.close()
            
            logging.debug("--- [setup_hook] Пул mysql УСПІШНО створено! ---")
        except Exception as e:
            logging.critical(f"!!! [setup_hook] КРИТИЧНА ПОМИЛКА створення пулу: {e}")
            logging.critical("!!! [setup_hook] Бот не може працювати без бази даних. Зупиняємось.")
            await self.close()
            return

        # --- Завантаження когів ---
        logging.debug("--- [setup_hook] Починаємо завантаження когів ---")
        cogs_dir = './cogs'
        try:
            if not os.path.isdir(cogs_dir):
                logging.critical(f"!!! [setup_hook] ПОМИЛКА: папка '{cogs_dir}' не знайдена!")
                await self.close()
            initial_extensions = [f'cogs.{filename[:-3]}' for filename in os.listdir(cogs_dir) if filename.endswith('.py')]
            logging.debug(f"--- [setup_hook] Знайдені коги: {initial_extensions} ---")
        except Exception as e:
            logging.critical(f"!!! [setup_hook] ПОМИЛКА при отриманні списку когів: {e}")
            await self.close()

        for extension in initial_extensions:

            try:
                # --- Детальна діагностика перед завантаженням ---
                logging.debug("-" * 20) # роздільник для ясності
                logging.debug(f"--- [setup_hook] Готуємось завантажити: {extension} ---")

                logging.debug(f"--- [setup_hook] Спроба: await self.load_extension({extension}) ---")
                await self.load_extension(extension)
                logging.debug(f"--- [setup_hook] УСПІХ: {extension} завантажено ---")

            except Exception as e:
                logging.critical(f"!!! [setup_hook] ПОМИЛКА при завантаженні {extension}: {type(e).__name__} - {e}")
                traceback.print_exc() # Друкуємо повний traceback
                
                await self.close()

        logging.info("--- [setup_hook] Завершено цикл завантаження когів ---")
        logging.debug("--- [MySuperBot] setup_hook КІНЕЦЬ ---")

        logging.debug("--- [setup_hook] Починаємо ГЛОБАЛЬНУ синхронізацію команд... ---")
        try:
            # Викликаємо sync() без аргументу guild
            synced = await self.tree.sync()
            # Зверни увагу: len(synced) тут покаже кількість УСІХ глобальних команд бота
            logging.debug(f"--- [setup_hook] Глобально синхронізовано {len(synced)} команд. Оновлення в Discord може тривати до години! ---")
        except Exception as e:
            logging.debug(f"!!! [setup_hook] Помилка ГЛОБАЛЬНОЇ синхронізації: {e}")
            # import traceback
            # traceback.print_exc() # Розкоментуй для деталей помилки
        # --- Кінець блоку синхронізації ---

        logging.debug("--- [MySuperBot] setup_hook КІНЕЦЬ ---")
        
    async def on_ready(self):
        logging.info(f'--- !!! ON_READY: бот {self.user} готовий !!! ---')

    async def close(self):
         # Очистка при завершенні роботи бота
         if self.db_pool:
             print("--- [close] Закриваємо пул з'єднань mysql...")
             self.db_pool.close()
             await self.db_pool.wait_closed()
             print("--- [close] Пул з'єднань mysql закрито.")
         await super().close()


# --- Ініціалізація та запуск ---
logging.debug("--- [main] Налаштування інтентів... ---")
intents = discord.Intents.default()
intents.members = True
intents.message_content = True # або інші потрібні інтенти

logging.debug("--- [main] Створення екземпляра MySuperBot... ---")
bot = MySuperBot(command_prefix=PREFIX, intents=intents)

@bot.tree.error # <-- Ось тут "вішаємо" обробник на дерево команд
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    # app_commands помилки часто обернуті. original містить оригінальну помилку.
    original_error = getattr(error, 'original', error)

    # --- Ловимо ТВОЇ ВЛАСНІ ЛОГІЧНІ ПОМИЛКИ! ---
    # Перевіряємо, чи помилка є екземпляром нашого базового класу BusinessLogicError
    # Це спрацює для GameNotFoundError, InvalidGameStateError та всіх інших, що від нього успадковані!
    if isinstance(original_error, LogicError):
        logging.info(f"Логічна помилка при виконанні команди {interaction.command.name if interaction.command else 'N/A'}: {original_error.message} (Користувач: {interaction.user.id}, Гільдія: {interaction.guild_id})")

        # Використовуємо ТВІЙ ШАБЛОН для створення ембеду з повідомленням про помилку логіки
        error_embed = ebmtemp.create("Помилка", original_error.message)

        # Відправляємо відповідь користувачу. Важливо перевірити, чи вже була відповідь (defer).
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=error_embed)
        else:
            await interaction.response.send_message(embed=error_embed, ephemeral=True) # ephemeral=True, щоб бачив тільки користувач


    # --- Ловимо ВБУДОВАНІ помилки discord.py (приклади) ---
    elif isinstance(original_error, app_commands.MissingPermissions):
         # Помилка прав доступу discord.py
         logging.warning(f"У користувача {interaction.user.id} недостатньо прав для команди {interaction.command.name if interaction.command else 'N/A'}. Потрібні: {', '.join(original_error.missing_permissions)}")
         error_message = f"У вас недостатньо прав для виконання цієї команди. Потрібні права: **{', '.join(original_error.missing_permissions)}**"
         error_embed = ebmtemp.create("Немає прав", error_message)

         if interaction.response.is_done():
              await interaction.edit_original_response(embed=error_embed)
         else:
              await interaction.response.send_message(embed=error_embed, ephemeral=True)


    # --- Ловимо будь-які інші НЕОЧІКУВАНІ помилки (технічні) ---
    else:
        # Це можуть бути помилки в твоєму коді, помилки БД, які не спіймав декоратор @db_operation (хоча він має їх ловити), тощо.
        logging.error(f"!!! Неочікувана КРИТИЧНА помилка в слеш-команді {interaction.command.name if interaction.command else 'N/A'}: {original_error}", exc_info=True) # exc_info=True для повного traceback

        # Використовуємо шаблон для критичної помилки
        critical_error_embed = ebmtemp.create("Критична помилка", "На жаль, сталася неочікувана помилка під час виконання команди. Розробники вже повідомлені!") # Або інше повідомлення

        if interaction.response.is_done():
            await interaction.edit_original_response(embed=critical_error_embed)
        else:
            await interaction.response.send_message(embed=critical_error_embed, ephemeral=True)


logging.debug("--- [main] Виклик bot.run(TOKEN)... ---")
try:
    bot.run(TOKEN)
except Exception as e:
    logging.critical(f"!!! [main] ПОМИЛКА під час bot.run(): {e}")
    traceback.print_exc()