readme_content = """# ♟️ Desktop AI Chess Coach

**Version:** 4.0.0 (Pro Dashboard Edition)

A local, hardware-accelerated desktop application that analyzes Chess.com games. It bridges the gap between raw engine calculations and human understanding by pairing a native **Stockfish** binary for precise position evaluation with a local **Large Language Model (Ollama)** to generate natural language, human-like coaching critiques.

---

## ✨ Features

- **Multi-Game Import:** Automatically fetches up to the last 15 games from the current month of any public Chess.com profile.
- **Interactive Game Selector:** Dropdown menu to dynamically switch between downloaded games.
- **Pro Dashboard UI:** - Massive 600x600px high-fidelity vector chess board.
  - Dynamic player nametags (White vs. Black) that swap when the board is flipped.
  - Physical on-screen buttons for Next Move, Prev Move, and Flip Board (keyboard arrow keys also supported).
- **Dual-Engine Evaluation:**
  - **Stockfish Metrics:** Real-time evaluation bar, centipawn/mate score, and top 3 best calculated lines in human-readable Algebraic Notation (SAN).
  - **AI Coach:** Asynchronous local LLM calls that interpret Stockfish score shifts, explaining positional strategies for standard moves and aggressively flagging critical tactical blunders.

---

## 🏗️ Architecture & Tech Stack

- **Language:** Python 3.x
- **UI Framework:** `tkinter` (Native Python GUI) + `ttk` (Themed widgets)
- **Chess Logic:** `python-chess` (Move generation, PGN parsing, FEN management)
- **Vector Graphics:** `cairosvg`, `cairocffi`, `Pillow` (SVG to PNG rendering)
- **Network:** `requests` (Chess.com Public API)
- **Engines:** - `stockfish` (Python wrapper for the local Stockfish executable)
  - `ollama` (Local LLM API for AI coaching generation)

---

## 🛠️ Setup & Installation

### 1. Prerequisites
- **Python 3.8+** installed.
- **Stockfish:** Download the latest [Stockfish executable](https://stockfishchess.org/download/) for your OS.
- **Ollama:** Install [Ollama](https://ollama.ai/) and pull your preferred model (e.g., `ollama run llama3`).

### 2. Windows Rendering Fix (Cairo/GTK3)
By default, Windows cannot render SVG vector files natively via Cairo. This app relies on the GTK3 runtime. 
1. Install the [GTK3-Runtime Win64](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases).
2. The application (`main.py`) is pre-configured to explicitly inject `C:\\Program Files\\GTK3-Runtime Win64\\bin` into the environment variable upon launch. *Note: Ensure your installation path matches this, or update `main.py` accordingly.*

### 3. Configuration
Before running the application, update the `PRODUCTION_CONFIG` block inside `main.py`:
- Map the absolute path to your local Stockfish `.exe`.
- Specify your local LLM model name (e.g., `'llama3'`).

### 4. Run the Application


<img width="1880" height="1018" alt="image" src="https://github.com/user-attachments/assets/46d9c395-0f4c-4b66-ac3a-855799113cb7" />
