from Bus.EventBus import Event
import cv2
from typing import List
from img import Img

class CommandLog:
    def __init__(self):
        self.white_moves: List[str] = []
        self.black_moves: List[str] = []
        
        # סגנון מינימליסטי - שחור לבן ועץ
        self.bg_color = (240, 238, 235)          # לבן חם (קרם)
        self.border_color = (80, 70, 60)         # חום כהה (עץ)
        self.text_color = (40, 35, 30)           # כמעט שחור
        self.title_color = (60, 50, 40)          # חום כהה
        self.accent_line = (120, 100, 80)        # חום בינוני
        
        # פונטים פשוטים
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.title_scale = 0.7
        self.text_scale = 0.5
        self.thickness = 1

    def handle_command(self, event: Event):
        piece = event.data["piece"]
        description = event.data["description"]
        time_val = event.data.get("time", 0)
        
        # פורמט זמן פשוט
        if isinstance(time_val, (int, float)) and time_val > 1000:
            seconds = int(time_val) // 1000
            minutes = seconds // 60
            secs = seconds % 60
            time_str = f"{minutes:02d}:{secs:02d}"
        else:
            time_str = "00:00"
            
        # טקסט פשוט ונקי
        command_text = f"{time_str} | {piece} - {description}"
        
        # הוספה לרשימה המתאימה
        if len(piece) > 1 and piece[1] == "W":  # כלי לבן
            self.white_moves.append(command_text)
            if len(self.white_moves) > 10:  # רק 10 פעולות אחרונות
                self.white_moves.pop(0)
        else:  # כלי שחור
            self.black_moves.append(command_text)
            if len(self.black_moves) > 10:
                self.black_moves.pop(0)
                
    def draw_moves_panel(self, img: Img, x: int, y: int, width: int, height: int, moves: List[str], title: str):
        """מציר לוח מהלכים פשוט ונקי"""
        # רקע לבן חם
        cv2.rectangle(img.img, (x, y), (x + width, y + height), self.bg_color, -1)
        
        # מסגרת פשוטה
        cv2.rectangle(img.img, (x, y), (x + width, y + height), self.border_color, 2)
        
        # כותרת פשוטה
        title_size = cv2.getTextSize(title, self.font, self.title_scale, self.thickness)[0]
        title_x = x + (width - title_size[0]) // 2
        cv2.putText(img.img, title, (title_x, y + 30), self.font, self.title_scale, self.title_color, self.thickness)
        
        # קו מפריד דק
        cv2.line(img.img, (x + 15, y + 40), (x + width - 15, y + 40), self.accent_line, 1)
        
        # המהלכים
        line_height = 25
        start_y = y + 60
        
        for i, move in enumerate(moves[-8:]):  # 8 מהלכים אחרונים
            move_y = start_y + i * line_height
            if move_y < y + height - 15:
                cv2.putText(img.img, move, (x + 15, move_y), self.font, 
                           self.text_scale, self.text_color, self.thickness)
                           
    def draw_ui(self, img: Img):
        """מציר את כל ה-UI של היסטוריית הפעולות על התמונה"""
        img_height, img_width = img.img.shape[:2]
        
        # פאנל מהלכים לבן (שמאל) - רחב יותר
        moves_width = 380
        moves_height = 450
        white_moves_x = 30
        white_moves_y = 180
        self.draw_moves_panel(img, white_moves_x, white_moves_y, moves_width, moves_height, 
                             self.white_moves, "White Moves")
        
        # פאנל מהלכים שחור (ימין) - רחב יותר
        black_moves_x = img_width - moves_width - 20
        black_moves_y = 180
        self.draw_moves_panel(img, black_moves_x, black_moves_y, moves_width, moves_height, 
                             self.black_moves, "Black Moves")