import shared_info
exports = shared_info.serverExports
import basics
import os
import pull_info
from pull_info import pinfo
from pull_info import tinfo
from shared_info import triviabl
import discord
import league_commands

## LEAGUE COMMANDS

commandFuncs = {
    'fa': league_commands.fa,
    'draftorder': league_commands.draftorder,
    'specialists': league_commands.specialists,
    'po': league_commands.po,
    'playoffpredict': league_commands.standingspredict,
    'sadprogs': league_commands.sadprogs,
    'godprogs': league_commands.godprogs,
    'draft': league_commands.draft,
    'pr': league_commands.pr,
    'pickvalue': league_commands.pickvalue,
    'matchups': league_commands.matchups,
    'top': league_commands.top,
    'injuries': league_commands.injuries,
    'deaths': league_commands.deaths,
    'leaders': league_commands.leaders,
    'summary': league_commands.summary,
    'leaguegraph': league_commands.leaguegraph,
    'mostunbalanced': league_commands.mostunbalanced,
    'lgoptions': league_commands.lgoptions,
    'topall': league_commands.topall,
    'standings': league_commands.standings,
    'playoffs': league_commands.playoffs,
    'to': league_commands.to,
    'mostaverage': league_commands.mostaverage,
    'reprog': league_commands.reprog,
    'stripnames': league_commands.stripnames
}


async def process_text(text, message):
    guild_id = str(message.guild.id)

    # Check if export exists
    if guild_id not in shared_info.serverExports:
        await message.channel.send("⚠️ You need an export to do this, but you don't have one.")
        return

    export = shared_info.serverExports[guild_id]

    # ✅ Validation: make sure it's a valid BBGM export
    if not export or "gameAttributes" not in export or "players" not in export or "teams" not in export:
        await message.channel.send("❌ Invalid or empty export found for this server. Please upload a valid export file first.")
        return

    season = export['gameAttributes']['season']
    players = export['players']
    teams = export['teams']

    commandSeason = season
    pageNumber = 1
    command = str.lower(text[0])

    # Handle numbers in command (season or page number)
    for m in list(text):  # copy of text for safe modification
        try:
            m_int = int(m)
            if m_int > 1500:  # treat as season
                commandSeason = m_int
                text.remove(m)
            else:  # treat as page number
                pageNumber = m_int
                text.remove(m)
        except ValueError:
            pass

    descripLine = str(commandSeason) + ' season'
    if command == 'fa' and season != commandSeason:
        descripLine = f"Page {commandSeason}"

    embed = discord.Embed(title=message.guild.name, description=descripLine)
    commandInfo = {
        'serverId': message.guild.id,
        'message': message,
        'season': commandSeason,
        'pageNumber': pageNumber,
        'text': text
    }

    # Block trivia conflict
    if commandInfo['message'].author.id in triviabl or message.channel in triviabl.values():
        embed = discord.Embed(
            title="Trivia",
            description="You're not allowed to run any league commands within 30 seconds of starting a trivia."
        )
        embed.set_footer(text=shared_info.embedFooter)
        await message.channel.send(embed=embed)
        return

    # Run the actual league command
    embed = commandFuncs[command](embed, commandInfo)
    embed.set_footer(text=shared_info.embedFooter)

    gc = ["leaguegraph", 'pickvalue']

    # Save DB if necessary
    if command in ["reprog", "stripnames"]:
        current_dir = os.getcwd()
        path_to_file = os.path.join(current_dir, "exports", f"{commandInfo['serverId']}-export.json")
        await basics.save_db(export, path_to_file)

        # 🔥 Save persistent exports too
        shared_info.save_exports()

    await message.channel.send(embed=embed)

    # Send graph if required
    if command in gc:
        waswrong = False
        for field in embed.fields:
            if field.name == "Error":
                waswrong = True
        if not waswrong:
            try:
                f = open("third_figure.png", 'rb')
                await message.channel.send("Your graph", file=discord.File(f))
                f.close()
            except Exception:
                await message.channel.send("There was some kind of mistake")
