# Fantasy Football Schedule Permutation Analysis

## Goal
Scrape all weekly scores from my NFL.com Fantasy Football league and analyze all possible schedule permutations to determine in which scenarios I would have made the playoffs and/or placed differently in the league.

## League Details
- **Platform**: NFL.com Fantasy
- **League URL**: https://fantasy.nfl.com/league/11757620
- **League Name**: Sheldon Lake FFB 25

---

## Step 1: Scrape the Data

Using ChromeDevTools MCP, I need you to:

### 1.1 Authentication
- Open the league URL and wait for me to confirm I'm logged in

### 1.2 Identify League Structure
- Number of teams
- Number of regular season weeks (before playoffs)
- Number of playoff teams
- My team name/number

### 1.3 Scrape Weekly Matchup Data

Navigate to the schedule/scoreboard pages and extract data for each week. For each week, capture:
- All matchups (Team A vs Team B)
- Final scores for each team

**Likely URL patterns:**
```
https://fantasy.nfl.com/league/11757620/history/2024/schedule?scheduleDetail={week}&scheduleType=week&standingsTab=schedule
```
or
```
https://fantasy.nfl.com/league/11757620/schedule?scheduleDetail={week}&scheduleType=week
```

### 1.4 Data Storage Format

Store the data in a structured format (JSON or CSV):

```json
{
  "teams": ["Team1", "Team2", "..."],
  "weeks": [
    {
      "week": 1,
      "matchups": [
        {"home": "Team1", "away": "Team2", "home_score": 120.5, "away_score": 115.2},
        {"home": "Team3", "away": "Team4", "home_score": 98.3, "away_score": 105.7}
      ]
    }
  ],
  "playoff_teams": 4,
  "my_team": "TeamName"
}
```

---

## Step 2: Permutation Analysis

Once data is collected, analyze all possible schedule permutations:

### 2.1 Extract Weekly Scores
- Get each team's weekly scores independent of who they played

### 2.2 Generate All Valid Round-Robin Schedules
Where:
- Each team plays exactly once per week
- No team plays itself
- Account for the actual schedule structure (if teams play each other twice, etc.)

### 2.3 For Each Permutation, Calculate:
- Each team's W-L record
- Tiebreakers (total points scored)
- Final standings
- Who makes playoffs

### 2.4 Output Analysis:
- Total number of possible schedule permutations
- In how many scenarios does my team make playoffs? (count and percentage)
- In how many scenarios does my team finish 1st, 2nd, 3rd, etc.?
- What was my "luck factor"? (actual wins vs expected wins based on scoring)
- Which teams benefited most/least from the schedule?

---

## Step 3: Deliverables

1. **Raw data file** (JSON/CSV) with all scores
2. **Python script** for the analysis
3. **Summary report** showing:
   - My playoff probability across all permutations
   - My placement distribution
   - Comparison of actual outcome vs. average expected outcome
   - "Luckiest" and "unluckiest" teams in the league

---

## Technical Notes

- The 2024 NFL fantasy regular season was typically weeks 1-14, with playoffs weeks 15-17
- Handle bye weeks if any exist
- Use ChromeDevTools MCP to navigate and execute JavaScript to extract data from the DOM
- For very large permutation counts, consider Monte Carlo sampling instead of exhaustive enumeration

---

## Example JavaScript for DOM Scraping

This may help extract matchup data from the scoreboard page:

```javascript
// Example: Extract matchup data from NFL.com fantasy scoreboard
const matchups = [];
document.querySelectorAll('.matchup').forEach(m => {
  const teams = m.querySelectorAll('.teamName');
  const scores = m.querySelectorAll('.teamScore');
  if (teams.length === 2 && scores.length === 2) {
    matchups.push({
      team1: teams[0].innerText.trim(),
      team2: teams[1].innerText.trim(),
      score1: parseFloat(scores[0].innerText),
      score2: parseFloat(scores[1].innerText)
    });
  }
});
console.log(JSON.stringify(matchups, null, 2));
```

Note: Selector names may vary - inspect the actual DOM to find correct selectors.
