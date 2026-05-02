from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPO_ROOT / "apps" / "web"
FAST_TEST_COMMAND = [
    sys.executable,
    "-m",
    "unittest",
    "-v",
    "tests.test_smoke",
    "tests.test_web_smoke",
    "tests.test_schema_contracts",
    "tests.test_desktop_schema_contracts",
]
CONTRACT_TEST_COMMAND = [
    sys.executable,
    "-m",
    "unittest",
    "-v",
    "tests.test_schema_contracts",
    "tests.test_desktop_schema_contracts",
]
DESKTOP_TEST_COMMAND = [
    sys.executable,
    "-m",
    "unittest",
    "-v",
    "tests.test_api",
    "tests.test_api_server",
    "tests.test_catalog",
    "tests.test_desktop_schema_contracts",
]
PYTHON_TEST_COMMAND = [
    sys.executable,
    "-m",
    "unittest",
    "-v",
    "tests.test_web_smoke",
    "tests.test_api_server",
    "tests.test_api",
    "tests.test_catalog",
]
WEB_TEST_COMMAND = ["npm", "run", "test:e2e"]


def main(argv: list[str]) -> int:
    target = argv[1] if len(argv) > 1 else "all"
    if target not in {"fast", "contracts", "desktop", "python", "web", "all"}:
        print(f"Unsupported test target: {target}", file=sys.stderr)
        print("Usage: python scripts/run_tests.py [fast|contracts|desktop|python|web|all]", file=sys.stderr)
        return 2

    try:
        if target == "fast":
            run_fast_tests()
        if target == "contracts":
            run_contract_tests()
        if target == "desktop":
            run_desktop_tests()
        if target in {"python", "all"}:
            run_python_tests()
        if target in {"web", "all"}:
            run_web_tests()
    except subprocess.CalledProcessError as error:
        return error.returncode
    return 0


def run_python_tests() -> None:
    print("==> Running Python regression suite")
    env = build_python_test_env()
    subprocess.run(PYTHON_TEST_COMMAND, cwd=REPO_ROOT, env=env, check=True)


def run_fast_tests() -> None:
    print("==> Running fast smoke + contract suite")
    env = build_python_test_env()
    subprocess.run(FAST_TEST_COMMAND, cwd=REPO_ROOT, env=env, check=True)


def run_contract_tests() -> None:
    print("==> Running schema + fixture contract suite")
    env = build_python_test_env()
    subprocess.run(CONTRACT_TEST_COMMAND, cwd=REPO_ROOT, env=env, check=True)


def run_desktop_tests() -> None:
    print("==> Running desktop catalog/api/schema suite")
    env = build_python_test_env()
    subprocess.run(DESKTOP_TEST_COMMAND, cwd=REPO_ROOT, env=env, check=True)


def build_python_test_env() -> dict[str, str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "").strip()
    src_path = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src_path if not existing_pythonpath else os.pathsep.join([src_path, existing_pythonpath])
    return env


def run_web_tests() -> None:
    print("==> Running web Playwright regression suite")
    subprocess.run(WEB_TEST_COMMAND, cwd=WEB_ROOT, check=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
