#!/usr/bin/env python3
"""
Fantasy Football Schedule Permutation Analysis

Analyzes all possible schedule permutations to determine playoff probabilities
and luck factors for each team in the league.
"""

import json
import random
from collections import defaultdict
from itertools import combinations
from typing import Dict, List, Tuple
import math


def load_data(filepath: str) -> dict:
    """Load league data from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def extract_weekly_scores(data: dict) -> Dict[str, List[float]]:
    """
    Extract each team's weekly scores regardless of opponent.
    Returns: {team_name: [week1_score, week2_score, ...]}
    """
    teams = {t['name'] for t in data['teams']}
    weekly_scores = {team: [0.0] * len(data['weeks']) for team in teams}

    for week_data in data['weeks']:
        week_idx = week_data['week'] - 1  # 0-indexed
        for matchup in week_data['matchups']:
            weekly_scores[matchup['team1']][week_idx] = matchup['score1']
            weekly_scores[matchup['team2']][week_idx] = matchup['score2']

    return weekly_scores


def get_actual_schedule(data: dict) -> List[List[Tuple[str, str]]]:
    """
    Extract the actual schedule that was played.
    Returns: List of weeks, each containing list of (team1, team2) matchups
    """
    schedule = []
    for week_data in data['weeks']:
        week_matchups = []
        for matchup in week_data['matchups']:
            week_matchups.append((matchup['team1'], matchup['team2']))
        schedule.append(week_matchups)
    return schedule


def calculate_standings(weekly_scores: Dict[str, List[float]],
                       schedule: List[List[Tuple[str, str]]]) -> List[Tuple[str, int, int, float]]:
    """
    Calculate standings given weekly scores and a schedule.
    Returns: List of (team, wins, losses, total_points) sorted by wins then points
    """
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

    # Sort by wins (desc), then by total points (desc) as tiebreaker
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
    """
    Calculate expected wins for each team based on scoring.
    Expected wins = sum over all weeks of (teams beaten / (total teams - 1))
    """
    teams = list(weekly_scores.keys())
    num_teams = len(teams)
    num_weeks = len(weekly_scores[teams[0]])

    expected_wins = {team: 0.0 for team in teams}

    for week_idx in range(num_weeks):
        week_scores = [(team, weekly_scores[team][week_idx]) for team in teams]
        week_scores.sort(key=lambda x: x[1], reverse=True)

        for rank, (team, score) in enumerate(week_scores):
            # Count how many teams this team would have beaten
            teams_beaten = sum(1 for t, s in week_scores if s < score)
            teams_tied = sum(1 for t, s in week_scores if s == score) - 1

            # Expected win rate for this week
            win_rate = (teams_beaten + 0.5 * teams_tied) / (num_teams - 1)
            expected_wins[team] += win_rate

    return expected_wins


def run_monte_carlo_analysis(data: dict, num_simulations: int = 100000) -> dict:
    """
    Run Monte Carlo simulation of random schedules.
    """
    print(f"Running Monte Carlo analysis with {num_simulations:,} simulations...")

    weekly_scores = extract_weekly_scores(data)
    teams = list(weekly_scores.keys())
    num_weeks = len(data['weeks'])
    num_playoff_teams = data['league_info']['playoff_teams']
    my_team = data['league_info']['my_team']

    # Track results
    playoff_counts = defaultdict(int)
    placement_counts = defaultdict(lambda: defaultdict(int))
    total_wins = defaultdict(int)

    rng = random.Random(42)  # Seed for reproducibility

    for sim in range(num_simulations):
        if sim % 10000 == 0 and sim > 0:
            print(f"  Completed {sim:,} simulations...")

        # Generate random schedule
        schedule = generate_random_schedule(teams, num_weeks, rng)

        # Calculate standings
        standings = calculate_standings(weekly_scores, schedule)

        # Track playoff appearances
        playoff_teams = get_playoff_teams(standings, num_playoff_teams)
        for team in playoff_teams:
            playoff_counts[team] += 1

        # Track placements
        for place, (team, wins, losses, points) in enumerate(standings, 1):
            placement_counts[team][place] += 1
            total_wins[team] += wins

    print(f"  Completed all {num_simulations:,} simulations!")

    return {
        'playoff_counts': dict(playoff_counts),
        'placement_counts': {t: dict(p) for t, p in placement_counts.items()},
        'total_wins': dict(total_wins),
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

    return {
        'standings': standings,
        'playoff_teams': playoff_teams,
        'expected_wins': expected_wins,
        'weekly_scores': weekly_scores
    }


def print_report(data: dict, actual: dict, simulation: dict):
    """Print the analysis report."""
    my_team = data['league_info']['my_team']
    num_sims = simulation['num_simulations']
    num_playoff_teams = data['league_info']['playoff_teams']
    teams = [t['name'] for t in data['teams']]

    print("\n" + "="*80)
    print("FANTASY FOOTBALL SCHEDULE ANALYSIS REPORT")
    print("="*80)
    print(f"\nLeague: {data['league_info']['name']}")
    print(f"Season: {data['league_info']['season']}")
    print(f"Your Team: {my_team}")
    print(f"Simulations Run: {num_sims:,}")

    # Actual Standings
    print("\n" + "-"*80)
    print("ACTUAL REGULAR SEASON STANDINGS")
    print("-"*80)
    print(f"{'Rank':<6}{'Team':<25}{'Record':<12}{'Points For':<12}{'Made Playoffs'}")
    print("-"*80)
    for rank, (team, wins, losses, points) in enumerate(actual['standings'], 1):
        made_playoffs = "YES" if team in actual['playoff_teams'] else "No"
        indicator = " <-- YOU" if team == my_team else ""
        print(f"{rank:<6}{team:<25}{wins}-{losses:<10}{points:<12.2f}{made_playoffs}{indicator}")

    # Expected Wins Analysis
    print("\n" + "-"*80)
    print("LUCK FACTOR ANALYSIS (Actual Wins vs Expected Wins)")
    print("-"*80)
    print(f"{'Team':<25}{'Actual':<10}{'Expected':<12}{'Luck':<10}{'Rating'}")
    print("-"*80)

    luck_data = []
    for team, wins, losses, points in actual['standings']:
        expected = actual['expected_wins'][team]
        luck = wins - expected
        luck_data.append((team, wins, expected, luck))

    # Sort by luck factor
    luck_data.sort(key=lambda x: x[3], reverse=True)

    for team, wins, expected, luck in luck_data:
        if luck > 1.5:
            rating = "VERY LUCKY"
        elif luck > 0.5:
            rating = "Lucky"
        elif luck < -1.5:
            rating = "VERY UNLUCKY"
        elif luck < -0.5:
            rating = "Unlucky"
        else:
            rating = "Neutral"
        indicator = " <-- YOU" if team == my_team else ""
        print(f"{team:<25}{wins:<10}{expected:<12.2f}{luck:+.2f}     {rating}{indicator}")

    # Playoff Probability
    print("\n" + "-"*80)
    print(f"PLAYOFF PROBABILITY (Top {num_playoff_teams} make playoffs)")
    print("-"*80)
    print(f"{'Team':<25}{'Probability':<15}{'Scenarios':<20}{'Actual'}")
    print("-"*80)

    playoff_probs = []
    for team in teams:
        count = simulation['playoff_counts'].get(team, 0)
        prob = count / num_sims * 100
        made_actual = "MADE IT" if team in actual['playoff_teams'] else "Missed"
        playoff_probs.append((team, prob, count, made_actual))

    playoff_probs.sort(key=lambda x: x[1], reverse=True)

    for team, prob, count, made_actual in playoff_probs:
        indicator = " <-- YOU" if team == my_team else ""
        print(f"{team:<25}{prob:>6.2f}%       {count:>12,}/{num_sims:<8}{made_actual}{indicator}")

    # My Team Analysis
    print("\n" + "-"*80)
    print(f"YOUR TEAM ANALYSIS: {my_team}")
    print("-"*80)

    # Find my team in standings
    my_actual_rank = None
    my_actual_wins = None
    for rank, (team, wins, losses, points) in enumerate(actual['standings'], 1):
        if team == my_team:
            my_actual_rank = rank
            my_actual_wins = wins
            break

    my_playoff_prob = simulation['playoff_counts'].get(my_team, 0) / num_sims * 100
    my_expected_wins = actual['expected_wins'][my_team]
    my_luck = my_actual_wins - my_expected_wins

    print(f"Actual Finish: {my_actual_rank}{'st' if my_actual_rank==1 else 'nd' if my_actual_rank==2 else 'rd' if my_actual_rank==3 else 'th'} place ({my_actual_wins} wins)")
    print(f"Made Playoffs: {'YES' if my_team in actual['playoff_teams'] else 'NO'}")
    print(f"Playoff Probability: {my_playoff_prob:.2f}%")
    print(f"Expected Wins: {my_expected_wins:.2f}")
    print(f"Luck Factor: {my_luck:+.2f} wins")

    # Placement distribution
    print("\nPlacement Distribution Across All Simulations:")
    placements = simulation['placement_counts'].get(my_team, {})
    for place in range(1, len(teams) + 1):
        count = placements.get(place, 0)
        pct = count / num_sims * 100
        bar = '#' * int(pct / 2)
        print(f"  {place:>2}{'st' if place==1 else 'nd' if place==2 else 'rd' if place==3 else 'th'}: {pct:>6.2f}% {bar}")

    # Average wins comparison
    print("\n" + "-"*80)
    print("AVERAGE WINS BY TEAM (Across All Simulations)")
    print("-"*80)

    avg_wins_data = []
    for team in teams:
        total = simulation['total_wins'].get(team, 0)
        avg = total / num_sims
        actual_wins = None
        for t, w, l, p in actual['standings']:
            if t == team:
                actual_wins = w
                break
        avg_wins_data.append((team, avg, actual_wins))

    avg_wins_data.sort(key=lambda x: x[1], reverse=True)

    print(f"{'Team':<25}{'Avg Sim Wins':<15}{'Actual Wins':<12}{'Diff'}")
    print("-"*80)
    for team, avg, actual_w in avg_wins_data:
        diff = actual_w - avg
        indicator = " <-- YOU" if team == my_team else ""
        print(f"{team:<25}{avg:<15.2f}{actual_w:<12}{diff:+.2f}{indicator}")

    # Weekly scoring summary
    print("\n" + "-"*80)
    print("WEEKLY SCORING SUMMARY")
    print("-"*80)

    weekly_scores = actual['weekly_scores']
    team_totals = {team: sum(scores) for team, scores in weekly_scores.items()}
    team_avgs = {team: sum(scores)/len(scores) for team, scores in weekly_scores.items()}

    sorted_by_total = sorted(team_totals.items(), key=lambda x: x[1], reverse=True)

    print(f"{'Rank':<6}{'Team':<25}{'Total Points':<15}{'Avg/Week'}")
    print("-"*80)
    for rank, (team, total) in enumerate(sorted_by_total, 1):
        avg = team_avgs[team]
        indicator = " <-- YOU" if team == my_team else ""
        print(f"{rank:<6}{team:<25}{total:<15.2f}{avg:.2f}{indicator}")

    print("\n" + "="*80)
    print("END OF REPORT")
    print("="*80)


def main():
    """Main entry point."""
    # Load data
    data = load_data('league_data.json')

    # Analyze actual results
    actual = analyze_actual_results(data)

    # Run Monte Carlo simulation
    simulation = run_monte_carlo_analysis(data, num_simulations=100000)

    # Print report
    print_report(data, actual, simulation)

    # Save results to file
    results = {
        'actual_standings': [(t, w, l, p) for t, w, l, p in actual['standings']],
        'playoff_teams': list(actual['playoff_teams']),
        'expected_wins': actual['expected_wins'],
        'simulation_results': {
            'playoff_probabilities': {t: c/simulation['num_simulations']*100
                                      for t, c in simulation['playoff_counts'].items()},
            'average_wins': {t: w/simulation['num_simulations']
                           for t, w in simulation['total_wins'].items()}
        }
    }

    with open('analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\nResults saved to analysis_results.json")


if __name__ == '__main__':
    main()
