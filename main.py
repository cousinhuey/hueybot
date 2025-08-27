import discord
from shared_info import iscrowded
from discord.ext import commands
import json
import urllib.request
import csv
import asyncio
import checks
import basics
import commands
import shared_info
import os
import math
import trade_functions
import gc
import commandmaster
from unidecode import unidecode
import gzip  # 🔧 added for gzip exports
from dotenv import load_dotenv


points = shared_info.points
shared_info.commandsRaw = commands.commandsRaw

intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(intents=intents)
shared_info.bot = client


# ----------------- FIXED PROCESS FUNCTION -----------------
async def process(path, g):
    """Load or initialize an export for the given guild."""
    if os.path.exists(path):
        try:
            # check gzip header (0x1f 0x8b)
            with open(path, "rb") as raw_file:
                magic = raw_file.read(2)

            if magic == b"\x1f\x8b":
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

            shared_info.serverExports[str(g.id)] = data
            print(f"✅ Loaded export for {g.name} ({g.id})")

        except Exception as e:
            print(f"⚠️ Error loading export for {g.name}: {e}")
            shared_info.serverExports[str(g.id)] = {}
    else:
        print(f"⚠️ No export found for {g.name} ({g.id}), creating empty export")
        shared_info.serverExports[str(g.id)] = {}
        # optional: directly create empty file
        os.makedirs("exports", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
# -----------------------------------------------------------


serversList = shared_info.serversList

# ----------------- SAVE EXPORTS SAFELY -----------------
@client.event
async def on_disconnect():
    print("⚠️ Bot disconnected from Discord. Saving exports...")
    shared_info.save_exports()

async def save_and_close():
    """Safe close method for the bot."""
    print("🛑 Bot shutting down. Saving exports...")
    shared_info.save_exports()
    await client.close()
# -------------------------------------------------------


@client.event
async def on_ready():
    print(client.user.id)
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='SolarBalls'))
    print('Bot connected')
    for g in client.guilds:
        serversList = checks.server_check(g.id, g.name)
        for item in serversList:
            if 'draftStatus' in serversList[item]:
                if serversList[item]['draftStatus']['draftRunning']:
                    serversList[item]['draftStatus'].update({'draftRunning': False})

        await basics.save_db(serversList)


@client.event
async def on_guild_join(g):
    print('Joined', g.name)
    serversList = checks.server_check(g.id, g.name)
    await basics.save_db(serversList)


commandAliases = shared_info.commandAliases
modOnlyCommands = shared_info.modOnlyCommands


@client.event
async def on_message(message):
    try:
        prefix = serversList[str(message.guild.id)]['prefix']
    except:
        prefix = '-'

    if message.content.startswith(prefix):
        print("============")
        print(message.guild.name)
        print(message.channel.name)
        print(message.author.name)
        print(message.content)
        print("-------------------")
    
    if not str(message.author.id) in points:
        points.update({str(message.author.id): 0})
    if not message.content.startswith(str(prefix)):
        increment = math.sqrt(len(message.content)) * 0.01
        points.update({str(message.author.id): points[str(message.author.id)] + increment})
        if str(points[str(message.author.id)]) == "nan":
            points.update({str(message.author.id): 0})
    
    # trade scanning
    if message.guild is not None:
        if f"<#{message.channel.id}>" == serversList[str(message.guild.id)]['tradechannel'] and message.author.id != client.user.id:
            if serversList[str(message.guild.id)]['draftStatus']['draftRunning']:
                await message.channel.send("No trades during draft!")
                return
            print("here")
            g = message.guild
            todelete = set()
            for item in shared_info.serverExports:
                if not serversList[item]['draftStatus']['draftRunning'] == True or item == str(g.id):
                    todelete.add(item)
                else:
                    print(item)
            for thing in todelete:
                del shared_info.serverExports[thing]
            if not str(g.id) in shared_info.serverExports:
                current_dir = os.getcwd()
                path_to_file = os.path.join(current_dir, "exports", f'{g.id}-export.json')
                await process(path_to_file, g)
                          
            print(len(shared_info.serverExports))
            if str.lower(message.content) == 'confirm':
                if not serversList[str(message.guild.id)]['draftStatus']['draftRunning']:
                    await trade_functions.confirm_message(message)
                else:
                    await message.channel.send("No trades during draft!")
            else:
                if not serversList[str(message.guild.id)]['draftStatus']['draftRunning'] == True:
                    await trade_functions.scan_text(message.content, message)
                else:
                    await message.channel.send("No trades during draft!")
        else:
            if message.content.startswith(str(prefix)):
                if message.author.guild_permissions.manage_messages and message.content == prefix+"forcestopdraft":
                    serversList[str(message.guild.id)]['draftStatus'].update({'draftRunning': False})
                    await message.channel.send("OK. Dont blame me if something went wrong though, as this is more like the equivalent of Danger Zone in the BBGM game.")
                
                text = message.content[1:].split(' ')
                command = text[0]
                
                command = str.lower(command)
                if command in commandAliases:
                    text[0] = commandAliases[command]
                    command = commandAliases[command]
                if command in commands.commands:
                    valid = False
                    if command in modOnlyCommands:
                        if message.author.guild_permissions.manage_messages:
                            valid = True
                    else:
                        valid = True
                    if valid:
                        if shared_info.iscrowded and (not command == 'pick') and (not commands.commandsRaw[command] in ['points','settings']):
                            await message.channel.send("your command is queued, please wait")
                            t = 0
                            while shared_info.iscrowded:
                                await asyncio.sleep(1)
                                t += 1
                                if t == 10:
                                    await message.channel.send("the wait was too long, you fell out of queue")
                                    return
                        print("got to command")

                        if not commands.commandsRaw[command] in ['points','settings','inventory']:
                            shared_info.iscrowded = True
                            try:
                                g = message.guild
                                todelete = set()
                                for item in shared_info.serverExports:
                                    if not (serversList[item]['draftStatus']['draftRunning'] == True or item == str(g.id)):
                                        todelete.add(item)
                                    else:
                                        print('not deleting '+str(item))
                                for thing in todelete:
                                    del shared_info.serverExports[thing]
                                if not str(g.id) in shared_info.serverExports:
                                    if not command == 'load':
                                        current_dir = os.getcwd()
                                        path_to_file = os.path.join("exports", f'{g.id}-export.json')
                                        print("Starting to load")
                                        await process(path_to_file, g)
                                    gc.collect()
                            except Exception as e:
                                print(e)
                                await message.channel.send("You need an export to do this, but you don't have one.")

                        await commandmaster.budubudu(command, text, message)
                        shared_info.iscrowded = False
                    else:
                        try:
                            await message.channel.send("You aren't authorized to run that command.")
                        except Exception as e:
                            print(e)
            
            elif message.content.endswith('ohce'+prefix):
                command = "ohce"
                text = message.content[:-1].split(' ')
                text = text[-1:] + text[:-1]
                print(text)
                await commandmaster.budubudu(command, text, message)
            else:
                if message.channel in shared_info.trivias and not len(message.content) > 30:
                    if unidecode(shared_info.trivias[message.channel].lower()) in message.content.lower():
                        todelete = set()
                        for item, value in shared_info.triviabl.items():
                            if value == message.channel:
                                todelete.add(item)
                        for item in todelete:
                            del shared_info.triviabl[item]
                        del shared_info.trivias[message.channel]
                        await message.channel.send(message.author.mention+" correct, and you gain 5 points")
                        p = points[str(message.author.id)]
                        points.update({str(message.author.id): p+5})


# Read Discord token
discord_token = os.getenv('DISCORD_TOKEN')
if not discord_token:
    try:
        f = open("token.txt","r")
        for line in f:
            discord_token = line.replace("\n","")
        f.close()
    except FileNotFoundError:
        print("ERROR: No Discord token found. Please set DISCORD_TOKEN environment variable or create token.txt file.")
        exit(1)

client.run(discord_token)
