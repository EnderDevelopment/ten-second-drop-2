import asyncio
import logging
import os
import time

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DROP_IMAGE_URL = os.getenv("DROP_IMAGE_URL", "").strip()
DROP_COOLDOWN_SECONDS = max(0, int(os.getenv("DROP_COOLDOWN_SECONDS", "60")))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("drop_bot")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
cooldown_lock = asyncio.Lock()
next_drop_allowed_at = 0.0


class DropView(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=300)
        self.channel_id = channel_id
        self.available = False
        self.claimed = False
        self.message = None

    async def start_countdown(self, message: discord.Message):
        self.message = message
        try:
            for remaining in range(10, 0, -1):
                embed = discord.Embed(
                    title="A drop is coming!",
                    description=f"**Claim opens in {remaining} seconds...**",
                    color=discord.Color.gold(),
                )
                if DROP_IMAGE_URL:
                    embed.set_image(url=DROP_IMAGE_URL)
                await message.edit(embed=embed, view=self)
                await asyncio.sleep(1)

            self.available = True
            self.claim_button.disabled = False
            embed = discord.Embed(
                title="Drop available!",
                description="Click **Claim drop** to claim it.",
                color=discord.Color.green(),
            )
            if DROP_IMAGE_URL:
                embed.set_image(url=DROP_IMAGE_URL)
            await message.edit(embed=embed, view=self)
            logger.info("Drop opened for claims in channel %s", self.channel_id)
        except discord.HTTPException:
            logger.exception("Could not update the drop message in channel %s", self.channel_id)

    @discord.ui.button(label="Claim drop", style=discord.ButtonStyle.success, disabled=True)
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.available:
            logger.info("User %s tried to claim a drop before it opened", interaction.user.id)
            await interaction.response.send_message("The drop is not open yet.", ephemeral=True)
            return
        if self.claimed:
            logger.info("User %s tried to claim an already claimed drop", interaction.user.id)
            await interaction.response.send_message("This drop has already been claimed.", ephemeral=True)
            return

        self.claimed = True
        button.disabled = True
        winner = interaction.user
        logger.info(
            "Drop in channel %s claimed by user %s (%s)",
            self.channel_id,
            winner.id,
            winner.display_name,
        )
        embed = discord.Embed(
            title="Drop claimed!",
            description=f"Winner: {winner.mention}\n**{discord.utils.escape_markdown(winner.display_name)}** claimed the drop!",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=winner.display_avatar.url)
        if DROP_IMAGE_URL:
            embed.set_image(url=DROP_IMAGE_URL)
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        if self.message is not None and not self.claimed:
            for item in self.children:
                item.disabled = True
            logger.info("Unclaimed drop timed out in channel %s", self.channel_id)
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                logger.exception("Could not disable the timed-out drop in channel %s", self.channel_id)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        logger.info("Logged in as %s; synced %s slash command(s)", bot.user, len(synced))
    except discord.HTTPException:
        logger.exception("Could not sync slash commands")


@bot.tree.command(name="drop", description="Start a timed drop with a claim button.")
async def drop(interaction: discord.Interaction):
    global next_drop_allowed_at

    if OWNER_ID == 0 or interaction.user.id != OWNER_ID:
        logger.warning("Unauthorized /drop attempt by user %s", interaction.user.id)
        await interaction.response.send_message("You are not allowed to start drops.", ephemeral=True)
        return

    async with cooldown_lock:
        now = time.monotonic()
        if now < next_drop_allowed_at:
            remaining = int(next_drop_allowed_at - now) + 1
            logger.info("Owner tried /drop during cooldown; %s seconds remain", remaining)
            await interaction.response.send_message(
                f"Drop cooldown is active. Try again in {remaining} seconds.",
                ephemeral=True,
            )
            return
        next_drop_allowed_at = now + DROP_COOLDOWN_SECONDS

    view = DropView(interaction.channel_id)
    initial_embed = discord.Embed(
        title="A drop is coming!",
        description="**Claim opens in 10 seconds...**",
        color=discord.Color.gold(),
    )
    if DROP_IMAGE_URL:
        initial_embed.set_image(url=DROP_IMAGE_URL)
    await interaction.response.send_message(embed=initial_embed, view=view)
    message = await interaction.original_response()
    logger.info(
        "Drop started by owner %s in channel %s; cooldown is %s seconds",
        interaction.user.id,
        interaction.channel_id,
        DROP_COOLDOWN_SECONDS,
    )
    asyncio.create_task(view.start_countdown(message))


@bot.tree.command(name="cooldown", description="Check the drop cooldown status.")
async def cooldown(interaction: discord.Interaction):
    if OWNER_ID == 0 or interaction.user.id != OWNER_ID:
        logger.warning("Unauthorized /cooldown attempt by user %s", interaction.user.id)
        await interaction.response.send_message("You are not allowed to check the drop cooldown.", ephemeral=True)
        return

    await interaction.response.send_message(
        "Checking the drop cooldown...",
        ephemeral=True,
    )

    try:
        while True:
            remaining = max(0, int(next_drop_allowed_at - time.monotonic() + 0.999))
            if remaining == 0:
                status = "Drop cooldown is ready. You can start a drop now."
            else:
                status = f"Drop cooldown is active: **{remaining} seconds** remaining."

            await interaction.edit_original_response(
                content=f"{status} (Configured cooldown: {DROP_COOLDOWN_SECONDS} seconds.)"
            )
            if remaining == 0:
                break
            await asyncio.sleep(1)
    except discord.HTTPException:
        logger.exception("Could not update the cooldown status for user %s", interaction.user.id)


if not TOKEN:
    raise RuntimeError("Set DISCORD_TOKEN in your .env file before starting the bot.")
bot.run(TOKEN)
