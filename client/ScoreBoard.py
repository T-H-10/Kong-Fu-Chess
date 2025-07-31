from Bus.EventBus import Event
import cv2
from img import Img

# class Piece_Values:
#     """מחלקה המגדירה את ערכי הכלים"""
#     P = 1  # Pawn
#     N = 3  # Knight
#     B = 3  # Bishop
#     R = 5  # Rook
#     Q = 9  # Queen

class ScoreBoard:
    def __init__(self):
        self.piece_values = {
            "P": 1, "N": 3, "B": 3, "R": 5, "Q": 9
        }
        self.scoreB = 0
        self.scoreW = 0
        
        # סגנון מינימליסטי - שחור לבן ועץ
        self.bg_color = (245, 243, 240)          # לבן חם
        self.border_color = (80, 70, 60)         # חום כהה
        self.text_color = (40, 35, 30)           # כמעט שחור
        self.title_color = (60, 50, 40)          # חום כהה
        self.score_color = (100, 85, 70)         # חום בינוני
        
        # פונטים פשוטים
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.title_scale = 0.8
        self.score_scale = 0.6
        self.thickness = 2

    def handle_capture(self, event: Event):
        piece = event.data["piece"]
        piece_type = piece[0]
        if piece[1] == "W":
            self.scoreB += self.piece_values.get(piece_type, 0)
            # הסרנו את ה-print
        else:
            self.scoreW += self.piece_values.get(piece_type, 0)
            # הסרנו את ה-print
            
    def draw_black_score_panel(self, img: Img, x: int, y: int, width: int, height: int):
        """מציר את לוח הניקוד של השחור למעלה במסך - בשורה אחת ללא מסגרת"""
        # טקסט ניקוד בשורה אחת
        score_text = f"Black Score: {self.scoreB}"
        text_size = cv2.getTextSize(score_text, self.font, self.title_scale, self.thickness)[0]
        text_x = x + (width - text_size[0]) // 2
        cv2.putText(img.img, score_text, (text_x, y + 25), self.font, self.title_scale, self.text_color, self.thickness)
        
    def draw_white_score_panel(self, img: Img, x: int, y: int, width: int, height: int):
        """מציר את לוח הניקוד של הלבן למטה במסך - בשורה אחת ללא מסגרת"""
        # טקסט ניקוד בשורה אחת
        score_text = f"White Score: {self.scoreW}"
        text_size = cv2.getTextSize(score_text, self.font, self.title_scale, self.thickness)[0]
        text_x = x + (width - text_size[0]) // 2
        cv2.putText(img.img, score_text, (text_x, y + 25), self.font, self.title_scale, self.text_color, self.thickness)
