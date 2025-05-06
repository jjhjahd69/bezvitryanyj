# profile.py
import discord
from discord.ext import commands
from discord import app_commands
from templates import ebmtemp
import aiomysql
from decimal import Decimal, ROUND_HALF_UP
from config import *
from typing import Optional
from errors import *
import logging

class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def checkadd(self, interaction, member):

        logging.debug(f"[CHECKADD] Користувач {member.name} перевіряється")

        user_exist = await self.bot.db_utils.check_user_exist(member)

        logging.debug(f"[CHECKADD] user_exist = {user_exist} у користувача {member.name}")

        if not user_exist:
            logging.debug(f"[CHECKADD] Користувач {member.name} не існує, виконую додавання.")
            await self.bot.db_utils.add_user_to_database(member)
   
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

        user_info = await self.bot.db_utils.get_user(member)

        playerrate_dict, masterrate_dict = await self.bot.db_utils.get_user_rating_average(member)
        playerrate = Decimal(playerrate_dict["avg_rate"] or 0).quantize(Decimal('0.0'), rounding=ROUND_HALF_UP)
        masterrate = Decimal(masterrate_dict["avg_rate"] or 0).quantize(Decimal('0.0'), rounding=ROUND_HALF_UP)

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
        embed.set_footer(text=f"ID {user_info["id"]}")

        # відправляємо ембед
        await interaction.edit_original_response(embed=embed)

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

        await self.bot.db_utils.set_user_image(image_link, interaction)
        await interaction.edit_original_response(embed=ebmtemp.create("Успіх", "Посилання встановлено банером профілю! :sparkling_heart:"))


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

        await self.bot.db_utils.set_user_description(text, interaction)
        await interaction.edit_original_response(embed=ebmtemp.create("Успіх", f"Опис успішно встановлений. :sparkling_heart: \n```{text}```"))

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
            raise NotEnoughtPermissions()

        await self.bot.db_utils.set_user_adminresponse(text, member)
        await interaction.edit_original_response(embed=ebmtemp.create("Успіх", f"Адмінське зауваження успішно встановлене. :sparkling_heart: \n```{text}```"))

# Реєстрація cog
async def setup(bot):
    await bot.add_cog(ProfileCog(bot))