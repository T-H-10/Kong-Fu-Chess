import csv
import pathlib
import time
import queue
import cv2
from typing import Dict, Tuple, Optional
import threading
from Board import Board
from Command import Command
from Piece import Piece
from img import Img
from PieceFactory import PieceFactory
from Bus.EventBus import event_bus
from GameUI import GameUI

class Game:
    def __init__(self, board: Board, pieces_root: pathlib.Path, placement_csv: pathlib.Path):
        self.board = board
        self.user_input_queue = queue.Queue()
        self.start_time = time.monotonic()
        self.piece_factory = PieceFactory(board, pieces_root)
        self.pieces: Dict[str, Piece] = {}
        self.pos_to_piece: Dict[Tuple[int, int], Piece] = {}
        self._current_board = None
        self._load_pieces_from_csv(placement_csv)
        self.focus_cell = (0, 0)
        self._selection_mode = "source"  # עבור משתמש ראשון
        self._selected_source: Optional[Tuple[int, int]] = None
        self.event_bus = event_bus
        self.game_ui = GameUI()

        # --- משתנים למשתמש השני ---
        self.focus_cell2 = (self.board.H_cells - 1, 0)  # התחלה בתחתית
        self._selection_mode2 = "source"
        self._selected_source2: Optional[Tuple[int, int]] = None
        
        # --- משתנים לשליטה בעכבר ---
        self.mouse_x = 0
        self.mouse_y = 0
        self.board_offset = (450, 100)  # מיקום הלוח על המסך
        
        # --- משתנים לרשת ---
        self.my_color = None  # הצבע שלי (white/black)
        self.network_callback = None  # פונקציה לשליחת מהלכים לרשת
        
        self._lock = threading.Lock()
        self._running = True

    def _load_pieces_from_csv(self, csv_path: pathlib.Path):
        with csv_path.open() as f:
            reader = csv.reader(f)
            for row_idx, row in enumerate(reader):
                for col_idx, code in enumerate(row):
                    code = code.strip()
                    if not code:
                        continue
                    cell = (row_idx, col_idx)
                    piece = self.piece_factory.create_piece(code, cell)
                    self.pieces[piece.get_id()] = piece
                    self.pos_to_piece[cell] = piece

    def game_time_ms(self) -> int:
        return int((time.monotonic() - self.start_time) * 1000)

    def clone_board(self) -> Board:
        return self.board.clone()

    def setup_mouse_control(self):
        """מגדיר שליטה בעכבר במקום מקלדת"""
        
        def mouse_callback(event, x, y, flags, param):
            """פונקציית callback לטיפול באירועי עכבר"""
            with self._lock:
                self.mouse_x = x
                self.mouse_y = y
                
                # המרת מיקום עכבר לתא בלוח
                board_x = x - self.board_offset[0]
                board_y = y - self.board_offset[1]
                
                if (0 <= board_x < self.board.W_cells * self.board.cell_W_pix and 
                    0 <= board_y < self.board.H_cells * self.board.cell_H_pix):
                    
                    cell_x = board_x // self.board.cell_W_pix
                    cell_y = board_y // self.board.cell_H_pix
                    new_focus = (int(cell_y), int(cell_x))
                    
                    # עדכון הפוקוס לשני השחקנים (העכבר שולט על שניהם)
                    self.focus_cell = new_focus
                    self.focus_cell2 = new_focus
                
                # טיפול בלחיצות עכבר
                if event == cv2.EVENT_LBUTTONDOWN:
                    # לחיצה שמאלית - בחירה עבור שני השחקנים
                    self._on_mouse_left_click()
                elif event == cv2.EVENT_RBUTTONDOWN:
                    # לחיצה ימנית - קפיצה (jump)
                    self._on_mouse_right_click()
        
        # שמירת הפונקציה לשימוש מאוחר יותר
        self.mouse_callback = mouse_callback
        print("🖱️ Mouse control prepared: Left click = Move (Both players), Right click = Jump")

    def _on_mouse_left_click(self):
        """טיפול בלחיצה שמאלית - תנועה עבור שני השחקנים"""
        # נבדוק אם יש כלי בתא הנוכחי
        if self.focus_cell in self.pos_to_piece:
            piece = self.pos_to_piece[self.focus_cell]
            piece_id = piece.get_id()
            
            # אם אנחנו במצב בחירת יעד, בדוק אם זו תנועה לאכילה
            if (self._selection_mode == "dest" and self._selected_source is not None):
                # שחקן 1 בוחר יעד - יכול להיות אכילה
                src_cell = self._selected_source
                dst_cell = self.focus_cell
                src_piece = self.pos_to_piece.get(src_cell)
                
                # בדוק אם זה כלי של היריב (מותר לאכול)
                if src_piece and src_piece.get_id()[1] == 'B' and piece_id[1] == 'W':
                    # שחקן שחור אוכל כלי לבן
                    src_alg = self.board.cell_to_algebraic(src_cell)
                    dst_alg = self.board.cell_to_algebraic(dst_cell)
                    cmd = Command(
                        timestamp=self.game_time_ms(),
                        piece_id=src_piece.get_id(),
                        type="move",
                        params=[src_alg, dst_alg]
                    )
                    self.user_input_queue.put(cmd)
                    
                    # שליחה לרשת
                    self.send_move_to_network("move", src_piece.get_id(), src_alg, dst_alg)
                    
                    print(f"Player 1 captured {piece_id} at {dst_cell}")
                    self._reset_selection()
                    return
                    
            elif (self._selection_mode2 == "dest" and self._selected_source2 is not None):
                # שחקן 2 בוחר יעד - יכול להיות אכילה
                src_cell = self._selected_source2
                dst_cell = self.focus_cell
                src_piece = self.pos_to_piece.get(src_cell)
                
                # בדוק אם זה כלי של היריב (מותר לאכול)
                if src_piece and src_piece.get_id()[1] == 'W' and piece_id[1] == 'B':
                    # שחקן לבן אוכל כלי שחור
                    src_alg = self.board.cell_to_algebraic(src_cell)
                    dst_alg = self.board.cell_to_algebraic(dst_cell)
                    cmd = Command(
                        timestamp=self.game_time_ms(),
                        piece_id=src_piece.get_id(),
                        type="move",
                        params=[src_alg, dst_alg]
                    )
                    self.user_input_queue.put(cmd)
                    
                    # שליחה לרשת
                    self.send_move_to_network("move", src_piece.get_id(), src_alg, dst_alg)
                    
                    print(f"Player 2 captured {piece_id} at {dst_cell}")
                    self._reset_selection2()
                    return
                    
            # אם זה לא אכילה, נמשיך עם הלוגיקה הרגילה לבחירת כלי
            # בדיקת הרשאה לשליטה בכלי רק אם זה לא במצב בחירת יעד
            if ((self._selection_mode == "source" or self._selection_mode2 == "source") and 
                not self.can_control_piece(piece_id)):
                print("🚫 אינך יכול לשלוט בכלי הזה")
                return
            
            # זיהוי סוג השחקן לפי הכלי
            if piece_id[1] == 'B':  # שחקן 1 (שחור)
                if self._selection_mode == "source":
                    # בחירת כלי מקור
                    src_alg = self.board.cell_to_algebraic(self.focus_cell)
                    self._selected_source = self.focus_cell
                    self._selection_mode = "dest"
                    print(f"Player 1 selected piece at {self.focus_cell}")
                elif self._selection_mode == "dest":
                    # ביצוע תנועה לאותו תא (כלי משלו)
                    if self._selected_source is None:
                        return
                    src_cell = self._selected_source
                    dst_cell = self.focus_cell
                    src_alg = self.board.cell_to_algebraic(src_cell)
                    dst_alg = self.board.cell_to_algebraic(dst_cell)
                    piece = self.pos_to_piece.get(src_cell)
                    if piece:
                        cmd = Command(
                            timestamp=self.game_time_ms(),
                            piece_id=piece.get_id(),
                            type="move",
                            params=[src_alg, dst_alg]
                        )
                        self.user_input_queue.put(cmd)
                        
                        # שליחה לרשת
                        self.send_move_to_network("move", piece.get_id(), src_alg, dst_alg)
                        
                        print(f"Player 1 moved from {src_cell} to {dst_cell}")
                    self._reset_selection()
                    
            elif piece_id[1] == 'W':  # שחקן 2 (לבן)
                if self._selection_mode2 == "source":
                    # בחירת כלי מקור
                    src_alg = self.board.cell_to_algebraic(self.focus_cell)
                    self._selected_source2 = self.focus_cell
                    self._selection_mode2 = "dest"
                    print(f"Player 2 selected piece at {self.focus_cell}")
                elif self._selection_mode2 == "dest":
                    # ביצוע תנועה לאותו תא (כלי משלו)
                    if self._selected_source2 is None:
                        return
                    src_cell = self._selected_source2
                    dst_cell = self.focus_cell
                    src_alg = self.board.cell_to_algebraic(src_cell)
                    dst_alg = self.board.cell_to_algebraic(dst_cell)
                    piece = self.pos_to_piece.get(src_cell)
                    if piece:
                        cmd = Command(
                            timestamp=self.game_time_ms(),
                            piece_id=piece.get_id(),
                            type="move",
                            params=[src_alg, dst_alg]
                        )
                        self.user_input_queue.put(cmd)
                        
                        # שליחה לרשת
                        self.send_move_to_network("move", piece.get_id(), src_alg, dst_alg)
                        
                        print(f"Player 2 moved from {src_cell} to {dst_cell}")
                    self._reset_selection2()
        else:
            # אם אין כלי בתא הנוכחי, זה יכול להיות יעד לתנועה
            # בודקים אם אחד השחקנים בבחירת יעד
            if self._selection_mode == "dest" and self._selected_source is not None:
                # שחקן 1 בוחר יעד
                src_cell = self._selected_source
                dst_cell = self.focus_cell
                src_alg = self.board.cell_to_algebraic(src_cell)
                dst_alg = self.board.cell_to_algebraic(dst_cell)
                piece = self.pos_to_piece.get(src_cell)
                if piece:
                    cmd = Command(
                        timestamp=self.game_time_ms(),
                        piece_id=piece.get_id(),
                        type="move",
                        params=[src_alg, dst_alg]
                    )
                    self.user_input_queue.put(cmd)
                    
                    # שליחה לרשת
                    self.send_move_to_network("move", piece.get_id(), src_alg, dst_alg)
                    
                    print(f"Player 1 moved from {src_cell} to {dst_cell}")
                self._reset_selection()
                
            elif self._selection_mode2 == "dest" and self._selected_source2 is not None:
                # שחקן 2 בוחר יעד
                src_cell = self._selected_source2
                dst_cell = self.focus_cell
                src_alg = self.board.cell_to_algebraic(src_cell)
                dst_alg = self.board.cell_to_algebraic(dst_cell)
                piece = self.pos_to_piece.get(src_cell)
                if piece:
                    cmd = Command(
                        timestamp=self.game_time_ms(),
                        piece_id=piece.get_id(),
                        type="move",
                        params=[src_alg, dst_alg]
                    )
                    self.user_input_queue.put(cmd)
                    
                    # שליחה לרשת
                    self.send_move_to_network("move", piece.get_id(), src_alg, dst_alg)
                    
                    print(f"Player 2 moved from {src_cell} to {dst_cell}")
                self._reset_selection2()

    def _on_mouse_right_click(self):
        """טיפול בלחיצה ימנית - קפיצה (jump) עבור שני השחקנים"""
        if self.focus_cell in self.pos_to_piece:
            piece = self.pos_to_piece[self.focus_cell]
            piece_id = piece.get_id()
            
            # בדיקת הרשאה לשליטה בכלי
            if not self.can_control_piece(piece_id):
                print("🚫 אינך יכול לשלוט בכלי הזה")
                return
            
            src_alg = self.board.cell_to_algebraic(self.focus_cell)
            cmd = Command(
                timestamp=self.game_time_ms(),
                piece_id=piece_id,
                type="jump",
                params=[src_alg, src_alg]
            )
            self.user_input_queue.put(cmd)
            
            # שליחה לרשת
            self.send_move_to_network("jump", piece_id, src_alg)
            
            # זיהוי השחקן לפי הכלי
            if piece_id[1] == 'B':
                print(f"Player 1 jumped with piece at {self.focus_cell}")
            elif piece_id[1] == 'W':
                print(f"Player 2 jumped with piece at {self.focus_cell}")
            else:
                print(f"Jumped with piece at {self.focus_cell}")

    def _on_mouse_middle_click(self):
        """טיפול בלחיצה אמצעית - קפיצה (jump) - לא בשימוש יותר, קפיצה עברה ללחיצה ימנית"""
        # קפיצה עבור שחקן 1 אם הכלי שייך לו
        if self.focus_cell in self.pos_to_piece:
            piece = self.pos_to_piece[self.focus_cell]
            
            # בדיקת הרשאה לשליטה בכלי
            if not self.can_control_piece(piece.get_id()):
                print("🚫 אינך יכול לשלוט בכלי הזה")
                return
            
            if piece.get_id()[1] == 'B':  # שחקן 1
                src_alg = self.board.cell_to_algebraic(self.focus_cell)
                cmd = Command(
                    timestamp=self.game_time_ms(),
                    piece_id=piece.get_id(),
                    type="jump",
                    params=[src_alg, src_alg]
                )
                self.user_input_queue.put(cmd)
                
                # שליחה לרשת
                self.send_move_to_network("jump", piece.get_id(), src_alg)
                
                print(f"Player 1 jumped with piece at {self.focus_cell}")
            elif piece.get_id()[1] == 'W':  # שחקן 2
                src_alg = self.board.cell_to_algebraic(self.focus_cell)
                cmd = Command(
                    timestamp=self.game_time_ms(),
                    piece_id=piece.get_id(),
                    type="jump",
                    params=[src_alg, src_alg]
                )
                self.user_input_queue.put(cmd)
                
                # שליחה לרשת
                self.send_move_to_network("jump", piece.get_id(), src_alg)
                
                print(f"Player 2 jumped with piece at {self.focus_cell}")

    def _on_jump_pressed(self, player: int):
        with self._lock:  # הגנה מפני race conditions
            if player == 1:
                if self.focus_cell in self.pos_to_piece:
                    piece = self.pos_to_piece[self.focus_cell]
                    if not piece.get_id()[1] == 'B':
                        print("User 1 cannot jump with this piece.")
                        return
                    src_alg = self.board.cell_to_algebraic(self.focus_cell)
                    cmd = Command(
                        timestamp=self.game_time_ms(),
                        piece_id=piece.get_id(),
                        type="jump",
                        params=[src_alg,src_alg]
                    )
                    self.user_input_queue.put(cmd)

            elif player == 2:
                if self.focus_cell2 in self.pos_to_piece:
                    piece = self.pos_to_piece[self.focus_cell2]
                    if not piece.get_id()[1] == 'W':
                        print("User 2 cannot jump with this piece.")
                        return
                    src_alg = self.board.cell_to_algebraic(self.focus_cell2)
                    cmd = Command(
                        timestamp=self.game_time_ms(),
                        piece_id=piece.get_id(),
                        type="jump",
                        params=[src_alg,src_alg]
                    )
                    self.user_input_queue.put(cmd)

    def run(self):
        background_width = 1530
        background_height = 850
    # טען את תמונת הרקע וודא שהיא בגודל הנכון
        background = Img().read("black_win.jpg", size=(background_width, background_height))
 
        # --- רקע ---
        # background = Img().read("../background.png")
        board_offset = (450, 100)
        self.board_offset = board_offset  # עדכון המיקום לשימוש בעכבר
        
        # הגדרת שליטה בעכבר
        self.setup_mouse_control()
        
        # שליחת אירוע תחילת המשחק
        self.event_bus.publish("game_start", {"message": "Game is starting!"})
        
        # self._wait_for_enter("Press ENTER\n to start the game",background)

        start_ms = self.game_time_ms()
        for piece in self.pieces.values():
            piece.reset(start_ms)

        while self._running and not self._is_win():
            now = self.game_time_ms()

            for piece in self.pieces.values():
                piece.update(now , self.pos_to_piece)

            self._update_position_mapping()

            while not self.user_input_queue.empty():
                cmd = self.user_input_queue.get()
                cell = self.board.algebraic_to_cell(cmd.params[0])
                if cell in self.pos_to_piece:
                     self.pos_to_piece[cell].on_command(cmd, now, self.pos_to_piece)

            self._draw()

            # יצירת תמונת מסך חדשה כל פריים
            frame = Img()
            frame.img = background.img.copy()
            self._current_board.img.draw_on(frame, *board_offset)
            
            # הוספת כל ה-UI
            if self.game_ui:
                self.game_ui.draw_all_ui(frame)

            cv2.imshow("Kong Fu Chess", frame.img)
            
            # הגדרת mouse callback בפעם הראשונה שהחלון נוצר
            if hasattr(self, 'mouse_callback') and not hasattr(self, '_mouse_callback_set'):
                cv2.setMouseCallback("Kong Fu Chess", self.mouse_callback)
                self._mouse_callback_set = True
                print("🖱️ Mouse control activated!")
            
            # בדיקת ESC ליציאה מהמשחק
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC key
                print("🚪 ESC pressed - Exiting game...")
                self._running = False
                break

        # שליחת הודעת סיום ומתן זמן להציגה
        self._send_end_message()
        
        # המתן קצר כדי להציג את הודעת הסיום
        for _ in range(100):  # 100 פריימים ~ 3 שניות
            frame = Img()
            frame.img = background.img.copy()
            self._current_board.img.draw_on(frame, *board_offset)
            
            if self.game_ui:
                self.game_ui.draw_all_ui(frame)
                
            cv2.imshow("Kong Fu Chess", frame.img)
            if cv2.waitKey(30) == 13:  # אם לחצו Enter
                break

        self._announce_win()
        self._running = False
        
        # ניקוי משאבים
        if self.game_ui:
            self.game_ui.cleanup()
            
        cv2.destroyAllWindows()


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

    def _check_pawn_promotion(self):
        """בודק אם יש חיילים שהגיעו לשורה האחרונה והופך אותם למלכה"""
        pieces_to_promote = []
        
        for piece in self.pieces.values():
            piece_id = piece.get_id()
            if piece_id[0] == 'P':  # זה חייל
                piece_color = piece_id[1]  # W או B
                current_pos = piece._state._physics.get_pos_in_cell()
                row = current_pos[0]
                
                # בדיקה שהחייל סיים את התנועה שלו (idle או רגוע)
                current_command_type = piece._state._current_command.type if piece._state._current_command else "idle"
                is_at_rest = current_command_type in ["idle", "long_rest", "short_rest"]
                
                # בדיקה אם הגיע לשורה של קידום ורק אחרי שסיים תנועה
                if is_at_rest and ((piece_color == 'W' and row == 0) or (piece_color == 'B' and row == 7)):
                    pieces_to_promote.append((piece_id, piece_color, current_pos))
        
        # ביצוע הקידום
        for old_id, color, pos in pieces_to_promote:
            self._promote_pawn_to_queen(old_id, color, pos)
    
    def _promote_pawn_to_queen(self, pawn_id: str, color: str, position: Tuple[int, int]):
        """מקדם חייל למלכה"""
        try:
            # יצירת ID חדש למלכה
            new_queen_id = f"Q{color}"
            
            # אם כבר יש מלכה עם השם הזה, נוסיף מספר
            counter = 1
            original_queen_id = new_queen_id
            while new_queen_id in self.pieces:
                new_queen_id = f"{original_queen_id}{counter}"
                counter += 1
            
            # יצירת מלכה חדשה במיקום הנוכחי
            new_queen = self.piece_factory.create_piece(original_queen_id, position)
            new_queen._id = new_queen_id  # עדכון ה-ID לייחודי
            
            # אתחול המלכה החדשה במצב idle
            now_ms = self.game_time_ms()
            new_queen.reset(now_ms)
            
            # הסרת החייל הישן והוספת המלכה החדשה
            old_piece = self.pieces.pop(pawn_id, None)
            self.pieces[new_queen_id] = new_queen
            
            # עדכון המיפוי
            if position in self.pos_to_piece and self.pos_to_piece[position].get_id() == pawn_id:
                self.pos_to_piece[position] = new_queen
            
            print(f"🎉 Pawn {pawn_id} promoted to Queen {new_queen_id} at {position}!")
            
            # שליחת אירוע קידום
            self.event_bus.publish("piece_promoted", {
                "old_piece": pawn_id,
                "new_piece": new_queen_id,
                "position": position,
                "message": f"Pawn promoted to Queen!"
            })
            
        except Exception as e:
            print(f"❌ Error promoting pawn {pawn_id}: {e}")


    def _draw(self):
            board = self.clone_board()
            now_ms = self.game_time_ms()
            for piece in self.pieces.values():
                piece.draw_on_board(board, now_ms)
            self.draw_rect(board, self.focus_cell, (0, 255, 255), 4)
            self.draw_rect(board, self.focus_cell2, (255, 0, 0), 2)   # כחול
            if self._selected_source:
                self.draw_rect(board, self._selected_source, (0, 0, 255), 4)  # אדום
            if self._selected_source2:
                self.draw_rect(board, self._selected_source2, (0, 255, 0), 2)  # ירוק
            self._current_board = board
    def draw_rect(self, board, cell, color, thickness):
        # ציור ריבוע פוקוס למשתמש
        y, x = cell
        x1 = x * board.cell_W_pix
        y1 = y * board.cell_H_pix
        x2 = (x + 1) * board.cell_W_pix
        y2 = (y + 1) * board.cell_H_pix
        cv2.rectangle(board.img.img, (x1, y1), (x2, y2), color, thickness)
    
    def _is_win(self) -> bool:
        kings = [p for p in self.pieces.values() if p.get_id().lower().startswith("k")]
        return len(kings) <= 1

    def _send_end_message(self):
        """שולח את הודעת הסיום לפני הודעת הניצחון הרשמית"""
        kings = [p for p in self.pieces.values() if p.get_id().startswith("KW") or p.get_id().startswith("KB")]

        if len(kings) == 2:
            winner = "draw"
        elif len(kings) == 1:
            winner_king = kings[0]
            winner = "white" if winner_king.get_id().startswith("KW") else "black"
        else:
            winner = "draw"

        # שליחת אירוע סיום המשחק
        self.event_bus.publish("game_end", {"winner": winner, "message": f"Game ended with {winner}"})

    def _announce_win(self):
        img = Img()
        img.img = self.board.img.img.copy()

        kings = [p for p in self.pieces.values() if p.get_id().startswith("KW") or p.get_id().startswith("KB")]

        if len(kings) == 2:
            message = "Both kings still on board. No winner yet."
            color = (255, 255, 255, 255)  # לבן
            winner = "draw"
        elif len(kings) == 1:
            winner_king = kings[0]
            winner_color = "White" if winner_king.get_id().startswith("KW") else "Black"
            message = f"{winner_color} Wins!"
            color = (0, 0, 255, 255)
            winner = winner_color.lower()
        else:
            message = "Draw – both kings are gone."
            color = (0, 0, 255, 255)  # אפור
            winner = "draw"

        # שליחת אירוע סיום המשחק
        self.event_bus.publish("game_end", {"winner": winner, "message": message})

        # מרכז הטקסט על התמונה
        # text_size, _ = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 2, 3)
        # text_x = (img.img.shape[1] - text_size[0]) // 2
        # text_y = (img.img.shape[0] + text_size[1]) // 2

        # img.put_text(message, text_x, text_y, font_size=2, color=color, thickness=3)

        # cv2.imshow("Chess", img.img)
        # print("Press ENTER to exit...")

        # # מחכים עד שלחצו Enter (key code 13) ואז סוגרים
        # while True:
        #     key = cv2.waitKey(100)
        #     if key == 13:  # Enter
        #         break

        # cv2.destroyAllWindows()

    def _on_enter_pressed(self):
        # טיפול בבחירה עבור משתמש ראשון - thread safe
        with self._lock:  # הגנה מפני race conditions
            if self._selection_mode == "source":
                if self.focus_cell in self.pos_to_piece:
                    piece = self.pos_to_piece[self.focus_cell]
                    # בדיקה שהכלי שייך למשתמש הראשון (מזהה שמתחיל ב-"B")
                    if not piece.get_id()[1] == 'B':
                        print("User 1 cannot select this piece.")
                        return
                    src_alg = self.board.cell_to_algebraic(self.focus_cell)
                    # print(f"User 1 source selected at {self.focus_cell} -> {src_alg}")
                    self._selected_source = self.focus_cell
                    self._selection_mode = "dest"
            elif self._selection_mode == "dest":
                if self._selected_source is None:
                    return
                src_cell = self._selected_source
                dst_cell = self.focus_cell
                src_alg = self.board.cell_to_algebraic(src_cell)
                dst_alg = self.board.cell_to_algebraic(dst_cell)
                # print(f"User 1 destination selected at {dst_cell} -> {dst_alg}")
                piece = self.pos_to_piece.get(src_cell)
                if piece:
                    cmd = Command(
                        timestamp=self.game_time_ms(),
                        piece_id=piece.get_id(),  # או get_id() לפי מה שמשמש בפקודות
                        type="move",
                        params=[src_alg, dst_alg]
                    )
                    self.user_input_queue.put(cmd)
                self._reset_selection()

    def _on_space_pressed(self):
        # טיפול בבחירה עבור משתמש שני - thread safe
        with self._lock:  # הגנה מפני race conditions
            if self._selection_mode2 == "source":
                if self.focus_cell2 in self.pos_to_piece:
                    piece = self.pos_to_piece[self.focus_cell2]
                    # בדיקה שהכלי שייך למשתמש השני (מזהה שמתחיל ב-"W")
                    if not piece.get_id()[1] == 'W':
                        print("User 2 cannot select this piece.")
                        return
                    src_alg = self.board.cell_to_algebraic(self.focus_cell2)
                    # print(f"User 2 source selected at {self.focus_cell2} -> {src_alg}")
                    self._selected_source2 = self.focus_cell2
                    self._selection_mode2 = "dest"
            elif self._selection_mode2 == "dest":
                if self._selected_source2 is None:
                    return
                src_cell = self._selected_source2
                dst_cell = self.focus_cell2
                src_alg = self.board.cell_to_algebraic(src_cell)
                dst_alg = self.board.cell_to_algebraic(dst_cell)
                print(f"User 2 destination selected at {dst_cell} -> {dst_alg}")
                piece = self.pos_to_piece.get(src_cell)
                if piece:
                    cmd = Command(
                        timestamp=self.game_time_ms(),
                        piece_id=piece.get_id(),
                        type="move",
                        params=[src_alg, dst_alg]
                    )
                    self.user_input_queue.put(cmd)
                self._reset_selection2()

    def _reset_selection(self):
        self._selection_mode = "source"
        self._selected_source = None

    def _reset_selection2(self):
        self._selection_mode2 = "source"
        self._selected_source2 = None

    # --- פונקציות רשת ---
    
    def set_player_color(self, color: str):
        """קובע את הצבע של השחקן הנוכחי"""
        self.my_color = color
        print(f"🎨 הצבע שלי: {color}")
        
        # הגבלת שליטה רק לצבע שלי
        if color == "white":
            print("🎮 אתה שולט על הכלים הלבנים (לחיצה ימנית)")
        else:
            print("🎮 אתה שולט על הכלים השחורים (לחיצה שמאלית)")

    def set_network_callback(self, callback):
        """קובע פונקציה לשליחת מהלכים לרשת"""
        self.network_callback = callback

    def apply_server_update(self, update_data):
        """מטפל בעדכון מהשרת"""
        try:
            board_state = update_data.get("board", {})
            print(f"🔄 מעדכן לוח מהשרת: {board_state}")
            # כאן יכול להיות לוגיקה לעדכון הלוח
        except Exception as e:
            print(f"❌ שגיאה בעדכון מהשרת: {e}")

    def apply_opponent_move(self, move_data):
        """מטפל במהלך של היריב"""
        try:
            action = move_data.get("action")
            if action == "move":
                from_pos = move_data.get("from")
                to_pos = move_data.get("to")
                piece_id = move_data.get("piece")
                
                print(f"🎯 יריב הזיז: {piece_id} מ-{from_pos} ל-{to_pos}")
                
                # יצירת פקודה ממהלך היריב
                cmd = Command(
                    timestamp=self.game_time_ms(),
                    piece_id=piece_id,
                    type="move",
                    params=[from_pos, to_pos]
                )
                self.user_input_queue.put(cmd)
                
            elif action == "jump":
                piece_id = move_data.get("piece")
                pos = move_data.get("position")
                
                print(f"🦘 יריב קפץ: {piece_id} ב-{pos}")
                
                cmd = Command(
                    timestamp=self.game_time_ms(),
                    piece_id=piece_id,
                    type="jump",
                    params=[pos, pos]
                )
                self.user_input_queue.put(cmd)
                
        except Exception as e:
            print(f"❌ שגיאה ביישום מהלך יריב: {e}")

    def send_move_to_network(self, action: str, piece_id: str, from_pos: str = None, to_pos: str = None):
        """שולח מהלך לרשת"""
        if not self.network_callback:
            print("⚠️ אין חיבור רשת - המהלך יתבצע רק מקומית")
            return
            
        move_data = {
            "action": action,
            "piece": piece_id,
            "player_color": self.my_color
        }
        
        if action == "move" and from_pos and to_pos:
            move_data["from"] = from_pos
            move_data["to"] = to_pos
            print(f"📤 שולח מהלך לרשת: {piece_id} מ-{from_pos} ל-{to_pos}")
        elif action == "jump" and from_pos:
            move_data["position"] = from_pos
            print(f"📤 שולח קפיצה לרשת: {piece_id} ב-{from_pos}")
            
        self.network_callback(move_data)

    def can_control_piece(self, piece_id: str) -> bool:
        """בודק אם השחקן יכול לשלוט בכלי הזה"""
        if not self.my_color:
            return True  # אם אין הגבלת רשת, מותר הכל
            
        piece_color = piece_id[1] if len(piece_id) > 1 else None
        
        if self.my_color == "white":
            return piece_color == 'W'
        elif self.my_color == "black":
            return piece_color == 'B'
            
        return False