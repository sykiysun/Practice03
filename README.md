# Practice03
Google Github Practice

I am editing the README file. Adding some more details about the project description.

## Blackjack Card Counting Practice App

This repository now includes a Python UI app for practicing **Hi-Lo card counting**
with an **8-deck blackjack shoe** and a **cut card near half penetration**.

### Run

```bash
python3 blackjack_counter_app.py
```

### Modes and controls

The app has two tabs:

1. **Counting Drill**  
   - **Deal Card** (or press `Space`)
   - Submit count value for shown card:
     - `-1` for 10, J, Q, K, A
     - `0` for 7, 8, 9
     - `+1` for 2, 3, 4, 5, 6
   - Keyboard shortcuts:
     - `-` for `-1`
     - `0` for `0`
     - `+` for `+1` (or `=`)

2. **Blackjack Table**
   - Set a bet amount and click **Deal Round**
   - Play hands with clickable buttons:
     - **Hit**
     - **Stand**
     - **Double**
     - **Surrender**
   - Tracks bankroll, current bet, wins/losses/pushes, and shoe/count stats.

### Counting values (Hi-Lo)

- `-1` for 10, J, Q, K, A
- `0` for 7, 8, 9
- `+1` for 2, 3, 4, 5, 6

### Tkinter requirement

The UI uses the Python standard `tkinter` module. If your system Python was built
without Tk support, install the OS package for Tkinter first.

