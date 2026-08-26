#!/usr/bin/env python3

from pathlib import Path
import os
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
    """
    Read a single key without requiring Enter.
    """
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
    """
    Execute a read-only command and return its stdout.
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

def print_header(title):
    width = 62

    print("╭" + "─" * width + "╮")
    print(f"│ {title:^{width - 2}} │")
    print("╰" + "─" * width + "╯")


def print_section(title):
    print()
    print(f"── {title} " + "─" * max(1, 55 - len(title)))


# ─────────────────────────────────────────────────────────────────────────────
# Check storage
# ─────────────────────────────────────────────────────────────────────────────

def show_disk_usage():
    print_section("Disk")

    usage = shutil.disk_usage("/")

    total = usage.total
    used = usage.used
    free = usage.free

    percentage = (used / total) * 100

    print(f"Filesystem:     /")
    print(f"Total:          {format_size(total)}")
    print(f"Used:           {format_size(used)} ({percentage:.1f}%)")
    print(f"Available:      {format_size(free)}")


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
            size = get_size(path)
            entries.append((size, path))
        except OSError:
            pass

    entries.sort(reverse=True, key=lambda item: item[0])

    for size, path in entries[:15]:
        print(f"{format_size(size):>10}   {path.name}")

    total = get_size(cache_root)

    print()
    print(f"{'Total cache:':>15} {format_size(total)}")


def show_package_cache():
    print_section("Pacman package cache")

    cache_path = Path("/var/cache/pacman/pkg")

    size = get_size(cache_path)

    print(f"/var/cache/pacman/pkg: {format_size(size)}")


def show_journal_usage():
    print_section("System journal")

    output = run_command("journalctl --disk-usage")

    if output:
        print(output)
    else:
        print("Unable to determine journal size.")


def show_orphans():
    print_section("Orphan packages")

    output = run_command("pacman -Qtdq")

    if not output:
        print("No orphan packages found.")
        return

    packages = [
        line.strip()
        for line in output.splitlines()
        if line.strip()
    ]

    print(f"Found: {len(packages)}")
    print()

    for package in packages:
        print(f"  • {package}")


def check_storage():
    clear_screen()

    print_header("CachyOS Storage Check")

    print("\nScanning filesystem...")

    # Move cursor back and redraw cleanly after scanning.
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


# ─────────────────────────────────────────────────────────────────────────────
# Clear cache
# ─────────────────────────────────────────────────────────────────────────────

def clear_directory_contents(path: Path):
    if not path.exists():
        return

    for item in path.iterdir():
        try:
            if item.is_dir() and not item.is_symlink():
                shutil.rmtree(item)
            else:
                item.unlink()

        except OSError as error:
            print(f"  Failed to remove {item}: {error}")


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

    print()

    for path in CACHE_DIRS:
        size_before = get_size(path)

        print(
            f"Clearing {path.name:<12} "
            f"({format_size(size_before)})..."
        )

        clear_directory_contents(path)

    print()
    print("─" * 64)
    print(f"Done. Approximately {format_size(total_size)} cleared.")

    wait_for_key()


# ─────────────────────────────────────────────────────────────────────────────
# Main menu
# ─────────────────────────────────────────────────────────────────────────────

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

if __name__ == "__main__":
    try:
        show_menu()

    except KeyboardInterrupt:
        clear_screen()
        print("Cleanup cancelled.")
