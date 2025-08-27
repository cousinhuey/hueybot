import decimal
import copy
import basics

def pstats(player, season, playoffs=False, qualifiers=False, tids="All"):
    if 'stats' not in player:
        return None

    stats = player['stats']

    # Safely calculate rebounds
    for s in stats:
        orb = s.get('orb', 0) or 0
        drb = s.get('drb', 0) or 0
        s['reb'] = orb + drb

    perGame = ['pts', 'reb', 'drb', 'orb', 'ast', 'stl', 'blk', 'tov', 'min', 'pm']
    totalStats = ['gp', 'gs','ows', 'dws', 'ortg', 'drtg', 'pm100', 'onOff100',
                  'vorp', 'obpm', 'dbpm', 'ewa', 'per', 'usgp', 'dd', 'td', 'qd', 'fxf']
    percents = {
        "fg": ['fg', 'fga'],
        "tp": ['tp', 'tpa'],
        "ft": ['ft', 'fta'],
        "at-rim": ['fgAtRim', 'fgaAtRim'],
        "low-post": ['fgLowPost', 'fgaLowPost'],
        "mid-range": ['fgMidRange', 'fgaMidRange']
    }

    statsDict = {}

    # Handle career stats
    if season == 'career':
        seasonsPlayed = list({s.get('season') for s in stats if s.get('gp',0) > 0 and (tids=="All" or s.get('tid')==tids)})
        season = seasonsPlayed
    else:
        season = [season]

    # Per-game stats
    for stat in perGame:
        total = 0
        totalGames = 0
        for s in stats:
            if s.get('season') in season and s.get('playoffs', False) == playoffs and (tids=="All" or s.get('tid')==tids):
                total += s.get(stat, 0) or 0
                totalGames += s.get('gp', 0)
        statsDict[stat] = round(decimal.Decimal(total)/totalGames,1) if totalGames else 0

    # Total stats
    for stat in totalStats:
        total = 0
        numGames = 0
        for s in stats:
            if s.get('season') in season and s.get('playoffs', False) == playoffs and (tids=="All" or s.get('tid')==tids):
                statVal = s.get(stat, 0) or 0
                if stat in ['per','obpm','dbpm','pm100','onOff100','usgp','ortg','drtg']:
                    statVal *= s.get('gp',0)
                total += statVal
                numGames += s.get('gp',0)
        if stat in ['per','obpm','dbpm','pm100','onOff100','usgp','ortg','drtg']:
            total = total/numGames if numGames else 0
        statsDict[stat] = round(decimal.Decimal(total),1)

    # Percent stats
    for stat,(madeKey,attKey) in percents.items():
        totalMade = totalAtt = 0
        for s in stats:
            if s.get('season') in season and s.get('playoffs', False) == playoffs and (tids=="All" or s.get('tid')==tids):
                totalMade += s.get(madeKey,0) or 0
                totalAtt += s.get(attKey,0) or 0
        statsDict[stat] = round(decimal.Decimal(totalMade)/totalAtt*100,1) if totalAtt else 0
        if totalAtt < 45 and qualifiers:
            statsDict[stat] = 0

    # eFG% and TS%
    totalnum = totaldenom = ts1 = ts2 = 0
    for s in stats:
        if s.get('season') in season and s.get('playoffs', False) == playoffs and (tids=="All" or s.get('tid')==tids):
            fg = s.get('fg',0) or 0
            tp = s.get('tp',0) or 0
            fga = s.get('fga',0) or 0
            pts = s.get('pts',0) or 0
            fta = s.get('fta',0) or 0
            totalnum += fg + 0.5*tp
            totaldenom += fga
            ts1 += pts
            ts2 += 2*(0.475*fta + fga)
    statsDict['eFG%'] = round(totalnum/totaldenom*100,1) if totaldenom else 0
    statsDict['TS%'] = round(ts1/ts2*100,1) if ts2 else 0

    # Teams
    statsDict['teams'] = list({s.get('tid') for s in stats if s.get('season') in season and s.get('playoffs',False)==playoffs and s.get('gp',0)>0 and (tids=="All" or s.get('tid')==tids)})

    return statsDict


def pinfo(p, season=None):
    # Height
    playerInches = divmod(p.get('hgt', 0), 12)
    playerHeight = f"{playerInches[0]}'{playerInches[1]}\""

    # Retired
    retiredYear = p.get('retiredYear')
    retired = retiredYear is not None

    # Draft info
    draft = p.get('draft', {})
    draftInfo = f"{draft.get('year','N/A')}: Round {draft.get('round','N/A')}, Pick {draft.get('pick','N/A')}"

    # Jersey
    try:
        jerseyNumber = p.get('stats', [])[-1].get('jerseyNumber', '00')
    except IndexError:
        jerseyNumber = '00'

    # Seasons played
    seasonsPlayed = sorted({s.get('season') for s in p.get('stats', []) if s.get('gp', 0) > 0})

    # Death info
    deathInfo = {"died": False}
    if 'diedYear' in p:
        deathInfo['yearDied'] = p['diedYear']
        deathInfo['ageDied'] = p['diedYear'] - p.get('born', {}).get('year', 0)
        deathInfo['died'] = True

    # Peak overall rating
    peakOvr = max((r.get('ovr', 0) for r in p.get('ratings', [])), default=0)

    # Contract
    contract = p.get('contract', {})
    contractAmount = contract.get('amount', 0) / 1000
    contractExp = contract.get('exp', "N/A")

    # Injury (safely)
    injuryInfo = p.get('injury', {"type": "Healthy", "gamesRemaining": 0})
    injuryList = [injuryInfo.get("type", "Healthy"), injuryInfo.get("gamesRemaining", 0)]

    # Team ID (safe)
    tid = p.get('tid', -1)

    # Player dict
    playerDict = {
        "name": f"{p.get('firstName','')} {p.get('lastName','')}",
        "born": p.get('born', {}).get('year'),
        "college": p.get('college'),
        "country": p.get('born', {}).get('loc'),
        "height": playerHeight,
        "weight": p.get('weight'),
        "contractAmount": contractAmount,
        "contractExp": contractExp,
        "moodTraits": ' '.join(p.get('moodTraits', [])),
        "ovr": p.get('ratings', [])[-1].get('ovr', 0) if p.get('ratings') else 0,
        "pid": p.get('pid'),
        "pot": p.get('ratings', [])[-1].get('pot', 0) if p.get('ratings') else 0,
        "position": p.get('ratings', [])[-1].get('pos', '') if p.get('ratings') else '',
        "skills": ' '.join(p.get('ratings', [])[-1].get('skills', [])) if p.get('ratings') else '',
        "retired": retired,
        "retiredYear": retiredYear,
        "draft": draftInfo,
        "draftYear": draft.get('year'),
        "draftPick": draft.get('pick'),
        "draftRound": draft.get('round'),
        "jerseyNumber": jerseyNumber,
        "seasonsPlayed": seasonsPlayed,
        "deathInfo": deathInfo,
        "ratings": p.get('ratings', [])[-1] if p.get('ratings') else {},
        "stats": None,
        "peakOvr": peakOvr,
        "injury": injuryList,
        "tid": tid
    }

    # Latest stats
    try:
        lastSeason = p.get('stats', [])[-1].get('season') if p.get('stats') else None
        playerDict['stats'] = pstats(p, lastSeason or season, False, True)
    except (IndexError, KeyError):
        playerDict['stats'] = None

    return playerDict


def tinfo(t, season=None):

    teamRecord = "nan"
    rw = -55
    if len(t['seasons']) > 0:
        rw = t['seasons'][-1]['playoffRoundsWon']
        teamRecord = f"{t['seasons'][-1]['won']}-{t['seasons'][-1]['lost']}"
        if t['seasons'][-1]['tied'] > 0:
            teamRecord += '-' + str(t['seasons'][-1]['tied'])
    teamColor = int(t['colors'][0].replace("#", ""),16)
    teamColor = int(hex(teamColor), 0)
    teamDict = {
        "tid": t['tid'],
        "name": t['region'] + ' ' + t['name'],
        "city": t['region'],
        "abbrev": t['abbrev'],
        "nickname": t['name'],
        "record": teamRecord,
        "color": teamColor,
        "roundsWon": rw,
        "pti": t['playThroughInjuries']
    }
    if season != None:
        for s in t['seasons']:
            if s['season'] == season:

                teamDict['name'] = s['region'] + ' ' + s['name']
                teamDict['city'] = s['region']
                teamDict['abbrev'] = s['abbrev']
                teamDict['nickName'] = s['name']
                seasonColor = int(s['colors'][0].replace("#", ""),16)
                seasonColor = int(hex(seasonColor), 0)
                teamDict['color'] = seasonColor
                teamRecord = f"{s['won']}-{s['lost']}"
                if s['tied'] > 0:
                    teamRecord += '-' + str(s['tied'])
                teamDict['record'] = teamRecord
                teamDict['roundsWon'] = s['playoffRoundsWon']

    return teamDict

def tgeneric(tid, p=None):

    if tid == -1:
        name = 'Free Agent'
    if tid == -3:
        name = 'Retired'
    if tid == -2:
        if p != None:
            name = f"{p['draftYear']} Draft Prospect"
        else:
            name = "Draft Prospect"
    return {
        "name": name,
        "record": '',
        "color": 0x000000,
        "roundsWon": -1
    }

def playoff_result(roundsWon, playoffSettings, season, omitMissed=False):

    result = 'missed playoffs'
    if roundsWon > -1:
        result = f'made round {roundsWon+1}'
    #print(playoffSettings)
    if len(playoffSettings) == 0:
        totalRounds = 0
    elif isinstance(playoffSettings[0], int):
        totalRounds = len(playoffSettings)
    else:
        for p in playoffSettings:

            if p['start'] == None:
                p['start'] = 0
            if p['start'] <= season:
                totalRounds = len(p['value'])
    if roundsWon == totalRounds:
        result = '**won championship**'
    if roundsWon == totalRounds-1:
        result = 'made finals'
    if roundsWon == totalRounds-2:
        result = 'made semifinals'
    if omitMissed:
        if result == 'missed playoffs':
            result = ''
    return result

def trade_penalty(teamId, serverExport):
    tradePenalty = 0
    events = serverExport['events']
    season = serverExport['gameAttributes']['season']
    players = serverExport['players']
    if 'thp' in players[-1]['ratings'][-1]:
        multiplier = 0.35
    else:
        multiplier = 1
    for e_i in range(len(events)-1, -1, -1):
        e = events[e_i]
        tradeTeam = -2
        if e['type'] == "trade" and e['season'] > (season - 3):
            tids = e['tids']
            if tids[0] == teamId:
                tradeTeam = 1
            if tids[1] == teamId:
                tradeTeam = 0
            if tradeTeam > -1:
                team = e['teams'][tradeTeam]
                assets = team['assets']
                for a in assets:
                    if 'pid' in a:
                        ratingIndex = a['ratingsIndex']
                        tradePid = a['pid']
                        for p in players:
                            if p['pid'] == tradePid:
                                try: tradeOvr = p['ratings'][ratingIndex]['ovr']
                                except IndexError: tradeOvr = 45
                                tradeAge = e['season'] - p['born']['year']
                                if tradeOvr > 54:
                                    tradePenalty += ((tradeOvr - 55)*0.15)*multiplier
                                seasonsLoyal = 0
                                if tradeOvr > 64 or tradeAge > 30:
                                    stats = p['stats']
                                    for s in stats:
                                        if s['tid'] == teamId:
                                            seasonsLoyal += 1
                                    tradePenalty += ((seasonsLoyal^2)/25)*multiplier
        if e['season'] <= (season - 3):
            break
    tradePenalty = round(tradePenalty, 1)
    tradePenalty = tradePenalty / 10
    if 'thp' in players[-1]['ratings'][-1]:
        tradePenalty = tradePenalty / 2
    if tradePenalty > 1:
        tradePenalty = 1
    return tradePenalty

import math
def team_rating(input, playoffs):
    if len(input) < 10:
        for i in range(10-len(input)):
            input.append(0)
    input.sort(reverse=True)
    if playoffs == True:
        a = 0.6388
        b = -0.2245
        k = 157.43
    else:
        a = 0.3334
        b = -0.1609
        k = 102.98
    ratings = input
    teamRatingSpread = -k + a * math.exp(b * 0) * ratings[0] + a * math.exp(b * 1) * ratings[1] + a * math.exp(b * 2) * ratings[2] + a * math.exp(b * 3) * ratings[3] + a * math.exp(b * 4) * ratings[4] + a * math.exp(b * 5) * ratings[5] + a * math.exp(b * 6) * ratings[6] + a * math.exp(b * 7) * ratings[7] + a * math.exp(b * 8) * ratings[8] + a * math.exp(b * 9) * ratings[9]
    teamRating = (teamRatingSpread * 50) / 15 + 50
    if playoffs == True:
        teamRating -= 40
    teamRating = round(teamRating)
    return(str(teamRating))

def game_info(game, export, message):
    players = export['players']
    teams = export['teams']

    #return should have the score line, the box scores for both teams, the top performers (top one always from winner, 2 and 3 indifferent), quarter by quarter, and records of each team at the time of game

    gameInfo = {
        "boxScore": []
    }

    #create the two score lines
    scoreLineAbbrev = ""
    scoreLineFull = ""
    homeTeam = ""
    awayTeam = ""
    for t in teams:
        if t['tid'] == game['teams'][0]['tid']:
            homeAbbrev = t['abbrev']
            homeTeam = t['name']
            teamLineAbbrev = f"{t['abbrev']} {game['teams'][0]['pts']}"
            teamLineFull = f"{basics.team_mention(message, (t['region'] + ' ' + t['name']), t['abbrev'])} ({game['teams'][0]['won']}-{game['teams'][0]['lost']}) "
            fullScore = f"{game['teams'][0]['pts']}"
            if game['won']['tid'] == t['tid']:
                teamLineAbbrev = '**' + teamLineAbbrev + '**'
                fullScore = '**' + fullScore + '**'
            teamLineFull += fullScore + ', '
            teamLineAbbrev += ', '
            scoreLineAbbrev += teamLineAbbrev
            scoreLineFull += teamLineFull
    for t in teams:
        if t['tid'] == game['teams'][1]['tid']:
            roadAbbrev = t['abbrev']
            awayTeam = t['name']
            teamLineAbbrev = f"{t['abbrev']} {game['teams'][1]['pts']}"
            teamLineFull = f"{basics.team_mention(message, (t['region'] + ' ' + t['name']), t['abbrev'])} ({game['teams'][1]['won']}-{game['teams'][1]['lost']}) "
            fullScore = f"{game['teams'][1]['pts']}"
            if game['won']['tid'] == t['tid']:
                teamLineAbbrev = '**' + teamLineAbbrev + '**'
                fullScore = '**' + fullScore + '**'
            teamLineFull += fullScore
            scoreLineAbbrev += teamLineAbbrev
            scoreLineFull += teamLineFull
    gameInfo['fullScore'] = scoreLineFull
    gameInfo['abbrevScore'] = scoreLineAbbrev
    gameInfo['home'] = homeTeam
    gameInfo['away'] = awayTeam
    
    #create box score first, then pull top performers

    performances = []

    for gt in game['teams']:
        boxScore = []
        gamePlayers= gt['players']
        dnpPlayers = []
        if gt['tid'] == game['won']['tid']:
            gameInfo['winningRecord'] = f"{gt['won']}-{gt['lost']}"
        else:
            gameInfo['losingRecord'] = f"{gt['won']}-{gt['lost']}"
        for p in gamePlayers:
            #top performer append
            performance = p['pts'] + (p['drb'] + p['orb'])/2 + p['ast'] + p['blk'] + p['stl']
            statistics = [[p['pts'], 'pts'], [p['orb'] + p['drb'], 'reb'], [p['ast'], 'ast'], [p['blk'], 'blk'], [p['stl'], 'stl']]
            statLine = ""
            for s in statistics:
                if s[0] > 1:
                    statLine+= f"{s[0]} {s[1]}, "
            statLine = statLine[:-2]
            if gt['tid'] == game['won']['tid']:
                won = True
            else:
                won = False
            performances.append([p['pos'], p['name'], performance, statLine, won, gt['tid']])


            plusMinus = p['pm']
            if p['pm'] > 0:
                plusMinus = '+' + str(plusMinus)
            if p['min'] == 0:
                if p['injury']['gamesRemaining'] > 0:
                    playerLine = f"#{p['jerseyNumber']} {p['pos']} **{p['name']}** | DNP - {p['injury']['type']}"
                    dnpPlayers.append(playerLine)
                else:
                    playerLine = f"#{p['jerseyNumber']} {p['pos']} **{p['name']}** | DNP - Coach's Decision"
                    dnpPlayers.append(playerLine)
            else:
                playerLine = f"#{p['jerseyNumber']} {p['pos']} **{p['name']}** | ``{round(p['min'], 1)} MP, {p['pts']} PTS, {p['orb']+p['drb']} REB, {p['ast']} AST, {p['blk']} BLK, {p['stl']} STL, {p['tov']} TOV, {p['fg']}-{p['fga']} FG, {p['tp']}-{p['tpa']} 3P, {p['ft']}-{p['fta']} FT, {plusMinus} +/-``"
                boxScore.append(playerLine)
        boxScore += dnpPlayers
        gameInfo['boxScore'].append(boxScore)

    #top performances
    performances.sort(key=lambda p: p[2], reverse=True)
    bestWinning = None
    bestLosing = None
    thirdBest = None

    for p in performances:
        if p[4]:
            if bestWinning == None:
                bestWinning = p
    for p in performances:
        if p[4] == False:
            if bestLosing == None:
                bestLosing = p
    for p in performances:
        if p != bestWinning and p != bestLosing and thirdBest == None:
            thirdBest = p
    
    topPerformances = [bestWinning, bestLosing, thirdBest]
    
    newPerformances = []
    for t in topPerformances:
        for te in teams:
            if te['tid'] == t[5]:
                abbrev = te['abbrev']
        t = f"{t[0]} **{t[1]}** ({abbrev}) - {t[3]}"

        newPerformances.append(t)


    gameInfo['topPerformances'] = newPerformances

    #quarter by quarter
    topLine = roadAbbrev + ' | ' + ' | '.join(map(str, game['teams'][1]['ptsQtrs'])) + ' | **' + str(game['teams'][1]['pts']) + '**'
    bottomLine = homeAbbrev + ' | ' + ' | '.join(map(str, game['teams'][0]['ptsQtrs'])) + ' | **' + str(game['teams'][0]['pts']) + '**'

    gameInfo['quarters'] = topLine + '\n' + bottomLine

    return gameInfo




            
    

    





            


