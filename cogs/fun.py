import enum
import io
import random

import discord
from discord import File
from discord.ext import commands
from discord.ext.commands import Context

from backend import database


def is_in_guild(guild_id):
    async def predicate(ctx: Context):
        return ctx.guild and ctx.guild.id == guild_id

    return commands.check(predicate)


class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.enabled = True
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.enabled:
            return
        if message.author.bot:
            return
        if not random.randint(0, 100) == 50:
            return
        await message.add_reaction("<:tutkegel:620927895132569601>")

    @commands.command(hidden=True)
    async def toggle(self, ctx):
        self.enabled = not self.enabled
        await ctx.send(f"Set enabled to: {self.enabled}")

    # Send 3x3 emote grid with tutkegel.
    # Emotes are from Davvos11's test discord,
    # therefore, there isn't a need to waste emote space on the TCS discord
    @commands.command(name="tutkegel")
    async def tutkegel(self, ctx):
        await ctx.send("<:tegel9:634119527680180261>"
                       "<:tegel8:634119528158199841>"
                       "<:tegel7:634119527927513089>"
                       "\n<:tegel6:634119527868661773>"
                       "<:tegel5:634119527877050399>"
                       "<:tegel4:634119528346812429>"
                       "\n<:tegel3:634119528825094164>"
                       "<:tegel2:634119528330035200>"
                       "<:tegel1:634119528439218206>")

    # Replies "Alexa, play Despacito" to messages containing "this is so sad"
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.enabled:
            return
        if message.author.bot:
            return
        if "this is so sad" not in message.content.lower():
            return
        await message.channel.send("Alexa, play Despacito")

    # Send the leaderboards in the following format:
    # {ranking}. {name} - {score} ({positives} Positives and {negatives} Negatives)
    @commands.command(name='wiezijnhetmooist',
                      aliases=['whoarehetmooist', 'spiegeltjespiegeltjeaandewand',
                               'wieishetmooist', 'mirrormirroronthewall'])
    async def on_karma_leaderboard_request(self, ctx: Context):
        message = self.order_leaderboard(await database.get_top_karma(10))
        await ctx.send(message if message else 'Nobody is mooi')

    # Send the negative leaderboards in the following format:
    # {ranking}. {name} - {score} ({positives} Positives and {negatives} Negatives)
    @commands.command(name='wiezijnhetminstmooi',
                      aliases=['whoarehetleastmooi', 'trash', 'whoishetleastmooi',
                               'wieishetminstmooi'])
    async def on_karma_worst_leaderboard_request(self, ctx: Context):
        message = self.order_leaderboard(await database.get_reversed_top_karma(10))
        await ctx.send(message if message else "Why don't you guys hate someone?")

    # The base command for the dasmooi settings
    @commands.group(name='dasmooi')
    @is_in_guild(613755161633882112)
    @commands.has_role('Committee')
    async def on_update_das_mooi_settings(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Please use one of the following subcommands: '
                           'threshold <threshold>, positivechannel, negativechannel')

    # The dasmooi settings command to update the threshold
    @on_update_das_mooi_settings.command(name='threshold')
    async def on_update_das_mooi_threshold(self, ctx, threshold: int):
        await database.settings.set_das_mooi_threshold(threshold)
        await ctx.send(f'Updated the das mooi threshold to: {threshold}.')

    # The dasmooi settings command to update the positive forward channel to the current channel
    @on_update_das_mooi_settings.command(name='positivechannel')
    async def on_update_das_mooi_channel(self, ctx):
        await database.settings.set_das_mooi_channel(ctx.channel.id)
        await ctx.send(f'All positive messages which pass the das mooi threshold,'
                       f' will be redirected to this channel')

    # The dasmooi settings command to update the negative forward channel to the current channel
    @on_update_das_mooi_settings.command(name='negativechannel')
    async def on_update_das_niet_mooi_channel(self, ctx):
        await database.settings.set_das_niet_mooi_channel(ctx.channel.id)
        await ctx.send(f'All negative messages which pass the das mooi threshold,'
                       f' will be redirected to this channel')

    # Returns a string in the following format:
    # {ranking}. {name} - {score} ({positives} Positives and {negatives} Negatives)
    def order_leaderboard(self, karma):
        return '\n'.join([f'{x[0] + 1}. {self.bot.get_user(x[1][0]).name} - '
                          f'**{x[1][1] - x[1][2]}** '
                          f'*({x[1][1]} Positives and {x[1][2]} Negatives)*'
                          for x in enumerate(karma)])

    # Send a current status for a given player in the following format:
    # {mention} - Your current score is: {score} ({positives} Positives and {negatives} Negatives)
    @commands.command(name='hoemooibenik', aliases=['howmooiami'])
    async def on_karma_self_request(self, ctx: Context):
        author: discord.User = ctx.author
        response: (int, int) = await database.get_karma(author.id)
        await ctx.send(
            f'{author.mention} - Your current score is: **{response[0] - response[1]}** '
            f'*({response[0]} Positives and {response[1]} Negatives)*')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        emoji: discord.emoji.PartialEmoji = payload.emoji
        guild: discord.Guild = self.bot.get_guild(payload.guild_id)
        member: discord.Member = guild.get_member(payload.user_id)
        channel: discord.TextChannel = guild.get_channel(payload.channel_id)
        message: discord.Message = await channel.fetch_message(payload.message_id)
        if member and message.author:
            await self.change_karma_check(emoji, member, message, True)
            await self.forward_message_check(emoji, message)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        emoji: discord.emoji.PartialEmoji = payload.emoji
        guild: discord.Guild = self.bot.get_guild(payload.guild_id)
        member: discord.Member = guild.get_member(payload.user_id)
        channel: discord.TextChannel = guild.get_channel(payload.channel_id)
        message: discord.Message = await channel.fetch_message(payload.message_id)
        await self.change_karma_check(emoji, member, message, False)

    class KarmaEmotes(enum.Enum):
        POSITIVE = 'dasmooi'
        NEGATIVE = 'dasnietmooi'

    # Check if the karma count should be changed, if so, change it
    async def change_karma_check(self, emoji: discord.emoji.PartialEmoji, member: discord.Member,
                                 message: discord.Message, increment: bool):
        # Check if the user doesn't want to give karma to themselves.
        # It is also important that Tegel's opinion doesn't count.
        if self.enabled and member != message.author \
                and not discord.utils.get(member.roles, name='Tegel'):
            if emoji.name == self.KarmaEmotes.POSITIVE.value:
                # Update the positive karma
                await database.update_karma(message.author.id,
                                            (1 if increment else -1, 0))
            elif emoji.name == self.KarmaEmotes.NEGATIVE.value:
                # Update the negative karma
                await database.update_karma(message.author.id,
                                            (0, 1 if increment else -1))

    # Check if the message obtained enough karma to get forwarded to another channel
    async def forward_message_check(self, emoji: discord.emoji.PartialEmoji,
                                    message: discord.Message):
        count: int = [reaction.count for reaction in message.reactions
                      if type(reaction.emoji) == discord.emoji.Emoji
                      and reaction.emoji.name == emoji.name][0]
        if self.enabled and not message.author.bot \
                and count >= database.settings.get_das_mooi_threshold():
            if emoji.name == self.KarmaEmotes.POSITIVE.value \
                    or emoji.name == self.KarmaEmotes.NEGATIVE.value:
                positive: bool = emoji.name == self.KarmaEmotes.POSITIVE.value
                if not await database.is_forwarded(message.id, positive):
                    await database.add_forwarded_message(message.id, positive)
                    channel = self.bot.get_channel(
                        database.settings.get_das_mooi_channel()) \
                        if positive \
                        else self.bot.get_channel(database.settings.get_das_niet_mooi_channel())
                    colour: discord.colour.Colour = discord.colour.Colour.green() \
                        if positive else discord.colour.Colour.red()
                    embed: discord.Embed = discord.Embed(title='New Message',
                                                         description=message.content,
                                                         url=message.jump_url,
                                                         colour=colour) \
                        .set_author(name=message.author.name,
                                    icon_url=message.author.avatar_url)

                    if len(message.attachments) == 0:
                        await channel.send(embed=embed)
                    elif len(message.attachments) == 1:
                        attachment = message.attachments[0]
                        if attachment.filename.endswith('.png') \
                                or attachment.filename.endswith('.jpg') \
                                or attachment.filename.endswith('.jpeg'):
                            embed.set_image(url=attachment.url)
                            await channel.send(embed=embed)
                        else:
                            await channel.send(embed=embed)
                            await channel.send(file=File(io.BytesIO(await attachment.read()),
                                                         filename=attachment.filename))
                    else:
                        await channel.send(embed=embed)
                        for file in \
                                [File(io.BytesIO(await attachment.read()),
                                      filename=attachment.filename)
                                 for attachment in message.attachments
                                 if not attachment.is_spoiler()]:
                            await channel.send(file=file)


def setup(bot):
    bot.add_cog(Fun(bot))
