import subprocess
from shutil import which


class CommandRunnerService:
    def run(self, command: str) -> str:
        return subprocess.check_output(command, shell=True).decode().strip()

    def is_installed(self, cmd: str) -> bool:
        return which(cmd) is not None
