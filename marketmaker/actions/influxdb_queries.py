from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands
import discord

from marketmaker.backend.influxdb import (
    query_item,
    query_fluid,
    plotter,
)

class InfluxDBQueries(commands.Cog):
    def __init__(self: InfluxDBQueries, bot) -> None:
        self.bot = bot

    async def plot_item(self: InfluxDBQueries, item: str, channel: discord.TextChannel):
        results = query_item(item)
        if not results:
            await channel.send(f"No data found for item: {item}")
            return
        img_buffer = plotter(results, item)
        await channel.send(file=discord.File(img_buffer, "plot.png"))
        
    async def plot_fluid(self: InfluxDBQueries, fluid: str, channel: discord.TextChannel):
        results = query_fluid(fluid)
        if not results:
            await channel.send(f"No data found for fluid: {fluid}")
            return
        img_buffer = plotter(results, fluid)
        await channel.send(file=discord.File(img_buffer, "plot.png"))