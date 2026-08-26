<div align="center">

# CachyOS Cleanup 🧹

**A lightweight interactive storage and cache cleanup utility for CachyOS and Arch Linux.**

<p>
  <img src="https://img.shields.io/github/last-commit/javiiervm/cachyos-cleanup/main" alt="Last Commit" />
  <img src="https://img.shields.io/badge/platform-linux-lightgrey" alt="Platform Support" />
  <img src="https://img.shields.io/github/issues/javiiervm/cachyos-cleanup" alt="Issues" />
  <img src="https://img.shields.io/github/stars/javiiervm/cachyos-cleanup" alt="Stars" />
  <br />
  <img src="https://img.shields.io/badge/python-3.10%2B-yellow?logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/CachyOS-supported-blue" alt="CachyOS" />
  <img src="https://img.shields.io/badge/Arch_Linux-compatible-1793D1?logo=arch-linux&logoColor=white" alt="Arch Linux" />
</p>

</div>

**CachyOS Cleanup** is a small terminal utility designed to simplify routine storage maintenance on CachyOS and Arch-based systems. It provides an interactive single-key interface for inspecting disk usage and safely clearing selected application and package-manager caches.

The project follows a conservative approach: **inspect first, confirm second, delete only known cache data**.

## Features

* **Storage Overview:** Displays total, used, and available filesystem space.
* **Home Directory Analysis:** Shows the largest files and directories inside the user's home directory.
* **Cache Analysis:** Lists the largest entries inside `~/.cache`.
* **Pacman Cache Monitoring:** Reports the current size of `/var/cache/pacman/pkg`.
* **System Journal Monitoring:** Displays disk usage from the systemd journal.
* **Orphan Package Detection:** Uses Pacman to identify installed dependencies that are no longer required.
* **Selective Cache Cleanup:** Clears known regenerable caches from Yay, Paru, Spotify, and Firefox.
* **Safety Confirmation:** Shows how much space will be recovered before deleting anything.
* **Single-Key Interface:** Menu options and confirmations work instantly without requiring Enter.
* **No Root Required for User Cache Cleanup:** Current cleanup operations only modify cache directories inside the user's home directory.

## Tech Stack

* **Language:** Python 3
* **Package Manager Integration:** Pacman
* **System Information:** systemd / `journalctl`
* **Terminal Input:** `termios` and `tty`
* **Target Systems:** CachyOS and Arch Linux

---

## Getting Started

### Prerequisites

The utility requires:

* Python 3
* Pacman
* systemd / `journalctl`
* A Linux terminal supporting `termios` and `tty`

Most CachyOS installations already provide these dependencies.

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/javiiervm/CachyOS-Cleanup.git
   cd CachyOS-Cleanup
   ```

2. Make the script executable:

   ```bash
   chmod +x cleanup.py
   ```

3. Run it:

   ```bash
   ./cleanup.py
   ```

### Recommended Setup

To make the utility available from anywhere, copy it to `~/.local/bin`:

```bash
mkdir -p ~/.local/bin
cp cleanup.py ~/.local/bin/cleanup.py
chmod +x ~/.local/bin/cleanup.py
```

Make sure `~/.local/bin` is included in your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

For Zsh, add the following alias to `~/.zshrc`:

```bash
alias cleanup="$HOME/.local/bin/cleanup.py"
```

Reload the shell:

```bash
source ~/.zshrc
```

You can now launch the utility from anywhere with:

```bash
cleanup
```

---

## Usage

Running `cleanup` opens the interactive menu:

```text
╭──────────────────────────────────────────────────────────────╮
│                       CachyOS Cleanup                        │
╰──────────────────────────────────────────────────────────────╯

  [1]  Check storage
  [2]  Clear Cache

  [0]  Exit

Select an option:
```

Menu controls use direct key input, so **Enter is not required**.

### Check Storage

Press:

```text
1
```

to perform a read-only storage analysis.

The utility reports:

* Root filesystem usage
* Largest home directory entries
* Largest user caches
* Pacman package cache size
* systemd journal size
* Pacman orphan packages

No files or packages are modified during this operation.

### Clear Cache

Press:

```text
2
```

to inspect and clear the configured user caches.

The current version manages:

```text
~/.cache/yay
~/.cache/paru
~/.cache/spotify
~/.cache/mozilla
```

Before deleting anything, the utility displays the size of each cache and the total amount of recoverable storage:

```text
Clear Cache

  10.8 GiB   /home/user/.cache/yay
   1.2 GiB   /home/user/.cache/paru
   5.6 GiB   /home/user/.cache/spotify
   1.1 GiB   /home/user/.cache/mozilla

Total removable cache: 18.7 GiB

Clear these caches? [y/N]
```

Press `y` to continue or any other key to cancel.

---

## What Gets Deleted?

Only the **contents** of explicitly configured cache directories are removed.

### Yay

```text
~/.cache/yay/*
```

Removes downloaded AUR build files and cached repositories.

Installed packages remain untouched, although Yay may need to download or rebuild packages again in the future.

### Paru

```text
~/.cache/paru/*
```

Removes cached AUR build data used by Paru.

Installed packages are not removed.

### Spotify

```text
~/.cache/spotify/*
```

Removes locally cached Spotify data.

Account information, playlists, followed artists, and the user's Spotify library are not affected.

### Firefox

```text
~/.cache/mozilla/*
```

Removes Firefox cache data.

Firefox profiles and persistent browser data stored under `~/.mozilla` are intentionally left untouched.

---

## Safety

CachyOS Cleanup is intentionally designed to avoid aggressive or opaque cleanup behavior.

* Storage scans are **read-only**.
* Only explicitly configured cache directories can be cleared.
* Cache size is displayed before deletion.
* Destructive actions require confirmation.
* The current cleaner does not use `sudo`.
* Personal files and application configuration directories are not intentionally modified.
* Pacman orphan packages are currently **detected but not automatically removed**.

The tool intentionally avoids commands such as:

```bash
sudo pacman -Scc
```

or unrestricted deletion of entire configuration directories.

---

## Project Structure

```text
CachyOS-Cleanup/
├── cleanup.py       # Interactive storage and cleanup utility
└── README.md        # Project documentation
```

The current project deliberately keeps the implementation small and self-contained.

---

## Configuration

Cache targets are defined in `cleanup.py`:

```python
CACHE_DIRS = [
    HOME / ".cache" / "yay",
    HOME / ".cache" / "paru",
    HOME / ".cache" / "spotify",
    HOME / ".cache" / "mozilla",
]
```

Additional directories can be added if their contents are known to be safely regenerable.

Avoid adding application configuration or persistent data directories.

---

## Roadmap

Planned or potential additions include:

* Pacman package cache cleanup
* Orphan package inspection and optional removal
* AUR package maintenance
* systemd journal cleanup
* `ncdu` integration for interactive disk exploration
* Btrfs snapshot inspection
* Configurable cleanup targets
* Detailed before/after storage reports
* Full system cleanup workflow

Potentially destructive operations should remain clearly separated from read-only diagnostics and require explicit confirmation.

---

## Contributing

Contributions, suggestions, and bug reports are welcome.

When adding new cleanup operations, they should:

* Clearly indicate what data will be removed.
* Prefer read-only analysis before deletion.
* Show the affected storage when possible.
* Require confirmation for destructive actions.
* Avoid deleting personal files or persistent configuration by default.

---

## License

This project is open source and can be distributed under the terms of the repository's license.
