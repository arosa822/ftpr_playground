"""
Example usage of the Scraper class
"""
from scraper import Scraper

# Option 1: Use configuration from config.py
try:
    from config import REPOS_CONFIG
    repos = REPOS_CONFIG
except ImportError:
    # Option 2: Define inline
    repos = [
        {
            'platform': 'github',
            'url': 'https://api.github.com',
            'token': 'your_token_here',
            'repo_path': 'owner/repo'
        }
    ]

# Create scraper instance
scraper = Scraper(repos)

# Run the analysis
scraper.run()

# Print formatted summary
scraper.print_summary()

# Get raw results for further processing
results = scraper.get_results()

# Example: Filter repos with FTPR < 80%
low_performers = [r for r in results if r['ftpr'] < 80]
if low_performers:
    print("\nRepositories with FTPR < 80%:")
    for repo in low_performers:
        print(f"  - {repo['repo_name']}: {repo['ftpr']}%")
