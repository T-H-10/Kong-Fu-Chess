from Bus.EventBus import Event, event_bus
import cv2
import time
import numpy as np
from img import Img
from typing import Optional
import math

# class GameMessages:
#     """מחלקה לניהול הודעות מעניינות בתחילת ובסוף המשחק"""
    
#     def __init__(self):
#         self.event_bus = event_bus
#         self.current_message: Optional[str] = None
#         self.message_start_time: Optional[float] = None
#         self.message_duration = 3.0  # 5 שניות לתחילה
#         self.end_message_duration = 10.0  # 10 שניות לסיום
#         self.show_message = False
#         self.is_end_message = False  # מסמן אם זו הודעת סיום
        
#         # סגנון מינימליסטי
#         self.bg_color = (40, 35, 30)           # רקע כהה
#         self.text_color = (240, 238, 235)      # טקסט לבן חם
#         self.border_color = (120, 100, 80)     # מסגרת חומה
        
#         # פונטים
#         self.font = cv2.FONT_HERSHEY_SIMPLEX
#         self.title_scale = 1.2
#         self.thickness = 2
        
#         # הודעות מעניינות
#         self.start_messages = [
#             "⚔️ The Battle Begins! ⚔️",
#             "🏆 May the Best Player Win! 🏆", 
#             "♟️ Let the Chess Battle Commence! ♟️",
#             "🎯 Strategy and Wit Await! 🎯",
#             "⭐ The Game of Kings Starts Now! ⭐"
#         ]
        
#         self.end_messages = {
#             "white": [
#                 "👑 White Emerges Victorious! 👑",
#                 "⚡ White's Strategy Prevails! ⚡",
#                 "🌟 White Claims the Crown! 🌟"
#             ],
#             "black": [
#                 "🖤 Black Dominates the Board! 🖤", 
#                 "⚔️ Black's Power Conquers All! ⚔️",
#                 "👑 Black Rules Supreme! 👑"
#             ],
#             "draw": [
#                 "🤝 A Noble Draw! 🤝",
#                 "⚖️ Honor Shared by Both! ⚖️",
#                 "🎭 A Tale of Equal Might! 🎭"
#             ]
#         }
        
#         # הרשמה לאירועים
#         self.event_bus.subscribe("game_start", self.handle_game_start)
#         self.event_bus.subscribe("game_end", self.handle_game_end)
#     def handle_game_start(self, event: Event):
#         """מטפל באירוע תחילת המשחק"""
#         import random
#         print("Game start event received!")  # הודעת debug
#         message = random.choice(self.start_messages)
#         self.show_timed_message(message, is_end=False)
    
#     def handle_game_end(self, event: Event):
#         """מטפל באירוע סיום המשחק"""
#         import random
#         print("🏁 Game end event received!")  # הודעת debug
#         winner = event.data.get("winner", "draw").lower()
#         print(f"Winner: {winner}")  # הודעת debug
        
#         if winner in self.end_messages:
#             message = random.choice(self.end_messages[winner])
#         else:
#             message = random.choice(self.end_messages["draw"])
            
#         print(f"End message: {message}")  # הודעת debug
#         self.show_timed_message(message, is_end=True)
    
#     def show_timed_message(self, message: str, is_end: bool = False):
#         """מציג הודעה לזמן מוגדר"""
#         self.current_message = message
#         self.message_start_time = time.time()
#         self.show_message = True
#         self.is_end_message = is_end
    
#     def update(self):
#         """מעדכן את מצב ההודעה - צריך לקרוא לזה בכל פריים"""
#         if self.show_message and self.message_start_time:
#             elapsed = time.time() - self.message_start_time
#             # זמן שונה להודעות סיום
#             duration = self.end_message_duration if self.is_end_message else self.message_duration
#             if elapsed >= duration:
#                 self.show_message = False
#                 self.current_message = None
#                 self.message_start_time = None
#                 self.is_end_message = False
    
#     def draw_message(self, img: Img):
#         """מציר את ההודעה על המסך אם צריך - על כל רוחב המסך"""
#         if not self.show_message or not self.current_message:
#             return
            
#         img_height, img_width = img.img.shape[:2]
        
#         # חישוב גודל הטקסט
#         text_size = cv2.getTextSize(self.current_message, self.font, self.title_scale, self.thickness)[0]
        
#         # מיקום במרכז המסך אופקית
#         text_x = (img_width - text_size[0]) // 2
#         text_y = (img_height + text_size[1]) // 2
        
#         # רקע על כל רוחב המסך
#         bar_height = 80
#         bar_y1 = text_y - text_size[1] - 25
#         bar_y2 = text_y + 25
        
#         # ציור רקע על כל הרוחב עם שקיפות
#         overlay = img.img.copy()
#         cv2.rectangle(overlay, (0, bar_y1), (img_width, bar_y2), self.bg_color, -1)
        
#         # קווי גבול עליון ותחתון
#         cv2.line(overlay, (0, bar_y1), (img_width, bar_y1), self.border_color, 3)
#         cv2.line(overlay, (0, bar_y2), (img_width, bar_y2), self.border_color, 3)
        
#         # מיזוג עם שקיפות
#         alpha = 0.9
#         cv2.addWeighted(overlay, alpha, img.img, 1 - alpha, 0, img.img)
        
#         # ציור הטקסט במרכז
#         cv2.putText(img.img, self.current_message, (text_x, text_y), 
#                    self.font, self.title_scale, self.text_color, self.thickness)


class GameMessages:
    def __init__(self):
        self.event_bus = event_bus
        self.current_message: Optional[str] = None
        self.current_image: Optional[np.ndarray] = None
        self.message_start_time: Optional[float] = None
        self.message_duration = 3.0
        self.end_message_duration = 6.0
        self.show_message = False
        self.is_end_message = False
        
        # הגדרות הבהוב
        self.blink_speed = 2.0  # מהירות הבהוב (cycles per second)
        self.min_alpha = 0.3    # שקיפות מינימלית (לא נעלם לגמרי)
        self.max_alpha = 1.0    # שקיפות מקסימלית

        # הודעות ברירת מחדל
        self.start_message = "The battle begins"
        self.end_messages = {
            "white": "🏆 WHITE WINS! 🏆",
            "black": "🏆 BLACK WINS! 🏆", 
            "draw": "🤝 IT'S A DRAW! 🤝"
        }

        # תמונות רקע לניצחון
        self.white_win_bg = cv2.imread("../white_win.jpg")  # תמונת רקע לבן
        self.black_win_bg = cv2.imread("../black_win.jpg")  # תמונת רקע שחור
        self.draw_bg = cv2.imread("images/draw_bg.png")           # תמונת רקע תיקו

        # עיצוב טקסט מנצח
        self.win_text_style = {
            "font": cv2.FONT_HERSHEY_DUPLEX,
            "scale": 2.5,
            "thickness": 4,
            "color": (255, 255, 255),      # לבן
            "shadow_color": (0, 0, 0),     # צל שחור
            "shadow_offset": 4
        }

        # עיצוב - הודעת פתיחה (עדיין טקסט)
        self.start_style = {
            "bg_color": (10, 90, 120),
            "text_color": (255, 255, 255),
            "border_color": (255, 255, 255),
            "font": cv2.FONT_HERSHEY_SIMPLEX,
            "scale": 1.2,
            "thickness": 2
        }

        # עיצוב - הודעת סיום (לא רלוונטי כי מציגים תמונה)
        self.end_style = {}

        # הרשמה לאירועים
        self.event_bus.subscribe("game_start", self.handle_game_start)
        self.event_bus.subscribe("game_end", self.handle_game_end)

    def set_messages(self, start_message: str, white_win: str, black_win: str, draw: str):
        self.start_message = start_message
        self.end_messages = {
            "white": white_win,
            "black": black_win,
            "draw": draw
        }

    def handle_game_start(self, event: Event):
        print("Game start event received!")
        self.show_timed_message(self.start_message, is_end=False)

    def handle_game_end(self, event: Event):
        print("🏁 Game end event received!")
        winner = event.data.get("winner", "draw").lower()
        
        # בחירת תמונת רקע והודעה
        if winner == "white":
            self.current_image = self.white_win_bg
            self.current_message = self.end_messages["white"]
        elif winner == "black":
            self.current_image = self.black_win_bg
            self.current_message = self.end_messages["black"]
        else:
            self.current_image = self.draw_bg
            self.current_message = self.end_messages["draw"]

        self.show_timed_message(message=self.current_message, is_end=True)

    def show_timed_message(self, message: Optional[str], is_end: bool = False):
        self.current_message = message
        self.message_start_time = time.time()
        self.show_message = True
        self.is_end_message = is_end

    def update(self):
        if self.show_message and self.message_start_time:
            elapsed = time.time() - self.message_start_time
            duration = self.end_message_duration if self.is_end_message else self.message_duration
            if elapsed >= duration:
                self.show_message = False
                self.current_message = None
                self.current_image = None
                self.message_start_time = None
                self.is_end_message = False

    def draw_message(self, img: Img):
        if not self.show_message:
            return

        if self.is_end_message and self.current_image is not None:
            # ציור תמונת הרקע
            target_h, target_w = img.img.shape[:2]
            background = cv2.resize(self.current_image, (target_w, target_h))
            img.img[:] = background
            
            # הוספת כיתוב מהבהב
            if self.current_message:
                self._draw_blinking_text(img, self.current_message)
                
        elif self.current_message:
            # הצגת טקסט רגיל (למסך פתיחה)
            self._draw_start_message(img, self.current_message)
    
    def _draw_blinking_text(self, img: Img, text: str):
        """מציר טקסט מהבהב מעל תמונת הרקע"""
        if not self.message_start_time:
            return
            
        # חישוב עוצמת ההבהוב
        elapsed = time.time() - self.message_start_time
        blink_cycle = math.sin(elapsed * self.blink_speed * 2 * math.pi)
        # המרה מ-[-1,1] ל-[min_alpha, max_alpha]
        alpha = self.min_alpha + (self.max_alpha - self.min_alpha) * (blink_cycle + 1) / 2
        
        style = self.win_text_style
        font = style["font"]
        scale = style["scale"]
        thickness = style["thickness"]
        text_color = style["color"]
        shadow_color = style["shadow_color"]
        shadow_offset = style["shadow_offset"]
        
        img_height, img_width = img.img.shape[:2]
        text_size = cv2.getTextSize(text, font, scale, thickness)[0]
        text_x = (img_width - text_size[0]) // 2
        text_y = (img_height + text_size[1]) // 2
        
        # יצירת overlay לטקסט עם שקיפות
        overlay = img.img.copy()
        
        # ציור צל
        cv2.putText(overlay, text, (text_x + shadow_offset, text_y + shadow_offset),
                   font, scale, shadow_color, thickness + 1)
        
        # ציור הטקסט הראשי
        cv2.putText(overlay, text, (text_x, text_y),
                   font, scale, text_color, thickness)
        
        # מיזוג עם אפקט הבהוב
        cv2.addWeighted(overlay, alpha, img.img, 1 - alpha, 0, img.img)
    
    def _draw_start_message(self, img: Img, text: str):
        """מציר הודעת התחלה (הקוד הישן)"""
        style = self.start_style
        font = style["font"]
        scale = style["scale"]
        thickness = style["thickness"]
        text_color = style["text_color"]
        bg_color = style["bg_color"]
        border_color = style["border_color"]

        img_height, img_width = img.img.shape[:2]
        text_size = cv2.getTextSize(text, font, scale, thickness)[0]
        text_x = (img_width - text_size[0]) // 2
        text_y = (img_height // 2) + (text_size[1] // 2)

        bar_height = 140
        bar_y1 = (img_height - bar_height) // 2
        bar_y2 = bar_y1 + bar_height

        overlay = img.img.copy()
        cv2.rectangle(overlay, (30, bar_y1), (img_width - 30, bar_y2), bg_color, -1)
        cv2.rectangle(overlay, (30, bar_y1), (img_width - 30, bar_y2), border_color, 2)

        alpha = 0.85
        cv2.addWeighted(overlay, alpha, img.img, 1 - alpha, 0, img.img)

        shadow_offset = 2
        cv2.putText(img.img, text, (text_x + shadow_offset, text_y + shadow_offset),
                    font, scale, (0, 0, 0), thickness + 1)
        cv2.putText(img.img, text, (text_x, text_y),
                    font, scale, text_color, thickness)
