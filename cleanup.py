#!/usr/bin/env python3

from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import termios
import tty


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

HOME = Path.home()

CACHE_DIRS = [
    HOME / ".cache" / "yay",
    HOME / ".cache" / "paru",
    HOME / ".cache" / "spotify",
    HOME / ".cache" / "mozilla",
]


# ─────────────────────────────────────────────────────────────────────────────
# Terminal utilities
# ─────────────────────────────────────────────────────────────────────────────

def clear_screen():
    print("\033[2J\033[H", end="")


def get_key():
    """Read a single key without requiring Enter."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return key


def wait_for_key(message="\nPress any key to continue..."):
    print(message, end="", flush=True)
    get_key()


def run_command(command):
    """Execute a read-only shell command and return stdout, or stderr on failure."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            check=False,
        )

        if result.returncode != 0:
            return result.stderr.strip()

        return result.stdout.strip()

    except Exception as error:
        return f"Error: {error}"


# ─────────────────────────────────────────────────────────────────────────────
# Size utilities
# ─────────────────────────────────────────────────────────────────────────────

def get_size(path: Path) -> int:
    if not path.exists():
        return 0

    if path.is_file() or path.is_symlink():
        try:
            return path.stat().st_size
        except OSError:
            return 0

    total = 0

    try:
        for item in path.rglob("*"):
            try:
                if item.is_file() and not item.is_symlink():
                    total += item.stat().st_size
            except OSError:
                pass
    except OSError:
        pass

    return total


def format_size(size: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(size)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024

    return f"{value:.1f} TiB"


def parse_journal_bytes(output: str) -> int:
    """Best-effort conversion of journalctl --disk-usage output to bytes."""
    # systemd commonly prints values such as "49.6M" rather than "49.6MB".
    # Accept both forms so the QML UI always receives a short formatted value.
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([KMGT]?)(?:i?B|B)?", output, re.IGNORECASE)
    if not match:
        return 0

    value = float(match.group(1))
    unit = match.group(2).upper()
    factors = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    return int(value * factors.get(unit, 1))


# ─────────────────────────────────────────────────────────────────────────────
# Machine-readable API for Launcher.qml
# ─────────────────────────────────────────────────────────────────────────────

def get_orphan_packages():
    try:
        result = subprocess.run(
            ["pacman", "-Qtdq"],
            text=True,
            capture_output=True,
            check=False,
        )
    except (OSError, FileNotFoundError):
        return []

    # pacman returns 1 when there are simply no orphan packages.
    if result.returncode not in (0, 1):
        return []

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def get_status_data():
    usage = shutil.disk_usage("/")
    percentage = (usage.used / usage.total) * 100 if usage.total else 0.0

    cache_entries = []
    total_removable = 0
    for path in CACHE_DIRS:
        size = get_size(path)
        total_removable += size
        cache_entries.append(
            {
                "name": path.name,
                "path": str(path),
                "bytes": size,
                "human": format_size(size),
            }
        )

    package_cache_size = get_size(Path("/var/cache/pacman/pkg"))
    journal_output = run_command("journalctl --disk-usage")
    journal_bytes = parse_journal_bytes(journal_output)
    orphans = get_orphan_packages()

    nonzero_names = [entry["name"] for entry in cache_entries if entry["bytes"] > 0]
    summary = " • ".join(nonzero_names) if nonzero_names else "Nothing to clean"

    return {
        "disk": {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "total_human": format_size(usage.total),
            "used_human": format_size(usage.used),
            "free_human": format_size(usage.free),
            "percentage": round(percentage, 1),
        },
        "removable_cache": {
            "total_bytes": total_removable,
            "total_human": format_size(total_removable),
            "summary": summary,
            "entries": cache_entries,
        },
        "package_cache": {
            "bytes": package_cache_size,
            "human": format_size(package_cache_size),
        },
        "journal": {
            "bytes": journal_bytes,
            "human": format_size(journal_bytes) if journal_bytes or "0B" in journal_output else (journal_output or "Unknown"),
            "raw": journal_output,
        },
        "orphans": {
            "count": len(orphans),
            "packages": orphans,
        },
    }


def clear_directory_contents(path: Path):
    failures = []

    if not path.exists():
        return failures

    for item in path.iterdir():
        try:
            if item.is_dir() and not item.is_symlink():
                shutil.rmtree(item)
            else:
                item.unlink()
        except OSError as error:
            failures.append(f"{item}: {error}")

    return failures


def clear_configured_caches():
    before = sum(get_size(path) for path in CACHE_DIRS)
    failures = []

    for path in CACHE_DIRS:
        failures.extend(clear_directory_contents(path))

    after = sum(get_size(path) for path in CACHE_DIRS)
    cleared = max(0, before - after)

    return {
        "success": len(failures) == 0,
        "cleared_bytes": cleared,
        "cleared_human": format_size(cleared),
        "remaining_bytes": after,
        "message": f"Cleared approximately {format_size(cleared)}.",
        "failures": failures,
    }


def print_json(data):
    # One compact line is intentional: Quickshell's SplitParser consumes it cleanly.
    print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


# ─────────────────────────────────────────────────────────────────────────────
# Terminal UI
# ─────────────────────────────────────────────────────────────────────────────

def print_header(title):
    width = 62
    print("╭" + "─" * width + "╮")
    print(f"│ {title:^{width - 2}} │")
    print("╰" + "─" * width + "╯")


def print_section(title):
    print()
    print(f"── {title} " + "─" * max(1, 55 - len(title)))


def show_disk_usage():
    print_section("Disk")
    usage = shutil.disk_usage("/")
    percentage = (usage.used / usage.total) * 100
    print("Filesystem:     /")
    print(f"Total:          {format_size(usage.total)}")
    print(f"Used:           {format_size(usage.used)} ({percentage:.1f}%)")
    print(f"Available:      {format_size(usage.free)}")


def show_home_usage():
    print_section("Home directories")
    entries = []

    try:
        for path in HOME.iterdir():
            if not path.exists():
                continue
            size = get_size(path)
            if size > 0:
                entries.append((size, path))
    except PermissionError:
        pass

    entries.sort(reverse=True, key=lambda item: item[0])
    for size, path in entries[:15]:
        print(f"{format_size(size):>10}   {path.name}")


def show_cache_usage():
    print_section("Largest caches")
    cache_root = HOME / ".cache"

    if not cache_root.exists():
        print("No ~/.cache directory found.")
        return

    entries = []
    for path in cache_root.iterdir():
        try:
            entries.append((get_size(path), path))
        except OSError:
            pass

    entries.sort(reverse=True, key=lambda item: item[0])
    for size, path in entries[:15]:
        print(f"{format_size(size):>10}   {path.name}")

    print()
    print(f"{'Total cache:':>15} {format_size(get_size(cache_root))}")


def show_package_cache():
    print_section("Pacman package cache")
    cache_path = Path("/var/cache/pacman/pkg")
    print(f"/var/cache/pacman/pkg: {format_size(get_size(cache_path))}")


def show_journal_usage():
    print_section("System journal")
    output = run_command("journalctl --disk-usage")
    print(output if output else "Unable to determine journal size.")


def show_orphans():
    print_section("Orphan packages")
    packages = get_orphan_packages()

    if not packages:
        print("No orphan packages found.")
        return

    print(f"Found: {len(packages)}")
    print()
    for package in packages:
        print(f"  • {package}")


def check_storage():
    clear_screen()
    print_header("CachyOS Storage Check")
    print("\nScanning filesystem...")

    clear_screen()
    print_header("CachyOS Storage Check")
    show_disk_usage()
    show_home_usage()
    show_cache_usage()
    show_package_cache()
    show_journal_usage()
    show_orphans()

    print()
    print("─" * 64)
    print("Read-only scan complete.")
    wait_for_key()


def clear_cache():
    clear_screen()
    print_header("Clear Cache")

    total_size = 0
    print()
    for path in CACHE_DIRS:
        size = get_size(path)
        total_size += size
        print(f"{format_size(size):>10}   {path}")

    print()
    print("─" * 64)
    print(f"Total removable cache: {format_size(total_size)}")

    if total_size == 0:
        print("\nNothing to clean.")
        wait_for_key()
        return

    print("\nClear these caches? [y/N] ", end="", flush=True)
    answer = get_key().lower()
    print(answer)

    if answer != "y":
        print("\nCancelled.")
        wait_for_key()
        return

    result = clear_configured_caches()
    print()
    print("─" * 64)
    print(result["message"])

    if result["failures"]:
        print("\nSome entries could not be removed:")
        for failure in result["failures"]:
            print(f"  • {failure}")

    wait_for_key()


def show_menu():
    while True:
        clear_screen()
        print_header("CachyOS Cleanup")
        print()
        print("  [1]  Check storage")
        print("  [2]  Clear Cache")
        print()
        print("  [0]  Exit")
        print()
        print("Select an option: ", end="", flush=True)

        choice = get_key()
        if choice == "1":
            check_storage()
        elif choice == "2":
            clear_cache()
        elif choice == "0":
            clear_screen()
            break


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if "--status-json" in sys.argv:
        print_json(get_status_data())
        return 0

    if "--clear-cache-json" in sys.argv:
        result = clear_configured_caches()
        print_json(result)
        return 0 if result["success"] else 1

    try:
        show_menu()
        return 0
    except KeyboardInterrupt:
        clear_screen()
        print("Cleanup cancelled.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
