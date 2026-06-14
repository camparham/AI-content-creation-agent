"""Check that required packages are installed."""

import importlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
REQUIREMENTS = ROOT / "requirements.txt"

# Pip package name -> Python import module (when they differ)
IMPORT_OVERRIDES = {
    "tavily-python": "tavily",
    "python-dotenv": "dotenv",
    "google-auth": "google.oauth2.service_account",
    "google-api-python-client": "googleapiclient",
}


def load_requirements(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Requirements file not found: {path}")

    packages = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)", line)
        if match:
            packages.append(match.group(1))
    return packages


def import_name(package: str) -> str:
    return IMPORT_OVERRIDES.get(package, package.replace("-", "_"))


def check_packages(packages: list[str]) -> list[str]:
    missing = []
    for package in packages:
        try:
            importlib.import_module(import_name(package))
        except ImportError:
            missing.append(package)
    return missing


def main() -> int:
    if sys.version_info < (3, 10):
        print("Python 3.10+ is required.")
        return 1

    try:
        packages = load_requirements(REQUIREMENTS)
    except FileNotFoundError as exc:
        print(exc)
        return 1

    missing = check_packages(packages)
    if not missing:
        print("All required packages are installed.")
        return 0

    print("Missing packages:")
    for package in missing:
        print(f"  - {package}")

    print(f"\nInstall them with:\n  pip install -r \"{REQUIREMENTS}\"")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
