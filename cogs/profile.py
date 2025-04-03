import discord
from discord.ext import commands
from templates import ebmtemp
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from config import *

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

    @commands.slash_command(name='profile', description='Відображення профілю користувача')
    async def profile(
    self,
    ctx,
    member: discord.Option(discord.Member, required = False, description="Учасник")
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

    @commands.slash_command(name='set-image', description='Встановити банер профілю')
    async def setimage(
        self,
        ctx,
        image_link: discord.Option(str, required = True, description="Пряме посилання на картинку банера.")
        ):    

        await self.checkadd(ctx, ctx.author)

        with sqlite3.connect('viter.db') as connection:
            cursor = connection.cursor()
            cursor.execute("UPDATE Users SET image = ? WHERE userid = ?", (image_link, ctx.author.id))
            connection.commit()

        await ctx.respond(embed=ebmtemp.create("Успіх", "Посилання встановлено банером профілю! :sparkling_heart:"))

    @commands.slash_command(name='set-description', description='Встановити опис профілю')
    async def setdescription(
        self,
        ctx,
        text: discord.Option(str, required = True, description="Опис профілю")
        ):    

        await self.checkadd(ctx, ctx.author)

        with sqlite3.connect('viter.db') as connection:
            cursor = connection.cursor()
            cursor.execute("UPDATE Users SET description = ? WHERE userid = ?", (text, ctx.author.id))
            connection.commit()

        await ctx.respond(embed=ebmtemp.create("Успіх", f"Опис успішно встановлений. :sparkling_heart: \n```{text}```"))


    @commands.slash_command(name='set-admin-response', description='Встановити адмінське зауваження користувачу.')
    async def setadminresponse(
        self,
        ctx,
        member: discord.Option(discord.Member, description="Учасник"),
        text: discord.Option(str, required = True, description="Текст адмінського відгуку")
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
def setup(bot):
    bot.add_cog(ProfileCog(bot))