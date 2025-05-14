import discord
from discord import app_commands
from discord.ext import commands 
from discord.utils import get
from discord import ui
from templates import ebmtemp
import time
import json
import aiomysql
from config import *
from typing import Optional
from errors import *

class GamesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    class CreateGameModal(ui.Modal): # Використовуємо ui.Modal
        def __init__(self, bot, game_type_value: str, original_interaction: discord.Interaction, *args, **kwargs) -> None:
            super().__init__(title="Створення гри", *args, **kwargs)

            self.game_type = game_type_value
            self.bot = bot
            self.original_interaction = original_interaction

            # --- Виправлено тут: InputText -> TextInput ---
            self.add_item(ui.TextInput( # <--- Змінено на TextInput
                label="Назва гри",
                placeholder="Введіть назву вашої гри",
                max_length=100
                # Тут можна додати інші параметри TextInput, якщо потрібно
            ))
            # --- Виправлено тут: InputText -> TextInput та стиль ---
            self.add_item(ui.TextInput( # <--- Змінено на TextInput
                label="Загальний, короткий опис гри",
                placeholder="Опишіть суть гри, сеттінг...",
                style=discord.TextStyle.paragraph, # <--- Змінено на discord.TextStyle.paragraph (для багаторядкового тексту)
                max_length=1500
            ))

        async def on_submit(self, interaction: discord.Interaction):
                # Спочатку відкладаємо відповідь
                await interaction.response.defer(ephemeral=True, thinking=True)

                # Отримуємо дані з полів модалки
                game_name = self.children[0].value
                game_description = self.children[1].value
                creator_id = interaction.user.id

                game_id = await self.bot.db_utils.create_game(game_name, game_description, self.game_type, creator_id)

                # Готуємо embed
                success_embed = ebmtemp.create("Успіх", f"Гра `{game_name}` успішно додана до реєстру! Її унікальний індитифікатор: `ID {game_id}`")

                # Надсилаємо відповідь користувачу

                await interaction.followup.send(embed=success_embed, ephemeral=True)



    @app_commands.command(name='create-game', description='Створити гру')
    @app_commands.describe(game_type="Оберіть тип гри, яку створюєте")
    @app_commands.choices(game_type=[
        app_commands.Choice(name="ТРГ", value="ТРГ"),
        app_commands.Choice(name="ВПГ", value="ВПГ"),
        app_commands.Choice(name="ДСГ", value="ДСГ"),
        app_commands.Choice(name="КШГ", value="КШГ"),
        app_commands.Choice(name="НРГ", value="НРГ")
    ])
    async def creategame(
        self,
        interaction: discord.Interaction,      # <--- interaction
        game_type: app_commands.Choice[str]    # <--- game_type як Choice
    ):
        # Отримуємо рядкове значення типу гри
        selected_game_type = game_type.value

        # Створюємо екземпляр модального вікна, передаючи тип гри та початкову взаємодію
        modal = self.CreateGameModal(bot=self.bot, game_type_value=selected_game_type, original_interaction=interaction)

        # Надсилаємо модальне вікно користувачу
        await interaction.response.send_modal(modal)

    @app_commands.command(name='delete-game', description='Видалити гру')
    @app_commands.describe(
        game_id="Унікальний індитифікатор гри." # Опис аргументу
    )
    async def deletegame(
        self,
        interaction: discord.Interaction, # 1. Використовуємо interaction
        game_id: int
    ):
        # 2. Завжди відкладай відповідь при роботі з БД
        await interaction.response.defer(ephemeral=True)

        game = await self.bot.db_utils.get_game_info(game_id) # Отримуємо результат асинхронно

        # 6. Перевірка, чи знайдено гру
        if game is None:
            raise GameNotFoundError()

        if game['gamestatus'] > 2: # Припускаємо: 1=Зареєстрована, 2=Затверджена, 3=Йде, 4=Закінчена
            raise CannotDeleteGame()

        creator_id = game['gamecreatorid']

        if interaction.user.id != game['gamecreatorid'] and interaction.user.id not in MODERATOR_LIST:
            raise NotEnoughtPermissions()

        await self.bot.db_utils.delete_game(game_id)

        game_name = game['gamename']
        await interaction.edit_original_response(embed=ebmtemp.create("Успіх", f"Гра `{game_name} (ID {game_id})` успішно видалена з реєстру."))


    @app_commands.command(name='game-member', description='Керування учасниками гри')
    @app_commands.describe(
        action="Оберіть дію: додати чи видалити учасника", # Опис для 'action'
        member="Учасник, над яким виконується дія",      # Опис для 'member'
        game_id="Унікальний індитифікатор гри",           # Опис для 'game_id'
        role="Роль учасника в грі: Майстер або Гравець"  # Опис для 'role'
    )
    @app_commands.choices(
        action=[ # Визначення варіантів для опції 'action'
            app_commands.Choice(name="Додати до гри", value=1), # Ім'я, яке бачить користувач, і значення, яке отримає код
            app_commands.Choice(name="Видалити з гри", value=2)
        ],
        role=[ # Визначення варіантів для опції 'role'
            app_commands.Choice(name="Майстер", value=1),
            app_commands.Choice(name="Гравець", value=2)
        ]
    )
    async def gamemember(
        self,
        interaction: discord.Interaction,      # <--- interaction замість ctx
        action: app_commands.Choice[int],      # <--- Обраний варіант (тип Choice)
        member: discord.Member,                # <--- Стандартний тип discord.Member
        game_id: int,                          # <--- Стандартний тип int
        role: app_commands.Choice[int]         # <--- Обраний варіант (тип Choice)
    ):

        await interaction.response.defer(ephemeral=True, thinking=True)

        pool = self.bot.db_pool
        if pool is None:
            # Якщо пул не створено (помилка при старті бота), повідомляємо і виходимо
            await interaction.edit_original_response(content="Помилка: База даних недоступна.") # Або інша відповідь
            return

        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:

                    sql_query = "SELECT * FROM games WHERE id = %s"
                    query_params = (game_id,)
                    await cursor.execute(sql_query, query_params)

                    game_data = await cursor.fetchone()

                    if not game_data:
                        await interaction.edit_original_response(embed=ebmtemp.create("Помилка", "Вказаної вами гри не існує."))
                        return

                    if interaction.user.id != game_data["gamecreatorid"] and not interaction.user.id in MODERATOR_LIST:
                        await interaction.edit_original_response(embed=ebmtemp.create("Помилка", f"Ви не маєте права на керування учасниками цієї гри."))
                        return

                    if game_data["gamestatus"] == 4 and not interaction.user.id in MODERATOR_LIST:
                        await interaction.edit_original_response(embed=ebmtemp.create("Помилка", f"Керувати завершеними іграми заборонено."))
                        return

                    game_masters = json.loads(game_data["gamemasters"])
                    game_players = json.loads(game_data["gameplayers"])

                    if role.value == 1:

                        if action.value == 1:

                            if member.id in game_masters:
                                await interaction.edit_original_response(embed=ebmtemp.create("Помилка", f"Користувач <@{member.id}> вже є майстром у грі"))
                                return

                            game_masters.append(member.id)
                            sql_query = "UPDATE games SET gamemasters = %s WHERE id = %s"
                            query_params = (json.dumps(game_masters), game_id, )
                            await cursor.execute(sql_query, query_params)
                            await interaction.edit_original_response(embed=ebmtemp.create("Успіх", f"Користувач <@{member.id}> став майстром гри!"))

                        else:

                            if member.id not in game_masters:
                                await interaction.edit_original_response(embed=ebmtemp.create("Помилка", f"Користувач <@{member.id}> не був майстром гри!"))
                                return

                            game_masters.remove(member.id)
                            sql_query = "UPDATE games SET gamemasters = %s WHERE id = %s"
                            query_params = (json.dumps(game_masters), game_id, )
                            await cursor.execute(sql_query, query_params)
                            await interaction.edit_original_response(embed=ebmtemp.create("Успіх", f"Користувач <@{member.id}> більше не є майстром гри!"))
                    

                    else:

                        if action.value == 1:

                            if member.id in game_players:
                                await interaction.edit_original_response(embed=ebmtemp.create("Помилка", f"Користувач <@{member.id}> вже є учасником гри"))
                                return

                            game_players.append(member.id)
                            sql_query = "UPDATE games SET gameplayers = %s WHERE id = %s"
                            query_params = (json.dumps(game_players), game_id, )
                            await cursor.execute(sql_query, query_params)

                            await interaction.edit_original_response(embed=ebmtemp.create("Успіх", f"Користувач <@{member.id}> тепер учасник гри!"))

                        else:

                            if member.id not in game_players:
                                await interaction.edit_original_response(embed=ebmtemp.create("Помилка", f"Користувач <@{member.id}> не був учасником гри!"))
                                return

                            game_players.remove(member.id)
                            sql_query = "UPDATE games SET gameplayers = %s WHERE id = %s"
                            query_params = (json.dumps(game_players), game_id, )
            
                            await interaction.edit_original_response(embed=ebmtemp.create("Успіх", f"Користувач <@{member.id}> більше не є учасником гри!"))
 
        except aiomysql.Error as db_err:
            # Обробка помилок, специфічних для бази даних
            print(f"Помилка бази даних: {db_err}")
            # Повідом користувачу про помилку
            # await interaction.edit_original_response(content="Помилка бази даних...")
        except Exception as e:
            # Обробка інших можливих помилок
            print(f"Інша помилка: {e}")
            # await interaction.edit_original_response(content="Сталася помилка...")


    @app_commands.command(name='set-game-status', description='Встановити статус грі')
    @app_commands.describe(
        game_id="Унікальний індитифікатор гри.", # Опис для game_id
        status="Оберіть новий статус для гри"     # Опис для status
    )
    @app_commands.choices(status=[ # Визначаємо варіанти для опції 'status'
        # Використовуємо числові значення (value), як зазначено у твоєму коментарі
        app_commands.Choice(name="Зареєстрована", value=1),
        app_commands.Choice(name="Затверджена", value=2),
        app_commands.Choice(name="Йде", value=3),
        app_commands.Choice(name="Закінчена", value=4)
    ])
    async def setgamestatus(
        self,
        interaction: discord.Interaction,    # <--- interaction замість ctx
        game_id: int,                        # <--- Стандартний тип int
        status: app_commands.Choice[int]     # <--- Обраний варіант (тип Choice, значення - int)
    ):

        await interaction.response.defer(ephemeral=True, thinking=True)

        if not interaction.user.id in MODERATOR_LIST:
            raise NotEnoughtPermissions()
            
        game_info = await self.bot.db_utils.get_game_info(game_id)

        if game_info is None:
            raise GameNotFoundError()

        await self.bot.db_utils.set_game_status(status, game_id)
        await interaction.edit_original_response(embed=ebmtemp.create("Успіх", f"Гра `ID {game_id}` успішно отримала статус `{status.name}`"))

    @app_commands.command(name='game-info', description='Інформація про гру')
    @app_commands.describe(
        game_id="Унікальний індитифікатор гри." # Опис для аргументу game_id
    )
    async def gameinfo(
        self,
        interaction: discord.Interaction, # <--- Правильна сигнатура
        game_id: int                      # <--- Правильна сигнатура
    ):

        await interaction.response.defer(ephemeral=True, thinking=True)

        game_data = await self.bot.db_utils.get_game_info(game_id)

        if not game_data:
            raise GameNotFoundError()

        masters, players = await self.bot.db_utils.get_game_participants(game_id)

        print(masters, players)

        game_masters_new = ""
        game_players_new = ""

        for i in masters:
            game_masters_new += f"<@{i}> "

        for i in players:
            game_players_new += f"<@{i}> "

        game_status_choice = {
            "1":    "Зареєстрована",
            "2":    "Затверджена",
            "3":    "Йде",
            "4":    "Закінчена"
        }

        embed = discord.Embed(
            title=f"Гра: {game_data['name']}",
            description=f"**Опис** \n{game_data['description']}",
            color=discord.Color(value=0x2F3136),
        )
        # додаємо поля
        embed.add_field(name="Тип", value=f"{game_data['type']}", inline=True)
        embed.add_field(name="Творець", value=f"<@{game_data['creator_id']}>", inline=True)
        embed.add_field(name="Ведучі", value=f"{game_masters_new}", inline=True)
        embed.add_field(name="Статус", value=f"{game_status_choice[str(game_data['status'])]}", inline=True)
        embed.add_field(name="Гравці", value=f"{game_players_new}", inline=False)

        # додаємо автора
        # embed.set_author(name=game_creator_object.name, icon_url=game_creator_object.avatar.url)

        # додаємо зображення
        # embed.set_image(url=user_info["image"])  # заміни на своє

        # додаємо футер
        embed.set_footer(text=f"ID {game_id}")

        # відправляємо ембед
        await interaction.edit_original_response(embed=embed)


# Реєструємо cog
async def setup(bot):
    await bot.add_cog(GamesCog(bot))