"""
engines.py - Stateless calculation layer handles Chess.com REST APIs,
native Stockfish binaries, and prompt engineering orchestration with Ollama.
"""

import io
import requests
import chess
import chess.pgn
import ollama
from stockfish import Stockfish

class ChessEngineWorker:
    def __init__(self, stockfish_path="stockfish", model_name="llama3", depth=12):
        self.model_name = model_name
        self.depth = depth
        self.stockfish = None
        
        # Defensive Subprocess Validation Path
        if stockfish_path:
            try:
                self.stockfish = Stockfish(path=stockfish_path, depth=self.depth)
            except (FileNotFoundError, Exception):
                # Fallback: Allows structural application navigation without system crashes
                self.stockfish = None

    def pgn_fetch_callback(self, username):
        """
        Fetches the latest completed game PGN for a given Chess.com user profile.
        Implements defensive transport validation blocks for HTTP limits.
        """
        try:
            headers = {"User-Agent": "DesktopAIChessCoach/4.0.0 (contact: admin@local.ai)"}
            url = f"https://api.chess.com/pub/player/{username}/games/archives"
            
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code != 200:
                return None
                
            archives = res.json().get("archives", [])
            if not archives:
                return None
            
            # Extract historical match logs from the latest operational month archive
            latest_month_url = archives[-1]
            res_games = requests.get(latest_month_url, headers=headers, timeout=8)
            if res_games.status_code != 200:
                return None
                
            games = res_games.json().get("games", [])
            if not games:
                return None
                
            # Return the raw PGN record array block of the most recently finalized game
            return games[-1].get("pgn", None)
        except Exception:
            return None

    def get_absolute_score(self, board):
        """
        Calculates position evaluations normalized to White's physical perspective.
        Adapts side-to-move relative scoring to unified evaluation metrics.
        """
        if not self.stockfish:
            return None
        try:
            self.stockfish.set_fen_position(board.fen())
            ev = self.stockfish.get_evaluation()
            
            val = ev['value']
            if ev['type'] == 'mate':
                score = 10.0 if val > 0 else -10.0
            else:
                score = float(val) / 100.0
                
            # If the engine uses side-to-move perspective, invert it when it's Black's turn
            if board.turn == chess.BLACK:
                score = -score
            return score
        except Exception:
            return None

    def generate_coach_critique(self, board_fen, game_state, role_context, move_san, is_blunder, score_shift):
        """
        Assembles structural tokens strictly using the Token Compilation Template
        to execute atomic instructions without text completion hallucinations.
        """
        prompt = (
            f"You are an elite International Master chess coach. Current Position (FEN): {board_fen}.\n"
            f"Context: {game_state} The player driving pieces for {role_context} just played '{move_san}'.\n"
        )

        if is_blunder:
            prompt += (
                f"CRITICAL OVERRIDE: This move is an outright tactical blunder! The engine score swung by "
                f"{abs(score_shift):.2f} pawns against them. Explicitly explain the immediate tactical punishment "
                f"or loose piece vulnerability created by this blunder in exactly 2 concise sentences."
            )
        else:
            prompt += (
                f"Explain the strategic positional intention behind '{move_san}' (e.g., active piece development, "
                f"securing an open file, creating space, or forcing tactical weaknesses) in exactly 2 clear sentences."
            )

        try:
            response = ollama.chat(model=self.model_name, messages=[{'role': 'user', 'content': prompt}])
            return response['message']['content'].strip()
        except Exception:
            # Resilient Model Transport Interception Path
            return f"[Local AI engine offline: Run 'ollama run {self.model_name}' in your terminal to fix]"