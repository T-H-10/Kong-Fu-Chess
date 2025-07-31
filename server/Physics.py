from typing import Tuple
from abc import ABC, abstractmethod
# from weakref import finalize

from Command import Command
from Board import Board
from Bus.EventBus import event_bus


class Physics(ABC):
    def __init__(self, start_cell: Tuple[int, int], board: Board, speed_m_s: float = 1.0):
        self.start_cell = start_cell
        self.board = board
        self.speed = speed_m_s * 200
        self.pos = self.board.cell_to_world(start_cell)  # (x, y) in meters
        self.end_cell = self.start_cell
        self.start_time = 0
        self.cmd = None
        self.finished = False
        self.event_bus = event_bus

    @abstractmethod
    def reset(self, cmd: Command):
        self.cmd = cmd
        self.start_time = 0  # will be set on first update

    @abstractmethod
    def update(self, now_ms: int) -> Command:
        pass

    @abstractmethod
    def can_be_captured(self) -> bool:
        pass

    @abstractmethod
    def can_capture(self) -> bool:
        pass

    def get_pos(self) -> Tuple[float, float]:
        return self.pos

    def get_pos_in_cell(self):
        return self.board.world_to_cell(self.pos)

    def is_at_destination(self, tolerance: float = 1.0) -> bool:
        """
        מחזירה True אם המיקום הנוכחי קרוב מספיק ליעד לפי פיקסלים.

        :param tolerance: טולרנס למרחק בפיקסלים (ברירת מחדל 1.0)
        """
        dx = self.pos[0] - self.end_pos[0]
        dy = self.pos[1] - self.end_pos[1]
        return dx * dx + dy * dy <= tolerance * tolerance


class IdlePhysics(Physics):
    def reset(self, cmd: Command):
        super().reset(cmd)
        self.start_cell = tuple(cmd.params[0])
        self.pos = self.board.cell_to_world(self.start_cell)

    def update(self, now_ms: int) -> Command:
        return None

    def can_be_captured(self) -> bool:
        return True

    def can_capture(self) -> bool:
        return True


from typing import Tuple
from Command import Command
from Board import Board
from Physics import Physics


class MovePhysics(Physics):
    def __init__(self, start_cell: Tuple[int, int], board: Board, speed_m_s: float = 1.0):
        super().__init__(start_cell, board, speed_m_s)
        self.start_pos = self.board.cell_to_world(start_cell)
        self.end_pos = self.start_pos
        self.end_cell = start_cell
        self.start_time = 0
        self.duration_ms = 1
        self.finished = False
        self.extra_delay_ms = 300  # הוספת 300ms לאחר סיום התנועה

    def reset(self, cmd: Command):
        self.cmd = cmd
        self.finished = False
        self.start_cell = self.board.algebraic_to_cell(cmd.params[0])
        self.end_cell = self.board.algebraic_to_cell(cmd.params[1])
        self.start_pos = self.board.cell_to_world(self.start_cell)
        self.end_pos = self.board.cell_to_world(self.end_cell)
        self.pos = self.start_pos
        dist = ((self.end_pos[0] - self.start_pos[0]) ** 2 +
                (self.end_pos[1] - self.start_pos[1]) ** 2) ** 0.5
        # חישוב הזמן הנדרש בהתבסס על המרחק והמהירות – החלק של התנועה
        self.duration_ms = max(1, int((dist / self.speed) * 1000))
        # סך כל הזמן כולל העיכוב לאחר התנועה
        self.total_duration_ms = self.duration_ms + self.extra_delay_ms
        self.event_bus.publish("piece_command", {"time":cmd.timestamp, "piece": cmd.piece_id, "description": f"move from {cmd.params[0]} to {cmd.params[1]}"})
        self.start_time = None

    def update(self, now_ms: int) -> Command:
        if self.finished:
            return self.cmd

        if self.start_time is None:
            self.start_time = now_ms

        elapsed = now_ms - self.start_time
        if elapsed < self.duration_ms:
            # תנועה נורמלית עד היעד – המיקום מתעדכן במגמה ליניארית
            t = elapsed / self.duration_ms
            self.pos = (
                self.start_pos[0] + t * (self.end_pos[0] - self.start_pos[0]),
                self.start_pos[1] + t * (self.end_pos[1] - self.start_pos[1])
            )
        elif elapsed < self.total_duration_ms:
            # סיימנו את התנועה – המיקום קבוע וממתינים לסיום הזמן הכולל
            self.pos = self.end_pos
        else:
            # עבר כל הזמן הכולל – מסמנים סיום החישוב
            self.finished = True
            return self.cmd

        return None

    def can_be_captured(self) -> bool:
        return True

    def can_capture(self) -> bool:
        return True

    def get_pos(self) -> Tuple[int, int]:
        return self.pos



class JumpPhysics(Physics):
    def reset(self, cmd: Command):

        super().reset(cmd)
        self.jump_duration = 1500  # 1 sec jump duration
        self.start_cell = self.board.algebraic_to_cell(cmd.params[0])
        self.end_cell = self.board.algebraic_to_cell(cmd.params[1])
        self.start_pos = self.board.cell_to_world(self.start_cell)
        self.end_pos = self.board.cell_to_world(self.end_cell)
        self.pos = self.start_pos  # התחלה בקואורדינטה התחלתית
        self.event_bus.publish("piece_command", {"time": cmd.timestamp, "piece": cmd.piece_id, "description": f"jump {cmd.params[0]}"})
        self.start_time = None

    def update(self, now_ms: int) -> Command:
        if self.start_time is None:
            self.start_time = now_ms

        elapsed = now_ms - self.start_time
        if elapsed >= self.jump_duration:
            # עדכון מיקום סופי
            self.pos = self.end_pos

            # מחזירים את הפקודה כדי לאפשר מעבר ל־short_rest
            return Command(
                timestamp=now_ms,
                piece_id=self.cmd.piece_id,
                type="short_rest",
                params=[self.end_cell, self.end_cell]
            )
        return None

    def can_be_captured(self) -> bool:
        return False  # "באוויר"

    def can_capture(self) -> bool:
        return False
class ShortRestPhysics(Physics):
    def reset(self, cmd: Command):
        super().reset(cmd)
        self.rest_duration = 1000  # half sec
        self.start_time = None
        self.start_cell = tuple(cmd.params[0])
        self.pos = self.board.cell_to_world(self.start_cell)

    def update(self, now_ms: int) -> Command:
        if self.start_time is None:
            self.start_time = now_ms

        if now_ms - self.start_time >= self.rest_duration:
            # מחזירים פקודת idle כמו ב־long_rest
            return Command(
                timestamp=now_ms,
                piece_id=self.cmd.piece_id,
                type="idle",
                params=[self.start_cell, self.start_cell]
            )
        return None

    def can_be_captured(self) -> bool:
        return True

    def can_capture(self) -> bool:
        return False


class LongRestPhysics(Physics):
    def reset(self, cmd: Command):
        super().reset(cmd)
        self.rest_duration = 1500  # 1.5 sec
        self.start_time = None
        self.start_cell = tuple(cmd.params[0])
        self.pos = self.board.cell_to_world(self.start_cell)

    def update(self, now_ms: int) -> Command:
        if self.start_time is None:
            self.start_time = now_ms

        # if now_ms - self.start_time >= self.rest_duration:
        #     return self.cmd

        if now_ms - self.start_time >= self.rest_duration:
            return Command(
                timestamp=now_ms,
                piece_id=self.cmd.piece_id,
                type="idle",
                params=[self.start_cell, self.start_cell]
            )
        return None

    def can_be_captured(self) -> bool:
        return True

    def can_capture(self) -> bool:
        return False