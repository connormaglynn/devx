import typer
from services.github_service import GitHubService
from rich import print
import json

app = typer.Typer()


def get_obj_dict(obj):
    return obj.__dict__


@app.command()
def get_repos(org: str, team: str, token: str = typer.Option(None)):
    """Get non-archived repos for a GitHub team - where the team also has admin acccess."""
    github_service = GitHubService(token)
    repos = github_service.get_repos(org, team)

    for repo in repos:
        typer.echo(repo)


@app.command()
def get_old_secrets(
    org: str,
    team: str,
    ignore: list[str] = [],
    age: int = 7,
    token: str = typer.Option(None),
):
    """Get secrets"""
    github_service = GitHubService(token)
    repos = github_service.get_old_secrets(org, team, age, ignore)

    print(json.dumps(repos, default=get_obj_dict))
