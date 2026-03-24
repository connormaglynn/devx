from pathlib import Path
from services.command_runner_service import CommandRunnerService
import tempfile


class GitService:
    def __init__(self, runner: CommandRunnerService):
        self.runner = runner

    def __get_tmp_dir(self) -> Path:
        base = Path(tempfile.gettempdir()) / "devx-git"
        base.mkdir(parents=True, exist_ok=True)
        return base

    def clean_checkout_main(self, org: str, repo: str) -> Path:
        base_dir = self.__get_tmp_dir()
        repo_dir = base_dir / repo

        if not repo_dir.exists():
            self.runner.run(f"git clone https://github.com/{org}/{repo}.git {repo_dir}")

        self.__update_repo(repo_dir)

        return repo_dir

    def __update_repo(self, repo_dir: Path):
        try:
            self.runner.run(f"cd {repo_dir} && git stash")
        except Exception:
            pass

        try:
            self.runner.run(f"cd {repo_dir} && git checkout main")
        except Exception:
            self.runner.run(f"cd {repo_dir} && git checkout master")

        self.runner.run(f"cd {repo_dir} && git pull")
