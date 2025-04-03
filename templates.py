import discord
from discord.ext import commands 
from discord.utils import get

class EmbedTemplate:
    def __init__(self, color=discord.Color(value=0x2F3136), footer_text=None):
        self.color = color
        self.footer_text = footer_text

    def create(self, title, description):

        embed = discord.Embed(
            title=title,
            description=description,
            color=self.color
        )
        if self.footer_text:
            embed.set_footer(text=self.footer_text)
        return embed

ebmtemp = EmbedTemplate()
