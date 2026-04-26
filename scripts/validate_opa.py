from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "policy-bundle-pmel-v1.0.0"


def run(command: list[str]) -> int:
    print(" ".join(command))
    completed = subprocess.run(command, cwd=ROOT)
    return completed.returncode


def main() -> int:
    if shutil.which("opa"):
        check = run(["opa", "check", "--strict", str(BUNDLE)])
        test = run(["opa", "test", str(BUNDLE), "--format", "pretty"])
        return check or test

    if shutil.which("docker"):
        docker_check = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
        )
        if docker_check.returncode != 0:
            print("Docker CLI exists, but Docker daemon is not available.")
            print(docker_check.stderr.strip())
            return 3
        image = "openpolicyagent/opa:0.68.0-rootless"
        mount = f"{BUNDLE}:/bundle:ro"
        check = run(["docker", "run", "--rm", "-v", mount, image, "check", "--strict", "/bundle"])
        test = run(["docker", "run", "--rm", "-v", mount, image, "test", "/bundle", "--format", "pretty"])
        return check or test

    print("Neither opa nor docker is available. Install OPA or start Docker Desktop.")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
