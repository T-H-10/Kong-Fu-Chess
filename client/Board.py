from dataclasses import dataclass
import copy
from typing import Tuple

from img import Img

@dataclass
class Board:
    cell_H_pix: int
    cell_W_pix: int
    cell_H_m: int
    cell_W_m: int
    W_cells: int
    H_cells: int
    img: Img

    def clone(self) -> "Board":
        return Board(
            cell_H_pix=self.cell_H_pix,
            cell_W_pix=self.cell_W_pix,
            cell_H_m=self.cell_H_m,
            cell_W_m=self.cell_W_m,
            W_cells=self.W_cells,
            H_cells=self.H_cells,
            img=copy.deepcopy(self.img)
        )
    def cell_to_world(self, cell: tuple[int, int]) -> tuple[int, int]:
        row, col = cell
        x = col * self.cell_W_pix
        y = row * self.cell_H_pix
        return x, y
    def algebraic_to_cell(self, notation: str) -> Tuple[int, int]:
        """
        Converts algebraic notation (e.g., "a1") to board coordinates.
        Example: "a1" -> (7, 0) if (0,0) is top-left
        """
        if len(notation) != 2:
            raise ValueError(f"Invalid algebric notation length: '{notation}'")
        col_char = notation[0].lower()
        row_char = notation[1]
        if not ('a' <= col_char <= 'h'):
            raise ValueError(f"Invalid column character: '{col_char}'")
        if not row_char.isdigit():
            raise ValueError(f"Row is not a digit: '{row_char}'")
        row_num = int(row_char)
        if not (1 <= row_num <= 8):
            raise ValueError(f"Row number out of bounds: {row_num}")
        col = ord(notation[0].lower()) - ord('a')
        row = 8 - int(notation[1])  # Assuming board is 8x8
        return row, col


    def world_to_cell(self, pos: Tuple[float, float]) -> Tuple[int, int]:
        x, y = pos
        col = int(x // self.cell_W_pix)
        row = int(y // self.cell_H_pix)
        return row, col
    

    def cell_to_algebraic(self, cell: Tuple[int, int]) -> str:
        row, col = cell
        col_letter = chr(ord('a') + col)
        row_number = str(8 - row)  # assuming 8x8 board
        return f"{col_letter}{row_number}"
