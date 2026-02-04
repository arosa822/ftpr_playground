"""
First-Run Pass Rate Scraper for GitHub and GitLab CI Pipelines
"""
import requests
import time
from typing import List, Dict, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PR_LIMIT = 100


class Scraper:
    """
    Scraper class to calculate First-Run Pass Rate for CI pipelines
    on GitHub Pull Requests and GitLab Merge Requests.
    """

    def __init__(self, repos: List[Dict[str, str]]):
        """
        Initialize the scraper with repository configurations.

        Args:
            repos: List of repository configs, each with:
                - platform: 'github' or 'gitlab'
                - url: Base URL (e.g., 'https://api.github.com' or 'https://gitlab.com')
                - token: Authentication token
                - repo_path: Repository path (e.g., 'owner/repo' for GitHub, project ID for GitLab)
        """
        self.repos = repos
        self.results = []

    def run(self) -> List[Dict]:
        """
        Run the scraper for all configured repositories.

        Returns:
            List of result dictionaries with metrics for each repo
        """
        for repo_config in self.repos:
            platform = repo_config['platform'].lower()

            logger.info(f"Processing {platform} repository: {repo_config['repo_path']}")

            try:
                if platform == 'github':
                    result = self._process_github(repo_config)
                elif platform == 'gitlab':
                    result = self._process_gitlab(repo_config)
                else:
                    logger.error(f"Unsupported platform: {platform}")
                    continue

                self.results.append(result)

            except Exception as e:
                logger.error(f"Error processing {repo_config['repo_path']}: {str(e)}")

        return self.results

    def _process_github(self, config: Dict[str, str]) -> Dict:
        """
        Process GitHub repository to calculate first-run pass rate.

        Args:
            config: Repository configuration

        Returns:
            Dictionary with metrics
        """
        base_url = config['url']
        repo_path = config['repo_path']
        token = config['token']

        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        prs = self._get_github_prs(base_url, repo_path, headers)

        total = 0
        passes = 0
        failures = 0

        for pr in prs:
            total += 1
            pr_number = pr['number']

            # Get the initial commit SHA (first commit when PR was opened)
            initial_sha = self._get_github_initial_commit(base_url, repo_path, pr_number, headers)
            if not initial_sha:
                logger.warning(f"Could not find initial SHA for PR #{pr_number}")
                continue

            # Get CI status for the initial commit
            status = self._get_github_ci_status(base_url, repo_path, initial_sha, headers)

            if status == 'success':
                passes += 1
            elif status == 'failure':
                failures += 1
            else:
                logger.info(f"PR #{pr_number}: Status is '{status}' - treating as failure")
                failures += 1

        pass_rate = (passes / total * 100) if total > 0 else 0

        return {
            'repo_name': repo_path,
            'platform': 'GitHub',
            'total': total,
            'passes': passes,
            'failures': failures,
            'pass_rate': round(pass_rate, 2)
        }

    def _get_github_prs(self, base_url: str, repo_path: str, headers: Dict) -> List[Dict]:
        """
        Get all pull requests with pagination.

        Args:
            base_url: GitHub API base URL
            repo_path: Repository path (owner/repo)
            headers: Request headers with auth

        Returns:
            List of PR objects
        """
        prs = []
        page = 1
        per_page = 100

        while (page-1)*per_page < PR_LIMIT:
            url = f"{base_url}/repos/{repo_path}/pulls"
            params = {
                'state': 'all',
                'page': page,
                'per_page': per_page,
                'sort': 'created',
                'direction': 'desc'
            }

            response = self._make_request(url, headers, params)

            if not response or not response.json():
                break

            batch = response.json()
            prs.extend(batch)

            if len(batch) < per_page:
                break

            page += 1

        logger.info(f"Found {len(prs)} PRs")
        return prs

    def _get_github_initial_commit(self, base_url: str, repo_path: str, pr_number: int, headers: Dict) -> Optional[str]:
        """
        Get the initial commit SHA when PR was opened.

        Args:
            base_url: GitHub API base URL
            repo_path: Repository path
            pr_number: PR number
            headers: Request headers

        Returns:
            Initial commit SHA or None
        """
        url = f"{base_url}/repos/{repo_path}/pulls/{pr_number}/commits"
        params = {'per_page': 1, 'page': 1}

        response = self._make_request(url, headers, params)

        if response and response.json():
            commits = response.json()
            if commits:
                return commits[0]['sha']

        return None

    def _get_github_ci_status(self, base_url: str, repo_path: str, sha: str, headers: Dict) -> str:
        """
        Get CI status for a specific commit SHA.

        Args:
            base_url: GitHub API base URL
            repo_path: Repository path
            sha: Commit SHA
            headers: Request headers

        Returns:
            Status string: 'success', 'failure', 'pending', etc.
        """
        # Try Check Runs API first (for GitHub Actions)
        logger.info(f"Fetching check runs from {base_url} for {sha}")
        check_runs_url = f"{base_url}/repos/{repo_path}/commits/{sha}/check-runs"
        response = self._make_request(check_runs_url, headers)
        # breakpoint()
        # for ci in response.json().get('check_runs',[]):
        #     logger.info(f"Check run: {ci['name']} - Conclusion: {ci['conclusion']}")

        if response and response.json():
            check_runs = response.json().get('check_runs', [])
            if check_runs:
                # Get the earliest check run
                check_runs.sort(key=lambda x: x['started_at'] if x.get('started_at') else '')
                if check_runs:
                    conclusion = check_runs[0].get('conclusion')
                    if conclusion:
                        return conclusion

        # Fallback to Status API (for other CI systems)
        status_url = f"{base_url}/repos/{repo_path}/commits/{sha}/status"
        logger.info(f"**failback** Fetching status from {status_url}")
        response = self._make_request(status_url, headers)

        if response and response.json():
            state = response.json().get('state', 'unknown')
            return state

        return 'unknown'

    def _process_gitlab(self, config: Dict[str, str]) -> Dict:
        """
        Process GitLab repository to calculate first-run pass rate.

        Args:
            config: Repository configuration

        Returns:
            Dictionary with metrics
        """
        base_url = config['url']
        project_id = config['repo_path']
        token = config['token']

        headers = {
            'PRIVATE-TOKEN': token
        }

        mrs = self._get_gitlab_mrs(base_url, project_id, headers)

        total = 0
        passes = 0
        failures = 0

        for mr in mrs:
            total += 1
            mr_iid = mr['iid']

            # Get the initial SHA (when MR was opened)
            initial_sha = mr.get('sha') or mr.get('diff_refs', {}).get('head_sha')

            if not initial_sha:
                logger.warning(f"Could not find initial SHA for MR !{mr_iid}")
                continue

            # Get the first pipeline for this MR
            status = self._get_gitlab_pipeline_status(base_url, project_id, mr_iid, headers)

            if status == 'success':
                passes += 1
            elif status in ['failed', 'canceled']:
                failures += 1
            else:
                logger.info(f"MR !{mr_iid}: Status is '{status}' - treating as failure")
                failures += 1

        pass_rate = (passes / total * 100) if total > 0 else 0

        return {
            'repo_name': project_id,
            'platform': 'GitLab',
            'total': total,
            'passes': passes,
            'failures': failures,
            'pass_rate': round(pass_rate, 2)
        }

    def _get_gitlab_mrs(self, base_url: str, project_id: str, headers: Dict) -> List[Dict]:
        """
        Get all merge requests with pagination.

        Args:
            base_url: GitLab API base URL
            project_id: Project ID or path
            headers: Request headers with auth

        Returns:
            List of MR objects
        """
        mrs = []
        page = 1
        per_page = 100

        while (page-1)*per_page < PR_LIMIT:
            url = f"{base_url}/api/v4/projects/{project_id}/merge_requests"
            params = {
                'state': 'all',
                'page': page,
                'per_page': per_page,
                'order_by': 'created_at',
                'sort': 'desc'
            }

            response = self._make_request(url, headers, params)

            if not response or not response.json():
                break

            batch = response.json()
            mrs.extend(batch)

            if len(batch) < per_page:
                break

            page += 1

        logger.info(f"Found {len(mrs)} MRs")
        return mrs

    def _get_gitlab_pipeline_status(self, base_url: str, project_id: str, mr_iid: int, headers: Dict) -> str:
        """
        Get the first pipeline status for a merge request.

        Args:
            base_url: GitLab API base URL
            project_id: Project ID
            mr_iid: MR internal ID
            headers: Request headers

        Returns:
            Pipeline status string
        """
        url = f"{base_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/pipelines"
        params = {'order_by': 'id', 'sort': 'asc', 'per_page': 1}

        response = self._make_request(url, headers, params)

        if response and response.json():
            pipelines = response.json()
            if pipelines:
                return pipelines[0].get('status', 'unknown')

        return 'unknown'

    def _make_request(self, url: str, headers: Dict, params: Optional[Dict] = None, retry_count: int = 3) -> Optional[requests.Response]:
        """
        Make HTTP request with error handling and rate limit management.

        Args:
            url: Request URL
            headers: Request headers
            params: Query parameters
            retry_count: Number of retries for rate limits

        Returns:
            Response object or None
        """
        for attempt in range(retry_count):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue

                # Handle other errors
                if response.status_code == 403:
                    reset_time = response.headers.get('X-RateLimit-Reset')
                    if reset_time:
                        wait_time = int(reset_time) - int(time.time())
                        if wait_time > 0:
                            logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds...")
                            time.sleep(wait_time)
                            continue

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{retry_count}): {str(e)}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

        return None

    def print_summary(self):
        """
        Print a formatted summary table of results.
        """
        if not self.results:
            print("\nNo results to display.")
            return

        print("\n" + "=" * 100)
        print("FIRST-RUN PASS RATE SUMMARY")
        print("=" * 100)
        print(f"{'Repo Name':<40} {'Platform':<10} {'Total':<8} {'Passes':<8} {'Failures':<10} {'Pass Rate %':<12}")
        print("-" * 100)

        for result in self.results:
            print(f"{result['repo_name']:<40} {result['platform']:<10} {result['total']:<8} "
                  f"{result['passes']:<8} {result['failures']:<10} {result['pass_rate']:<12.2f}")

        print("=" * 100)

    def get_results(self) -> List[Dict]:
        """
        Get the raw results data.

        Returns:
            List of result dictionaries
        """
        return self.results


if __name__ == "__main__":
    # Example usage
    repos_config = [
        {
            'platform': 'github',
            'url': 'https://api.github.com',
            'token': 'your_github_token_here',
            'repo_path': 'owner/repo'
        },
        {
            'platform': 'gitlab',
            'url': 'https://gitlab.com',
            'token': 'your_gitlab_token_here',
            'repo_path': 'project_id_or_path'
        }
    ]

    scraper = Scraper(repos_config)
    scraper.run()
    scraper.print_summary()
