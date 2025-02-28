from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import discord
from discord.ext import commands

from marketmaker.backend.db import (
    bonus_transfer,
    fetch_wallet_amount,
    tax_backend,
    wallet_transfer_backend,
)

if TYPE_CHECKING:
    from marketmaker.subclass import GameVars


class Economy(commands.Cog):
    def __init__(self: Economy, bot) -> None:
        self.bot = bot


    async def force_anarchy(
        self: Economy,
        channel: discord.TextChannel,
        game_vars: GameVars,
    ):
        await channel.send("Anarchy has been forcibly activated!")
        game_vars.anarchy = True


    async def force_deflation(
        self: Economy,
        channel: discord.TextChannel, 
        user: discord.Member, 
        amount: int,
    ):
        await channel.send(
            f"Deflation!  {amount}$ of {user.mention}'s wagered cash has disappeared from the bank!  The economy shrinks by {amount}$.",
        )
        bonus_transfer("BANK", -amount, 9)


    async def rand_inflation(
        self: Economy,
        channel: discord.TextChannel,
        user: discord.Member,
        wager: int,
        amount: int,
    ):
        await channel.send(
            f"Inflation!  {amount}$ has appeared from out of nowhere into {user.mention}'s wallet, and they get their wager back!  The economy grows by {amount}$.",
        )
        wallet_transfer_backend("BANK", user.id, wager, 8)
        bonus_transfer(user.id, amount, 8)


    async def tax(self: Economy, channel: discord.TextChannel):
        tax_backend()
        bank_money = fetch_wallet_amount("BANK")
        await channel.send(
            f"Taxation time!  The value of the bank is now {bank_money}$.  Good work everyone!",
        )


    async def wallet_transfer(
        self: Economy,
        sender: discord.Member | Literal["BANK"],
        receiver: discord.Member | Literal["BANK"],
        amount: int,
        channel: discord.TextChannel,
        transaction: int,
    ) -> int:
        if isinstance(receiver, (discord.User, discord.Member)):
            recid: Literal["BANK"] | int = receiver.id
        elif receiver != "BANK":
            raise Exception("receiver is neither discord.Member nor BANK")
        else:
            recid = "BANK"

        if isinstance(sender, (discord.User, discord.Member)):
            sendid: Literal["BANK"] | int = sender.id
        elif sender != "BANK":
            raise Exception("sender is neither discord.Member nor BANK")
        else:
            sendid = "BANK"

        result = wallet_transfer_backend(sendid, recid, amount, transaction)

        if isinstance(sender, (discord.User, discord.Member)):
            sendmen = sender.mention
        elif sender != "BANK":
            raise Exception("sender is neither discord.Member nor BANK")
        else:
            sendmen = "The bank"

        if isinstance(receiver, (discord.User, discord.Member)):
            recmen = receiver.mention
        elif receiver != "BANK":
            raise Exception("receiver is neither discord.Member nor BANK")
        else:
            recmen = "the bank"

        if result < amount:
            await channel.send(
                f"{sendmen} somehow doesn't have enough cash, so we'll just send all of their {result}$ to {recmen}.",
            )
        print(f"Transferred {result} from {sender} to {receiver}.")
        return result


    async def donation(
        self: Economy,
        channel: discord.TextChannel,
        sender: discord.Member,
        receiver: discord.Member | Literal["BANK"],
        amount: int,
    ):
        if receiver == "BANK":
            await channel.send(
                f"{sender.mention} must be feeling generous, since they just donated a further {amount}$ to the bank on top of their initial wager!",
            )
        else:
            await channel.send(
                f"{sender.mention} must be feeling generous, since they just donated {amount}$ to {receiver.mention}!",
            )

        await self.wallet_transfer(sender, receiver, amount, channel, 5)
