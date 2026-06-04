import io
import time
import queue
import threading
import requests
import chess.pgn
import chess
from stockfish import Stockfish
import ollama

def pgn_fetch_callback(username, year, month):
    """
    Fetches the archives from the Chess.com public API.
    Returns a list of dictionaries with game metadata and PGNs (max 15).
    """
    url = f"https://api.chess.com/pub/player/{username}/games/{year}/{month:02d}"
    headers = {"User-Agent": "DesktopAIChessCoach/4.0 (contact: admin@example.com)"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        games = data.get("games", [])[-15:] # Get the last 15 games
        parsed_games = []
        
        for game in games:
            pgn_str = game.get("pgn", "")
            if pgn_str:
                pgn_io = io.StringIO(pgn_str)
                parsed_game = chess.pgn.read_game(pgn_io)
                white = parsed_game.headers.get("White", "Unknown")
                black = parsed_game.headers.get("Black", "Unknown")
                parsed_games.append({
                    "label": f"{white} vs {black}",
                    "white": white,
                    "black": black,
                    "pgn": pgn_str,
                    "game_obj": parsed_game
                })
        return parsed_games
    except Exception as e:
        print(f"Error fetching games: {e}")
        return []

class PonderWorker:
    """
    Background worker that continuously evaluates the current FEN at increasing depths
    and pushes the results to a thread-safe queue for the GUI.
    """
    def __init__(self, stockfish_path, result_queue, threads=2):
        self.stockfish = Stockfish(path=stockfish_path, parameters={"Threads": threads, "Hash": 256})
        self.result_queue = result_queue
        self.current_fen = None
        self.lock = threading.Lock()
        self.is_running = True
        
        self.thread = threading.Thread(target=self._ponder_loop, daemon=True)
        self.thread.start()

    def update_position(self, fen):
        """Called by the GUI to change the board position."""
        with self.lock:
            self.current_fen = fen

    def stop(self):
        """Safely kills the thread when closing the app."""
        self.is_running = False

    def _ponder_loop(self):
        last_evaluated_fen = None
        current_depth = 10
        max_depth = 26
        
        while self.is_running:
            with self.lock:
                fen_to_eval = self.current_fen
                
            if fen_to_eval is None:
                time.sleep(0.1)
                continue
                
            if fen_to_eval != last_evaluated_fen:
                last_evaluated_fen = fen_to_eval
                current_depth = 10
                self.stockfish.set_fen_position(fen_to_eval)
            
            if current_depth <= max_depth:
                self.stockfish.set_depth(current_depth)
                
                eval_data = self.stockfish.get_evaluation()
                top_moves_uci = self.stockfish.get_top_moves(3)
                
                # Convert UCI to SAN for human-readable lines
                board = chess.Board(last_evaluated_fen)
                top_moves_san = []
                for move in top_moves_uci:
                    try:
                        san_move = board.san(chess.Move.from_uci(move["Move"]))
                        top_moves_san.append(f"{san_move} ({move['Centipawn']/100 if move['Centipawn'] else f'M{move['Mate']}'})")
                    except:
                        top_moves_san.append(move["Move"])

                with self.lock:
                    if self.current_fen == last_evaluated_fen:
                        self.result_queue.put({
                            "fen": last_evaluated_fen,
                            "depth": current_depth,
                            "eval": eval_data,
                            "lines": top_moves_san
                        })
                        current_depth += 2 
            else:
                time.sleep(0.2)

def generate_coach_critique(model_name, previous_eval, current_eval, move_san):
    """
    Synchronous local LLM call via Ollama. It interprets the score shift.
    (This should be wrapped in a thread by the GUI).
    """
    prev_score = previous_eval.get("value", 0) / 100 if previous_eval.get("type") == "cp" else 100
    curr_score = current_eval.get("value", 0) / 100 if current_eval.get("type") == "cp" else 100
    
    score_shift = curr_score - prev_score
    
    if abs(score_shift) > 2.0:
        prompt_context = f"The player played {move_san}. This was a critical blunder, shifting the evaluation by {score_shift:.2f} points. Aggressively explain the tactical mistake."
    else:
        prompt_context = f"The player played {move_san}. The position is relatively stable (shift: {score_shift:.2f}). Briefly explain the positional strategy here."

    prompt = f"You are a master chess coach. Keep your answer under 3 sentences. {prompt_context}"

    try:
        response = ollama.chat(model=model_name, messages=[
            {"role": "system", "content": "You are a concise, insightful desktop chess AI coach."},
            {"role": "user", "content": prompt}
        ])
        return response['message']['content']
    except Exception as e:
        return f"Coach is unavailable. Ensure Ollama is running. Error: {e}"