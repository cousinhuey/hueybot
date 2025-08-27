import commands
import os
import json
import random
from shared_info import serversList
from datetime import datetime

# Initialize tracking file if missing
if not "tracking.json" in os.listdir():
    with open("tracking.json", "w") as f:
        f.write("{}")

# Load existing tracking data
with open("tracking.json", "r") as f:
    for line in f:
        tracks = json.loads(line)


async def budubudu(command, text, message):
    d = serversList[str(message.guild.id)]
    if 'redirect' in d:
        if str(message.channel.id) in d['redirect']:
            await message.channel.send(d['redirect'][str(message.channel.id)])
            return

    # ✅ Special case: run_draft needs clockTime and a numeric pick
    if command in ["rundraft", "startdraft"]:
        clockTime = 60  # default draft timer in seconds
        pick = 1        # always start draft at pick 1
        await commands.commands[command](message, pick, clockTime)
    else:
        await commands.commands[command](text, message)

    # 📊 Track command usage
    today = datetime.today().strftime('%Y-%m-%d')
    if str(message.guild.id) not in tracks:
        tracks.update({str(message.guild.id): {}})
    servertracks = tracks[str(message.guild.id)]
    if today not in servertracks:
        servertracks.update({today: {}})
    daytracks = servertracks[today]
    if str(message.author.id) not in daytracks:
        daytracks.update({str(message.author.id): {}})
    usertracks = daytracks[str(message.author.id)]
    if command not in usertracks:
        usertracks.update({command: 1})
    else:
        usertracks.update({command: usertracks[command] + 1})

    # Backup and save
    if os.path.exists("tracking_backup.json"):
        os.remove("tracking_backup.json")
    os.rename("tracking.json", "tracking_backup.json")

    with open("tracking.json", "w") as f:
        f.write(json.dumps(tracks))
    f.close()
