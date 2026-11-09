# Discord Drop Bot

Ten-Second Drop is a Discord bot that lets one configured owner start timed drops with the `/drop` slash command. It displays an optional image, counts down for 10 seconds, then opens a claim button; the first person to claim wins, and the bot shows the winner’s profile.

## Install

1. Install Python 3.10 or newer.
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env`.
4. Set `DISCORD_TOKEN` to your bot token and `OWNER_ID` to your Discord user ID. Optionally configure `DROP_IMAGE_URL`, `DROP_COOLDOWN_SECONDS`, and `LOG_LEVEL`.
5. Invite the bot to your Discord server with permission to send messages, embed links, and use application commands.
6. Start the bot:
   ```bash
   python main.py
   ```

## Use

1. Run `/drop` as the configured owner. The bot posts a drop message and counts down from 10 seconds.
2. When the countdown ends, anyone can click **Claim drop**. The first claim wins; later attempts are rejected.
3. The bot updates the message with the winner’s mention, display name, and avatar.
4. Run `/cooldown` as the owner to check how long remains before another drop can be started. Unclaimed drop buttons are disabled after five minutes.

---

More Discord bot projects by EnderDevelopment: https://github.com/EnderDevelopment

Project page: https://dash.enderdevelopment.com/community/cc647e00-b302-44ec-b299-e348310de837?utm_source=github&utm_medium=readme&utm_campaign=auto_publish&utm_content=cc647e00-b302-44ec-b299-e348310de837
