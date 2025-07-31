import pathlib
import time
import queue
from typing import Dict, Tuple, Optional
from Board import Board
from Command import Command
from Piece import Piece
from PieceFactory import PieceFactory

class Game:
    def __init__(self, board: Board, pieces_root: pathlib.Path, placement_csv: pathlib.Path):
        self.board = board
        self.user_input_queue = queue.Queue()
        self.pieces: Dict[str, Piece] = {}
        self.pos_to_piece: Dict[Tuple[int, int], Piece] = {}

    def game_time_ms(self) -> int:
        return int((time.monotonic() - self.start_time) * 1000)

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
    
    def handle_move(self, player_color: str, from_pos: str, to_pos: str) -> Tuple[bool, str]:
        """
        מטפל במהלך של שחקן - בודק חוקיות ומבצע את המהלך
        """
        try:
            # המרת מיקומים אלגבריים לתאים
            from_cell = self.board.algebraic_to_cell(from_pos)
            to_cell = self.board.algebraic_to_cell(to_pos)
            
            # בדיקה שיש כלי במיקום המקור
            if from_cell not in self.pos_to_piece:
                return False, f"אין כלי במיקום {from_pos}"
            
            piece = self.pos_to_piece[from_cell]
            piece_id = piece.get_id()
            
            # בדיקה שהכלי שייך לשחקן הנכון
            piece_color_char = piece_id[1] if len(piece_id) > 1 else None
            expected_color = 'W' if player_color == "white" else 'B'
            
            if piece_color_char != expected_color:
                return False, f"הכלי {piece_id} לא שייך לשחקן {player_color}"
            
            # בדיקה שהמהלך חוקי
            if not piece.can_move(to_cell, self.pos_to_piece):
                return False, f"מהלך לא חוקי מ-{from_pos} ל-{to_pos}"
            
            # ביצוע המהלך
            now_ms = self.game_time_ms()
            cmd = Command(
                timestamp=now_ms,
                piece_id=piece_id,
                type="move",
                params=[from_pos, to_pos]
            )
            
            # הוספת הפקודה לתור
            self.user_input_queue.put(cmd)
            
            return True, f"מהלך הושלם בהצלחה: {piece_id} מ-{from_pos} ל-{to_pos}"
            
        except Exception as e:
            return False, f"שגיאה במהלך: {str(e)}"

    def get_board_state(self) -> Dict:
        """
        מחזיר את מצב הלוח הנוכחי כמבנה נתונים שניתן להמיר ל-JSON
        """
        pieces_data = []
        
        for piece_id, piece in self.pieces.items():
            try:
                position = piece.get_position()
                algebraic_pos = self.board.cell_to_algebraic(position)
                
                pieces_data.append({
                    "id": piece_id,
                    "position": {
                        "cell": position,
                        "algebraic": algebraic_pos
                    },
                    "color": piece_id[1] if len(piece_id) > 1 else "unknown",
                    "type": piece_id[0] if len(piece_id) > 0 else "unknown"
                })
            except Exception as e:
                print(f"שגיאה בקריאת מיקום כלי {piece_id}: {e}")
        
        return {
            "pieces": pieces_data,
            "board_size": {
                "width": self.board.W_cells,
                "height": self.board.H_cells
            },
            "timestamp": self.game_time_ms()
        }
    
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