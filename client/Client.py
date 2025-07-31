import asyncio
import websockets
import json
import threading
import queue
import time
from pathlib import Path
from Board import Board
from Game import Game
from img import Img

player_color = None
game = None
websocket_connection = None
move_queue = queue.Queue()  # תור למהלכים שצריך לשלוח

async def ws_handler():
    global player_color, game, websocket_connection

    uri = "ws://localhost:8765"
    try:
        print(f"🔌 מנסה להתחבר ל-{uri}...")
        async with websockets.connect(uri) as ws:
            print("✅ התחברתי לשרת!")
            websocket_connection = ws
            
            # מקבל צבע מהשרת
            msg = json.loads(await ws.recv())
            if msg.get("type") == "assign_color":
                player_color = msg["color"]
                print(f"🎨 קיבלתי צבע: {player_color}")
                
                # המתנה שהמשחק יהיה מוכן
                while game is None:
                    await asyncio.sleep(0.1)
                    
                # עדכון המשחק עם הצבע שלי
                game.set_player_color(player_color)
                print(f"✅ עדכנתי את המשחק עם צבע: {player_color}")
            else:
                print("שגיאה בקבלת הצבע")
                return

            # יצירת task לשליחת מהלכים
            send_task = asyncio.create_task(send_moves())
            receive_task = asyncio.create_task(receive_updates(ws))
            
            # המתן לשני ה-tasks
            try:
                await asyncio.gather(send_task, receive_task)
            except Exception as e:
                print(f"שגיאה בטיפול WebSocket: {e}")
            finally:
                websocket_connection = None
                
    except ConnectionRefusedError:
        print("❌ שגיאה: לא ניתן להתחבר לשרת. וודא שהשרת רץ על localhost:8765")
    except Exception as e:
        print(f"❌ שגיאת חיבור: {e}")
        websocket_connection = None

async def send_moves():
    """שולח מהלכים מהתור לשרת"""
    global websocket_connection
    
    while websocket_connection:
        try:
            # בדיקה אם יש מהלך חדש לשלוח
            if not move_queue.empty():
                move_data = move_queue.get_nowait()
                await websocket_connection.send(json.dumps(move_data))
                print(f"📤 שלחתי מהלך: {move_data}")
            
            await asyncio.sleep(0.1)  # המתנה קצרה
        except queue.Empty:
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"שגיאה בשליחת מהלך: {e}")
            break

async def receive_updates(ws):
    """מקבל עדכונים מהשרת"""
    try:
        async for message in ws:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "board_update":
                # עדכון מצב הלוח במשחק
                if game:
                    game.apply_server_update(data.get("board", {}))
                print(f"📥 קיבלתי עדכון לוח מהשרת")
                
            elif msg_type == "move":
                # מהלך מאושר מהשרת - זה המהלך שהשרת בדק ואישר
                if game:
                    game.apply_opponent_move(data)
                action = data.get("action", "move")
                player = data.get("player_color")
                if action == "move":
                    from_pos = data.get("from")
                    to_pos = data.get("to")
                    piece = data.get("piece")
                    print(f"🎯 השרת אישר מהלך: {player} - {piece} מ-{from_pos} ל-{to_pos}")
                elif action == "jump":
                    position = data.get("position")
                    piece = data.get("piece")
                    print(f"🦘 השרת אישר קפיצה: {player} - {piece} ב-{position}")
                
            elif msg_type == "move_rejected":
                # מהלך נדחה ע"י השרת
                message = data.get("message")
                print(f"❌ השרת דחה מהלך: {message}")
                
            elif msg_type == "jump_rejected":
                # קפיצה נדחתה ע"י השרת
                message = data.get("message")
                print(f"❌ השרת דחה קפיצה: {message}")
                
            elif msg_type == "error":
                print(f"⚠️ שגיאה מהשרת: {data.get('message')}")
                
            else:
                print(f"❓ הודעה לא מזוהה מהשרת: {data}")
                
    except Exception as e:
        print(f"❌ שגיאה בקבלת עדכונים: {e}")

def send_move_to_server(move_data):
    """פונקציה להוספת מהלך לתור השליחה"""
    global move_queue
    move_queue.put(move_data)
    print(f"➕ הוספתי מהלך לתור: {move_data}")

async def run_ws():
    await ws_handler()

def start_ws():
    asyncio.run(run_ws())

if __name__ == "__main__":
    base_path = Path(__file__).resolve().parent
    pieces_root = base_path.parent / "pieces"  # שימוש בתיקיית pieces במקום PIECES
    placement_csv = base_path / "board.csv"

    board = Board(
        cell_H_pix=80,
        cell_W_pix=80,
        cell_H_m=1,
        cell_W_m=1,
        W_cells=8,
        H_cells=8,
        img=Img().read("board.png", size=(640, 640))
    )
    
    print("🎮 יוצר משחק...")
    game = Game(board, pieces_root, placement_csv)
    
    print("🔗 מגדיר חיבור רשת...")
    # חיבור פונקציית שליחה לרשת
    game.set_network_callback(send_move_to_server)
    
    print("🌐 מתחיל חיבור WebSocket...")
    # מריצים את קישור הרשת ב־Thread נפרד
    ws_thread = threading.Thread(target=start_ws, daemon=True)
    ws_thread.start()
    
    # המתנה קצרה שהרשת תתחבר
    print("⏳ ממתין לחיבור רשת...")
    time.sleep(2)
    
    print("🚀 מפעיל את המשחק...")
    # מפעילים את חלון המשחק
    game.run()


# import asyncio
# import websockets
# import json
# import threading
# import queue
# import time
# from pathlib import Path
# from Board import Board
# from Game import Game
# from img import Img

# player_color = None
# game = None
# websocket_connection = None
# move_queue = queue.Queue()  # תור למהלכים שצריך לשלוח

# async def ws_handler():
#     global player_color, game, websocket_connection

#     uri = "ws://localhost:8765"
#     try:
#         print(f"🔌 מנסה להתחבר ל-{uri}...")
#         async with websockets.connect(uri) as ws:
#             print("✅ התחברתי לשרת!")
#             websocket_connection = ws
            
#             # מקבל צבע מהשרת
#             msg = json.loads(await ws.recv())
#             if msg.get("type") == "assign_color":
#                 player_color = msg["color"]
#                 print(f"🎨 קיבלתי צבע: {player_color}")
                
#                 # המתנה שהמשחק יהיה מוכן
#                 while game is None:
#                     await asyncio.sleep(0.1)
                    
#                 # עדכון המשחק עם הצבע שלי
#                 game.set_player_color(player_color)
#                 print(f"✅ עדכנתי את המשחק עם צבע: {player_color}")
#             else:
#                 print("שגיאה בקבלת הצבע")
#                 return

#             # יצירת task לשליחת מהלכים
#             send_task = asyncio.create_task(send_moves())
#             receive_task = asyncio.create_task(receive_updates(ws))
            
#             # המתן לשני ה-tasks
#             try:
#                 await asyncio.gather(send_task, receive_task)
#             except Exception as e:
#                 print(f"שגיאה בטיפול WebSocket: {e}")
#             finally:
#                 websocket_connection = None
                
#     except ConnectionRefusedError:
#         print("❌ שגיאה: לא ניתן להתחבר לשרת. וודא שהשרת רץ על localhost:8765")
#     except Exception as e:
#         print(f"❌ שגיאת חיבור: {e}")
#         websocket_connection = None

# async def send_moves():
#     """שולח מהלכים מהתור לשרת"""
#     global websocket_connection
    
#     while websocket_connection:
#         try:
#             # בדיקה אם יש מהלך חדש לשלוח
#             if not move_queue.empty():
#                 move_data = move_queue.get_nowait()
#                 await websocket_connection.send(json.dumps(move_data))
#                 print(f"📤 שלחתי מהלך: {move_data}")
            
#             await asyncio.sleep(0.1)  # המתנה קצרה
#         except queue.Empty:
#             await asyncio.sleep(0.1)
#         except Exception as e:
#             print(f"שגיאה בשליחת מהלך: {e}")
#             break

# async def receive_updates(ws):
#     """מקבל עדכונים מהשרת"""
#     try:
#         async for message in ws:
#             data = json.loads(message)
#             if data.get("type") == "update":
#                 # עדכון מצב הלוח במשחק
#                 if game:
#                     game.apply_server_update(data)
#                 print(f"📥 קיבלתי עדכון: {data}")
#             elif data.get("type") == "move":
#                 # עדכון מהלך ספציפי
#                 if game:
#                     game.apply_opponent_move(data)
#                 print(f"🎯 קיבלתי מהלך מהיריב: {data}")
#     except Exception as e:
#         print(f"שגיאה בקבלת עדכונים: {e}")

# def send_move_to_server(move_data):
#     """פונקציה להוספת מהלך לתור השליחה"""
#     global move_queue
#     move_queue.put(move_data)
#     print(f"➕ הוספתי מהלך לתור: {move_data}")

# async def run_ws():
#     await ws_handler()

# def start_ws():
#     asyncio.run(run_ws())

# if __name__ == "__main__":
#     base_path = Path(__file__).resolve().parent
#     pieces_root = base_path.parent / "PIECES"
#     placement_csv = base_path / "board.csv"

#     board = Board(
#         cell_H_pix=80,
#         cell_W_pix=80,
#         cell_H_m=1,
#         cell_W_m=1,
#         W_cells=8,
#         H_cells=8,
#         img=Img().read("board.png", size=(640, 640))
#     )
    
#     print("🎮 יוצר משחק...")
#     game = Game(board, pieces_root, placement_csv)
    
#     print("🔗 מגדיר חיבור רשת...")
#     # חיבור פונקציית שליחה לרשת
#     game.set_network_callback(send_move_to_server)
    
#     print("🌐 מתחיל חיבור WebSocket...")
#     # מריצים את קישור הרשת ב־Thread נפרד
#     ws_thread = threading.Thread(target=start_ws, daemon=True)
#     ws_thread.start()
    
#     # המתנה קצרה שהרשת תתחבר
#     print("⏳ ממתין לחיבור רשת...")
#     time.sleep(2)
    
#     print("🚀 מפעיל את המשחק...")
#     # מפעילים את חלון המשחק
#     game.run()