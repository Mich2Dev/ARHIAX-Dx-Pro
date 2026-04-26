from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "policy-bundle-pmel-v1.0.0"
POLICY_DIRS = [
    BUNDLE / "base",
    BUNDLE / "pmel_governance",
    BUNDLE / "bpmn_lint",
    BUNDLE / "decommissioning",
    BUNDLE / "data",
]

sys.path.insert(0, str(ROOT / "src"))

from dxpro_runtime.policy import PolicyEngine  # noqa: E402


def run(command: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    print(" ".join(command))
    return subprocess.run(command, cwd=ROOT, input=input_text, capture_output=True, text=True)


def opa_command() -> list[str] | None:
    opa = shutil.which("opa")
    if opa:
        return [opa]
    if shutil.which("docker"):
        docker_check = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
        )
        if docker_check.returncode == 0:
            image = "openpolicyagent/opa:0.68.0-rootless"
            mount = f"{BUNDLE}:/bundle:ro"
            return ["docker", "run", "--rm", "-i", "-v", mount, image]
        print("Docker CLI exists, but Docker daemon is not available.")
        print(docker_check.stderr.strip())
    return None


def data_args(command: list[str]) -> list[str]:
    if command[0] == "docker":
        return [
            "--data",
            "/bundle/base",
            "--data",
            "/bundle/pmel_governance",
            "--data",
            "/bundle/bpmn_lint",
            "--data",
            "/bundle/decommissioning",
            "--data",
            "/bundle/data",
        ]
    args: list[str] = []
    for path in POLICY_DIRS:
        args.extend(["--data", str(path)])
    return args


def check_policies(command: list[str]) -> int:
    if command[0] == "docker":
        check = command + ["check", "--strict", "/bundle/base", "/bundle/pmel_governance", "/bundle/bpmn_lint", "/bundle/decommissioning", "/bundle/data"]
    else:
        check = command + ["check", "--strict", *[str(path) for path in POLICY_DIRS]]
    completed = run(check)
    if completed.stdout:
        print(completed.stdout)
    if completed.stderr:
        print(completed.stderr)
    return completed.returncode


def eval_manifest_packages(command: list[str]) -> int:
    engine = PolicyEngine(BUNDLE, opa_path="")
    packages = engine.package_names()
    failures: list[str] = []
    for package in packages:
        expression = f"data.{package}.decision"
        payload = engine._normalize_input(package, {}, "opa-validation")  # Runtime contract input adapter.
        completed = run(
            command + ["eval", "--stdin-input", "--format", "json", *data_args(command), expression],
            input_text=json.dumps(payload),
        )
        if completed.returncode != 0:
            failures.append(f"{package}: {completed.stderr.strip()}")
            continue
        try:
            data = json.loads(completed.stdout)
            value = data["result"][0]["expressions"][0]["value"]
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            failures.append(f"{package}: invalid OPA result: {exc}")
            continue
        if not isinstance(value, dict) or "outcome" not in value or "reason" not in value:
            failures.append(f"{package}: decision missing outcome/reason: {value}")
    if failures:
        print("OPA manifest evaluation failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"OPA manifest evaluation passed for {len(packages)} packages.")
    return 0


def main() -> int:
    command = opa_command()
    if not command:
        print("Neither opa nor available Docker daemon is present. Install OPA or start Docker Desktop.")
        return 3
    return check_policies(command) or eval_manifest_packages(command)


if __name__ == "__main__":
    raise SystemExit(main())
