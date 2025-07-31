import pathlib
import time
import queue
from typing import Dict, Tuple, Optional
from Board import Board
from Command import Command
from Piece import Piece
from PieceFactory import PieceFactory
from CommandLog import CommandLog

class Game:
    def __init__(self, board: Board, pieces_root: pathlib.Path, placement_csv: pathlib.Path):
        # self.board = board
        # self.user_input_queue = queue.Queue()
        # self.pieces: Dict[str, Piece] = {}
        # self.pos_to_piece: Dict[Tuple[int, int], Piece] = {}

        self.board = board
        self.piece_factory = PieceFactory(board, pieces_root)
        self.command_log = CommandLog
        self.pieces = {}
        self.pos_to_piece = {}
        # self._load_pieces_from_csv(placement_csv)
        
    def game_time_ms(self) -> int:
        return int((time.monotonic() - self.start_time) * 1000)


    def _load_pieces_from_csv(self, csv_path: pathlib.Path):
        with csv_path.open() as f:
            # reader = csv.reader(f)
            for row_idx, row in enumerate(f):
                for col_idx, code in enumerate(row.strip().split(",")):
                    code = code.strip()
                    if code:
                        cell = (row_idx, col_idx)
                        piece = self.piece_factory.create_piece(code, cell)
                        self.pieces[piece.get_id()] = piece
                        self.pos_to_piece[cell] = piece

    def _update_position_mapping(self):
        self.pos_to_piece.clear()
        to_remove = set()

        for piece in list(self.pieces.values()):  # שימוש ב-list כדי להקפיא את הערכים בזמן הלולאה
            x, y = map(int, piece._state._physics.get_pos())
            cell_x = x / self.board.cell_W_pix
            cell_y = y / self.board.cell_H_pix
            pos = (cell_y, cell_x)
            if pos in self.pos_to_piece:
                opponent = self.pos_to_piece[pos]
                print(piece._state._current_command)
                print(opponent._state._current_command)
                print(opponent._state._current_command.type in ["idle", "long_rest", "short_rest"])
                print()
                if (opponent._state._current_command.type in ["idle", "long_rest", "short_rest"] or
                        (piece._state._current_command and
                         piece._state._current_command.type not in ["idle", "long_rest", "short_rest"] and
                        opponent._state._physics.start_time > piece._state._physics.start_time and
                        opponent._state._current_command.type != "jump") or
                        piece._state._current_command.type == "jump"):
                    print(f"Removing opponent {opponent.get_id()} at {pos}")
                    self.pos_to_piece[pos] = piece
                    to_remove.add(opponent.get_id())
                else:
                    print(f"Removing piece {piece.get_id()} at {pos}")
                    to_remove.add(piece.get_id())
            else:
                self.pos_to_piece[pos] = piece

        for k in to_remove:
            self.event_bus.publish("piece_captured", {"piece": k})
            self.pieces.pop(k, None)  # pop עם None כדי למנוע שגיאת KeyError

        # בדיקת קידום חיילים למלכה
        self._check_pawn_promotion()
    
    # def handle_move(self, player_color: str, from_pos: str, to_pos: str) -> Tuple[bool, str]:
    #     """
    #     מטפל במהלך של שחקן - בודק חוקיות ומבצע את המהלך
    #     """
    #     try:
    #         # המרת מיקומים אלגבריים לתאים
    #         from_cell = self.board.algebraic_to_cell(from_pos)
    #         to_cell = self.board.algebraic_to_cell(to_pos)
            
    #         # בדיקה שיש כלי במיקום המקור
    #         if from_cell not in self.pos_to_piece:
    #             return False, f"אין כלי במיקום {from_pos}"
            
    #         piece = self.pos_to_piece[from_cell]
    #         piece_id = piece.get_id()
            
    #         # בדיקה שהכלי שייך לשחקן הנכון
    #         piece_color_char = piece_id[1] if len(piece_id) > 1 else None
    #         expected_color = 'W' if player_color == "white" else 'B'
            
    #         if piece_color_char != expected_color:
    #             return False, f"הכלי {piece_id} לא שייך לשחקן {player_color}"
            
    #         # בדיקה שהמהלך חוקי
    #         if not piece.can_move(to_cell, self.pos_to_piece):
    #             return False, f"מהלך לא חוקי מ-{from_pos} ל-{to_pos}"
            
    #         # ביצוע המהלך
    #         now_ms = self.game_time_ms()
    #         cmd = Command(
    #             timestamp=now_ms,
    #             piece_id=piece_id,
    #             type="move",
    #             params=[from_pos, to_pos]
    #         )
            
    #         # הוספת הפקודה לתור
    #         self.user_input_queue.put(cmd)
            
    #         return True, f"מהלך הושלם בהצלחה: {piece_id} מ-{from_pos} ל-{to_pos}"
            
    #     except Exception as e:
    #         return False, f"שגיאה במהלך: {str(e)}"

    def handle_move(self, player_color, from_alg, to_alg):
        from_cell = self.board.algebraic_to_cell(from_alg)
        to_cell = self.board.algebraic_to_cell(to_alg)

        piece = self.pos_to_piece.get(from_cell)
        if not piece:
            return False, "No piece at source"

        if piece.get_id()[1].lower() != player_color[0].lower():
            return False, "Wrong color"

        valid_moves = piece.get_valid_moves(from_cell, self.pos_to_piece)
        if to_cell not in valid_moves:
            return False, "Invalid move"

        # עדכון בפועל של המצב
        self.pos_to_piece[to_cell] = piece
        del self.pos_to_piece[from_cell]
        piece.set_position(to_cell)

        return True, "OK"
    
    def get_board_state(self):
        return {
            self.board.cell_to_algebraic(pos): piece.get_id()
            for pos, piece in self.pos_to_piece.items()
        }

    # def get_board_state(self) -> Dict:
    #     """
    #     מחזיר את מצב הלוח הנוכחי כמבנה נתונים שניתן להמיר ל-JSON
    #     """
    #     pieces_data = []
        
    #     for piece_id, piece in self.pieces.items():
    #         try:
    #             position = piece.get_position()
    #             algebraic_pos = self.board.cell_to_algebraic(position)
                
    #             pieces_data.append({
    #                 "id": piece_id,
    #                 "position": {
    #                     "cell": position,
    #                     "algebraic": algebraic_pos
    #                 },
    #                 "color": piece_id[1] if len(piece_id) > 1 else "unknown",
    #                 "type": piece_id[0] if len(piece_id) > 0 else "unknown"
    #             })
    #         except Exception as e:
    #             print(f"שגיאה בקריאת מיקום כלי {piece_id}: {e}")
        
    #     return {
    #         "pieces": pieces_data,
    #         "board_size": {
    #             "width": self.board.W_cells,
    #             "height": self.board.H_cells
    #         },
    #         "timestamp": self.game_time_ms()
    #     }
    
    def update_server(self):
        """
        עדכון השרת - מעבד פקודות ועדכן כלים בלי GUI
        """
        now = self.game_time_ms()
        
        # עדכון כל הכלים
        for piece in self.pieces.values():
            piece.update(now, self.pos_to_piece)
        
        # עדכון מיפוי מיקומים
        self._update_position_mapping()
        
        # עיבוד פקודות מהתור
        while not self.user_input_queue.empty():
            cmd = self.user_input_queue.get()
            try:
                cell = self.board.algebraic_to_cell(cmd.params[0])
                if cell in self.pos_to_piece:
                    self.pos_to_piece[cell].on_command(cmd, now, self.pos_to_piece)
            except Exception as e:
                print(f"שגיאה בעיבוד פקודה {cmd}: {e}")
                
    # def handle_move(self, player_color: str, from_alg: str, to_alg: str) -> tuple[bool, str]:
    #     from_cell = self.board.algebraic_to_cell(from_alg)
    #     to_cell = self.board.algebraic_to_cell(to_alg)

    #     piece = self.pos_to_piece.get(from_cell)
    #     if not piece:
    #         return False, "No piece at source"

    #     piece_color = piece.get_id()[1].lower()
    #     if piece_color != player_color[0].lower():
    #         return False, "Wrong color"

    #     valid_moves = piece.get_valid_moves(from_cell, self.pos_to_piece)
    #     if to_cell not in valid_moves:
    #         return False, "Invalid move"

    #     # עדכון הלוח
    #     self.pos_to_piece[to_cell] = piece
    #     del self.pos_to_piece[from_cell]
    #     piece.set_position(to_cell)

    #     return True, "OK"

    def handle_jump(self, player_color: str, pos_alg: str) -> tuple[bool, str]:
        cell = self.board.algebraic_to_cell(pos_alg)
        piece = self.pos_to_piece.get(cell)
        if not piece:
            return False, "No piece to jump"
        piece_color = piece.get_id()[1].lower()
        if piece_color != player_color[0].lower():
            return False, "Wrong color"
        # נקרא jump סטטי שלא משנה מיקום — רק שדר
        return True, "Jumped"

    def get_board_state(self) -> dict[str, str]:
        state = {}
        for pos, piece in self.pos_to_piece.items():
            alg = self.board.cell_to_algebraic(pos)
            state[alg] = piece.get_id()
        return state

    def apply_server_update(self, board_state: dict[str, str]):
            """מתעדכן לפי הודעה מהשרת בלבד"""
            self.pieces.clear()
            self.pos_to_piece.clear()

            for cell_alg, piece_id in board_state.items():
                cell = self.board.algebraic_to_cell(cell_alg)
                piece = self.piece_factory.create_piece(piece_id, cell)
                self.pieces[piece.get_id()] = piece
                self.pos_to_piece[cell] = piece

    def handle_command(self, result: dict):
        """מקבל תוצאה מהשרת (move / jump)"""
        if result["type"] == "move":
            self.command_log.log_command(result)
            # לא נוגעים בלוח – רק מחכים ל-board_update
        elif result["type"] == "move_rejected":
            print("❌ מהלך נדחה:", result["message"])
        elif result["type"] == "jump":
            self.command_log.log_command(result)
            # גם כאן – עדכון לוח רק מהשרת
        elif result["type"] == "jump_rejected":
            print("❌ קפיצה נדחתה:", result["message"])

    def get_piece(self, pos):
        return self.pos_to_piece.get(pos)

    def get_all_pieces(self):
        return self.pieces.values()

    def get_piece_by_id(self, piece_id):
        return self.pieces.get(piece_id)