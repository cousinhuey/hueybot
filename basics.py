import os
import json
import dropbox
import requests
import asyncio
import aiohttp
import aiofiles
import gzip
from unidecode import unidecode
from difflib import SequenceMatcher
import random
import discord
import copy
import shared_info
import shutil
import storage 

bot = shared_info.bot

# Basis-Verzeichnis für Railway Volume
VOLUME_PATH = "/mnt/data"
EXPORTS_PATH = os.path.join(VOLUME_PATH, "exports")
os.makedirs(EXPORTS_PATH, exist_ok=True)

# 🔑 App-Credentials (von Dropbox Dev Console)
CLIENT_ID = "bwmbvhvhg74009d"
CLIENT_SECRET = "gfpqqt6ncmm73e1"

# ✅ Dein Refresh Token hier
REFRESH_TOKEN = "UIIbxxU4hfMAAAAAAAAAAQjqHSamFSIJHlQvUuHBjv4Jkk5WC_o27upWYId93ooq"

DROPBOX_TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"


# ----------------------------------------------------------------------
# Dropbox Helpers
# ----------------------------------------------------------------------
def get_access_token():
    """Holt mit dem Refresh Token automatisch ein frisches Access Token"""
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    r = requests.post(DROPBOX_TOKEN_URL, data=data)
    r.raise_for_status()
    token_data = r.json()
    return token_data["access_token"]


def upload_to_dropbox(path_to_file, dest_path):
    """Lädt eine Datei zu Dropbox hoch und gibt die Sharing-URL zurück"""
    CHUNK_SIZE = 4 * 1024 * 1024
    access_token = get_access_token()
    dbx = dropbox.Dropbox(access_token)

    # Falls Datei schon existiert -> löschen
    try:
        dbx.files_get_metadata(dest_path)
        dbx.files_delete_v2(dest_path)
    except dropbox.exceptions.ApiError:
        pass

    with open(path_to_file, "rb") as f:
        file_size = os.path.getsize(path_to_file)
        if file_size <= CHUNK_SIZE:
            dbx.files_upload(f.read(), dest_path)
        else:
            upload_session_start_result = dbx.files_upload_session_start(f.read(CHUNK_SIZE))
            session_id = upload_session_start_result.session_id
            offset = CHUNK_SIZE

            while offset < file_size:
                if file_size - offset <= CHUNK_SIZE:
                    dbx.files_upload_session_finish(
                        f.read(CHUNK_SIZE),
                        dropbox.files.UploadSessionCursor(session_id=session_id, offset=offset),
                        dropbox.files.CommitInfo(path=dest_path),
                    )
                else:
                    dbx.files_upload_session_append_v2(
                        f.read(CHUNK_SIZE),
                        dropbox.files.UploadSessionCursor(session_id=session_id, offset=offset),
                    )
                offset += CHUNK_SIZE

    # Sharing-Link erstellen oder bestehenden zurückgeben
    try:
        shared_link_metadata = dbx.sharing_create_shared_link_with_settings(dest_path)
        url = shared_link_metadata.url
    except dropbox.exceptions.ApiError as e:
        if (
            isinstance(e.error, dropbox.sharing.CreateSharedLinkWithSettingsError)
            and e.error.is_shared_link_already_exists()
        ):
            links = dbx.sharing_list_shared_links(path=dest_path).links
            if len(links) > 0:
                url = links[0].url
    return url


async def update_export_content(message):
    """Export hochladen und Link im Discord-Channel posten"""
    await message.channel.send("Uploading your export to Dropbox...")

    path_to_file = os.path.join(EXPORTS_PATH, f"{message.guild.id}-export.json")

    if not os.path.exists(path_to_file):
        await message.channel.send("⚠️ No export file found for this server.")
        return

    loop = asyncio.get_event_loop()
    url = await loop.run_in_executor(
        None,
        upload_to_dropbox,
        path_to_file,
        f"/exports/{message.guild.id}-export.json"
    )

    text = "**Your Dropbox link:** " + url.replace("www.", "dl.")
    await message.channel.send(text)



async def update_export(text, message):
    """Command für -update oder -updateexport"""
    if message.content.startswith("-updateexport"):
        await message.channel.send("⚠️ WARNING: The call '-updateexport' is deprecated. Use '-update' instead.")
    if message.content.startswith("-update") or message.content.startswith("-updateexport"):
        print("updating export")
        asyncio.create_task(update_export_content(message))


# ----------------------------------------------------------------------
# JSON + DB Helpers
# ----------------------------------------------------------------------
async def load_json_or_gzip(file_path):
    async with aiofiles.open(file_path, "rb") as f:
        raw_data = await f.read()
    try:
        if raw_data[:2] == b"\x1f\x8b":  # gzip Header
            decompressed_data = gzip.decompress(raw_data)
            return json.loads(decompressed_data.decode("utf-8"))
        else:
            return json.loads(raw_data.decode("utf-8"))
    except Exception as e:
        print(f"❌ Fehler beim Laden von {file_path}: {e}")
        raise


def clean_priorities(db):
    for n, s in db.items():
        offers = s["offers"]
        offers = sorted(offers, key=lambda o: o["priority"])
        teams = []
        for o in offers:
            teams.append(o["team"])
        teams = list(set(teams))
        for t in teams:
            pri = 1
            for o in offers:
                if o["team"] == t:
                    o["priority"] = pri
                    pri += 1
    return db




# ----------------------------------------------------------------------
# DB Funktionen
# ----------------------------------------------------------------------
async def save_db_content(db, name="servers.json"):
    if name == "servers.json":
        db = clean_priorities(db)
    async with aiofiles.open(os.path.join(VOLUME_PATH, name), "w") as f:
        await f.write(json.dumps(db))


async def save_db(db, name="servers.json"):
    if name == "servers.json":
        shutil.copy(
            os.path.join(VOLUME_PATH, "servers.json"),
            os.path.join(VOLUME_PATH, "serversb.json")
        )
    await asyncio.create_task(save_db_content(db, name))


def load_db(name="servers.json"):
    with open(os.path.join(VOLUME_PATH, name)) as f:
        db = json.load(f)
    return db


# ----------------------------------------------------------------------
# Exports
# ----------------------------------------------------------------------
def get_export(guild_id):
    path = os.path.join(EXPORTS_PATH, f"{guild_id}-export.json")
    if not os.path.exists(path):
        return {"settings": {}}

    with open(path, "rb") as f:
        raw_data = f.read()
    if raw_data[:2] == b"\x1f\x8b":
        decompressed_data = gzip.decompress(raw_data)
        data = json.loads(decompressed_data.decode("utf-8"))
    else:
        data = json.loads(raw_data.decode("utf-8"))

    # immer settings sicherstellen
    if "settings" not in data:
        data["settings"] = {}
    return data


async def load_json_or_gzip(path):
    async with aiofiles.open(path, "rb") as f:
        raw_data = await f.read()
    if raw_data[:2] == b"\x1f\x8b":
        decompressed_data = gzip.decompress(raw_data)
        return json.loads(decompressed_data.decode("utf-8"))
    return json.loads(raw_data.decode("utf-8"))


# ----------------------------------------------------------------------
# Export Loader
# ----------------------------------------------------------------------
async def load_export_content(text, message):
    if len(text) == 1:
        await message.channel.send("Please provide an export URL.")
        return

    url = text[1]
    if not url.startswith("http"):
        await message.channel.send("Invalid link.")
        return

    await message.channel.send("Loading export...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                path = os.path.join(EXPORTS_PATH, f"{message.guild.id}-export.json")
                async with aiofiles.open(path, "wb") as f:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        await f.write(chunk)

        shared_info.serverExports[str(message.guild.id)] = await load_json_or_gzip(path)

        # ✅ Export zusätzlich im persistenten Storage speichern
        storage.save_export(
            str(message.guild.id),
            shared_info.serverExports[str(message.guild.id)]
        )

        players = shared_info.serverExports[str(message.guild.id)].get("players", [])
        for p in players:
            p["stats"].sort(key=lambda s: s["season"])
            p["ratings"].sort(key=lambda r: r["season"])

        await message.channel.send("Export loaded successfully!")

    except Exception as e:
        print(f"Error loading export: {e}")
        await message.channel.send(
            "There was an error loading that file. Ensure it's a valid JSON or gzipped JSON, or try another link."
        )


async def load_export(text, message):
    print("loading")
    loop = asyncio.get_event_loop()
    await loop.create_task(load_export_content(text, message))


# ----------------------------------------------------------------------
# Utility Functions
# ----------------------------------------------------------------------
def find_match(input, export, fa=False, activeOnly=False, settings=None):
    bestMatch = 0
    players = export["players"]
    winningPlayer = None
    for p in players:
        tid_value = p.get("tid")

        if tid_value is None:
            p["tid"] = -1   # None → Free Agent
        else:
            try:
                p["tid"] = int(tid_value)
            except Exception:
                p["tid"] = -1   # Fallback → Free Agent
        playerName = unidecode(p["firstName"] + " " + p["lastName"])
        matchScore = SequenceMatcher(a=str.lower(input), b=str.lower(playerName.replace(".", ""))).ratio()
        try:
            if p["ratings"][-1]["ovr"] > 50:
                matchScore += (random.randint(7500, 10000)) / 100000000
            else:
                matchScore += (random.randint(1, 10000)) / 100000000
        except Exception:
            matchScore += (random.randint(1, 10000)) / 100000000

        if p["tid"] > -1 or p["tid"] == -2:
            matchScore += 0.1
            if export["gameAttributes"]["phase"] == 5 and p["tid"] == -2:
                matchScore += 0.15

        if fa and p["tid"] == -1:
            matchScore += 0.5
        if activeOnly and p["tid"] > -2:
            matchScore += 0.5
        if input.replace(" ", "") == playerName.replace(" ", ""):
            matchScore += 1

        for y in range(1, 5):
            for x in range(0, len(input) - y):
                tocomp = input[x : x + y]
                if playerName.lower().__contains__(tocomp):
                    matchScore += 0.05 * y

        if matchScore > bestMatch:
            bestMatch = matchScore
            winningPlayer = p["pid"]

    if settings is not None and "nickname" in settings:
        for a, b in settings["nickname"].items():
            if b.lower().strip() == input.lower().strip():
                winningPlayer = int(a)
    return winningPlayer


def group_numbers(numbers):
    if numbers == []:
        return "No Experience"
    numbers.sort()
    groups = []
    start = numbers[0]
    end = numbers[0]
    for i in range(1, len(numbers)):
        if numbers[i] == end + 1:
            end = numbers[i]
        else:
            groups.append(str(start) if start == end else f"{start}-{end}")
            start = numbers[i]
            end = numbers[i]
    groups.append(str(start) if start == end else f"{start}-{end}")
    return ", ".join(groups)


def rating_names(text):
    text = str.lower(text)
    ratingTerms = {
        "hgt": ["height", "tall", "size", "stature"],
        "stre": ["strength", "muscle", "toughness", "fat", "big"],
        "spd": ["speed", "quick", "velocity", "agility"],
        "jmp": ["jump", "vertical", "leap", "bounce"],
        "endu": ["endurance", "stamina", "cardio", "resilience"],
        "ins": ["inside", "post", "interior", "paint"],
        "dnk": ["dunks", "layups", "slashing", "finishing"],
        "ft": ["freethrow", "foulshot", "free"],
        "fg": ["midrange", "2pt", "two"],
        "tp": ["threepoint", "outside", "range", "3pt"],
        "oiq": ["offensiveiq", "offense"],
        "diq": ["defensiveiq", "defense"],
        "drb": ["dribbling", "handling", "control"],
        "pss": ["passing", "playmaking", "assist"],
        "reb": ["rebounding", "boards", "boxout"],
    }
    for r, t in ratingTerms.items():
        if text in t:
            return r
    return text


def get_setting_value(setting, export, year=None):
    settingData = export["gameAttributes"][setting]
    if year is None:
        year = export["gameAttributes"]["season"]
    value = None
    if isinstance(settingData, list):
        if isinstance(settingData[0], dict):
            for s in settingData:
                if s["start"] <= int(year):
                    value = s["value"]
        else:
            value = settingData
    else:
        value = settingData
    return value


def calculate_formula(p, season, formula):
    age = season - p["born"]["year"]
    r = p["ratings"][-1]
    hgt, stre, spd, jmp, endu = r["hgt"], r["stre"], r["spd"], r["jmp"], r["endu"]
    ins, dnk, fg, ft, tp = r["ins"], r["dnk"], r["fg"], r["ft"], r["tp"]
    oiq, diq, drb, pss, reb = r["oiq"], r["diq"], r["drb"], r["pss"], r["reb"]
    ovr, pot = r["ovr"], r["pot"]
    value = eval(formula)
    return value


def formula_ranking(players, season, formula):
    playerList = []
    for p in players:
        value = calculate_formula(p, season, formula)
        playerList.append([p["pid"], value])
    playerList.sort(key=lambda p: p[1], reverse=True)
    return playerList


def team_mention(message, teamName, abbrev, emoji_add=True):
    role = discord.utils.get(message.guild.roles, name=teamName)
    for role2 in message.guild.roles:
        if role2.name.replace(" ", "").lower() == teamName.replace(" ", "").lower():
            role = role2
    roleMention = role.mention if role else teamName
    emoji = discord.utils.get(message.guild.emojis, name=str.lower(abbrev))
    if emoji and emoji_add:
        return f"{roleMention} {emoji}"
    return roleMention


def rookie_salary(pick, serverExport):
    draftPicks = serverExport["draftPicks"]
    players = serverExport["players"]
    season = serverExport["gameAttributes"]["season"]
    totalPicks = sum(1 for dpick in draftPicks if dpick["round"] == 1 and dpick["season"] == season)
    totalPicks += sum(1 for p in players if p["draft"]["year"] == season and p["draft"]["round"] == 1)

    topRookieSalary = (
        (serverExport["gameAttributes"]["draftPickAutoContractPercent"] / 100)
        * serverExport["gameAttributes"]["maxContract"]
    )
    minContract = serverExport["gameAttributes"]["minContract"]
    salary = topRookieSalary * (1 - pick / totalPicks) + minContract * (pick / totalPicks)
    return round(salary)


def get_nested_value(dct, keys):
    for key in keys:
        if key in dct:
            dct = dct[key]
        else:
            return None
    return dct


def player_list_embed(playerList, pageNum, season, sortBy, reverse=True, draft=False, export=None):
    values = ['ovr', 'pot', 'hgt', 'stre', 'spd', 'jmp', 'endu',
              'ins', 'dnk', 'ft', 'fg', 'tp', 'oiq', 'diq',
              'drb', 'pss', 'reb']

    # Sortierung vorbereiten
    if isinstance(sortBy, str):
        sortBy = rating_names(sortBy)
        if str.lower(sortBy) in values:
            sortBy = str.lower(sortBy)
            playerList.sort(key=lambda o: o['ratings'].get(sortBy, 0), reverse=reverse)
        else:
            sortBy = 'ovr'
            playerList.sort(key=lambda o: o['ratings'].get(sortBy, 0), reverse=reverse)
    else:
        playerList.sort(key=lambda p: get_nested_value(p, sortBy) or 0, reverse=reverse)

    # Pagination
    totalPages, remainder = divmod(len(playerList), 14)
    totalPages += 1
    playerList = playerList[((pageNum-1)*14):(pageNum*14)]

    commandText = ''
    number = (pageNum-1)*14 + 1

    for f in playerList:
        if draft:
            # Absicherung: Werte holen oder Defaults setzen
            draft_round = f.get('draftRound')
            draft_pick = f.get('draftPick')
            draft_year = f.get('draftYear', season)
            born = f.get('born', 0)
            # DraftRating → fallback auf OVR
            draft_rating = f.get('draftRating', f['ratings'].get('ovr', '?'))
            position = f.get('position', '?')
            name = f.get('name', 'Unknown')

            # Falls keine Draft-Infos vorhanden → UDFA
            if draft_round is None or draft_pick is None:
                draft_info = "UDFA"
            else:
                draft_info = f"R{draft_round} P{draft_pick}"

            line = f"- ``{draft_info}``. {position} **{name}** - {draft_year - born} yo {draft_rating}"

            if isinstance(sortBy, str):
                line += f": **{f['ratings'].get(sortBy, 'OVR')} {str.upper(sortBy)}**"
            commandText += line + '\n'

        else:
            born = f.get('born', 0)
            position = f.get('position', '?')
            name = f.get('name', 'Unknown')
            ovr = f.get('ovr', '?')
            pot = f.get('pot', '?')
            skills = f.get('skills', [])

            line = f"- ``{number}``. {position} **{name}** - {season - born} yo {ovr}/{pot} {skills}"

            if isinstance(sortBy, str):
                line += f" **{f['ratings'].get(sortBy, 'OVR')} {str.upper(sortBy)}**"
            else:
                if sortBy != ['value']:
                    line += f": **{get_nested_value(f, sortBy)}**"

            commandText += line + '\n'
            number += 1

    commandText += '\n' + f"*{totalPages} total pages.*"

    if isinstance(sortBy, str):
        return [commandText, str.upper(sortBy), totalPages]
    else:
        return [commandText, str(sortBy[-1]), totalPages]


async def resign_odds(playerPrices, years, offerAmount):
    if int(years) in playerPrices:
        askingPrice = playerPrices[int(years)]
        offerRatio = float(offerAmount) / (askingPrice / 1000)
        if offerRatio >= 1:
            probability = 1
        else:
            probability = ((offerRatio - 0.5) / 0.5) ** 2 if offerRatio > 0.5 else 0
    else:
        probability = 0
    return probability


# ----------------------------------------------------------------------
# Player Management (Release etc.)
# ----------------------------------------------------------------------
async def release_player(pid, message, commandInfo, updateexport=True, export=None):
    serverId = message.guild.id
    if export is None:
        if str(serverId) in shared_info.serverExports:
            export = shared_info.serverExports[str(serverId)]
        else:
            await message.channel.send("No export detected, which is weird")
            return

    players = export["players"]
    events = export["events"]
    season = export["gameAttributes"]["season"]
    teams = export["teams"]

    for p in players:
        if p["pid"] == pid:
            playerName = p["firstName"] + " " + p["lastName"]
            age = season - p["born"]["year"]
            ovr = p["ratings"][-1]["ovr"]
            pot = p["ratings"][-1]["pot"]

            serverSettings = shared_info.serversList[str(commandInfo["serverId"])]
            if "PO" in serverSettings:
                serverSettings["PO"].pop(pid, None)
                serverSettings["PO"].pop(str(pid), None)
            if "TO" in serverSettings:
                serverSettings["TO"].pop(pid, None)
                serverSettings["TO"].pop(str(pid), None)
            await save_db(shared_info.serversList)

            tid = copy.deepcopy(p["tid"])
            for t in teams:
                if t["tid"] == tid:
                    abbrev = t["abbrev"]
                    teamName = t["region"] + " " + t["name"]

            newEvent = {
                "type": "release",
                "pids": [pid],
                "tids": [tid],
                "season": season,
                "eid": events[-1]["eid"] + 1,
                "text": f'The <a href="/l/20/roster/{abbrev}/{season}">{teamName}</a> released <a href="/l/20/player/{pid}">{playerName}</a>.',
            }
            events.append(newEvent)

            transaction = {
                "season": export["gameAttributes"]["season"],
                "phase": export["gameAttributes"]["phase"],
                "tid": tid,
                "type": "release",
            }
            p.setdefault("transactions", []).append(transaction)

            if p["draft"]["year"] != season:
                if p["draft"]["year"] == season - 1 and export["gameAttributes"]["phase"] == 0:
                    p["salaries"] = []
                else:
                    newRelease = {"pid": p["pid"], "tid": tid, "contract": copy.deepcopy(p["contract"])}
                    newRelease["rid"] = export.get("releasedPlayers", [{"rid": -1}])[-1]["rid"] + 1
                    export.setdefault("releasedPlayers", []).append(newRelease)
            else:
                p["salaries"] = []

            p["tid"] = -1
            p["contract"]["amount"] = export["gameAttributes"]["minContract"]
            p["contract"]["exp"] = season + 1

            text = f">>> **Release** \n -- \n The {teamName} release **{playerName}** ({age} yo {ovr}/{pot}). \n --"
            try:
                channelId = int(shared_info.serversList[str(serverId)]["releasechannel"].replace("<#", "").replace(">", ""))
                channel = shared_info.bot.get_channel(channelId)
            except Exception:
                channel = message.channel

            if isinstance(channel, discord.TextChannel):
                await channel.send(text)
                if updateexport:
                    current_dir = os.getcwd()
                    path_to_file = os.path.join(current_dir, "exports", f"{serverId}-export.json")
                    await save_db(export, path_to_file)
            else:
                await message.channel.send("Release still executed.")

def find_pick_info(text, export):
    text = str.lower(text)
    pickData = {"round": None, "year": None, "tid": None}

    roundTerms = {
        1: ['first', '1st', 'round 1', ' 1 round', 'rd 1', ' 1 rd'],
        2: ['second', '2nd', 'round 2', ' 2 round', 'rd 2', ' 2 rd'],
        3: ['third', '3rd', 'round 3', ' 3 round', 'rd 3', ' 3 rd'],
        4: ['fourth', '4th', 'round 4', ' 4 round', 'rd 4', ' 4 rd'],
        5: ['fifth', '5th', 'round 5', ' 5 round', 'rd 5', ' 5 rd'],
        6: ['sixth', '6th', 'round 6', ' 6 round', 'rd 6', ' 6 rd'],
        7: ['seventh', '7th', 'round 7', ' 7 round', 'rd 7', ' 7 rd'],
        8: ['eighth', '8th', 'round 8', ' 8 round', 'rd 8', ' 8 rd'],
        9: ['ninth', '9th', 'round 9', ' 9 round', 'rd 9', ' 9 rd']
    }

    rounds = export['gameAttributes'].get('numDraftRounds', 2)
    if rounds > 9:
        for i in range(10, rounds):
            roundTerms[i] = [str(i), f'round {i}', f'{i} round', f'rd {i}', f'{i} rd']

    # Runde erkennen
    for roundNum, roundTexts in roundTerms.items():
        for txt in roundTexts:
            if txt in text:
                pickData['round'] = roundNum

    # Jahr erkennen
    for i in range(0, 3000):
        if str(i) in text:
            pickData['year'] = i

    # Team erkennen
    teams = export['teams']
    if "(" in text and ")" in text:
        text_b = text.split("(")[1].split(")")[0]
        for t in teams:
            if t['abbrev'].lower() == text_b.lower():
                pickData['tid'] = t['tid']

    if pickData["tid"] is None:
        for t in teams:
            if (
                t['abbrev'].lower() in text
                or t['region'].lower() in text
                or t['name'].lower() in text.replace('round', '').replace('pick', '')
            ):
                pickData['tid'] = t['tid']

    return pickData

