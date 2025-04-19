import discord
from discord.ext import commands
from discord import app_commands
from templates import ebmtemp
import aiomysql
from decimal import Decimal, ROUND_HALF_UP
from config import *
from typing import Optional

class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def checkadd(self, interaction, member):

        print(f"[CHECKADD] Користувач {member.name} перевіряється")
        pool = self.bot.db_pool
        if pool is None:
            # Якщо пул не створено (помилка при старті бота), повідомляємо і виходимо
            await interaction.edit_original_response(content="Помилка: База даних недоступна.") # Або інша відповідь
            return

        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    sql_query = "SELECT 1 FROM users WHERE userid = %s LIMIT 1"
                    query_params = (member.id,)
                    await cursor.execute(sql_query, query_params)
                    user_exist = await cursor.fetchone()

                    print(f"[CHECKADD] user_exist = {user_exist} у користувача {member.name}")

                    if not user_exist:
                        print(f"[CHECKADD] Користувач {member.name} не існує, виконую додавання.")
                        sql_query = """
                            INSERT INTO users (userid, adminresponse, balance, description, image)
                            VALUES (%s, %s, %s, %s, %s)
                        """
                        query_params = (member.id, "Відсутні", 0, "Опис профілю не встановлений.", None,)
                        await cursor.execute(sql_query, query_params)
            
        except aiomysql.Error as db_err:
            # Обробка помилок, специфічних для бази даних
            print(f"Помилка бази даних: {db_err}")
            # Повідом користувачу про помилку
            # await interaction.edit_original_response(content="Помилка бази даних...")
        except Exception as e:
            # Обробка інших можливих помилок
            print(f"Інша помилка: {e}")
            # await interaction.edit_original_response(content="Сталася помилка...")

    @app_commands.command(name='profile', description='Відображення профілю користувача')
    @app_commands.describe(
        member="Учасник, чий профіль показати (якщо не вказано - покаже ваш)" # <--- Опис аргументу
    )
    async def profile(
        self,
        interaction: discord.Interaction,              # <--- interaction замість ctx
        member: Optional[discord.Member] = None        # <--- Необов'язковий аргумент discord.Member
    ):  

        await interaction.response.defer(ephemeral=True, thinking=True)
        member = member or interaction.user
        await self.checkadd(interaction, member)

        pool = self.bot.db_pool
        if pool is None:
            # Якщо пул не створено (помилка при старті бота), повідомляємо і виходимо
            await interaction.edit_original_response(content="Помилка: База даних недоступна.") # Або інша відповідь
            return

        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    sql_query = "SELECT * FROM users WHERE userid = %s"
                    query_params = (member.id,)
                    await cursor.execute(sql_query, query_params)
                    user_info = await cursor.fetchone()

                    await cursor.execute('SELECT AVG(rate) AS avg_rate FROM responses WHERE receiver = %s AND type = %s', (member.id, 2))
                    playerrate_dict = await cursor.fetchone()
                    playerrate = Decimal(playerrate_dict["avg_rate"] or 0).quantize(Decimal('0.0'), rounding=ROUND_HALF_UP)

                    await cursor.execute('SELECT AVG(rate) AS avg_rate FROM responses WHERE receiver = %s AND type = %s', (member.id, 1))
                    masterrate_dict = await cursor.fetchone()
                    masterrate = Decimal(masterrate_dict["avg_rate"] or 0).quantize(Decimal('0.0'), rounding=ROUND_HALF_UP)
                
                    await cursor.execute("SELECT id FROM users WHERE userid = %s", (member.id,))
                    user_id = await cursor.fetchone()

                    embed = discord.Embed(
                        title="Профіль користувача",
                        description=f"**Про себе** \n{user_info['description']}",
                        color=discord.Color(value=0x2F3136),  # можна обрати інший колір
                    )
                    # додаємо поля
                    embed.add_field(name="Рейтинг (Гравця)", value=f"{playerrate}/10", inline=True)
                    embed.add_field(name="Рейтинг (Майстра)", value=f"{masterrate}/10", inline=True)
                    embed.add_field(name=f"🪙 {user_info['balance']}", value="", inline=True)
                    embed.add_field(name="Зауваження адміністрації", value=user_info["adminresponse"], inline=False)

                    # додаємо автора
                    embed.set_author(name=member.name, icon_url=member.avatar.url)

                    # додаємо зображення
                    embed.set_image(url=user_info["image"])  # заміни на своє

                    # додаємо футер
                    embed.set_footer(text=f"ID {user_id["id"]}")

                    # відправляємо ембед
                    await interaction.edit_original_response(embed=embed)

        except aiomysql.Error as db_err:
            # Обробка помилок, специфічних для бази даних
            print(f"Помилка бази даних: {db_err}")
            # Повідом користувачу про помилку
            # await interaction.edit_original_response(content="Помилка бази даних...")
        except Exception as e:
            # Обробка інших можливих помилок
            print(f"Інша помилка: {e}")
            # await interaction.edit_original_response(content="Сталася помилка...")

            embed = discord.Embed(
                title="Профіль користувача",
                description=f"**Про себе** \n{user_info['description']}",
                color=discord.Color(value=0x2F3136),  # можна обрати інший колір
            )
            # додаємо поля
            embed.add_field(name="Рейтинг (Гравця)", value=f"{playerrate}/10", inline=True)
            embed.add_field(name="Рейтинг (Майстра)", value=f"{masterrate}/10", inline=True)
            embed.add_field(name=f"🪙 {user_info['balance']}", value="", inline=True)
            embed.add_field(name="Зауваження адміністрації", value=user_info["adminresponse"], inline=False)

            # додаємо автора
            embed.set_author(name=member.name, icon_url=member.avatar.url)

            # додаємо зображення
            embed.set_image(url=user_info["image"])  # заміни на своє

            # додаємо футер
            embed.set_footer(text=f"ID {rowid[0]}")

            # відправляємо ембед
            await ctx.respond(embed=embed)

    @app_commands.command(name='set-image', description='Встановити банер профілю')
    @app_commands.describe(
        image_link="Пряме посилання на картинку банера (наприклад, https://... .png)" # <--- Опис аргументу
    )
    async def setimage(
        self,
        interaction: discord.Interaction, # <--- interaction замість ctx
        image_link: str                   # <--- Стандартний тип str (обов'язковий за замовчуванням)
    ):   

        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.checkadd(interaction, interaction.user)

        pool = self.bot.db_pool
        if pool is None:
            # Якщо пул не створено (помилка при старті бота), повідомляємо і виходимо
            await interaction.edit_original_response(content="Помилка: База даних недоступна.") # Або інша відповідь
            return
    
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    sql_query = "UPDATE responses SET image = %s WHERE userid = %s"
                    query_params = (image_link, interaction.user.id,)
                    await cursor.execute(sql_query, query_params)

                    await interaction.edit_original_response(embed=ebmtemp.create("Успіх", "Посилання встановлено банером профілю! :sparkling_heart:"))

        except aiomysql.Error as db_err:
            # Обробка помилок, специфічних для бази даних
            print(f"Помилка бази даних: {db_err}")
            # Повідом користувачу про помилку
            # await interaction.edit_original_response(content="Помилка бази даних...")
        except Exception as e:
            # Обробка інших можливих помилок
            print(f"Інша помилка: {e}")
            # await interaction.edit_original_response(content="Сталася помилка...")

    @app_commands.command(name='set-description', description='Встановити опис профілю')
    @app_commands.describe(
        text="Текст опису вашого профілю" # <--- Опис аргументу
    )
    async def setdescription(
        self,
        interaction: discord.Interaction, # <--- interaction замість ctx
        text: str                         # <--- Стандартний тип str (обов'язковий за замовчуванням)
    ):

        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.checkadd(interaction, interaction.user)

        pool = self.bot.db_pool
        if pool is None:
            # Якщо пул не створено (помилка при старті бота), повідомляємо і виходимо
            await interaction.edit_original_response(content="Помилка: База даних недоступна.") # Або інша відповідь
            return

        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    sql_query = "UPDATE users SET description = %s WHERE userid = %s"
                    query_params = (text, interaction.user.id, )
                    await cursor.execute(sql_query, query_params)

                    await interaction.edit_original_response(embed=ebmtemp.create("Успіх", f"Опис успішно встановлений. :sparkling_heart: \n```{text}```"))

            
        except aiomysql.Error as db_err:
            # Обробка помилок, специфічних для бази даних
            print(f"Помилка бази даних: {db_err}")
            # Повідом користувачу про помилку
            # await interaction.edit_original_response(content="Помилка бази даних...")
        except Exception as e:
            # Обробка інших можливих помилок
            print(f"Інша помилка: {e}")
            # await interaction.edit_original_response(content="Сталася помилка...")


    @app_commands.command(name='set-admin-response', description='Встановити адмінське зауваження користувачу.')
    @app_commands.describe(
        member="Учасник, якому встановлюється зауваження", # <--- Опис аргументу
        text="Текст адмінського зауваження"                # <--- Опис аргументу
    )
    async def setadminresponse(
        self,
        interaction: discord.Interaction, # <--- interaction замість ctx
        member: discord.Member,           # <--- Стандартний тип discord.Member
        text: str                         # <--- Стандартний тип str
    ):

        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.checkadd(interaction, member)    

        if not interaction.user.id in MODERATOR_LIST:
            await interaction.edit_original_response(embed=ebmtemp.create("Помилка", f"Ви не маєте прав на встановлення адмінського зауваження."))
            return

        pool = self.bot.db_pool
        if pool is None:
            # Якщо пул не створено (помилка при старті бота), повідомляємо і виходимо
            await interaction.edit_original_response(content="Помилка: База даних недоступна.") # Або інша відповідь
            return

        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    sql_query = "UPDATE users SET adminresponse = %s WHERE userid = %s"
                    query_params = (text, member.id, )
                    await cursor.execute(sql_query, query_params)

                    await interaction.edit_original_response(embed=ebmtemp.create("Успіх", f"Адмінське зауваження успішно встановлене. :sparkling_heart: \n```{text}```"))

            
        except aiomysql.Error as db_err:
            # Обробка помилок, специфічних для бази даних
            print(f"Помилка бази даних: {db_err}")
            # Повідом користувачу про помилку
            # await interaction.edit_original_response(content="Помилка бази даних...")
        except Exception as e:
            # Обробка інших можливих помилок
            print(f"Інша помилка: {e}")
            # await interaction.edit_original_response(content="Сталася помилка...")

# Реєстрація cog
async def setup(bot):
    await bot.add_cog(ProfileCog(bot))