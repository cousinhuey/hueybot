import discord
import asyncio
import basics
import shared_info
import os
import settings
from typing import List, Dict, Any, Optional
from shared_info import serversList


drafts: Dict[str, Dict[str, Any]] = {}
draftPaused: Dict[str, bool] = {}
draftChannels: Dict[str, int] = {}
draftTasks: Dict[str, asyncio.Task] = {}
draftEvents: Dict[str, asyncio.Event] = {}


def _teams_by_tid(server_export: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    return {t["tid"]: t for t in server_export.get("teams", []) if isinstance(t, dict) and "tid" in t}


def _players_by_pid(server_export: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    return {p["pid"]: p for p in server_export.get("players", []) if isinstance(p, dict) and "pid" in p}


def _draft_picks(server_export: Dict[str, Any]) -> List[Dict[str, Any]]:
    return server_export.get("draftPicks", [])


def _current_season(server_export: Dict[str, Any]) -> int:
    return int(server_export.get("gameAttributes", {}).get("season", 1))


def _picks_for_season(server_export: Dict[str, Any], season: int) -> List[Dict[str, Any]]:
    return [p for p in _draft_picks(server_export) if p.get("season") == season]


def _picks_per_round(server_export: Dict[str, Any]) -> int:
    return max(1, len(server_export.get("teams", [])))


def _num_rounds(server_export: Dict[str, Any]) -> int:
    return int(server_export.get("gameAttributes", {}).get("numDraftRounds", 2))


def _build_order(server_export: Dict[str, Any]) -> List[Optional[int]]:
    season = _current_season(server_export)
    picks = _picks_for_season(server_export, season)
    picks_per_round = _picks_per_round(server_export)
    rounds = _num_rounds(server_export)
    if picks:
        picks_sorted = sorted(picks, key=lambda x: (x.get("round", 1), x.get("pick", 1)))
        order: List[Optional[int]] = []
        for r in range(1, rounds + 1):
            round_picks = [p for p in picks_sorted if p.get("round") == r]
            tid_list = [None] * picks_per_round
            for p in round_picks:
                idx = p.get("pick", 1) - 1
                if 0 <= idx < picks_per_round:
                    tid_list[idx] = p.get("tid", p.get("ownerTid"))
            order.extend(tid_list)
        return order
    tids = [t.get("tid", i) for i, t in enumerate(server_export.get("teams", []))]
    order = []
    for _ in range(rounds):
        order.extend(tids)
    return order


def _pick_to_round_pick(idx_1_based: int, picks_per_round: int) -> (int, int):
    return (idx_1_based - 1) // picks_per_round + 1, (idx_1_based - 1) % picks_per_round + 1


def _available_prospects(server_export: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    return {p["pid"]: p for p in server_export.get("players", []) if p.get("draft", {}).get("year") == _current_season(server_export) and p.get("tid") == -2}


def _team_name_from_tid(server_export: Dict[str, Any], tid: Optional[int]) -> str:
    if tid is None:
        return "None"
    for t in server_export.get("teams", []):
        if t.get("tid") == tid:
            return f"{t.get('region', 'Team')} {t.get('name', str(tid))}".strip()
    return f"Team {tid}"


def _available_players_sorted(server_export: Dict[str, Any]) -> List[Dict[str, Any]]:
    players = list(_available_prospects(server_export).values())
    def ov(p): return p.get("ratings", [{}])[-1].get("ovr", 0)
    def po(p): return p.get("ratings", [{}])[-1].get("pot", 0)
    players.sort(key=lambda p: (-ov(p), -po(p), p.get("lastName", "")))
    return players


def _player_by_pid(server_export: Dict[str, Any], pid: int) -> Optional[Dict[str, Any]]:
    return next((p for p in server_export.get("players", []) if p.get("pid") == pid), None)


def _best_player_pid(server_export: Dict[str, Any]) -> Optional[int]:
    avail = _available_players_sorted(server_export)
    return avail[0]["pid"] if avail else None


def _player_name(p: Dict[str, Any]) -> str:
    return f'{p.get("firstName","")} {p.get("lastName","")}'.strip()


async def run_draft(message, pick, clockTime):
    guild_id = str(message.guild.id)
    if guild_id not in serversList:
        await message.channel.send("⚠️ No server configuration found for this guild.")
        return
    server_export = shared_info.serverExports.get(guild_id)
    if not server_export:
        await message.channel.send("⚠️ No export loaded for this server.")
        return
    draft_channel_id = serversList[guild_id].get("draftchannel")
    if not draft_channel_id:
        await message.channel.send("⚠️ No draft channel configured.")
        return
    raw_id = str(draft_channel_id)
    if raw_id.startswith("<#") and raw_id.endswith(">"):
        raw_id = raw_id[2:-1]
    draft_channel = message.guild.get_channel(int(raw_id))
    if not draft_channel:
        await message.channel.send("⚠️ Draft channel not found.")
        return
    order = _build_order(server_export)
    try:
        pick = int(pick)
    except Exception:
        pick = 1
    if pick < 1:
        pick = 1
    drafts[guild_id] = {
        "picks": [],
        "clockTime": int(clockTime),
        "currentPick": int(pick),
        "order": order,
        "picksPerRound": _picks_per_round(server_export),
        "numRounds": _num_rounds(server_export),
    }
    draftPaused[guild_id] = False
    draftChannels[guild_id] = draft_channel.id
    draftEvents[guild_id] = asyncio.Event()
    tid_on_clock = order[pick - 1] if 0 <= pick - 1 < len(order) else None
    r, p_in_r = _pick_to_round_pick(pick, _picks_per_round(server_export))
    serversList[guild_id].setdefault("draftStatus", {})
    serversList[guild_id]["draftStatus"].update({
        "draftRunning": True,
        "onTheClock": {"tid": tid_on_clock, "round": r, "pick": p_in_r} if tid_on_clock is not None else None
    })
    await basics.save_db(serversList)
    draftTasks[guild_id] = asyncio.create_task(draft_loop(guild_id, draft_channel))
    await message.channel.send(f"✅ Draft started at Pick {pick} with a {clockTime}s clock.")


async def draft_loop(guild_id: str, draft_channel: discord.TextChannel):
    try:
        while True:
            if draftPaused.get(guild_id):
                ev = draftEvents.get(guild_id)
                if ev:
                    await ev.wait()
                    ev.clear()

            draft_data = drafts.get(guild_id)
            if not draft_data:
                break

            # DraftChannel laden
            draft_channel_id = serversList[guild_id].get("draftchannel")
            if not draft_channel_id:
                break
            raw_id = str(draft_channel_id)
            if raw_id.startswith("<#") and raw_id.endswith(">"):
                raw_id = raw_id[2:-1]
            draft_channel = discord.utils.get(
                shared_info.bot.get_guild(int(guild_id)).channels, id=int(raw_id)
            )
            if not draft_channel:
                break

            currentPick = draft_data["currentPick"]
            server_settings = settings.get_settings(guild_id)
            order = draft_data.get("order", [])
            ppr = draft_data.get("picksPerRound", max(1, len(order) or 1))
            rnd, _ = _pick_to_round_pick(currentPick, ppr)

            # ClockTime bestimmen
            if "draftclock" in server_settings:
                draftclock = server_settings["draftclock"]
                if isinstance(draftclock, list):
                    clockTime = draftclock[rnd - 1] if rnd - 1 < len(draftclock) else 60
                else:
                    try:
                        clockTime = int(draftclock)
                    except Exception:
                        clockTime = draft_data.get("clockTime", 60)
            else:
                clockTime = draft_data.get("clockTime", 60)

            # Draft fertig?
            if currentPick < 1 or currentPick > len(order):
                await draft_channel.send("🏁 Draft is finished!")
                serversList[guild_id].setdefault("draftStatus", {})
                serversList[guild_id]["draftStatus"].update({
                    "draftRunning": False, "onTheClock": None
                })
                await basics.save_db(serversList)
                break

            server_export = shared_info.serverExports.get(guild_id)
            if not server_export:
                await draft_channel.send("⚠️ Export not loaded; aborting.")
                break

            tid_on_clock = order[currentPick - 1]
            rnd, pick_in_rnd = _pick_to_round_pick(currentPick, ppr)
            team_name = _team_name_from_tid(server_export, tid_on_clock)

            embed = discord.Embed(
                title=f"Draft Pick {currentPick} (Round {rnd}, Pick {pick_in_rnd})",
                description=f"**{team_name}** is on the clock for {clockTime} seconds."
            )
            await draft_channel.send(embed=embed)

            # Event-Handling
            event = draftEvents.get(guild_id)
            if event is None:
                draftEvents[guild_id] = asyncio.Event()
                event = draftEvents[guild_id]

            try:
                await asyncio.wait_for(event.wait(), timeout=clockTime)
                event.clear()
            except asyncio.TimeoutError:
                await _autopick_and_advance(guild_id)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"⚠️ Draft loop crashed: {e}")
        try:
            draft_channel = None
            draft_channel_id = serversList[guild_id].get("draftchannel")
            if draft_channel_id:
                draft_channel = discord.utils.get(
                    shared_info.bot.get_guild(int(guild_id)).channels,
                    id=int(str(draft_channel_id).strip("<#>"))
                )
            if draft_channel:
                await draft_channel.send(f"⚠️ Draft loop crashed: {e}")
        except Exception:
            pass


async def _autopick_and_advance(guild_id: str):
    draft_data = drafts.get(guild_id)
    if not draft_data:
        return

    server_export = shared_info.serverExports.get(guild_id)
    if not server_export:
        return

    # DraftChannel aus serversList laden
    draft_channel_id = serversList[guild_id].get("draftchannel")
    if not draft_channel_id:
        return

    raw_id = str(draft_channel_id)
    if raw_id.startswith("<#") and raw_id.endswith(">"):
        raw_id = raw_id[2:-1]
    draft_channel = discord.utils.get(
        shared_info.bot.get_guild(int(guild_id)).channels, id=int(raw_id)
    )
    if not draft_channel:
        return

    currentPick = draft_data.get("currentPick", 1)
    order = draft_data.get("order", [])

    if not (1 <= currentPick <= len(order)):
        await draft_channel.send("🏁 Draft is finished!")
        return

    tid_on_clock = order[currentPick - 1]

    # 🟢 Draft Board Check
    pid = None
    draft_boards = serversList[guild_id].get("draftBoards", {})
    board = draft_boards.get(str(tid_on_clock), [])
    for player_pid in board:
        player = _player_by_pid(server_export, player_pid)
        if player and player.get("tid") == -2:  # noch verfügbar
            pid = player_pid
            break

    # 🔄 Falls kein Spieler auf dem Board verfügbar → Best Available
    if pid is None:
        pid = _best_player_pid(server_export)

    if pid is None:
        await draft_channel.send("⚠️ No available prospects to pick.")
    else:
        await _select_player_internal(guild_id, draft_channel, tid_on_clock, pid)

    # Pick counter hochsetzen
    draft_data["currentPick"] = currentPick + 1

    # Nächstes Team bestimmen
    nxt_idx = currentPick
    next_tid = order[nxt_idx] if 0 <= nxt_idx < len(order) else None
    next_name = (
        _team_name_from_tid(server_export, next_tid)
        if next_tid is not None else "End of draft"
    )

    



async def select_player(guild_id: str, pid: int, message, draft_channel: discord.TextChannel):
    draft_data = drafts.get(guild_id)
    if not draft_data:
        await message.channel.send("⚠️ No active draft.")
        return

    server_export = shared_info.serverExports.get(guild_id)
    if not server_export:
        await message.channel.send("⚠️ Export not loaded.")
        return

    currentPick = draft_data.get("currentPick", 1)
    order = draft_data.get("order", [])
    if not (1 <= currentPick <= len(order)):
        await draft_channel.send("🏁 Draft is finished!")
        return

    tid_on_clock = order[currentPick - 1]
    player = _player_by_pid(server_export, int(pid))
    if not player:
        await draft_channel.send("⚠️ Player not found or not a prospect.")
        return

    # Auswahl nur im Draft-Channel posten
    await _select_player_internal(guild_id, draft_channel, tid_on_clock, int(pid))

    # Bestätigung NUR dort, wo der Command ausgeführt wurde
    await message.channel.send("✅ Pick recorded.")

    # Draftstatus aktualisieren
    draft_data["currentPick"] = currentPick + 1
    nxt_idx = currentPick
    next_tid = order[nxt_idx] if 0 <= nxt_idx < len(order) else None

    serversList[guild_id].setdefault("draftStatus", {})
    serversList[guild_id]["draftStatus"].update({
        "draftRunning": next_tid is not None,
        "onTheClock": {"tid": next_tid} if next_tid is not None else None
    })

    await basics.save_db(serversList)


async def _select_player_internal(
    guild_id: str, draft_channel: discord.TextChannel, tid_on_clock: int, player_pid: int
):
    draft_data = drafts.get(guild_id)
    if not draft_data:
        return

    server_export = shared_info.serverExports.get(guild_id)
    if not server_export:
        return

    player = next(
        (p for p in server_export.get("players", []) if p.get("pid") == int(player_pid)),
        None
    )
    if not player:
        await draft_channel.send("⚠️ Player not found.")
        return

    # Spieler dem Team zuordnen
    player["tid"] = tid_on_clock

    # Spieler aus DraftBoards entfernen
    for team_id, board in serversList[guild_id].get("draftBoards", {}).items():
        if player_pid in board:
            board.remove(player_pid)

    team_name = _team_name_from_tid(server_export, tid_on_clock)
    player_name = _player_name(player)

    # 🟢 aktuelle Picknummer + Rundendaten
    currentPick = draft_data.get("currentPick", 1)
    rnd, pick_in_rnd = _pick_to_round_pick(
        currentPick, draft_data.get("picksPerRound", 30)
    )

    # Draft-Embed ins DraftChannel
    embed = discord.Embed(
        title=f"Draft Selection - Round {rnd}, Pick {pick_in_rnd}",
        description=f"**{team_name}** selects **{player_name}**."
    )
    await draft_channel.send(embed=embed)

    # Pick speichern
    draft_data.setdefault("picks", []).append({
        "pick": currentPick,
        "tid": tid_on_clock,
        "pid": int(player_pid),
        "playerName": player_name,
    })

    # Pick-Zähler hochsetzen
    draft_data["currentPick"] = currentPick + 1

    # Nächstes Team bestimmen
    nxt_idx = currentPick
    order = draft_data.get("order", [])
    next_tid = order[nxt_idx] if 0 <= nxt_idx < len(order) else None
    next_name = (
        _team_name_from_tid(server_export, next_tid)
        if next_tid is not None else "End of draft"
    )

    serversList[guild_id].setdefault("draftStatus", {})
    serversList[guild_id]["draftStatus"].update({
        "draftRunning": next_tid is not None,
        "onTheClock": {"tid": next_tid} if next_tid is not None else None
    })

    # Draft-State speichern
    try:
        current_dir = basics.get_server_dir(guild_id)
        await basics.save_json(
            os.path.join(current_dir, "draft_state.json"),
            {
                "currentPick": draft_data["currentPick"],
                "order": draft_data.get("order", []),
                "channel": draftChannels.get(guild_id),
            }
        )
    except Exception:
        pass

    # Nächstes Team im DraftChannel ankündigen
    await draft_channel.send(f"➡️ Next up: {next_name}")


    draft_data.setdefault("picks", []).append({
        "pick": currentPick,
        "tid": tid_on_clock,
        "pid": int(player_pid),
        "playerName": player_name,
    })

    draft_data["currentPick"] = currentPick + 1
    nxt_idx = currentPick
    order = draft_data.get("order", [])
    next_tid = order[nxt_idx] if 0 <= nxt_idx < len(order) else None
    next_name = _team_name_from_tid(server_export, next_tid) if next_tid is not None else "End of draft"

    serversList[guild_id].setdefault("draftStatus", {})
    serversList[guild_id]["draftStatus"].update({
        "draftRunning": next_tid is not None,
        "onTheClock": {"tid": next_tid} if next_tid is not None else None
    })

    try:
        current_dir = basics.get_server_dir(guild_id)
        await basics.save_json(os.path.join(current_dir, "draft_state.json"), {
            "currentPick": draft_data["currentPick"],
            "order": draft_data.get("order", []),
            "channel": draftChannels.get(guild_id),
        })
    except Exception:
        pass

    await draft_channel.send(f"➡️ Next up: {next_name}")



def pause_draft(guild_id: str, pause: bool = True):
    draftPaused[guild_id] = pause


def resume_draft(guild_id: str):
    draftPaused[guild_id] = False
    ev = draftEvents.get(guild)
