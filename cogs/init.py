from config import *
import discord
from discord.ext import commands 
from discord import app_commands
from typing import Optional

class InitCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #@commands.Cog.listener()
    #async def on_ready(self):
    #    print(f"бот запущений як {self.bot.user}!")
    #    for guild in bot.guilds:
    #        if guild.id != ALLOWED_GUILD:
    #            print(f"виходжу з серверу: {guild.name} ({guild.id})")
    #            await guild.leave()

    #   @commands.Cog.listener()
    #   async def on_guild_join(self, guild):
    #       if guild.id != ALLOWED_GUILD:
    #           print(f"бот доданий на недозволений сервер: {guild.name} ({guild.id})")
    #           await guild.leave()

    # Встановлюємо боту активність
    @commands.Cog.listener()
    async def on_ready(self):
        activity = discord.Game(name="розглядає перекотиполе")
        await self.bot.change_presence(status=discord.Status.idle, activity=activity)

# Реєструємо cog
async def setup(bot):
    await bot.add_cog(InitCog(bot))