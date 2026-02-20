from pathlib import Path
import re

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Fail if direct AuditLog/SystemLog writes are used outside audit backends."

    FORBIDDEN_PATTERNS = [
        re.compile(r"\bAuditLog\.objects\.create\s*\("),
        re.compile(r"\bSystemLog\.objects\.create\s*\("),
    ]

    ALLOWED_FILES = {
        Path("apps/audit/backends.py"),
    }

    SKIP_DIRS = {
        ".git",
        ".idea",
        ".pytest_cache",
        "venv",
        "__pycache__",
    }

    def handle(self, *args, **options):
        root = Path.cwd()
        violations = []

        for file_path in root.rglob("*.py"):
            rel = file_path.relative_to(root)

            if any(part in self.SKIP_DIRS for part in rel.parts):
                continue

            if rel in self.ALLOWED_FILES:
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

            for idx, line in enumerate(content.splitlines(), start=1):
                for pattern in self.FORBIDDEN_PATTERNS:
                    if pattern.search(line):
                        violations.append((str(rel), idx, line.strip()))

        if violations:
            self.stdout.write(self.style.ERROR("Direct audit writes found:"))
            for rel, line_no, line in violations:
                self.stdout.write(f"- {rel}:{line_no} -> {line}")
            raise CommandError(
                "Use apps.audit.log_event(...) instead of direct AuditLog/SystemLog writes."
            )

        self.stdout.write(self.style.SUCCESS("No forbidden direct audit writes found."))

