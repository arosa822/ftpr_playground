"""
Example configuration file for the scraper.
Copy this to config.py and fill in your actual values.
"""

REPOS_CONFIG = [
    # GitHub Example
    {
        'platform': 'github',
        'url': 'https://api.github.com',
        'token': 'ghp_your_github_personal_access_token_here',
        'repo_path': 'owner/repository'  # e.g., 'facebook/react'
    },

    # GitLab Example
    {
        'platform': 'gitlab',
        'url': 'https://gitlab.com',  # or your self-hosted GitLab URL
        'token': 'glpat-your_gitlab_personal_access_token_here',
        'repo_path': '12345678'  # Project ID or 'group/project' path (URL-encoded)
    },

    # You can add more repositories here
]
