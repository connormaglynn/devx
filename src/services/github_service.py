from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Optional

from github import Github
from requests import Session


@dataclass(frozen=True)
class TemplateRepoHit:
    repo_full_name: str
    repo_url: str
    template_full_name: str
    template_url: str


class GitHubService:
    def __init__(self, token: str | None = None):
        self.token = token or self.__get_token()
        self.client = Github(self.token)
        self.rest_client = Session()
        self.rest_client.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
            }
        )
        self.graphql_client = Session()
        self.graphql_client.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }
        )

        self.graphql_url = "https://api.github.com/graphql"

    def __get_token(self) -> str:
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token

        try:
            token = (
                subprocess.check_output("gh auth token", shell=True).decode().strip()
            )
            return token
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

    def __graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        resp = self.graphql_client.post(
            self.graphql_url,
            json={"query": query, "variables": variables},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(payload["errors"])
        return payload

    def get_all_repos_created_from_template(
        self,
        org_name: str,
        template_full_name: str | None = None,
    ) -> list[TemplateRepoHit]:
        query = """
        query($org:String!, $after:String) {
          organization(login: $org) {
            repositories(first: 100, after: $after, orderBy: {field: NAME, direction: ASC}) {
              pageInfo { hasNextPage endCursor }
              nodes {
                nameWithOwner
                url
                templateRepository { nameWithOwner url }
              }
            }
          }
        }
        """

        hits: list[TemplateRepoHit] = []
        after: Optional[str] = None

        while True:
            payload = self.__graphql(query, {"org": org_name, "after": after})
            repos = payload["data"]["organization"]["repositories"]

            for repo in repos["nodes"]:
                templateRepo = repo.get("templateRepository")
                if not templateRepo:
                    continue
                if (
                    template_full_name
                    and templateRepo["nameWithOwner"] != template_full_name
                ):
                    continue

                hits.append(
                    TemplateRepoHit(
                        repo_full_name=repo["nameWithOwner"],
                        repo_url=repo["url"],
                        template_full_name=templateRepo["nameWithOwner"],
                        template_url=templateRepo["url"],
                    )
                )

            if not repos["pageInfo"]["hasNextPage"]:
                break
            after = repos["pageInfo"]["endCursor"]

        return hits
