import discord
from discord.ext import commands
from discord import app_commands
from templates import ebmtemp
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from config import *
from typing import Optional

class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def checkadd(self, ctx, member):
        with sqlite3.connect('viter.db') as connection:
            cursor = connection.cursor()

            cursor.execute('SELECT EXISTS(SELECT 1 FROM Users WHERE userid = ?)', (member.id,))
            user_exist = cursor.fetchone()[0]

            print(user_exist)
            
            if user_exist == 0:
                cursor.execute('INSERT INTO Users VALUES (?, ?, ?, ?, ?)', (member.id, "Відсутні", 0, "Опис профілю не встановлений.", None))
                connection.commit()

    @app_commands.command(name='profile', description='Відображення профілю користувача')
    @app_commands.describe(
        member="Учасник, чий профіль показати (якщо не вказано - покаже ваш)" # <--- Опис аргументу
    )
    async def profile(
        self,
        interaction: discord.Interaction,              # <--- interaction замість ctx
        member: Optional[discord.Member] = None        # <--- Необов'язковий аргумент discord.Member
    ):

        member = member or ctx.author

        await self.checkadd(ctx, member)

        with sqlite3.connect('viter.db') as connection:
            cursor = connection.cursor()

            cursor.execute('SELECT * FROM Users WHERE userid = ?', (member.id,))
            user_info_list = cursor.fetchone()

            user_info = {
                "userid": user_info_list[0],
                "adminresponse": user_info_list[1],
                "balance": user_info_list[2],
                "description": user_info_list[3],
                "image": user_info_list[4],
            }

            cursor.execute('SELECT AVG(rate) FROM Responses WHERE receiver = ? AND type = ?', (member.id, "Гравця"))
            playerrate = Decimal(cursor.fetchone()[0] or 0).quantize(Decimal('0.0'), rounding=ROUND_HALF_UP)

            cursor.execute('SELECT AVG(rate) FROM Responses WHERE receiver = ? AND type = ?', (member.id, "Майстра"))
            masterrate = Decimal(cursor.fetchone()[0] or 0).quantize(Decimal('0.0'), rounding=ROUND_HALF_UP)

            cursor.execute("SELECT rowid FROM Users WHERE userid = ?", (member.id,))
            rowid = cursor.fetchone()

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

            connection.commit()

    @app_commands.command(name='set-image', description='Встановити банер профілю')
    @app_commands.describe(
        image_link="Пряме посилання на картинку банера (наприклад, https://... .png)" # <--- Опис аргументу
    )
    async def setimage(
        self,
        interaction: discord.Interaction, # <--- interaction замість ctx
        image_link: str                   # <--- Стандартний тип str (обов'язковий за замовчуванням)
    ):   

        await self.checkadd(ctx, ctx.author)

        with sqlite3.connect('viter.db') as connection:
            cursor = connection.cursor()
            cursor.execute("UPDATE Users SET image = ? WHERE userid = ?", (image_link, ctx.author.id))
            connection.commit()

        await ctx.respond(embed=ebmtemp.create("Успіх", "Посилання встановлено банером профілю! :sparkling_heart:"))

    @app_commands.command(name='set-description', description='Встановити опис профілю')
    @app_commands.describe(
        text="Текст опису вашого профілю" # <--- Опис аргументу
    )
    async def setdescription(
        self,
        interaction: discord.Interaction, # <--- interaction замість ctx
        text: str                         # <--- Стандартний тип str (обов'язковий за замовчуванням)
    ):

        await self.checkadd(ctx, ctx.author)

        with sqlite3.connect('viter.db') as connection:
            cursor = connection.cursor()
            cursor.execute("UPDATE Users SET description = ? WHERE userid = ?", (text, ctx.author.id))
            connection.commit()

        await ctx.respond(embed=ebmtemp.create("Успіх", f"Опис успішно встановлений. :sparkling_heart: \n```{text}```"))


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

        await self.checkadd(ctx, member)

        if not ctx.author.id in MODERATOR_LIST:
            await ctx.respond(embed=ebmtemp.create("Помилка", f"Ви не маєте прав на встановлення адмінського зауваження."), ephemeral=True)
            return

        with sqlite3.connect('viter.db') as connection:
            cursor = connection.cursor()
            cursor.execute("UPDATE Users SET adminresponse = ? WHERE userid = ?", (text, member.id))
            connection.commit()
            
        await ctx.respond(embed=ebmtemp.create("Успіх", f"Адмінське зауваження успішно встановлене. :sparkling_heart: \n```{text}```"))

# Реєстрація cog
async def setup(bot):
    await bot.add_cog(ProfileCog(bot))