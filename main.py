"""
main.py - Configuration Injector Core setup handles initial boot sequences 
and runtime overrides before instantiating the UI framework.
"""

import tkinter as tk
import sys
from engines import ChessEngineWorker
from gui import ChessCoachGUI
import tkinter as tk
import sys
import os

# --- NEW WINDOWS FIX: Force Python to see the Cairo Graphics DLLs ---
if os.name == 'nt':
    gtk_path = r"C:\Program Files\GTK3-Runtime Win64\bin"
    if os.path.exists(gtk_path):
        # This bypasses the Python 3.8+ Windows security block
        os.add_dll_directory(gtk_path)
# 


# Add a global configuration dictionary for easy adjustments and overrides
PRODUCTION_CONFIG = {
    "stockfish_path": r"C:\Program Files\stockfish\stockfish-windows-x86-64-avx2.exe", # Adjust this path as needed for your system
    "model_name": "gemma4:26b",  
    "depth": 13,                     
    "default_username": "MagnusCarlsen"
}

def main():
    # Parse manual command-line config adjustments
    if len(sys.argv) > 1:
        PRODUCTION_CONFIG["default_username"] = sys.argv[1]
    if len(sys.argv) > 2:
        PRODUCTION_CONFIG["stockfish_path"] = sys.argv[2]

    print("[Bootstrap] Initializing background engines & processing paths...")
    worker_node = ChessEngineWorker(
        stockfish_path=PRODUCTION_CONFIG["stockfish_path"],
        model_name=PRODUCTION_CONFIG["model_name"],
        depth=PRODUCTION_CONFIG["depth"]
    )

    print("[Bootstrap] Handoff to interface event-loop container active.")
    app_root = tk.Tk()
    _ = ChessCoachGUI(app_root, worker_node, PRODUCTION_CONFIG)
    app_root.mainloop()

if __name__ == "__main__":
    main()