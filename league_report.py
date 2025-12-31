#!/usr/bin/env python3
"""
Fantasy Football League-Wide Schedule Analysis Report

Generates a comprehensive analysis for all team managers in the league.
"""

import json
import random
from collections import defaultdict
from typing import Dict, List, Tuple


def load_data(filepath: str) -> dict:
    """Load league data from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def extract_weekly_scores(data: dict) -> Dict[str, List[float]]:
    """Extract each team's weekly scores regardless of opponent."""
    teams = {t['name'] for t in data['teams']}
    weekly_scores = {team: [0.0] * len(data['weeks']) for team in teams}

    for week_data in data['weeks']:
        week_idx = week_data['week'] - 1
        for matchup in week_data['matchups']:
            weekly_scores[matchup['team1']][week_idx] = matchup['score1']
            weekly_scores[matchup['team2']][week_idx] = matchup['score2']

    return weekly_scores


def get_actual_schedule(data: dict) -> List[List[Tuple[str, str]]]:
    """Extract the actual schedule that was played."""
    schedule = []
    for week_data in data['weeks']:
        week_matchups = []
        for matchup in week_data['matchups']:
            week_matchups.append((matchup['team1'], matchup['team2']))
        schedule.append(week_matchups)
    return schedule


def calculate_standings(weekly_scores: Dict[str, List[float]],
                       schedule: List[List[Tuple[str, str]]]) -> List[Tuple[str, int, int, float]]:
    """Calculate standings given weekly scores and a schedule."""
    records = {team: {'wins': 0, 'losses': 0, 'ties': 0, 'points': sum(scores)}
               for team, scores in weekly_scores.items()}

    for week_idx, week_matchups in enumerate(schedule):
        for team1, team2 in week_matchups:
            score1 = weekly_scores[team1][week_idx]
            score2 = weekly_scores[team2][week_idx]

            if score1 > score2:
                records[team1]['wins'] += 1
                records[team2]['losses'] += 1
            elif score2 > score1:
                records[team2]['wins'] += 1
                records[team1]['losses'] += 1
            else:
                records[team1]['ties'] += 1
                records[team2]['ties'] += 1

    standings = [(team, r['wins'], r['losses'], r['points'])
                 for team, r in records.items()]
    standings.sort(key=lambda x: (x[1], x[3]), reverse=True)

    return standings


def get_playoff_teams(standings: List[Tuple[str, int, int, float]],
                      num_playoff_teams: int) -> set:
    """Get the set of teams that make playoffs."""
    return {standings[i][0] for i in range(min(num_playoff_teams, len(standings)))}


def generate_round_robin_week(teams: List[str], rng: random.Random) -> List[Tuple[str, str]]:
    """Generate a random valid round-robin matchup for a single week."""
    shuffled = teams.copy()
    rng.shuffle(shuffled)
    matchups = []
    for i in range(0, len(shuffled), 2):
        matchups.append((shuffled[i], shuffled[i+1]))
    return matchups


def generate_random_schedule(teams: List[str], num_weeks: int,
                            rng: random.Random) -> List[List[Tuple[str, str]]]:
    """Generate a random valid schedule for the season."""
    schedule = []
    for _ in range(num_weeks):
        week = generate_round_robin_week(teams, rng)
        schedule.append(week)
    return schedule


def calculate_expected_wins(weekly_scores: Dict[str, List[float]]) -> Dict[str, float]:
    """Calculate expected wins based on all-play scoring."""
    teams = list(weekly_scores.keys())
    num_teams = len(teams)
    num_weeks = len(weekly_scores[teams[0]])

    expected_wins = {team: 0.0 for team in teams}

    for week_idx in range(num_weeks):
        week_scores = [(team, weekly_scores[team][week_idx]) for team in teams]
        week_scores.sort(key=lambda x: x[1], reverse=True)

        for rank, (team, score) in enumerate(week_scores):
            teams_beaten = sum(1 for t, s in week_scores if s < score)
            teams_tied = sum(1 for t, s in week_scores if s == score) - 1
            win_rate = (teams_beaten + 0.5 * teams_tied) / (num_teams - 1)
            expected_wins[team] += win_rate

    return expected_wins


def calculate_all_play_record(weekly_scores: Dict[str, List[float]]) -> Dict[str, Tuple[int, int]]:
    """Calculate all-play record (if you played everyone every week)."""
    teams = list(weekly_scores.keys())
    num_weeks = len(weekly_scores[teams[0]])

    all_play = {team: {'wins': 0, 'losses': 0} for team in teams}

    for week_idx in range(num_weeks):
        week_scores = {team: weekly_scores[team][week_idx] for team in teams}

        for team in teams:
            my_score = week_scores[team]
            for opp in teams:
                if opp != team:
                    if my_score > week_scores[opp]:
                        all_play[team]['wins'] += 1
                    elif my_score < week_scores[opp]:
                        all_play[team]['losses'] += 1

    return {team: (r['wins'], r['losses']) for team, r in all_play.items()}


def run_monte_carlo_analysis(data: dict, num_simulations: int = 100000) -> dict:
    """Run Monte Carlo simulation of random schedules."""
    print(f"Running Monte Carlo analysis with {num_simulations:,} simulations...")

    weekly_scores = extract_weekly_scores(data)
    teams = list(weekly_scores.keys())
    num_weeks = len(data['weeks'])
    num_playoff_teams = data['league_info']['playoff_teams']

    playoff_counts = defaultdict(int)
    placement_counts = defaultdict(lambda: defaultdict(int))
    total_wins = defaultdict(int)
    championship_counts = defaultdict(int)  # 1st place finishes

    rng = random.Random(42)

    for sim in range(num_simulations):
        if sim % 20000 == 0 and sim > 0:
            print(f"  Completed {sim:,} simulations...")

        schedule = generate_random_schedule(teams, num_weeks, rng)
        standings = calculate_standings(weekly_scores, schedule)

        playoff_teams = get_playoff_teams(standings, num_playoff_teams)
        for team in playoff_teams:
            playoff_counts[team] += 1

        for place, (team, wins, losses, points) in enumerate(standings, 1):
            placement_counts[team][place] += 1
            total_wins[team] += wins
            if place == 1:
                championship_counts[team] += 1

    print(f"  Completed all {num_simulations:,} simulations!")

    return {
        'playoff_counts': dict(playoff_counts),
        'placement_counts': {t: dict(p) for t, p in placement_counts.items()},
        'total_wins': dict(total_wins),
        'championship_counts': dict(championship_counts),
        'num_simulations': num_simulations
    }


def analyze_actual_results(data: dict) -> dict:
    """Analyze the actual season results."""
    weekly_scores = extract_weekly_scores(data)
    actual_schedule = get_actual_schedule(data)
    num_playoff_teams = data['league_info']['playoff_teams']

    standings = calculate_standings(weekly_scores, actual_schedule)
    playoff_teams = get_playoff_teams(standings, num_playoff_teams)
    expected_wins = calculate_expected_wins(weekly_scores)
    all_play = calculate_all_play_record(weekly_scores)

    return {
        'standings': standings,
        'playoff_teams': playoff_teams,
        'expected_wins': expected_wins,
        'all_play': all_play,
        'weekly_scores': weekly_scores
    }


def get_weekly_rankings(weekly_scores: Dict[str, List[float]]) -> Dict[str, List[int]]:
    """Get each team's rank for each week."""
    teams = list(weekly_scores.keys())
    num_weeks = len(weekly_scores[teams[0]])

    rankings = {team: [] for team in teams}

    for week_idx in range(num_weeks):
        week_scores = [(team, weekly_scores[team][week_idx]) for team in teams]
        week_scores.sort(key=lambda x: x[1], reverse=True)

        for rank, (team, score) in enumerate(week_scores, 1):
            rankings[team].append(rank)

    return rankings


def ordinal(n: int) -> str:
    """Return ordinal string for a number."""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


def print_league_report(data: dict, actual: dict, simulation: dict):
    """Print comprehensive league-wide report."""
    num_sims = simulation['num_simulations']
    num_playoff_teams = data['league_info']['playoff_teams']
    teams = [t['name'] for t in data['teams']]
    weekly_scores = actual['weekly_scores']
    weekly_rankings = get_weekly_rankings(weekly_scores)

    print("\n" + "="*100)
    print("SHELDON LAKE FFB 25 - COMPLETE SEASON ANALYSIS")
    print("="*100)
    print(f"\nLeague: {data['league_info']['name']}")
    print(f"Season: {data['league_info']['season']}")
    print(f"Teams: {len(teams)} | Regular Season: 14 weeks | Playoff Teams: {num_playoff_teams}")
    print(f"Analysis based on {num_sims:,} schedule simulations")

    # ==========================================================================
    # FINAL STANDINGS
    # ==========================================================================
    print("\n" + "="*100)
    print("FINAL REGULAR SEASON STANDINGS")
    print("="*100)
    print(f"{'Rank':<6}{'Team':<25}{'Record':<10}{'Points For':<12}{'Avg/Week':<10}{'Playoffs'}")
    print("-"*100)
    for rank, (team, wins, losses, points) in enumerate(actual['standings'], 1):
        made_playoffs = "YES" if team in actual['playoff_teams'] else "-"
        avg = points / 14
        print(f"{rank:<6}{team:<25}{wins}-{losses:<8}{points:<12.2f}{avg:<10.2f}{made_playoffs}")

    # ==========================================================================
    # LUCK ANALYSIS - THE BIG PICTURE
    # ==========================================================================
    print("\n" + "="*100)
    print("LUCK FACTOR ANALYSIS")
    print("Who got lucky/unlucky with the schedule?")
    print("="*100)
    print(f"{'Rank':<6}{'Team':<25}{'Actual':<8}{'Expected':<10}{'Luck':<10}{'Verdict'}")
    print("-"*100)

    luck_data = []
    for team, wins, losses, points in actual['standings']:
        expected = actual['expected_wins'][team]
        luck = wins - expected
        luck_data.append((team, wins, expected, luck))

    luck_data.sort(key=lambda x: x[3], reverse=True)

    for rank, (team, wins, expected, luck) in enumerate(luck_data, 1):
        if luck > 1.5:
            verdict = "VERY LUCKY"
        elif luck > 0.5:
            verdict = "Lucky"
        elif luck < -1.5:
            verdict = "VERY UNLUCKY"
        elif luck < -0.5:
            verdict = "Unlucky"
        else:
            verdict = "Fair"
        print(f"{rank:<6}{team:<25}{wins:<8}{expected:<10.2f}{luck:+6.2f}    {verdict}")

    # ==========================================================================
    # PLAYOFF PROBABILITY
    # ==========================================================================
    print("\n" + "="*100)
    print("PLAYOFF PROBABILITY ANALYSIS")
    print(f"What were the odds of making the top {num_playoff_teams}?")
    print("="*100)
    print(f"{'Team':<25}{'Probability':<12}{'Made It?':<12}{'Outcome'}")
    print("-"*100)

    playoff_probs = []
    for team in teams:
        count = simulation['playoff_counts'].get(team, 0)
        prob = count / num_sims * 100
        made_actual = team in actual['playoff_teams']
        playoff_probs.append((team, prob, made_actual))

    playoff_probs.sort(key=lambda x: x[1], reverse=True)

    for team, prob, made_actual in playoff_probs:
        made_str = "YES" if made_actual else "No"
        if made_actual and prob < 50:
            outcome = "OVERACHIEVED"
        elif not made_actual and prob > 50:
            outcome = "UNDERACHIEVED"
        elif made_actual and prob >= 80:
            outcome = "Expected"
        elif not made_actual and prob <= 20:
            outcome = "Expected"
        else:
            outcome = "Close Call"
        print(f"{team:<25}{prob:>6.1f}%      {made_str:<12}{outcome}")

    # ==========================================================================
    # POWER RANKINGS (By Points)
    # ==========================================================================
    print("\n" + "="*100)
    print("POWER RANKINGS (Total Points)")
    print("The 'true' strength of each team based on scoring")
    print("="*100)

    team_totals = [(team, sum(scores), sum(scores)/14) for team, scores in weekly_scores.items()]
    team_totals.sort(key=lambda x: x[1], reverse=True)

    print(f"{'Power':<7}{'Team':<25}{'Total Pts':<12}{'Avg/Week':<10}{'Actual':<10}{'Diff'}")
    print("-"*100)

    actual_ranks = {team: rank for rank, (team, w, l, p) in enumerate(actual['standings'], 1)}

    for power_rank, (team, total, avg) in enumerate(team_totals, 1):
        actual_rank = actual_ranks[team]
        diff = actual_rank - power_rank
        diff_str = f"{diff:+d}" if diff != 0 else "="
        print(f"{power_rank:<7}{team:<25}{total:<12.2f}{avg:<10.2f}{actual_rank:<10}{diff_str}")

    # ==========================================================================
    # ALL-PLAY RECORDS
    # ==========================================================================
    print("\n" + "="*100)
    print("ALL-PLAY RECORDS")
    print("Record if you played EVERY team EVERY week")
    print("="*100)

    all_play_data = [(team, w, l, w/(w+l)*100) for team, (w, l) in actual['all_play'].items()]
    all_play_data.sort(key=lambda x: x[3], reverse=True)

    print(f"{'Rank':<6}{'Team':<25}{'All-Play Record':<18}{'Win %':<10}{'H2H Record'}")
    print("-"*100)

    for rank, (team, ap_wins, ap_losses, win_pct) in enumerate(all_play_data, 1):
        # Find actual record
        for t, w, l, p in actual['standings']:
            if t == team:
                actual_rec = f"{w}-{l}"
                break
        print(f"{rank:<6}{team:<25}{ap_wins}-{ap_losses:<15}{win_pct:<10.1f}{actual_rec}")

    # ==========================================================================
    # INDIVIDUAL TEAM REPORTS
    # ==========================================================================
    print("\n" + "="*100)
    print("INDIVIDUAL TEAM ANALYSIS")
    print("="*100)

    # Sort teams by actual standing
    for rank, (team, wins, losses, points) in enumerate(actual['standings'], 1):
        print(f"\n{'─'*100}")
        print(f"#{rank} {team.upper()}")
        print(f"{'─'*100}")

        # Basic stats
        expected = actual['expected_wins'][team]
        luck = wins - expected
        playoff_prob = simulation['playoff_counts'].get(team, 0) / num_sims * 100
        made_playoffs = "YES" if team in actual['playoff_teams'] else "NO"
        avg_sim_wins = simulation['total_wins'].get(team, 0) / num_sims
        champ_prob = simulation['championship_counts'].get(team, 0) / num_sims * 100
        ap_wins, ap_losses = actual['all_play'][team]

        print(f"  Record: {wins}-{losses} | Points: {points:.2f} | Avg/Week: {points/14:.2f}")
        print(f"  Made Playoffs: {made_playoffs}")
        print(f"  Playoff Probability: {playoff_prob:.1f}%")
        print(f"  1st Place Probability: {champ_prob:.1f}%")
        print(f"  Expected Wins: {expected:.2f} | Luck Factor: {luck:+.2f}")
        print(f"  All-Play Record: {ap_wins}-{ap_losses} ({ap_wins/(ap_wins+ap_losses)*100:.1f}%)")

        # Placement distribution
        placements = simulation['placement_counts'].get(team, {})
        print(f"\n  Placement Distribution (across {num_sims:,} simulations):")

        # Show as a histogram
        for place in range(1, len(teams) + 1):
            count = placements.get(place, 0)
            pct = count / num_sims * 100
            bar_len = int(pct / 2)
            bar = '█' * bar_len
            marker = " ◄── ACTUAL" if place == rank else ""
            print(f"    {ordinal(place):>4}: {pct:>5.1f}% {bar}{marker}")

        # Weekly performance
        team_scores = weekly_scores[team]
        team_ranks = weekly_rankings[team]
        best_week = max(team_scores)
        worst_week = min(team_scores)
        best_week_num = team_scores.index(best_week) + 1
        worst_week_num = team_scores.index(worst_week) + 1

        top3_weeks = sum(1 for r in team_ranks if r <= 3)
        bottom3_weeks = sum(1 for r in team_ranks if r >= 10)

        print(f"\n  Weekly Performance:")
        print(f"    Best Week: {best_week:.2f} (Week {best_week_num})")
        print(f"    Worst Week: {worst_week:.2f} (Week {worst_week_num})")
        print(f"    Top 3 Finishes: {top3_weeks}/14 weeks")
        print(f"    Bottom 3 Finishes: {bottom3_weeks}/14 weeks")

    # ==========================================================================
    # SUMMARY INSIGHTS
    # ==========================================================================
    print("\n" + "="*100)
    print("KEY INSIGHTS & TAKEAWAYS")
    print("="*100)

    # Find extremes
    luckiest = max(luck_data, key=lambda x: x[3])
    unluckiest = min(luck_data, key=lambda x: x[3])
    highest_scorer = team_totals[0]
    lowest_scorer = team_totals[-1]

    # Find biggest over/under achievers
    over_under = []
    for team, prob, made in playoff_probs:
        if made and prob < 50:
            over_under.append((team, prob, "overachieved", 50 - prob))
        elif not made and prob > 50:
            over_under.append((team, prob, "underachieved", prob - 50))

    print(f"""
    LUCK OF THE DRAW:
    • Luckiest Team: {luckiest[0]} ({luckiest[3]:+.2f} wins above expected)
    • Unluckiest Team: {unluckiest[0]} ({unluckiest[3]:+.2f} wins vs expected)

    SCORING:
    • Highest Scorer: {highest_scorer[0]} ({highest_scorer[1]:.2f} total, {highest_scorer[2]:.2f}/week)
    • Lowest Scorer: {lowest_scorer[0]} ({lowest_scorer[1]:.2f} total, {lowest_scorer[2]:.2f}/week)

    PLAYOFF SURPRISES:""")

    if over_under:
        for team, prob, status, margin in sorted(over_under, key=lambda x: x[3], reverse=True):
            if status == "overachieved":
                print(f"    • {team} MADE playoffs with only {prob:.1f}% probability!")
            else:
                print(f"    • {team} MISSED playoffs despite {prob:.1f}% probability!")
    else:
        print("    • No major surprises - playoff results matched expectations")

    print(f"""
    CONSISTENCY LEADERS (All-Play Win %):
    • Most Consistent: {all_play_data[0][0]} ({all_play_data[0][3]:.1f}% all-play win rate)
    • Least Consistent: {all_play_data[-1][0]} ({all_play_data[-1][3]:.1f}% all-play win rate)
    """)

    print("="*100)
    print("END OF LEAGUE REPORT")
    print("="*100)


def main():
    """Main entry point."""
    data = load_data('league_data.json')
    actual = analyze_actual_results(data)
    simulation = run_monte_carlo_analysis(data, num_simulations=100000)
    print_league_report(data, actual, simulation)


if __name__ == '__main__':
    main()
