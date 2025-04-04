import discord
from discord.ext import commands
from discord import app_commands
from templates import ebmtemp
import sqlite3
from datetime import datetime
import math
import json
from config import *
from typing import Optional

class RespondsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class RespondModal(discord.ui.Modal):
        def __init__(self, member, gameid, ctx, type, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)

            self.member = member
            self.gameid = gameid
            self.ctx = ctx
            self.type = type

            self.add_item(discord.ui.InputText(label="Текст відгуку", max_length=1000, style=discord.InputTextStyle.long))
            self.add_item(discord.ui.InputText(label="Оцінка (від 1 до 10)", max_length=2))

        async def callback(self, interaction: discord.Interaction):
            respond_text = self.children[0].value
            respond_rate = int(self.children[1].value)

            if respond_rate not in range(1, 11):
                await interaction.response.send_message(embed=ebmtemp.create("Помилка", "Вказана вами оцінка виходить за межі оцінювання. (Від 1 до 10 включно)"), ephemeral=True)
                return

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            with sqlite3.connect('viter.db') as connection:
                cursor = connection.cursor()

                cursor.execute('INSERT INTO Responses (receiver, writer, type, gameid, text, rate, date) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                                (self.member.id, self.ctx.author.id, self.type, self.gameid, respond_text, respond_rate, timestamp))
                connection.commit()

            await interaction.response.send_message(embed=ebmtemp.create("Успіх", "Ваш відгук успішно доданий!"), ephemeral=True)

    @app_commands.command(name='to-respond', description='Додати відгук користувачу')
    @app_commands.describe(
        member="Учасник, якому ви залишаєте відгук",
        game_id="Унікальний індитифікатор гри, в якій ви брали участь", # Перейменував gameid -> game_id для консистентності
        role_type="Ви пишете відгук на користувача як на?" # Перейменував type -> role_type
    )
    @app_commands.choices(role_type=[ # Визначаємо варіанти для 'role_type'
        app_commands.Choice(name="Гравця", value="player"), # Значення, яке отримає код
        app_commands.Choice(name="Майстра", value="master")
    ])
    async def torespond(
        self,
        interaction: discord.Interaction,    # <--- interaction замість ctx
        member: discord.Member,              # <--- Стандартний тип
        game_id: int,                        # <--- Стандартний тип, перейменовано
        role_type: app_commands.Choice[str]  # <--- Тип Choice, перейменовано
    ):

        if ctx.author.id == member.id:
            await ctx.respond(embed=ebmtemp.create("Помилка", "Ви не можете залишити відгук на самого себе, як би вам не хотілося :С"), ephemeral=True)
            return

        with sqlite3.connect('viter.db') as connection:
            cursor = connection.cursor()

            cursor.execute('SELECT * FROM Games WHERE rowid = ?', (gameid, ))
            game_info = cursor.fetchone()

            if game_info is None:
                await ctx.respond(embed=ebmtemp.create("Помилка", "Вказана вами гра не існує."), ephemeral=True)
                return

            all_game_members_id = json.loads(game_info[4]) + json.loads(game_info[5])
            print(all_game_members_id)
            status = game_info[6]

            if ctx.author.id not in all_game_members_id:
                await ctx.respond(embed=ebmtemp.create("Помилка", "Ви не були учасником цієї гри."), ephemeral=True)
                return

            if member.id not in all_game_members_id:
                await ctx.respond(embed=ebmtemp.create("Помилка", "Користувач не був учасником цієї гри."), ephemeral=True)
                return

            if status != 4: # 4 статуси: 1 Зареєстрована, 2 Підтверджена, 3 Проходить, 4 Закінчена
                await ctx.respond(embed=ebmtemp.create("Помилка", "Ви не можете написати відгук у рамках незавершеної гри."), ephemeral=True)
                return

            if type == "Гравця" and member.id in json.loads(game_info[4]):
                await ctx.respond(embed=ebmtemp.create("Помилка", "Вказаний вами користувач був ведучим цієї гри. Написання відгуку як на гравця неможливе."), ephemeral=True)
                return

            if type == "Майстра" and member.id in json.loads(game_info[5]):
                await ctx.respond(embed=ebmtemp.create("Помилка", "Вказаний вами користувач був гравцем цієї гри. Написання відгуку як на майстра неможливе."), ephemeral=True)
                return

            cursor.execute('SELECT EXISTS( SELECT 1 FROM Responses WHERE receiver = ? AND writer = ? AND gameid = ? AND type = ?)', (member.id, ctx.author.id, gameid, type))

            exist = cursor.fetchone()[0]

            if exist == True:
                await ctx.respond(embed=ebmtemp.create("Помилка", "У цій грі ви вже написали відгук вказаного типу на цього користувача."), ephemeral=True)
                return

            modal = self.RespondModal(title="Написання відгуку", member=member, gameid=gameid, ctx=ctx, type=type)

        await ctx.send_modal(modal)

    async def get_responds(self, member_id, review_type, page, page_size=3):
        offset = (page - 1) * page_size
        with sqlite3.connect('viter.db') as connection:
            cursor = connection.cursor()
            cursor.execute('''
            SELECT writer, type, gameid, text, rate, date
            FROM Responses 
            WHERE receiver = ? AND type = ?
            ORDER BY datetime(date) DESC
            LIMIT ? OFFSET ?
            ''', (member_id, review_type, page_size, offset))
            return cursor.fetchall()

    async def get_total_reviews(self, member_id, review_type):
        with sqlite3.connect('viter.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM Responses WHERE receiver = ? AND type = ?', (member_id, review_type))
            return cursor.fetchone()[0]

    class ReviewsView(discord.ui.View):
        def __init__(self, user_id, review_type, page, bot, ctx):
            super().__init__(timeout=None)
            self.user_id = user_id
            self.review_type = review_type
            self.page = page
            self.bot = bot 
            self.ctx = ctx

            # Створюємо Select меню
            select = discord.ui.Select(
                placeholder="Виберіть тип відгуків",
                options=[
                    discord.SelectOption(label="Гравця", value="Гравця"),
                    discord.SelectOption(label="Майстра", value="Майстра")
                ]
            )
            select.callback = self.select_callback
            self.add_item(select)

            # Створюємо кнопки
            self.prev_button = discord.ui.Button(label="⬅️", style=discord.ButtonStyle.primary)
            self.next_button = discord.ui.Button(label="➡️", style=discord.ButtonStyle.primary)
            
            self.prev_button.callback = self.prev_page_callback
            self.next_button.callback = self.next_page_callback
            
            self.add_item(self.prev_button)
            self.add_item(self.next_button)

        async def select_callback(self, interaction: discord.Interaction):
            self.review_type = interaction.data['values'][0]
            self.page = 1
            await self.update_message(interaction)

        async def prev_page_callback(self, interaction: discord.Interaction):
            if self.page > 1:
                self.page -= 1
                await self.update_message(interaction)

        async def next_page_callback(self, interaction: discord.Interaction):
            self.page += 1
            await self.update_message(interaction)

        async def update_message(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("RespondsCog")
            reviews = await cog.get_responds(self.user_id, self.review_type, self.page)
            total_reviews = await cog.get_total_reviews(self.user_id, self.review_type)
            total_pages = math.ceil(total_reviews / 5)

            embed = discord.Embed(
                title=f"Відгуки на користувача",
                description=f"Тип: {self.review_type}, сторінка {self.page}/{total_pages}", color=discord.Color(value=0x2F3136),
            )

            embed.set_author(name=self.ctx.guild.get_member(self.user_id).name, icon_url=self.ctx.guild.get_member(self.user_id).avatar.url)
            
            for review in reviews:
                writer, review_type, game_id, review_text, rating, review_date = review
                embed.add_field(
                    name=f"Від: {await self.bot.fetch_user(writer)} | Гра: `ID {game_id}`",
                    value=f">>> Оцінка: {rating}/10 ⭐\nДата: {review_date}\nВідгук: {review_text}\nКористувач: <@{writer}>",
                    inline=False
                )

            self.prev_button.disabled = self.page <= 1
            self.next_button.disabled = self.page >= total_pages
            
            await interaction.response.edit_message(embed=embed, view=self)

    @app_commands.command(name='responses', description='Відображення відгуків користувача')
    @app_commands.describe(
        member="Учасник, чиї відгуки показати (за замовчуванням - ваші)",
        review_role_type="Тип відгуків для фільтрації (необов'язково)" # Перейменував для ясності
    )
    @app_commands.choices(review_role_type=[ # Визначаємо варіанти для 'review_role_type'
        app_commands.Choice(name="Як Гравця", value="player"),
        app_commands.Choice(name="Як Майстра", value="master")
    ])
    async def responses(
        self,
        interaction: discord.Interaction,               # <--- interaction замість ctx
        member: Optional[discord.Member] = None,        # <--- Необов'язковий учасник
        review_role_type: Optional[app_commands.Choice[str]] = None # <--- Необов'язковий вибір типу
    ):

        member = member or ctx.author
        review_type = review_type or "Гравця"
        
        page = 1
        reviews = await self.get_responds(member.id, review_type, page)

        total_reviews = await self.get_total_reviews(member.id, review_type)
        total_pages = math.ceil(total_reviews / 3)

        embed = discord.Embed(title=f"Відгуки на користувача", description=f"Тип: {review_type}, сторінка {page}/{total_pages}", color=discord.Color(value=0x2F3136))
        embed.set_author(name=member.name, icon_url=member.avatar.url)

        for review in reviews:
            writer, review_type, game_id, review_text, rating, review_date = review
            embed.add_field(name=f"Від: {await self.bot.fetch_user(writer)} | Гра: `ID {game_id}`", value=f">>> Оцінка: {rating}/10 ⭐\nДата: {review_date}\nВідгук: {review_text}\nКористувач: <@{writer}>", inline=False)

        view = self.ReviewsView(member.id, review_type, page, self.bot, ctx)
        await ctx.respond(embed=embed, view=view, ephemeral=True)

# Реєстрація cog
async def setup(bot):
    await bot.add_cog(RespondsCog(bot))