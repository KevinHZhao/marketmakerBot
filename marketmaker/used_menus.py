import discord
from discord.ext import menus
from discord.ext.menus import First, Last, button


class MyMenuPages(menus.MenuPages, inherit_buttons=True):
    @button('⏮️', position=First(0))
    async def go_to_first_page(self, payload) -> None:
        await self.show_page(0)

    @button('◀️', position=First(1))
    async def go_to_previous_page(self, payload) -> None:
        await self.show_checked_page(self.current_page - 1)

    @button('▶️', position=Last(1))
    async def go_to_next_page(self, payload) -> None:
        await self.show_checked_page(self.current_page + 1)

    @button('⏭️', position=Last(2))
    async def go_to_last_page(self, payload) -> None:
        max_pages = self._source.get_max_pages()
        last_page = max(max_pages - 1, 0)
        await self.show_page(last_page)

    # @button('⏹️', position=Last(0))
    # async def stop_pages(self, payload):
    #     self.stop()

class MySource(menus.ListPageSource):
    async def format_page(self, menu, entries):
        embed = discord.Embed(
            description=entries,
            color=discord.Colour.random(),
        )
        embed.set_footer(text=f"Requested by {menu.ctx.author}")
        return embed
    