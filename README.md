# First-Run Pass Rate Scraper

A Python tool to calculate the "First-Run Pass Rate" for CI pipelines on GitHub Pull Requests and GitLab Merge Requests.

## What It Does

For each PR/MR, the scraper:
1. Identifies the very first commit SHA when the PR/MR was opened
2. Finds the earliest CI pipeline/check-run for that specific SHA
3. Determines if that first run passed or failed
4. Calculates pass rate statistics across all PRs/MRs

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the example config:
```bash
cp config.example.py config.py
```

2. Edit `config.py` with your repository details and tokens:
   - **GitHub**: Create a Personal Access Token with `repo` scope
   - **GitLab**: Create a Personal Access Token with `read_api` scope

## Usage

### Basic Usage

```python
from scraper import Scraper
from config import REPOS_CONFIG

scraper = Scraper(REPOS_CONFIG)
scraper.run()
scraper.print_summary()
```

Or run the example:
```bash
python example_usage.py
```

### Inline Configuration

```python
from scraper import Scraper

repos = [
    {
        'platform': 'github',
        'url': 'https://api.github.com',
        'token': 'ghp_xxxxx',
        'repo_path': 'owner/repo'
    },
    {
        'platform': 'gitlab',
        'url': 'https://gitlab.com',
        'token': 'glpat-xxxxx',
        'repo_path': '12345678'  # Project ID
    }
]

scraper = Scraper(repos)
scraper.run()
scraper.print_summary()
```

## Output

The scraper produces a summary table:

```
====================================================================================================
FIRST-RUN PASS RATE SUMMARY
====================================================================================================
Repo Name                                Platform   Total    Passes   Failures   Pass Rate %
----------------------------------------------------------------------------------------------------
owner/repo                               GitHub     150      120      30         80.00
group/project                            GitLab     200      180      20         90.00
====================================================================================================
```

## Features

- ✅ Supports both GitHub and GitLab
- ✅ Handles pagination for large repositories
- ✅ Rate limit handling with automatic retries
- ✅ Modular design for easy extension
- ✅ Logging for debugging
- ✅ Error handling and retry logic

## API Token Permissions

### GitHub
- Required scope: `repo` (for private repos) or `public_repo` (for public repos only)
- Create at: https://github.com/settings/tokens

### GitLab
- Required scope: `read_api`
- Create at: https://gitlab.com/-/profile/personal_access_tokens

## Rate Limits

- **GitHub**: 5,000 requests/hour (authenticated)
- **GitLab**: 2,000 requests/minute

The scraper automatically handles rate limiting with exponential backoff and retry logic.

## Future Enhancements

- Slack notifications via `send_slack_notification()` method
- Export to CSV/JSON
- Time-based filtering (e.g., only PRs from last 30 days)
- Support for GitHub GraphQL API for better performance
- Webhook integration for real-time monitoring

## Project Structure

```
ftpr/
├── scraper.py          # Main Scraper class
├── config.py           # Your configuration (git-ignored)
├── config.example.py   # Example configuration
├── example_usage.py    # Usage examples
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Troubleshooting

### Authentication Errors
- Verify your token has the correct permissions
- Check token hasn't expired

### Rate Limiting
- The scraper automatically handles rate limits
- For very large repos, consider running during off-peak hours

### No CI Data
- Ensure the repository has CI/CD configured
- Some PRs may not have CI runs if created before CI was set up
