import discord
from discord.ext import commands 
from discord.utils import get
import sqlite3
from templates import ebmtemp
from datetime import datetime
import time
import json
from config import *

class GamesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    class CreateGameModal(discord.ui.Modal):
        def __init__(self, type, ctx, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)

            self.type = type
            self.ctx = ctx

            self.add_item(discord.ui.InputText(label="Назва гри", max_length=100))
            self.add_item(discord.ui.InputText(label="Загальний, короткий опис гри", style=discord.InputTextStyle.long, max_length=1500))

        async def callback(self, interaction: discord.Interaction):
            with sqlite3.connect('viter.db') as connection:
                cursor = connection.cursor()

                game_name = self.children[0].value
                game_description = self.children[1].value
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                cursor.execute('''
                INSERT INTO Games (gamename, gamedescription, gametype, gamecreatorid, gamemasters, gameplayers, gamestatus, gamecreationdate) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (game_name, game_description, self.type, self.ctx.author.id, json.dumps([]), json.dumps([]), 1, timestamp))

                game_id = cursor.lastrowid
                await interaction.response.send_message(embed=ebmtemp.create("Успіх", f"Гра `{game_name}`успішно додана до реєстру! Її унікальний індитифікатор: `ID {game_id}`"), ephemeral=True)

                connection.commit()


    @commands.slash_command(name='create-game', description='Створити гру')
    async def creategame(
        self,
        ctx,
        type: discord.Option(str, choices=["ТРГ", "ВПГ", "ДСГ", "КШГ", "НРГ"], description="Тип гри")
        ):    

        modal = self.CreateGameModal(title="Створення гри", type=type, ctx=ctx)
        await ctx.send_modal(modal)

    @commands.slash_command(name='delete-game', description='Видалити гру')
    async def deletegame(
        self,
        ctx,
        game_id: discord.Option(int, description="Унікальний індитифікатор гри.")
        ):

        with sqlite3.connect('viter.db') as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM Games WHERE rowid = ?", (game_id, ))

            game = cursor.fetchone()

            if game is None:
                await ctx.respond(embed=ebmtemp.create("Помилка", "Вказаної вами гри не існує."), ephemeral=True)
                return

            elif game[7] > 2:
                await ctx.respond(embed=ebmtemp.create("Помилка", "Ви не можете видалити гру, що йде або завершена."), ephemeral=True)
                return

            if ctx.author.id == game[3] or ctx.author.id in MODERATOR_LIST:
                cursor.execute("DELETE FROM Games WHERE rowid = ?", (game_id, ))
                await ctx.respond(embed=ebmtemp.create("Успіх", f"Гра `{game[0]} (ID {game_id})` успішно видалена з реєстру."), ephemeral=True)
                connection.commit()

            else:
                await ctx.respond(embed=ebmtemp.create("Помилка", "Для вказаної гри, ви не маєте повноважень для видалення."), ephemeral=True)


    @commands.slash_command(name='game-member', description='Керування учасниками гри')
    async def gamemember(
        self,
        ctx,
        action: discord.Option(str, choices=["Додати до гри", "Видалити з гри"], description="Дія"),
        member: discord.Option(discord.Member, description="Учасник"),
        game_id: discord.Option(int, description="Унікальний індитифікатор гри."),
        role: discord.Option(str, choices=["Майстер", "Гравець"])
        ):  

        with sqlite3.connect('viter.db') as connection:
            cursor = connection.cursor()

            cursor.execute('SELECT * FROM Games WHERE rowid = ?', (game_id,))
            game_info = cursor.fetchone()

            if not game_info:
                await ctx.respond(embed=ebmtemp.create("Помилка", f"Вказаної вами гри не існує."), ephemeral=True)
                return

            game_creator_id = game_info[3]
            game_roles = None

            game_players = json.loads(game_info[5])
            game_masters = json.loads(game_info[4])
            game_status = game_info[6]

            if ctx.author.id != game_creator_id and not ctx.author.id in MODERATOR_LIST:
                await ctx.respond(embed=ebmtemp.create("Помилка", f"Ви не маєте права на керування учасниками цієї гри."), ephemeral=True)
                return

            if game_status == 4 and not ctx.author.id in MODERATOR_LIST:
                await ctx.respond(embed=ebmtemp.create("Помилка", f"Керувати завершеними іграми заборонено."), ephemeral=True)
                return
                
            if role == "Майстер":

                if action == "Додати до гри":

                    if member.id in game_masters:
                        await ctx.respond(embed=ebmtemp.create("Помилка", f"Користувач <@{member.id}> вже є у грі"), ephemeral=True)
                        return

                    game_masters.append(member.id)
                    cursor.execute("UPDATE Games SET gamemasters = ? WHERE rowid = ?", (json.dumps(game_masters), game_id))
                    await ctx.respond(embed=ebmtemp.create("Успіх", f"Користувач <@{member.id}> став майстром гри!"), ephemeral=True)

                else:

                    if member.id not in game_masters:
                        await ctx.respond(embed=ebmtemp.create("Помилка", f"Користувач <@{member.id}> не був майстром гри!"), ephemeral=True)
                        return

                    game_masters.remove(member.id)
                    cursor.execute("UPDATE Games SET gamemasters = ? WHERE rowid = ?", (json.dumps(game_masters), game_id))
                    await ctx.respond(embed=ebmtemp.create("Успіх", f"Користувач <@{member.id}> більше не є майстром гри!"), ephemeral=True)
                    

            else:

                if action == "Додати до гри":

                    if member.id in game_players:
                        await ctx.respond(embed=ebmtemp.create("Помилка", f"Користувач <@{member.id}> вже є учасником гри"), ephemeral=True)
                        return

                    game_players.append(member.id)
                    cursor.execute("UPDATE Games SET gameplayers = ? WHERE rowid = ?", (json.dumps(game_players), game_id))
                    await ctx.respond(embed=ebmtemp.create("Успіх", f"Користувач <@{member.id}> тепер учасник гри!"), ephemeral=True)

                else:

                    if member.id not in game_players:
                        await ctx.respond(embed=ebmtemp.create("Помилка", f"Користувач <@{member.id}> не був учасником гри!"), ephemeral=True)
                        return

                    game_players.remove(member.id)
                    cursor.execute("UPDATE Games SET gameplayers = ? WHERE rowid = ?", (json.dumps(game_players), game_id))
                    await ctx.respond(embed=ebmtemp.create("Успіх", f"Користувач <@{member.id}> більше не є учасником гри!"), ephemeral=True)

            connection.commit()

    @commands.slash_command(name='set-game-status', description='Встановити статус грі')
    async def setgamestatus(
        self,
        ctx,
        game_id: discord.Option(int, description="Унікальний індитифікатор гри."),
        status: discord.Option(str, choices=["Зареєстрована", "Затверджена", "Йде", "Закінчена"]) # 4 статуси: 1 Зареєстрована, 2 Підтверджена, 3 Проходить, 4 Закінчена
        ):  

        if not ctx.author.id in MODERATOR_LIST:
            await ctx.respond(embed=ebmtemp.create("Помилка", f"Ви не маєте права на зміну статусу гри."), ephemeral=True)
            return
        
        with sqlite3.connect('viter.db') as connection:
            cursor = connection.cursor()

            cursor.execute('SELECT EXISTS(SELECT 1 FROM Games WHERE rowid = ?)', (game_id, ))

            exist = cursor.fetchone()[0]

            if exist == False:
                await ctx.respond(embed=ebmtemp.create("Помилка", "Вказаної гри не існує."), ephemeral=True)
                return

            choice = {
                "Зареєстрована": 1, 
                "Затверджена": 2, 
                "Йде": 3, 
                "Закінчена": 4
            }

            cursor.execute('UPDATE Games SET gamestatus = ? WHERE rowid = ?', (choice[str(status)], game_id))
            connection.commit()

        await ctx.respond(embed=ebmtemp.create("Успіх", f"Гра `ID {game_id}` успішно отримала статус `{status} ({choice[str(status)]})`"), ephemeral=True)

    @commands.slash_command(name='game-info', description='Інформація про гру')
    async def gameinfo(
        self,
        ctx,
        game_id: discord.Option(int, description="Унікальний індитифікатор гри."),
        ):

        with sqlite3.connect('viter.db') as connection:
            cursor = connection.cursor()

            cursor.execute("SELECT * FROM Games WHERE rowid = ?", (game_id, ))
            try:
                game_name, game_description, game_type, game_creator_id, game_masters, game_players, game_status, game_creation_date = cursor.fetchone()
            except:
                await ctx.respond(embed=ebmtemp.create("Помилка", "Вказаної гри не існує."), ephemeral=True)
                return

            game_masters_new = ""
            game_players_new = ""

            for i in json.loads(game_masters):
                game_masters_new += f"<@{i}> "

            for i in json.loads(game_players):
                game_players_new += f"<@{i}> "

            game_status_choice = {
                "1":    "Зареєстрована",
                "2":    "Затверджена",
                "3":    "Йде",
                "4":    "Закінчена"
            }

            embed = discord.Embed(
                title=f"Гра: {game_name}",
                description=f"**Опис** \n{game_description}",
                color=discord.Color(value=0x2F3136),  # можна обрати інший колір
            )
            # додаємо поля
            embed.add_field(name="Тип", value=f"{game_type}", inline=True)
            embed.add_field(name="Творець", value=f"<@{game_creator_id}>", inline=True)
            embed.add_field(name="Ведучі", value=f"{game_masters_new}", inline=True)
            embed.add_field(name="Статус", value=f"{game_status_choice[str(game_status)]}", inline=True)
            embed.add_field(name="Гравці", value=f"{game_players_new}", inline=False)

            # додаємо автора
            # embed.set_author(name=game_creator_object.name, icon_url=game_creator_object.avatar.url)

            # додаємо зображення
            # embed.set_image(url=user_info["image"])  # заміни на своє

            # додаємо футер
            embed.set_footer(text=f"ID {game_id}")

            # відправляємо ембед
            await ctx.respond(embed=embed)

        #@commands.slash_command(name='game-info', description='Перелік існуючих ігор')
        #async def gameinfo(
        #    self,
        #    ctx,
        #    member: discord.Option(discord.Member, required = False, description = "Користувач")
        #    ):
        #
        #    print("s")

# Реєструємо cog
def setup(bot):
    bot.add_cog(GamesCog(bot))