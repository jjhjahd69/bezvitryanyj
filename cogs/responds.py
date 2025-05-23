# responds.py

import discord
from discord.ext import commands
from discord import app_commands
from templates import ebmtemp # Припускаємо, що цей модуль існує і працює
from discord import ui
import aiomysql
from datetime import datetime
import math
import json
from errors import *
from config import * # Припускаємо, що тут є налаштування БД
from typing import Optional, Union # Додано Union

# --- Додано константу для розміру сторінки ---
PAGE_SIZE = 3

# --- Константи для типів відгуків ---
REVIEW_TYPE_MASTER = 1
REVIEW_TYPE_PLAYER = 2

class RespondsCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    # --- Функція для отримання назви типу ---
    def get_review_type_name(self, review_type_value: int) -> str:
        if review_type_value == REVIEW_TYPE_PLAYER:
            return "Гравця"
        elif review_type_value == REVIEW_TYPE_MASTER:
            return "Майстра"
        else:
            return "Невідомий тип"

    # --- Модальне вікно для написання відгуку ---
    class RespondModal(ui.Modal):
        # Очікуємо role_value як int (1 або 2)
        def __init__(self, bot, target_member_id: int, game_id: int, role_value: int, original_interaction: discord.Interaction) -> None:
            super().__init__(title="Написання відгуку")

            self.bot = bot
            self.target_member_id = target_member_id
            self.game_id = game_id
            self.role_value = role_value # Зберігаємо int (1 або 2)
            self.original_interaction = original_interaction

            self.respond_text = ui.TextInput(
                label="Текст відгуку",
                placeholder="Напишіть свій відгук тут...",
                style=discord.TextStyle.paragraph,
                max_length=1000,
                required=True
            )
            self.add_item(self.respond_text)

            self.respond_rate = ui.TextInput(
                label="Оцінка (ціле число від 1 до 10)",
                placeholder="Наприклад: 8",
                max_length=2,
                min_length=1,
                required=True
            )
            self.add_item(self.respond_rate)

        async def on_submit(self, interaction: discord.Interaction):
            respond_text_value = self.respond_text.value
            respond_rate_value = self.respond_rate.value


            respond_rate_int = int(respond_rate_value)
            if not (1 <= respond_rate_int <= 10):
                raise RatingOutOfRangeError()

            await interaction.response.defer(ephemeral=True, thinking=True)

            writer_id = interaction.user.id

            await self.bot.db_utils.add_response(
                self.target_member_id,
                writer_id,
                self.role_value, # Передаємо int (1 або 2)
                self.game_id,
                respond_text_value,
                respond_rate_int,
                )

            await interaction.followup.send(embed=ebmtemp.create("Успіх", "Ваш відгук успішно доданий!"), ephemeral=True)


    @app_commands.command(name='to-respond', description='Додати відгук користувачу за результатами гри')
    @app_commands.describe(
        member="Учасник, якому ви залишаєте відгук",
        game_id="Унікальний ID гри (число)",
        type="Ким був цей користувач у грі?" # Змінено опис
    )
    @app_commands.choices(type=[ # Використовуємо цілі числа 1 і 2
        app_commands.Choice(name="Гравцем", value=REVIEW_TYPE_PLAYER), # value=2
        app_commands.Choice(name="Майстром", value=REVIEW_TYPE_MASTER) # value=1
    ])
    async def torespond(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        game_id: int,
        type: app_commands.Choice[int] # Отримуємо Choice[int]
    ):

        if interaction.user.id == member.id:
            raise CannotToRespondToMySelfError()

        game_info = await self.bot.db_utils.get_game_info(game_id)

        if game_info is None:
            raise GameNotFoundError()

        # Припускаємо, що 4 - це статус "Закінчена"
        if game_info["status"] != 4:
            raise InvalidGameStateError()

        game_masters, game_players = await self.bot.db_utils.get_game_participants(game_id)

        if interaction.user.id not in (game_masters + game_players):
            raise LogicError("Ви не є учасником цієї гри!")

        target_user_is_player = member.id in game_players
        target_user_is_master = member.id in game_masters
        type_value = type.value # Отримуємо int (1 або 2)

        # Якщо пишемо відгук на гравця (type=2), а користувач не був гравцем
        if type_value == REVIEW_TYPE_PLAYER and not target_user_is_player:
            raise UserNotInGameError("Користувач не був учасником цієї гри.")

        # Якщо пишемо відгук на майстра (type=1), а користувач не був майстром
        if type_value == REVIEW_TYPE_MASTER and not target_user_is_master:
            raise UserNotInGameError("Користувач не був майстром цієї гри.")

        # Перевірка існуючого відгуку
        exist_result = await self.bot.db_utils.check_response_exist(member, interaction, game_id, type.value)

        if exist_result and exist_result['review_exists']:
                # Використовуємо функцію для отримання назви типу
            type_name = self.get_review_type_name(type_value)
            await interaction.response.send_message(
                embed=ebmtemp.create("Помилка", f"Ви вже залишали відгук на {member.mention} як на **{type_name}** у грі `{game_id}`."),
                ephemeral=True
            )
            return

        # Викликаємо модальне вікно
        modal = self.RespondModal(
            self.bot,
            target_member_id=member.id,
            game_id=game_id,
            role_value=type_value, # Передаємо int (1 або 2)
            original_interaction=interaction
        )

        await interaction.response.send_modal(modal)



    class ReviewsView(discord.ui.View):
         # Очікуємо initial_review_type як int (1 або 2)
        def __init__(self, user_id: int, initial_review_type: int, initial_page: int, bot: commands.Bot, original_interaction: discord.Interaction, cog_instance: 'RespondsCog'):
            super().__init__(timeout=180.0)
            self.user_id = user_id
            self.current_review_type = initial_review_type # Зберігаємо int
            self.current_page = initial_page
            self.bot = bot
            self.original_interaction = original_interaction
            self.message: Optional[Union[discord.Message, discord.WebhookMessage]] = None # Тип може бути різним
            self.cog_instance = cog_instance # Зберігаємо екземпляр кога для доступу до get_review_type_name

            # Select меню для вибору типу відгуків
            self.select_type = discord.ui.Select(
                placeholder="Виберіть тип відгуків для перегляду",
                options=[
                    # Використовуємо int у value
                    discord.SelectOption(label="Відгуки як на Гравця", value=str(REVIEW_TYPE_PLAYER), description="Показати відгуки, де користувач був гравцем", default=initial_review_type == REVIEW_TYPE_PLAYER),
                    discord.SelectOption(label="Відгуки як на Майстра", value=str(REVIEW_TYPE_MASTER), description="Показати відгуки, де користувач був майстром", default=initial_review_type == REVIEW_TYPE_MASTER)
                    # Значення SelectOption має бути рядком! Тому конвертуємо int -> str
                ],
                row=0
            )
            self.select_type.callback = self.select_callback
            self.add_item(self.select_type)

            self.prev_button = discord.ui.Button(label="⬅️ Попередня", style=discord.ButtonStyle.primary, row=1, disabled=True)
            self.next_button = discord.ui.Button(label="Наступна ➡️", style=discord.ButtonStyle.primary, row=1, disabled=True)

            self.prev_button.callback = self.prev_page_callback
            self.next_button.callback = self.next_page_callback

            self.add_item(self.prev_button)
            self.add_item(self.next_button)

        async def select_callback(self, interaction: discord.Interaction):
            # Отримуємо вибране значення як рядок ("1" або "2") і конвертуємо в int
            self.current_review_type = int(self.select_type.values[0])
            self.current_page = 1
            await self.update_message(interaction)

        async def prev_page_callback(self, interaction: discord.Interaction):
            if self.current_page > 1:
                self.current_page -= 1
                await self.update_message(interaction)
            else:
                await interaction.response.defer() # Просто ігноруємо

        async def next_page_callback(self, interaction: discord.Interaction):
            # Перевірка на максимальну сторінку відбувається в update_message
            self.current_page += 1
            await self.update_message(interaction)

        async def update_message(self, interaction: discord.Interaction):
            await interaction.response.defer() # Відповідь на взаємодію компонента

            # Отримуємо відгуки та кількість (передаємо int)
            reviews = await self.bot.db_utils.get_responds(self.user_id, self.current_review_type, self.current_page, PAGE_SIZE)
            total_reviews = await self.bot.db_utils.get_total_reviews(self.user_id, self.current_review_type)

            if reviews is None:
                 await interaction.followup.send(embed=ebmtemp.create("Помилка", "Не вдалося завантажити відгуки."), ephemeral=True)
                 return

            total_pages = math.ceil(total_reviews / PAGE_SIZE)
            if total_pages == 0: total_pages = 1

            target_user = interaction.guild.get_member(self.user_id) if interaction.guild else None
            if not target_user:
                 try:
                     target_user = await self.bot.fetch_user(self.user_id)
                 except discord.NotFound:
                     target_user = None

            embed_title = f"Відгуки на {target_user.display_name if target_user else f'ID: {self.user_id}'}"
            # Використовуємо функцію для отримання назви типу
            type_name = self.cog_instance.get_review_type_name(self.current_review_type)
            embed_description = f"Тип відгуків: **Як на {type_name}**\nСторінка {self.current_page}/{total_pages} (Всього: {total_reviews})"

            embed = discord.Embed(
                title=embed_title,
                description=embed_description,
                color=discord.Color(value=0x2F3136)
            )
            if target_user and target_user.display_avatar:
                embed.set_thumbnail(url=target_user.display_avatar.url)

            if not reviews and self.current_page == 1:
                embed.add_field(name="Немає відгуків", value="Поки що немає відгуків цього типу.", inline=False)
            elif not reviews and self.current_page > 1:
                 embed.add_field(name="Пуста сторінка", value="Тут немає відгуків.", inline=False)
                 if self.current_page > total_pages and total_pages > 0:
                     self.current_page = total_pages # Корегуємо сторінку, якщо вона "за межами"
            else:
                for review in reviews:
                    writer_id, _, game_id, review_text, rating, review_date = review
                    writer_user = self.bot.get_user(writer_id) or f"ID: {writer_id}"
                    date_str = review_date.strftime('%d.%m.%Y %H:%M') if isinstance(review_date, datetime) else str(review_date)

                    embed.add_field(
                        name=f"Гра ID: `{game_id}` | Від: `{writer_user}` | Оцінка: {rating}/10 ⭐",
                        value=f"> Дата: {date_str}"
                              f"\n{discord.utils.escape_markdown(review_text)}\n",
                        inline=False
                    )

            self.prev_button.disabled = self.current_page <= 1
            self.next_button.disabled = self.current_page >= total_pages

            # Оновлюємо select, щоб показувати поточний вибір
            for option in self.select_type.options:
                # Порівнюємо значення опції (рядок) з поточним типом (int), конвертуючи тип опції
                try:
                    option.default = int(option.value) == self.current_review_type
                except ValueError:
                     option.default = False # Якщо значення опції не число

            # Редагуємо повідомлення
            message_id_to_edit = self.message.id if self.message else interaction.message.id
            try:
                # Використовуємо followup.edit_message для редагування відповіді на взаємодію з компонентом
                await interaction.followup.edit_message(message_id=message_id_to_edit, embed=embed, view=self)
            except discord.NotFound:
                 print(f"Не вдалося знайти повідомлення {message_id_to_edit} для редагування View.")
            except discord.HTTPException as e:
                 print(f"HTTP помилка при редагуванні View: {e}")


        async def on_timeout(self):
            if not self.message: return # Немає чого редагувати
            for item in self.children:
                item.disabled = True
            try:
                # Використовуємо edit напряму на об'єкті повідомлення
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException) as e:
                 print(f"Помилка при оновленні View після таймауту для повідомлення {self.message.id}: {e}")

    @app_commands.command(name='responses', description='Показати відгуки на користувача')
    @app_commands.describe(
        member="Учасник, чиї відгуки показати (за замовчуванням - ви)",
        review_type="Показати відгуки тільки певного типу"
    )
    @app_commands.choices(review_type=[ # Використовуємо int
        app_commands.Choice(name="Як на Гравця", value=REVIEW_TYPE_PLAYER), # value=2
        app_commands.Choice(name="Як на Майстра", value=REVIEW_TYPE_MASTER) # value=1
    ])
    async def responses(
        self,
        interaction: discord.Interaction,
        member: Optional[discord.Member] = None,
        review_type: Optional[app_commands.Choice[int]] = None # Очікуємо Choice[int]
    ):
        await interaction.response.defer(thinking=True)

        target_member = member or interaction.user
        # Визначаємо початковий тип (int), дефолт - гравець (2)
        initial_review_type = review_type.value if review_type else REVIEW_TYPE_PLAYER
        initial_page = 1

        # Отримуємо дані (передаємо int)
        reviews = await self.bot.db_utils.get_responds(target_member.id, initial_review_type, initial_page, PAGE_SIZE)
        total_reviews = await self.bot.db_utils.get_total_reviews(target_member.id, initial_review_type)

        if reviews is None:
            await interaction.edit_original_response(embed=ebmtemp.create("Помилка", "Не вдалося завантажити відгуки."))
            return

        total_pages = math.ceil(total_reviews / PAGE_SIZE)
        if total_pages == 0: total_pages = 1

        # Формуємо Embed
        embed_title = f"Відгуки на {target_member.display_name}"
        # Використовуємо функцію для отримання назви типу
        type_name = self.get_review_type_name(initial_review_type)
        embed_description = f"Тип відгуків: **Як на {type_name}**\nСторінка {initial_page}/{total_pages} (Всього: {total_reviews})"

        embed = discord.Embed(
            title=embed_title,
            description=embed_description,
            color=discord.Color(value=0x2F3136)
        )
        embed.set_thumbnail(url=target_member.display_avatar.url)

        if not reviews:
            embed.add_field(name="Немає відгуків", value="Поки що немає відгуків цього типу.", inline=False)
        else:
            for review in reviews:
                writer_id, _, game_id, review_text, rating, review_date = review
                writer_user = self.bot.get_user(writer_id) or f"ID: {writer_id}"
                date_str = review_date.strftime('%d.%m.%Y %H:%M') if isinstance(review_date, datetime) else str(review_date)

                embed.add_field(
                    name=f"Гра ID: `{game_id}` | Від: `{writer_user}` | Оцінка: {rating}/10 ⭐",
                    value=f"> Дата: {date_str}"
                          f"\n{discord.utils.escape_markdown(review_text)}\n",
                    inline=False
                )

        # Створюємо View, передаємо екземпляр кога
        view = self.ReviewsView(target_member.id, initial_review_type, initial_page, self.bot, interaction, self)

        # Надсилаємо відповідь
        message = await interaction.edit_original_response(embed=embed, view=view)
        # Зберігаємо повідомлення у View
        view.message = message # edit_original_response повертає WebhookMessage

        # Початкове налаштування стану кнопок (виклик update_message не потрібен тут, бо __init__ вже налаштував)
        # Просто перевіримо стан кнопок ще раз після надсилання
        view.prev_button.disabled = view.current_page <= 1
        view.next_button.disabled = view.current_page >= total_pages
        # Редагуємо повідомлення ще раз, щоб точно оновити стан кнопок (можливо, це зайве)
        try:
            # Потрібно перевірити, чи повідомлення об'єкт WebhookMessage чи Message
             if isinstance(message, discord.WebhookMessage):
                 await interaction.edit_original_response(view=view) # webhook message редагується так
             elif isinstance(message, discord.Message):
                  await message.edit(view=view) # звичайне повідомлення так
        except discord.HTTPException as e:
             print(f"Незначна помилка при фінальному оновленні View: {e}")


async def setup(bot):
    # Переконайся, що bot.db_pool існує
    await bot.add_cog(RespondsCog(bot))
