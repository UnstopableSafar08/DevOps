A **complete tmux cheatsheet including installation instructions for both Ubuntu and EL9**.

---

# TMUX CHEATSHEET & INSTALLATION GUIDE

## 1. Installation

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y tmux
tmux -V
# Should show: tmux 3.x
```

### EL9 (RHEL 9, Oracle Linux 9, Rocky Linux 9)

```bash
sudo dnf install -y tmux
tmux -V
# Should show: tmux 3.x
```

> Optional: For latest tmux on EL9, you can build from source:

```bash
cd /usr/local/src
wget https://github.com/tmux/tmux/releases/download/3.3a/tmux-3.3a.tar.gz
tar -xzf tmux-3.3a.tar.gz
cd tmux-3.3a
sudo dnf install -y gcc make ncurses-devel libevent-devel
./configure && make
sudo make install
tmux -V
```

---

## 2. Starting tmux

```bash
tmux
tmux new -s session_name
tmux ls
tmux attach -t session_name
tmux detach
tmux kill-session -t session_name
tmux kill-server
```

---

## 3. Windows

```bash
Ctrl+b c        # Create a new window
Ctrl+b ,        # Rename current window
Ctrl+b w        # List all windows
Ctrl+b n        # Next window
Ctrl+b p        # Previous window
Ctrl+b &        # Kill current window
Ctrl+b <number> # Switch to window <number>
```

---

## 4. Panes

```bash
Ctrl+b "        # Split pane horizontally
Ctrl+b %        # Split pane vertically
Ctrl+b o        # Switch to next pane
Ctrl+b ;        # Switch to last active pane
Ctrl+b x        # Kill current pane
Ctrl+b {        # Move current pane left/up
Ctrl+b }        # Move current pane right/down
Ctrl+b q        # Show pane numbers
Ctrl+b z        # Toggle zoom (maximize pane)
```

---

## 5. Resizing Panes

```bash
Ctrl+b :resize-pane -L 10   # Resize left 10 cells
Ctrl+b :resize-pane -R 10   # Resize right 10 cells
Ctrl+b :resize-pane -U 10   # Resize up 10 cells
Ctrl+b :resize-pane -D 10   # Resize down 10 cells
```

* Or interactively: `Ctrl+b` + hold `Ctrl` + arrow keys

---

## 6. Copy Mode & Scrolling

```bash
Ctrl+b [      # Enter copy/scroll mode
q             # Exit copy mode
Space         # Start selection
Enter         # Copy selection
Ctrl+b ]      # Paste buffer
PgUp / PgDn   # Scroll in copy mode
/             # Search forward
?             # Search backward
```

---

## 7. Buffers & Copy-Paste

```bash
tmux show-buffer         # Show buffer content
tmux list-buffers        # List all saved buffers
tmux save-buffer file    # Save buffer to file
tmux paste-buffer        # Paste buffer
```

---

## 8. Session Management & Misc

```bash
Ctrl+b d                 # Detach session
Ctrl+b t                 # Show time
Ctrl+b ?                 # Show key bindings
tmux source-file ~/.tmux.conf  # Reload config
Ctrl+b r                 # Redraw screen
```

---

## 9. Configuration Tips (~/.tmux.conf)

```bash
# Change prefix to Ctrl+a
set -g prefix C-a
unbind C-b
bind C-a send-prefix

# Enable mouse support
set -g mouse on

# Start windows at 1
set -g base-index 1

# Split panes with | and -
bind | split-window -h
bind - split-window -v

# Enable true color
set -g default-terminal "tmux-256color"
```

---

## 10. Advanced / Useful Tricks

```bash
tmux attach -d -t session_name       # Attach, detach if already attached
tmux rename-session new_name          # Rename current session
tmux pipe-pane 'cat >> ~/pane.log'    # Log pane output
tmux setw synchronize-panes on        # Send input to all panes simultaneously
tmux display-message -p '#{session_name}:#{window_index}.#{pane_index}' # Show current pane info
```

---
