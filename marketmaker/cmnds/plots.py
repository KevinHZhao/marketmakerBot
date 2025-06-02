from __future__ import annotations

from typing import List, Literal

import discord
from discord.ext import commands
from discord import app_commands

from marketmaker.used_menus import MyMenuPages, MySource


class Plots(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    async def item_autocomplete(self, interaction: discord.Interaction, current: str):
        all_items = ["Carbon Dust", "Iron Ingot", "Gold Ingot", "Diamond", "Redstone", "Lapis Dust", "Sulfur Dust"]
        return [
            app_commands.Choice(name=item, value=item)
            for item in all_items if current.lower() in item.lower()
        ]

    async def fluid_autocomplete(self, interaction: discord.Interaction, current: str):
        all_fluids = ["Oxygen Gas", "Hydrogen Gas", "Nitrogen Gas", "Chlorine", "Hydrochloric Acid", "Sulfuric Acid", "Raw Bio Catalyst Medium", "Molten Infinity", "Molten Hypogen"]
        return [
            app_commands.Choice(name=fluid, value=fluid)
            for fluid in all_fluids if current.lower() in fluid.lower()
        ]

    @commands.hybrid_command(name="itemplot")
    @app_commands.describe(item="The item to plot")
    @app_commands.autocomplete(item=item_autocomplete)
    async def itemplot(self, ctx: commands.Context, item: str):
        """Plot the amount of an item."""
        IDB = self.bot.get_cog("InfluxDBQueries")
        await IDB.plot_item(item, ctx.channel)
        
    @commands.hybrid_command(name="fluidplot")
    @app_commands.describe(fluid="The fluid to plot")
    @app_commands.autocomplete(fluid=fluid_autocomplete)
    async def fluidplot(self, ctx: commands.Context, fluid: str):
        """Plot the amount of a fluid."""
        IDB = self.bot.get_cog("InfluxDBQueries")
        await IDB.plot_fluid(fluid, ctx.channel)