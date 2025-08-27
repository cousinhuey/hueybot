## DRAFT COMMANDS

import shared_info
from shared_info import serverExports
from shared_info import serversList
import pull_info
import basics
import discord
import draft_commands as dc

commandFuncs = {
    'board': dc.board,
    'add': dc.add,
    'remove': dc.remove,
    'dmove': dc.move,
    'clearboard': dc.clear,
    'auto': dc.auto,
    'pick': dc.pick,
    'pausedraft': dc.pause,
    'resumedraft': dc.resume,   # ✅ hinzugefügt
    'bulkadd': dc.bulkadd
}


async def process_text(text, message):
    export = shared_info.serverExports[str(message.guild.id)]
    season = export['gameAttributes']['season']
    command = str.lower(text[0])

    # Saison-Argument herausfiltern (falls vorhanden) – aktuell nicht weiter genutzt
    for m in list(text):
        try:
            _m = int(m)
            text.remove(m)
        except:
            pass

    # Immer ein Embed anlegen
    embed = discord.Embed(
        title='Draft Preparation',
        description=f"{season} season"
    )

    # Command ausführen
    try:
        if command in commandFuncs:
            embed = await commandFuncs[command](embed, message)
        else:
            embed.add_field(
                name="Error",
                value=f"Unknown command: `{command}`",
                inline=False
            )
    except Exception as e:
        print(f"⚠️ Draft command error: {e}")
        embed.add_field(
            name='Error',
            value="An error occurred while executing this command.",
            inline=False
        )

    embed.set_footer(text=shared_info.embedFooter)
    await message.channel.send(embed=embed)
