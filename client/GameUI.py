import cv2
from CommandLog import CommandLog
from ScoreBoard import ScoreBoard
from img import Img
from typing import Optional
from GameMessages import GameMessages
from GameSounds import GameSounds
from Bus.EventBus import event_bus

class GameUI:
    """מחלקה אחראית על הצגת כל ה-UI של המשחק בסגנון מינימליסטי"""
    
    def __init__(self, command_log=None, scoreboard=None):
        self.command_log = CommandLog()
        self.scoreboard = ScoreBoard()
        self.game_messages = GameMessages() 
        self.game_sounds = GameSounds()  # הוספת מערכת הקולות
        self.event_bus = event_bus
        self.event_bus.subscribe("game_start", self.game_messages.handle_game_start)
        self.event_bus.subscribe("game_end", self.game_messages.handle_game_end)
        self.event_bus.subscribe("piece_captured", self.scoreboard.handle_capture)
        self.event_bus.subscribe("piece_command", self.command_log.handle_command)
    
    def draw_all_ui(self, frame: Img):
        """מציגה את כל ה-UI על הפריים בסגנון נקי"""
        # עדכון ההודעות
        self.game_messages.update()
        
        # הוספת היסטוריית הפעולות
        if self.command_log:
            self.command_log.draw_ui(frame)
        
        # הוספת לוחות ניקוד נפרדים - בשורה אחת ללא מסגרת
        if self.scoreboard:
            img_height, img_width = frame.img.shape[:2]
            score_width = 200
            score_height = 40
            
            # ניקוד שחור למעלה במסך
            black_score_x = (img_width - score_width) // 2
            black_score_y = 20
            self.scoreboard.draw_black_score_panel(frame, black_score_x, black_score_y, score_width, score_height)
            
            # ניקוד לבן למטה במסך
            white_score_x = (img_width - score_width) // 2
            white_score_y = img_height - score_height - 20
            self.scoreboard.draw_white_score_panel(frame, white_score_x, white_score_y, score_width, score_height)
        
        # הוספת הודעות המשחק (אחרונות כדי שיופיעו מעל הכל)
        self.game_messages.draw_message(frame)
    
    def cleanup(self):
        """ניקוי משאבים"""
        if hasattr(self, 'game_sounds'):
            self.game_sounds.cleanup()
