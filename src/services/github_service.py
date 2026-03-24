import os
import subprocess
from types import SimpleNamespace
from github import Github
from datetime import datetime, timedelta, timezone


class GitHubService:
    def __init__(self, token: str | None = None):
        self.token = token or self.__get_token()
        self.client = Github(self.token)

    def __get_token(self) -> str:
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token

        try:
            return subprocess.check_output("gh auth token", shell=True).decode().strip()
        except Exception:
            pass

        raise RuntimeError(
            "No GitHub token found. Provide via --token, "
            "GITHUB_TOKEN env var, or `gh auth login`."
        )

    def get_repos(self, org_name: str, team_slug: str) -> list[str]:
        org = self.client.get_organization(org_name)
        team = org.get_team_by_slug(team_slug)
        repos = team.get_repos()
        return [
            repo.name for repo in repos if not repo.archived and repo.permissions.admin
        ]

    def get_old_secrets(
        self, org_name: str, team_slug: str, age: int, secrets_to_ignore
    ) -> list[SimpleNamespace]:
        cutoff_datetime = datetime.now(timezone.utc) - timedelta(days=age)

        org = self.client.get_organization(org_name)
        team = org.get_team_by_slug(team_slug)
        repos = team.get_repos()

        results: list[SimpleNamespace] = []
        for repo in repos:
            if not repo.archived and repo.permissions.admin:
                secrets: list = []
                for secret in repo.get_secrets():
                    updated_at = secret.updated_at
                    if updated_at.tzinfo is None:
                        updated_at = updated_at.replace(tzinfo=timezone.utc)

                    if updated_at < cutoff_datetime:
                        # secrets.append(
                        #     SimpleNamespace(
                        #         secret_name=secret.name,
                        #         secret_last_updated=updated_at.isoformat(),
                        #     )
                        # )
                        if secret.name not in secrets_to_ignore:
                            secrets.append(secret.name)
                if secrets:
                    results.append(
                        SimpleNamespace(repository_name=repo.name, secrets=secrets)
                    )

        return results
