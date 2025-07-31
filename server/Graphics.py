import pathlib
import time
# from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
# import copy
from img import Img
# from Command import Command
from Board import Board


class Graphics:
    def __init__(self,
                 sprites_folder: pathlib.Path,
                 board: Board,
                 loop: bool = True,
                 fps: float = 6.0):
        self.board = board 