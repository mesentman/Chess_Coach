"""
gui.py - Event-driven interface container. Implements safe asynchronous callback execution loops,
isolated threading structures, vector rendering pipelines, and manual board navigation.
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
        
        self.root.title("Desktop AI Chess Coach (v4.0.0)")
        self.root.geometry("1050x650")
        self.root.configure(background='#262522')
        
        # State Machinery Track Containers
        self.current_board = chess.Board()
        self.current_move_index = -1 
        self.move_history_san = []
        self.moves_list = []
        self.boards_cache = [chess.Board()]
        self.analysis_cache = {}  # Format: index -> (raw_score_val, descriptive_critique_string)
        
        self._setup_ui_styles()
        self._build_interface_layout()
        self._bind_hardware_signals()
        
        # Render initial empty layout state
        self.update_board_ui()

    def _setup_ui_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#262522')
        style.configure('TLabel', background='#262522', foreground='#ffffff', font=('Helvetica', 11))
        style.configure('TButton', font=('Helvetica', 10, 'bold'), background='#45433f', foreground='#ffffff')
        style.map('TButton', background=[('active', '#5c5a54')])

    def _build_interface_layout(self):
        # Top Panel Execution Control Bar
        self.top_bar = ttk.Frame(self.root, padding=10)
        self.top_bar.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Label(self.top_bar, text="Chess.com Username:").pack(side=tk.LEFT, padx=5)
        self.username_entry = ttk.Entry(self.top_bar, width=18, font=('Helvetica', 11))
        self.username_entry.insert(0, self.config.get("default_username", ""))
        self.username_entry.pack(side=tk.LEFT, padx=5)
        
        self.fetch_btn = ttk.Button(self.top_bar, text="Fetch Latest Game", command=self.trigger_fetch_game)
        self.fetch_btn.pack(side=tk.LEFT, padx=5)
        
        self.status_lbl = ttk.Label(self.top_bar, text="Ready.", foreground='#999999')
        self.status_lbl.pack(side=tk.LEFT, padx=15)

        # Operational Workspace Splits
        self.workspace = ttk.Frame(self.root, padding=10)
        self.workspace.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Left Column Stack: Evaluation Metric + Rendered Canvas Vector Matrix
        self.left_panel = ttk.Frame(self.workspace)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5)

        self.eval_canvas = tk.Canvas(self.left_panel, width=25, height=400, bg='#312e2b', highlightthickness=0)
        self.eval_canvas.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        self._draw_empty_eval_bar()

        self.board_label = tk.Label(self.left_panel, bg='#262522')
        self.board_label.pack(side=tk.LEFT)

        # Right Column Stack: Navigation Logs + Contextual Coach Feedback Box
        self.right_panel = ttk.Frame(self.workspace)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        ttk.Label(self.right_panel, text="AI Coach Analysis Log", font=('Helvetica', 12, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        self.coach_log = scrolledtext.ScrolledText(
            self.right_panel, wrap=tk.WORD, font=('Consolas', 11),
            bg='#1e1e1c', fg='#f1f1f1', insertbackground='white', relief=tk.FLAT
        )
        self.coach_log.pack(fill=tk.BOTH, expand=True, pady=5)
        self.write_log("System ready. Import a game profile to start the technical review loop.")

        # Lower Help Label Hint Area
        self.hint_lbl = ttk.Label(self.root, text="Keyboard Mapping: ◄ Left Arrow (Prev Position) | Right Arrow (Next Position) ►", 
                                  font=('Helvetica', 10, 'italic'), foreground='#777777')
        self.hint_lbl.pack(side=tk.BOTTOM, pady=8)

    def _bind_hardware_signals(self):
        self.root.bind("<Left>", self.handle_prev_move)
        self.root.bind("<Right>", self.handle_next_move)

    def write_log(self, text, alert_style=None):
        self.coach_log.configure(state=tk.NORMAL)
        if alert_style == "blunder_alert":
            self.coach_log.insert(tk.END, f"\n⚠️ {text}\n", "blunder")
            self.coach_log.tag_config("blunder", foreground="#ff5555", font=('Consolas', 11, 'bold'))
        elif alert_style == "system_notif":
            self.coach_log.insert(tk.END, f"\n⚙️ {text}\n", "system")
            self.coach_log.tag_config("system", foreground="#55ff55", font=('Consolas', 11))
        else:
            self.coach_log.insert(tk.END, f"\n{text}\n")
        self.coach_log.see(tk.END)
        self.coach_log.configure(state=tk.DISABLED)

    def trigger_fetch_game(self):
        username = self.username_entry.get().strip()
        if not username:
            self.status_lbl.configure(text="Error: Missing entry key details.", foreground="#ff5555")
            return
        
        self.status_lbl.configure(text="Downloading game arrays from Chess.com network...", foreground="#ffff55")
        self.fetch_btn.configure(state=tk.DISABLED)
        
        # Fork Network Operations directly to background workers
        threading.Thread(target=self._async_network_pipeline, args=(username,), daemon=True).start()

    def _async_network_pipeline(self, username):
        pgn_text = self.worker.pgn_fetch_callback(username)
        if not pgn_text:
            self.root.after(0, self._on_fetch_failed)
            return
        self.root.after(0, lambda: self._on_fetch_success(pgn_text))

    def _on_fetch_failed(self):
        self.fetch_btn.configure(state=tk.NORMAL)
        self.status_lbl.configure(text="Profile sync skipped.", foreground="#ff5555")
        self.write_log("Error: Profile lookup failed. Verify network access.", "blunder_alert")

    def _on_fetch_success(self, pgn_text):
        self.fetch_btn.configure(state=tk.NORMAL)
        self.status_lbl.configure(text="Sync processing complete. Game active.", foreground="#55ff55")
        
        pgn_io = io.StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)
        if not game:
            self.write_log("Failed parsing runtime PGN array strings.", "blunder_alert")
            return

        white = game.headers.get("White", "Player1")
        black = game.headers.get("Black", "Player2")
        self.write_log(f"Match Synced: {white} vs {black}", "system_notif")
        
        # Build state history tracking matrices
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
        self.analysis_cache.clear()
        self.update_board_ui()

    def handle_prev_move(self, event=None):
        if self.current_move_index > -1:
            self.current_move_index -= 1
            self.update_board_ui()

    def handle_next_move(self, event=None):
        if self.current_move_index < len(self.boards_cache) - 2:
            self.current_move_index += 1
            self.update_board_ui()
            self._dispatch_analysis_pipeline()

    def update_board_ui(self):
        # Read visual vector layout from the current position cache index
        self.current_board = self.boards_cache[self.current_move_index + 1]
        
        try:
            last_played_move = None
            if self.current_move_index >= 0 and self.current_move_index < len(self.moves_list):
                last_played_move = self.moves_list[self.current_move_index]
                
            # Convert python-chess vector components to functional display formats via Pillow
            svg_data = chess.svg.board(board=self.current_board, size=400, lastmove=last_played_move)
            png_bytes = cairosvg.svg2png(bytestring=svg_data.encode('utf-8'))
            
            img = Image.open(io.BytesIO(png_bytes))
            render = ImageTk.PhotoImage(img)
            self.board_label.configure(image=render)
            self.board_label.image = render
        except Exception as e:
            self.write_log(f"Graphics vector layer initialization crash: {str(e)}", "blunder_alert")

        # Handle UI evaluation bar updates
        if self.current_move_index in self.analysis_cache:
            score, _ = self.analysis_cache[self.current_move_index]
            self._render_eval_bar(score)
        else:
            self._draw_empty_eval_bar()

    def _dispatch_analysis_pipeline(self):
        idx = self.current_move_index
        if idx in self.analysis_cache:
            _, cached_critique = self.analysis_cache[idx]
            self.write_log(cached_critique)
            return
            
        threading.Thread(target=self._async_analysis_worker, args=(idx,), daemon=True).start()

    def _async_analysis_worker(self, idx):
        prev_board = self.boards_cache[idx]
        target_board = self.boards_cache[idx + 1]
        move_san = self.move_history_san[idx]
        
        # Compute absolute positional scores
        s_prev = self.worker.get_absolute_score(prev_board)
        s_curr = self.worker.get_absolute_score(target_board)
        
        # Intercept missing engine binary profiles gracefully
        if s_prev is None or s_curr is None:
            fallback_feedback = self.worker.generate_coach_critique(
                board_fen=target_board.fen(),
                game_state="Engine components bypassed.",
                role_context="White" if prev_board.turn == chess.WHITE else "Black",
                move_san=move_san,
                is_blunder=False,
                score_shift=0.0
            )
            self.root.after(0, lambda: self._on_analysis_finalized(idx, None, fallback_feedback))
            return

        score_shift = s_curr - s_prev
        is_blunder = False
        
        # Evaluate game blunder triggers relative to active player colors
        if prev_board.turn == chess.WHITE:
            if score_shift < -1.5:
                is_blunder = True
        else:
            if score_shift > 1.5:
                is_blunder = True

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
        
        self.root.after(0, lambda: self._on_analysis_finalized(idx, s_curr, coach_critique))

    def _on_analysis_finalized(self, idx, score, critique_text):
        self.analysis_cache[idx] = (score, critique_text)
        if self.current_move_index == idx:
            self._render_eval_bar(score)
            is_error = "CRITICAL OVERRIDE" in critique_text or "[local ai engine offline]" in critique_text.lower()
            self.write_log(critique_text, "blunder_alert" if is_error else None)

    def _draw_empty_eval_bar(self):
        self.eval_canvas.delete("all")
        self.eval_canvas.create_rectangle(0, 0, 25, 400, fill="#45433f", outline="")
        self.eval_canvas.create_line(0, 200, 25, 200, fill="#999999", width=2)

    def _render_eval_bar(self, score):
        self.eval_canvas.delete("all")
        if score is None:
            self._draw_empty_eval_bar()
            return
            
        # Clamp bounds to handle high evaluation spikes smoothly (-5.0 to +5.0 pawns)
        clamped = max(-5.0, min(5.0, score))
        percentage = (clamped + 5.0) / 10.0
        
        # Translate White wins to expanded graphical sections
        white_height = int(400 * percentage)
        
        # Draw top-down structural layouts (White vs Black bar frames)
        self.eval_canvas.create_rectangle(0, 0, 25, 400 - white_height, fill="#111111", outline="")
        self.eval_canvas.create_rectangle(0, 400 - white_height, 25, 400, fill="#ffffff", outline="")
        self.eval_canvas.create_line(0, 200, 25, 200, fill="#ff5555", width=1.5)