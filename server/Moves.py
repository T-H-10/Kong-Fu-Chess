# # Moves.py  – drop-in replacement
import pathlib
from typing import Dict, List, Tuple
# from typing import TYPE_CHECKING
# if TYPE_CHECKING:
#     from Piece import Piece
class Moves:
    def __init__(self, txt_path: pathlib.Path, dims: Tuple[int, int]):
        """Initialize moves with rules from text file and board dimensions."""
        self.dims = dims  # Dimensions of the board (rows, cols)
        self.rules = self._load_rules(txt_path)  # Load movement rules from file
    
    def _load_rules(self, txt_path: pathlib.Path) -> List[Tuple[int, int]]:
        """Load movement rules from a text file."""
        rules = []
        try:
            with txt_path.open('r') as file:
                for line in file:
                    # Parse each line as a tuple of integers (e.g., "1,2" -> (1, 2))
                    parts = line.strip().split(',')
                    if len(parts) != 2:
                        raise ValueError(f"Invalid format on line: {line}")
                    rules.append((int(parts[0]), int(parts[1])))
        except Exception as e:
            raise ValueError(f"Error loading rules from {txt_path}: {e}")
        return rules

#     def get_moves(self, r: int, c: int, pos_to_piece: Dict[Tuple[int, int], 'Piece']) -> List[Tuple[int, int]]:
#         possible_moves = []
#         curr_piece = pos_to_piece.get((r, c))
#         if curr_piece is None:
#             return possible_moves

#         piece_id = curr_piece.get_id()
#         piece_type = piece_id[0]
#         curr_color = piece_id[1]

#         # 🟩 טיפול בחיילים (P)
#         if piece_type == "P":
#             direction = -1 if curr_color == "W" else 1
#             start_row = 6 if curr_color == "W" else 1

#             # צעד אחד קדימה
#             one_step = (r + direction, c)
#             if 0 <= one_step[0] < self.dims[0] and one_step not in pos_to_piece:
#                 possible_moves.append(one_step)

#                 # צעד כפול אם בשורה ההתחלתית וגם ריק
#                 two_step = (r + 2 * direction, c)
#                 if r == start_row and two_step not in pos_to_piece:
#                     if one_step not in pos_to_piece:
#                         possible_moves.append(two_step)

#             # אכילה באלכסון
#             for dc in [-1, 1]:
#                 diag_r, diag_c = r + direction, c + dc
#                 if 0 <= diag_r < self.dims[0] and 0 <= diag_c < self.dims[1]:
#                     target_piece = pos_to_piece.get((diag_r, diag_c))
#                     if target_piece and target_piece.get_id()[1] != curr_color:
#                         possible_moves.append((diag_r, diag_c))

#             return possible_moves  # אין צורך להמשיך לחלק הכללי

#         # 🟦 טיפול בשאר הכלים – לפי self.rules
#         blocked_dirs = set()

#         for dr, dc in self.rules:
#             nr = r + dr
#             nc = c + dc
#             if not (0 <= nr < self.dims[0] and 0 <= nc < self.dims[1]):
#                 continue

#             # כיוון כללי (נורמליזציה)
#             gcd = max(abs(dr), abs(dc))
#             dir_vec = (dr // gcd if gcd != 0 else 0, dc // gcd if gcd != 0 else 0)

#             if dir_vec in blocked_dirs:
#                 continue

#             target_piece = pos_to_piece.get((nr, nc))
#             if target_piece is not None:
#                 if target_piece.get_id()[1] != curr_color:
#                     possible_moves.append((nr, nc))  # אכילה
#                 blocked_dirs.add(dir_vec)  # חסימה
#             else:
#                 possible_moves.append((nr, nc))

#         return possible_moves
