from discord import Message


async def fish_react(message: Message) -> None:
    """
    Adds a fish reaction to a message,
    and sends a message to the channel
    encouraging further reactions.

    Parameters
    ----------
    message : Message
        The message to react to.

    """
    FISH = "🐟"
    GIF_LINK = "https://tenor.com/view/fish-react-fish-react-him-thanos-gif-26859685"
    await message.add_reaction(FISH)
    await message.channel.send(GIF_LINK)
