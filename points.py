import shared_info
pointdb = shared_info.points
import basics
import pull_info
from shared_info import serversList
from pull_info import pinfo
from pull_info import tinfo
import discord
import points_commands as pc
import json
import random

##PLAYER COMMANDS

commandFuncs = {
    'bal': pc.bal,
    'pleaders':pc.leaders,
    'mostactive':pc.mostactiveusers,
    'calls':pc.calls,
    'flip':pc.flip,
    'rob':pc.rob,
    'shared':pc.shared,
    'daily':pc.dailyclaim,
    'resetdaily':pc.resetdaily,
    'globalleaders':pc.all_leaders,
    'lotterypool':pc.lotterypool,
    'lottery':pc.lottery,
    'give':pc.give,
    "chatgpt":pc.chatgpt,
    "wiigeneral":pc.loseall,
    'servers':pc.servers,
    "mostused":pc.mostusedcommands,
    'leastused':pc.leastusedcommands
    
}


async def process_text(text, message):

    command = str.lower(text[0])
    if command == 'testfrog':
        await message.channel.send("https://tenor.com/view/frog-attacker-jumpscare-frog-jumpscare-boo-gif-1410553638666856648")
        return
    if command == 'testpig':
        await message.channel.send("https://tenor.com/view/pig-pig-funny-pig-chewing-animal-animal-funny-gif-15291725007664352238")
        return
    if command == 'echo':
        await message.channel.send(" ".join(message.content.split(" ")[1:]).replace("@",""))
   
    if command == 'ohce':
        await message.channel.send(" ".join(message.content.split(" ")[:-1])[::-1].replace("@",""))
        return
    if command == 'echo':
        return
    if command == 'count':
        try:
            value = int(text[1])
            for i in range (1, 2):
                await message.channel.send('we not counting no more')
            return
        except ValueError:
            return
    commandInfo = {"user":str(message.author.id)}
    commandInfo.update({"guild":message.guild})
    commandInfo.update({"guess":'Heads'})
    commandInfo.update({"bet":0.1})
    commandInfo.update({"number":1})
    commandInfo.update({"message":message.content})
    commandInfo.update({"ch":message.channel})
    for word in text:
        if word.__contains__("@"):
            commandInfo.update({"user":word.replace("<","").replace("!","").replace(">","").replace("@","")})
        try:
            commandInfo.update({"number":int(word)})
        except ValueError:
            pass
        try:
            commandInfo.update({"bet":float(word)})
        except ValueError:
            pass
        if word == "t" or word == "T" or word.upper() == "TAILS":
            commandInfo.update({"guess":'Tails'})
        
    
    
    embed = discord.Embed(title = "Points System:")
    
    embed = commandFuncs[command](embed, message.author, commandInfo)
    if isinstance(embed,str):
        await message.channel.send(embed)
        return
    #try: embed = commandFuncs[command](embed, p, commandInfo) #fill the embed with the specified function
    #except Exception as e:
     #   print(e) 
     #   embed.add_field(name='Error', value="An error occured. Command may not be specified.", inline=False)
    #print(pointdb)
    
    embed = pc.balance(embed, message.author, message.guild)
    #add the bottom parts
    s = shared_info.embedFooter
    if random.random() < 0.05:
        s = "Dedicated to Ben135, the best multiplayer GM in history"
    embed.set_footer(text=s)
    print(shared_info.curdate)
    await message.channel.send(embed=embed)
    x = open("points.json",'w')
    x.write(json.dumps(pointdb))
    x.close()




