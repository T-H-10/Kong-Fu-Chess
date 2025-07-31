import pathlib
import time
from typing import List, Dict, Tuple, Optional
from img import Img
from Board import Board


class Graphics:
    def __init__(self,
                 sprites_folder: pathlib.Path,
                 board: Board,
                 loop: bool = True,
                 fps: float = 6.0):
        self.board = board 