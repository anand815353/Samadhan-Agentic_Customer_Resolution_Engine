#!/usr/bin/env python3
"""Samadhan demo seed script (T-014 validate-only; T-015 reset/upsert)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.seed.template_spec import WORKBOOK_RELATIVE_PATH  # noqa: E402
from app.seed.validator import validate_workbook  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Samadhan demo seed data utility")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["validate-only", "reset", "upsert"],
        help="Operation mode",
    )
    parser.add_argument(
        "--env",
        choices=["local", "demo"],
        default="local",
        help="Target environment label (uses MONGODB_URI / MONGODB_DB_NAME from settings)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow reset on non-local env",
    )
    parser.add_argument(
        "--file",
        default=None,
        help=f"Path to seed workbook (default: {WORKBOOK_RELATIVE_PATH})",
    )
    return parser


def _print_validation_issues(result) -> None:
    for issue in result.issues:
        if issue.level == "warning":
            print(issue.format_line())
        else:
            print(issue.format_line(), file=sys.stderr)


def _run_validate_only(workbook_path: Path) -> int:
    result = validate_workbook(workbook_path.resolve())
    _print_validation_issues(result)

    if result.ok:
        print(
            "Seed workbook validation passed "
            f"({result.sheets_checked} sheets, {result.rows_checked} data rows checked)."
        )
        return 0

    print(
        f"Seed workbook validation failed with {len(result.errors)} error(s).",
        file=sys.stderr,
    )
    return 1


def _run_seed_mode(mode: str, workbook_path: Path, env_label: str, force: bool) -> int:
    from app.seed.loader import format_seed_summary, run_seed

    settings = get_settings()
    if env_label != settings.app_env:
        print(
            f"Note: --env {env_label} differs from APP_ENV={settings.app_env}; "
            "using configured MongoDB settings.",
        )

    result = run_seed(
        mode,  # type: ignore[arg-type]
        workbook_path.resolve(),
        settings,
        env_label=env_label,
        force_reset=force,
    )

    for issue in result.validation.issues:
        if issue.level == "warning":
            print(issue.format_line())

    if not result.validation.ok:
        _print_validation_issues(result.validation)
        print(
            f"Seed workbook validation failed with {len(result.validation.errors)} error(s).",
            file=sys.stderr,
        )
        return 1

    if not result.ok:
        print(result.error_message or "Seed operation failed.", file=sys.stderr)
        return 1

    print(format_seed_summary(result))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workbook_path = Path(args.file) if args.file else ROOT / WORKBOOK_RELATIVE_PATH

    if args.mode == "validate-only":
        return _run_validate_only(workbook_path)

    return _run_seed_mode(args.mode, workbook_path, args.env, args.force)


if __name__ == "__main__":
    raise SystemExit(main())
