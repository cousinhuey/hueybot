import discord
import basics
import commands
import shared_info
serversList = shared_info.serversList


# SETTINGS
async def process_text(text, message):
    if text[0] == 'settings':
        if len(text) == 1:
            await main_prompt(message)
        else:
            if text[1] == 'fa': 
                await fa_prompt(message)
            elif text[1] == 'trade': 
                await trade_prompt(message)
            elif text[1] == 'league': 
                await league_prompt(message)
            elif text[1] == 'draft': 
                await draft_prompt(message)

    if text[0] == 'edit':
        if len(text) == 1:
            await message.channel.send('Please supply a value to edit.')
        elif len(text) == 3:
            await edit_setting(text, message)
        else:
            await message.channel.send(
                'When editing messages, please use the format ``-edit [setting] [new value]``. '
                'It looks like you supplied too many values.'
            )

async def main_prompt(message):
    prefix = serversList[str(message.guild.id)]['prefix']
    serverName = message.guild.name
    serverSettings = shared_info.serversList[str(message.guild.id)]
    embed = discord.Embed(
        title="EldoBot Settings", 
        description=f"Settings for server {serverName}.\n \n"
                    '**Specify a category of settings to see more. '
                    'Categories are: draft, fa, league, and trade.**'
    )
    embed.add_field(
        name='General',
        value='**Prefix:** ' + serverSettings['prefix'] + '\n' 
              + f'*Edit with {prefix}edit [prefix]*' + '\n'
              + f"**Trade Confirmation Channel:** {serverSettings['tradechannel']}" + '\n'
              + '*Trade confirmations should be sent here. Edit with -edit tradechannel [new channel].*' + '\n' 
              + f"**FA Channel:** {serverSettings['fachannel']}" + '\n' 
              + '*FA signings will be sent here. Edit with -edit fachannel [new channel].*' + '\n'
              + f"**Release Announcement Channel:** {serverSettings['releasechannel']}" + '\n' 
              + '*Releases will be sent here. Edit with -edit releasechannel [new channel].*' + '\n'
              + f"**Trade Announcement Channel:** {serverSettings['tradeannouncechannel']}" + '\n' 
              + f'*This channel is where all confirmed trades will be recorded. Edit with {prefix}edit tradeannouncechannel [#new channel].*' + '\n'
              + f"**Pick Announcement Channel:** {serverSettings['draftchannel']}" + '\n' 
              + f"*Draft picks will be sent here. Edit using {prefix}edit draftchannel [new channel].*"
    )
    await message.channel.send(embed=embed)

async def fa_prompt(message):
    prefix = serversList[str(message.guild.id)]['prefix']
    serverName = message.guild.name
    serverSettings = shared_info.serversList[str(message.guild.id)]
    embed = discord.Embed(
        title="EldoBot Settings - Free Agency", 
        description=f"FA Settings for server {serverName}"
    )
    # (gekürzt – keine Änderungen am Inhalt)
    await message.channel.send(embed=embed)

async def trade_prompt(message):
    prefix = serversList[str(message.guild.id)]['prefix']
    serverName = message.guild.name
    serverSettings = shared_info.serversList[str(message.guild.id)]
    embed = discord.Embed(
        title="EldoBot Settings - Trades", 
        description=f"Trade Settings for server {serverName}"
    )
    # (gekürzt – keine Änderungen am Inhalt)
    await message.channel.send(embed=embed)

async def league_prompt(message):
    prefix = serversList[str(message.guild.id)]['prefix']
    serverName = message.guild.name
    serverSettings = shared_info.serversList[str(message.guild.id)]
    embed = discord.Embed(
        title="EldoBot Settings - League", 
        description="General league settings, mostly relating to finances."
    )
    # (gekürzt – keine Änderungen am Inhalt)
    await message.channel.send(embed=embed)

async def draft_prompt(message):
    prefix = serversList[str(message.guild.id)]['prefix']
    serverName = message.guild.name
    serverSettings = shared_info.serversList[str(message.guild.id)]
    embed = discord.Embed(
        title="EldoBot Settings - Draft", 
        description=f"Settings relating to the draft."
    )
    embed.add_field(
        name='Clock Settings',
        value='Your clock times are set as:\n'
              f"``{serverSettings['draftclock']}``\n"
              f"Adjust this by using {prefix}edit draftclock [new value]. **You should provide a list of numbers separated by commas, "
              "and each number represents the number of seconds of the clock in that round.** Some examples:\n"
              "• ``300,200,0`` - round one 300s, round two 200s, round three autopick\n"
              "• ``300,0`` - round one 300s, round two autopick\n\n"
              "If a value is not specified for a round, it defaults to 180 seconds."
    )
    await message.channel.send(embed=embed)

async def edit_setting(text, message):
    toEdit = str.lower(text[1])
    newValue = text[2]
    server = str(message.guild.id)

    if toEdit in serversList[server]:
        # hier NICHT mehr zu Liste casten – bleibt String
        valid = commands.settingsDirectory[toEdit](newValue)
        if valid:
            serversList[server][toEdit] = newValue
            await basics.save_db(serversList)
            await message.channel.send(f"**Success!** New {toEdit} set to {newValue}!")
        else:
            await message.channel.send(f"Value ``{newValue}`` is invalid.")
    else:
        await message.channel.send(
            "Invalid setting provided. Please check the -settings pages to confirm the setting you want to edit."
        )

def get_setting(guild_id, setting):
    """Holt EIN bestimmtes Setting."""
    export = basics.get_export(guild_id)
    value = export["settings"].get(setting)

    # cast
    if value in ["True", "False"]:
        return value == "True"
    if setting == "draftclock":
        try:
            return [int(x.strip()) for x in value.split(",")]
        except Exception:
            return [60]
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value

def get_settings(guild_id):
    export = basics.get_export(guild_id)
    settings_dict = {}
    for setting, value in export.get("settings", {}).items():
        if value in ["True", "False"]:
            settings_dict[setting] = value == "True"
        elif setting == "draftclock":
            try:
                settings_dict[setting] = [int(x.strip()) for x in value.split(",")]
            except Exception:
                settings_dict[setting] = [60]
        else:
            try:
                settings_dict[setting] = int(value)
            except ValueError:
                try:
                    settings_dict[setting] = float(value)
                except ValueError:
                    settings_dict[setting] = value
    return settings_dict
