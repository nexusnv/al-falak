import subprocess
from pathlib import Path

GRID = (
    ("Raleigh", 35.7750, -78.6336, "2015-07-12"),
    ("Raleigh", 35.7750, -78.6336, "2015-12-01"),
    ("London", 51.5074, -0.1278, "2024-06-21"),
    ("London", 51.5074, -0.1278, "2024-12-21"),
    ("Singapore", 1.3521, 103.8198, "2024-03-20"),
    ("Tokyo", 35.6762, 139.6503, "2024-09-01"),
    ("Sydney", -33.8688, 151.2093, "2024-01-15"),
    ("Nairobi", -1.2921, 36.8219, "2024-04-10"),
    ("New York", 40.7128, -74.0060, "2024-11-03"),
    ("Cape Town", -33.9249, 18.4241, "2024-07-01"),
    ("Madrid", 40.4168, -3.7038, "2024-02-29"),
    ("Kuala Lumpur", 3.1390, 101.6869, "2024-06-01"),
)
METHODS = ("MUSLIM_WORLD_LEAGUE", "NORTH_AMERICA")

SOURCE_PINS = {
    "adhanpy": {
        "sha": "f9cfed51a857cb6a8436ad4f5685e7ac27896782",
        "version": "f9cfed51",
        "seconds_procedure": "minute-only",
        "high_latitude_rule": "MIDDLE_OF_THE_NIGHT",
    },
    "adhan_kotlin": {
        "sha": "e23d14385f6203954256b935ef91dc3c6565de34",
        "version": "e23d1438",
        "seconds_procedure": "second",
        "high_latitude_rule": "MIDDLE_OF_THE_NIGHT",
    },
}


def assert_pinned_head(repo_dir: Path, expected_sha: str) -> None:
    """Exit if ``repo_dir`` is not a git checkout at ``expected_sha``."""
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"cannot read git HEAD in {repo_dir}")
    head = result.stdout.strip()
    if head != expected_sha:
        raise SystemExit(
            f"{repo_dir} HEAD {head} does not match pinned SHA {expected_sha}"
        )


def assert_clean_worktree(repo_dir: Path) -> None:
    """Exit if ``repo_dir`` has tracked or untracked changes.

    Vectors generated from a dirty ``--source-dir`` checkout would claim the
    pinned SHA while running different code.
    """
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"cannot read git status in {repo_dir}")
    if result.stdout.strip():
        raise SystemExit(f"{repo_dir} is dirty; generate vectors from a clean checkout")
