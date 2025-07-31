import asyncio
import websockets
import json
from pathlib import Path
from Board import Board
from Game import Game

clients = {}  # websocket -> color ("white" או "black")

# אתחול המשחק בצד השרת
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
    img=None  # אין צורך בתמונה בשרת
)

game = Game(board, pieces_root, placement_csv)

async def notify_all():
    """שליחת מצב הלוח המעודכן לכל הלקוחות"""
    if clients:
        board_state = game.get_board_state()
        msg = json.dumps({"type": "board_update", "board": board_state})
        await asyncio.gather(*[ws.send(msg) for ws in clients])

async def handle_client(websocket):
    # global clients
    client_id = id(websocket)
    
    # הקצאת צבע
    colors_in_use = [c["color"] for c in clients.values()]
    if "white" not in colors_in_use:
        clients[client_id] = {"ws": websocket, "color": "white"}
        await websocket.send(json.dumps({"type": "assign_color", "color": "white"}))
        print("✅ לקוח לבן התחבר")
    elif "black" not in colors_in_use:
        clients[client_id] = {"ws": websocket, "color": "black"}
        await websocket.send(json.dumps({"type": "assign_color", "color": "black"}))
        print("✅ לקוח שחור התחבר")
    else:
        await websocket.send(json.dumps({"type": "error", "message": "כבר יש 2 שחקנים"}))
        await websocket.close()
        return
    # # הקצאת צבע ללקוח החדש
    # if "white" not in clients.values():
    #     clients[websocket] = "white"
    #     await websocket.send(json.dumps({"type": "assign_color", "color": "white"}))
    #     print("✅ לקוח לבן התחבר")
    # elif "black" not in clients.values():
    #     clients[websocket] = "black"
    #     await websocket.send(json.dumps({"type": "assign_color", "color": "black"}))
    #     print("✅ לקוח שחור התחבר")
    # else:
    #     await websocket.send(json.dumps({"type": "error", "message": "כבר יש 2 שחקנים"}))
    #     await websocket.close()
    #     return

    print(f"📊 כמות לקוחות מחוברים: {len(clients)}")

    try:
        async for message in websocket:
            print(f"📨 קיבלתי הודעה: {message}")
            data = json.loads(message)

            action = data.get("action")
            player_color = data.get("player_color")

            if action == "move":
                from_pos = data.get("from")
                to_pos = data.get("to")
                piece_id = data.get("piece", "unknown")  # קבלת מזהה הכלי

                print(f"📥 מעבד מהלך מ-{player_color}: {piece_id} מ-{from_pos} ל-{to_pos}")

                # בדיקת חוקיות המהלך בשרת
                success, msg_text = game.handle_move(player_color, from_pos, to_pos)

                if success:
                    # עדכון המשחק
                    game.update_server()
                    
                    print(f"✅ מהלך חוקי! מעדכן את כל הלקוחות")
                    
                    # שליחת המהלך המאושר לכל הלקוחות (כולל הפרטים המלאים)
                    move_msg = json.dumps({
                        "type": "move",
                        "action": "move",
                        "from": from_pos,
                        "to": to_pos,
                        "piece": piece_id,
                        "player_color": player_color
                    })
                    
                    for client_ws in clients:
                        try:
                            await client_ws.send(move_msg)
                        except:
                            pass
                    
                    # עדכון מצב הלוח לכל הלקוחות
                    await notify_all()
                else:
                    # מהלך לא חוקי - שליחת שגיאה רק לשחקן ששלח
                    print(f"❌ מהלך לא חוקי: {msg_text}")
                    await websocket.send(json.dumps({
                        "type": "move_rejected", 
                        "message": msg_text
                    }))

            elif action == "jump":
                position = data.get("position")
                piece_id = data.get("piece", "unknown")  # קבלת מזהה הכלי

                print(f"🦘 מעבד קפיצה מ-{player_color}: {piece_id} ב-{position}")

                success, msg_text = game.handle_jump(player_color, position)

                if success:
                    game.update_server()
                    
                    print(f"✅ קפיצה חוקית! מעדכן את כל הלקוחות")
                    
                    # שליחת הקפיצה המאושרת לכל הלקוחות (כולל הפרטים המלאים)
                    jump_msg = json.dumps({
                        "type": "move",
                        "action": "jump",
                        "piece": piece_id,
                        "position": position,
                        "player_color": player_color
                    })
                    
                    for client_ws in clients:
                        try:
                            await client_ws.send(jump_msg)
                        except:
                            pass
                    
                    await notify_all()
                else:
                    print(f"❌ קפיצה לא חוקית: {msg_text}")
                    await websocket.send(json.dumps({
                        "type": "jump_rejected", 
                        "message": msg_text
                    }))

            else:
                await websocket.send(json.dumps({"type": "error", "message": "פעולה לא מוכרת"}))

    except websockets.exceptions.ConnectionClosed:
        print(f"❌ לקוח {clients.get(websocket)} התנתק")
    finally:
        if websocket in clients:
            del clients[websocket]
            print(f"📊 כמות לקוחות נותרים: {len(clients)}")

async def main():
    print("🚀 מתחיל שרת Kong Fu Chess עם לוגיקת משחק מלאה...")
    print(f"🎮 מצב משחק: {len(game.pieces)} כלים טעונים")
    print(f"📁 קובץ CSV: {placement_csv}")
    
    async with websockets.serve(handle_client, "localhost", 8765):
        print("✅ שרת רץ על ws://localhost:8765")
        print("🧠 השרת יבדוק חוקיות כל מהלך ויחזיק את מצב הלוח האמיתי")
        print("⏳ ממתין ללקוחות...")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
