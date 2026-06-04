"""
gui.py - Event-driven interface container. Implements async thread loops,
massive 600px vector graphics, board flipping, dynamic player labels, and multi-game selection.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import io
import chess
import chess.pgn
import chess.svg
import cairosvg
from PIL import Image, ImageTk

class ChessCoachGUI:
    def __init__(self, root, engine_worker, config):
        self.root = root
        self.worker = engine_worker
        self.config = config
        
        self.root.title("Desktop AI Chess Coach (v4.0.0) - Pro Dashboard")
        self.root.geometry("1300x850")
        self.root.configure(background='#262522')
        
        # State Machinery
        self.current_board = chess.Board()
        self.current_move_index = -1 
        self.move_history_san = []
        self.moves_list = []
        self.boards_cache = [chess.Board()]
        
        self.fetched_games = []
        self.white_name = "Player 1"
        self.black_name = "Player 2"
        
        self.engine_cache = {}  
        self.coach_cache = {}   
        self.board_flipped = False
        
        self._setup_ui_styles()
        self._build_interface_layout()
        self._bind_hardware_signals()
        
        self.update_board_ui()

    def _setup_ui_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#262522')
        style.configure('TLabel', background='#262522', foreground='#ffffff', font=('Helvetica', 11))
        style.configure('TButton', font=('Helvetica', 10, 'bold'), background='#45433f', foreground='#ffffff')
        style.map('TButton', background=[('active', '#5c5a54')])
        style.configure('TCombobox', font=('Helvetica', 10))

    def _build_interface_layout(self):
        # Top Panel Execution Control Bar
        self.top_bar = ttk.Frame(self.root, padding=10)
        self.top_bar.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Label(self.top_bar, text="Chess.com Username:").pack(side=tk.LEFT, padx=5)
        self.username_entry = ttk.Entry(self.top_bar, width=15, font=('Helvetica', 11))
        self.username_entry.insert(0, self.config.get("default_username", ""))
        self.username_entry.pack(side=tk.LEFT, padx=5)
        
        self.fetch_btn = ttk.Button(self.top_bar, text="Fetch Recent Games", command=self.trigger_fetch_games)
        self.fetch_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(self.top_bar, text="Select Game:").pack(side=tk.LEFT, padx=(20, 5))
        self.game_selector = ttk.Combobox(self.top_bar, state="readonly", width=40)
        self.game_selector.pack(side=tk.LEFT, padx=5)
        self.game_selector.bind("<<ComboboxSelected>>", self.on_game_selected)
        
        self.status_lbl = ttk.Label(self.top_bar, text="Ready.", foreground='#999999')
        self.status_lbl.pack(side=tk.LEFT, padx=15)

        # Operational Workspace
        self.workspace = ttk.Frame(self.root, padding=10)
        self.workspace.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Left Column: Evaluation, Names, Board, and Physical Controls
        self.left_panel = ttk.Frame(self.workspace)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=5)

        self.board_wrapper = ttk.Frame(self.left_panel)
        self.board_wrapper.pack(side=tk.TOP)

        self.eval_canvas = tk.Canvas(self.board_wrapper, width=25, height=600, bg='#312e2b', highlightthickness=0)
        self.eval_canvas.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        self._draw_empty_eval_bar()

        # Board container housing the Player Names + The Vector Image
        self.board_container = tk.Frame(self.board_wrapper, bg='#262522')
        self.board_container.pack(side=tk.LEFT)

        self.top_player_lbl = tk.Label(self.board_container, bg='#262522', fg='#ffffff', font=('Helvetica', 12, 'bold'))
        self.top_player_lbl.pack(side=tk.TOP, pady=(0, 5))

        self.board_label = tk.Label(self.board_container, bg='#262522')
        self.board_label.pack(side=tk.TOP)

        self.bottom_player_lbl = tk.Label(self.board_container, bg='#262522', fg='#ffffff', font=('Helvetica', 12, 'bold'))
        self.bottom_player_lbl.pack(side=tk.TOP, pady=(5, 0))

        # Physical Control Buttons
        self.controls_frame = ttk.Frame(self.left_panel)
        self.controls_frame.pack(side=tk.TOP, fill=tk.X, pady=(15, 10))
        
        self.prev_btn = ttk.Button(self.controls_frame, text="◄ Prev Move", command=self.handle_prev_move)
        self.prev_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        self.next_btn = ttk.Button(self.controls_frame, text="Next Move ►", command=self.handle_next_move)
        self.next_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        self.flip_btn = ttk.Button(self.controls_frame, text="Flip Board ⇅", command=self.toggle_flip)
        self.flip_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # Stockfish Readouts
        self.eval_text_lbl = tk.Label(self.left_panel, text="Eval: +0.00", bg='#262522', fg='#55ff55', font=('Helvetica', 14, 'bold'), anchor='w')
        self.eval_text_lbl.pack(side=tk.TOP, fill=tk.X, pady=(10, 2))

        self.best_moves_lbl = tk.Label(self.left_panel, text="Engine Best: N/A", bg='#262522', fg='#bbbbbb', font=('Helvetica', 11), anchor='w')
        self.best_moves_lbl.pack(side=tk.TOP, fill=tk.X)

        # Right Column: AI Coach Feedback
        self.right_panel = ttk.Frame(self.workspace)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20)
        
        self.coach_log = scrolledtext.ScrolledText(
            self.right_panel, wrap=tk.WORD, font=('Consolas', 12),
            bg='#1e1e1c', fg='#f1f1f1', insertbackground='white', relief=tk.FLAT, padx=10, pady=10
        )
        self.coach_log.pack(fill=tk.BOTH, expand=True, pady=5)
        self.write_log("System ready. Fetch games and select one to begin.", "system_notif")

    def _bind_hardware_signals(self):
        self.root.bind("<Left>", self.handle_prev_move)
        self.root.bind("<Right>", self.handle_next_move)

    def toggle_flip(self):
        self.board_flipped = not self.board_flipped
        self.update_board_ui()

    def write_log(self, text, alert_style=None):
        self.coach_log.configure(state=tk.NORMAL)
        self.coach_log.delete('1.0', tk.END)
        
        if alert_style == "blunder_alert":
            self.coach_log.insert(tk.END, f"⚠️ AI Coach Alert\n\n{text}\n", "blunder")
            self.coach_log.tag_config("blunder", foreground="#ff5555", font=('Consolas', 13, 'bold'))
        elif alert_style == "system_notif":
            self.coach_log.insert(tk.END, f"⚙️ {text}\n", "system")
            self.coach_log.tag_config("system", foreground="#888888", font=('Consolas', 12, 'italic'))
        else:
            self.coach_log.insert(tk.END, f"♟️ AI Coach Positional Breakdown\n\n{text}\n", "normal")
            self.coach_log.tag_config("normal", foreground="#f1f1f1", font=('Consolas', 13))
            
        self.coach_log.configure(state=tk.DISABLED)

    def trigger_fetch_games(self):
        username = self.username_entry.get().strip()
        if not username: return
        self.status_lbl.configure(text="Fetching archives...", foreground="#ffff55")
        self.fetch_btn.configure(state=tk.DISABLED)
        threading.Thread(target=self._async_network_pipeline, args=(username,), daemon=True).start()

    def _async_network_pipeline(self, username):
        games_list = self.worker.pgn_fetch_callback(username)
        if not games_list:
            self.root.after(0, self._on_fetch_failed)
        else:
            self.root.after(0, lambda: self._on_fetch_success(games_list))

    def _on_fetch_failed(self):
        self.fetch_btn.configure(state=tk.NORMAL)
        self.status_lbl.configure(text="Profile sync failed.", foreground="#ff5555")
        self.write_log("Error: Profile lookup failed. Verify network access.", "system_notif")

    def _on_fetch_success(self, games_list):
        self.fetch_btn.configure(state=tk.NORMAL)
        self.status_lbl.configure(text=f"Loaded {len(games_list)} games.", foreground="#55ff55")
        self.fetched_games = games_list
        
        # Populate the dropdown UI
        labels = [g["label"] for g in self.fetched_games]
        self.game_selector['values'] = labels
        if labels:
            self.game_selector.current(0)
            self.load_selected_game(0)

    def on_game_selected(self, event):
        idx = self.game_selector.current()
        if idx >= 0:
            self.load_selected_game(idx)

    def load_selected_game(self, index):
        game_data = self.fetched_games[index]
        self.white_name = game_data["white"]
        self.black_name = game_data["black"]
        
        pgn_io = io.StringIO(game_data["pgn"])
        game = chess.pgn.read_game(pgn_io)
        if not game: return

        self.moves_list = list(game.mainline_moves())
        self.boards_cache = []
        self.move_history_san = []
        
        trace_board = game.board()
        self.boards_cache.append(trace_board.copy())
        
        for move in self.moves_list:
            self.move_history_san.append(trace_board.san(move))
            trace_board.push(move)
            self.boards_cache.append(trace_board.copy())
            
        self.current_move_index = -1
        self.engine_cache.clear()
        self.coach_cache.clear()
        
        self.update_board_ui()
        self._dispatch_evaluation()

    def handle_prev_move(self, event=None):
        if self.current_move_index > -1:
            self.current_move_index -= 1
            self.update_board_ui()
            self._dispatch_evaluation()

    def handle_next_move(self, event=None):
        if self.current_move_index < len(self.boards_cache) - 2:
            self.current_move_index += 1
            self.update_board_ui()
            self._dispatch_evaluation()

    def update_board_ui(self):
        # Update Player Names based on orientation
        if self.board_flipped:
            self.top_player_lbl.config(text=f"♔ White: {self.white_name}")
            self.bottom_player_lbl.config(text=f"♚ Black: {self.black_name}")
        else:
            self.top_player_lbl.config(text=f"♚ Black: {self.black_name}")
            self.bottom_player_lbl.config(text=f"♔ White: {self.white_name}")

        self.current_board = self.boards_cache[self.current_move_index + 1]
        try:
            last_played_move = None
            if 0 <= self.current_move_index < len(self.moves_list):
                last_played_move = self.moves_list[self.current_move_index]
                
            orientation = chess.BLACK if self.board_flipped else chess.WHITE
            
            svg_data = chess.svg.board(
                board=self.current_board, 
                size=600, 
                lastmove=last_played_move,
                orientation=orientation
            )
            png_bytes = cairosvg.svg2png(bytestring=svg_data.encode('utf-8'))
            img = Image.open(io.BytesIO(png_bytes))
            render = ImageTk.PhotoImage(img)
            self.board_label.configure(image=render)
            self.board_label.image = render
        except Exception as e:
            self.write_log(f"Graphics error: {str(e)}", "system_notif")

    def _dispatch_evaluation(self):
        fen = self.current_board.fen()
        idx = self.current_move_index
        
        if fen not in self.engine_cache:
            self.eval_text_lbl.config(text="Eval: ...")
            self.best_moves_lbl.config(text="Engine Best: Calculating...")
            threading.Thread(target=self._async_stockfish_worker, args=(fen,), daemon=True).start()
        else:
            self._apply_engine_data(fen)
            
        if idx >= 0:
            if idx not in self.coach_cache:
                self.write_log(f"Analyzing {self.move_history_san[idx]}...", "system_notif")
                threading.Thread(target=self._async_coach_worker, args=(idx,), daemon=True).start()
            else:
                self.write_log(self.coach_cache[idx], "blunder_alert" if "CRITICAL" in self.coach_cache[idx] else None)
        else:
            self.write_log("Initial position. Press Next Move (►) to step forward.", "system_notif")

    def _async_stockfish_worker(self, fen):
        board = chess.Board(fen)
        data = self.worker.get_analysis(board)
        self.engine_cache[fen] = data
        self.root.after(0, lambda: self._apply_engine_data(fen))

    def _apply_engine_data(self, fen):
        if self.current_board.fen() == fen:
            data = self.engine_cache[fen]
            self._render_eval_bar(data["score"])
            self.eval_text_lbl.config(text=f"Eval: {data['eval_text']}")
            self.best_moves_lbl.config(text=f"Engine Best: {data['top_moves']}")

    def _async_coach_worker(self, idx):
        prev_board = self.boards_cache[idx]
        target_board = self.boards_cache[idx + 1]
        move_san = self.move_history_san[idx]
        
        prev_data = self.worker.get_analysis(prev_board)
        curr_data = self.worker.get_analysis(target_board)
        s_prev, s_curr = prev_data["score"], curr_data["score"]
        
        if s_prev is None or s_curr is None:
            self.root.after(0, lambda: self._on_coach_finalized(idx, "Engine bypassed."))
            return

        score_shift = s_curr - s_prev
        is_blunder = (score_shift < -1.5) if prev_board.turn == chess.WHITE else (score_shift > 1.5)
        role_str = "White" if prev_board.turn == chess.WHITE else "Black"
        game_desc = f"Move {idx + 1}: {role_str} played '{move_san}'."
        
        coach_critique = self.worker.generate_coach_critique(
            board_fen=target_board.fen(),
            game_state=game_desc,
            role_context=role_str,
            move_san=move_san,
            is_blunder=is_blunder,
            score_shift=score_shift
        )
        self.root.after(0, lambda: self._on_coach_finalized(idx, coach_critique))

    def _on_coach_finalized(self, idx, critique_text):
        self.coach_cache[idx] = critique_text
        if self.current_move_index == idx:
            is_error = "CRITICAL OVERRIDE" in critique_text or "[local ai engine offline]" in critique_text.lower()
            self.write_log(critique_text, "blunder_alert" if is_error else None)

    def _draw_empty_eval_bar(self):
        self.eval_canvas.delete("all")
        self.eval_canvas.create_rectangle(0, 0, 25, 600, fill="#45433f", outline="")
        self.eval_canvas.create_line(0, 300, 25, 300, fill="#999999", width=2)

    def _render_eval_bar(self, score):
        self.eval_canvas.delete("all")
        if score is None:
            self._draw_empty_eval_bar()
            return
            
        clamped = max(-5.0, min(5.0, score))
        percentage = (clamped + 5.0) / 10.0
        white_height = int(600 * percentage)
        
        self.eval_canvas.create_rectangle(0, 0, 25, 600 - white_height, fill="#111111", outline="")
        self.eval_canvas.create_rectangle(0, 600 - white_height, 25, 600, fill="#ffffff", outline="")
        self.eval_canvas.create_line(0, 300, 25, 300, fill="#ff5555", width=1.5)