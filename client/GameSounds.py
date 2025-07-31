from Bus.EventBus import Event, event_bus
import pygame
import random
import pathlib
from typing import Dict, List
import threading
import time

class GameSounds:
    
    def __init__(self, sounds_folder: str = "snd"):
        self.sounds_folder = pathlib.Path("..") / sounds_folder
        self.event_bus = event_bus
        
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.last_sound_time = {}
        self.sound_cooldown = 0.1  # 100ms cooldown

        self.capture_sounds = ["capture.wav", "capture2.wav", "capture3.wav", "capture4.wav"]
        self.start_sounds = ["Ready.wav", "Steady.wav", "Go!.wav", "game_start.wav"]
        self.move_sounds = ["move.wav"]
        self.jump_sounds = ["jump.wav"]
        self.victory_sounds = ["victory.wav"]
        self.promotion_sounds = ["victory.wav", "capture.wav"]  # קול מיוחד לקידום
        self.error_sounds = ["error.wav"]

        try:
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=1024)
            pygame.mixer.init()

            pygame.mixer.get_init()
            self.sound_enabled = True
            print("🔊 Sound system initialized successfully!")

            self._load_sounds()
        except Exception as e:
            print(f"⚠️ Sound system failed to initialize: {e}")
            print("🔇 Running in silent mode")
            self.sound_enabled = False

        self._subscribe_to_events()
    
    def _load_sounds(self):
        if not self.sound_enabled:
            return
            
        all_sound_files = (self.capture_sounds + self.start_sounds + 
                          self.move_sounds + self.jump_sounds + 
                          self.victory_sounds + self.promotion_sounds + self.error_sounds)
        
        for sound_file in all_sound_files:
            sound_path = self.sounds_folder / sound_file
            if sound_path.exists():
                try:
                    self.sounds[sound_file] = pygame.mixer.Sound(str(sound_path))
                    print(f"✅ Loaded sound: {sound_file}")
                except Exception as e:
                    print(f"❌ Failed to load {sound_file}: {e}")
            else:
                print(f"⚠️ Sound file not found: {sound_path}")
    
    def _subscribe_to_events(self):
        self.event_bus.subscribe("game_start", self.handle_game_start)
        self.event_bus.subscribe("game_end", self.handle_game_end)
        self.event_bus.subscribe("piece_command", self.handle_piece_command)
        self.event_bus.subscribe("piece_captured", self.handle_piece_captured)
        self.event_bus.subscribe("piece_move", self.handle_piece_move)
        self.event_bus.subscribe("piece_jump", self.handle_piece_jump)
        print("🎵 Subscribed to game events for sound effects")
    
    def _can_play_sound(self, sound_type: str) -> bool:
        current_time = time.time()
        if sound_type in self.last_sound_time:
            if current_time - self.last_sound_time[sound_type] < self.sound_cooldown:
                return False
        self.last_sound_time[sound_type] = current_time
        return True
    
    def play_sound(self, sound_files: List[str], volume: float = 0.7):
        if not self.sound_enabled or not sound_files:
            return
            
        try:
            # בחירת קול רנדומלי
            sound_file = random.choice(sound_files)
            if sound_file in self.sounds:
                sound = self.sounds[sound_file]
                sound.set_volume(volume)
                sound.play()
                print(f"🎵 Playing: {sound_file}")
        except Exception as e:
            print(f"❌ Error playing sound: {e}")
    
    def handle_game_start(self, event: Event):
        if self._can_play_sound("game_start"):
            print("🎮 Game start sound triggered!")
            # נגן רצף קולות התחלה
            threading.Thread(target=self._play_start_sequence, daemon=True).start()
    
    def _play_start_sequence(self):
        try:
            # Ready
            if "Ready.wav" in self.sounds:
                self.sounds["Ready.wav"].set_volume(0.8)
                self.sounds["Ready.wav"].play()
                time.sleep(1.2)
            
            # Steady
            if "Steady.wav" in self.sounds:
                self.sounds["Steady.wav"].set_volume(0.8)
                self.sounds["Steady.wav"].play()
                time.sleep(1.2)
            
            # Go!
            if "Go!.wav" in self.sounds:
                self.sounds["Go!.wav"].set_volume(0.9)
                self.sounds["Go!.wav"].play()
        except Exception as e:
            print(f"❌ Error in start sequence: {e}")
    
    def handle_game_end(self, event: Event):
        if self._can_play_sound("game_end"):
            print("🏁 Game end sound triggered!")
            self.play_sound(self.victory_sounds, volume=0.8)
    
    def handle_piece_command(self, event: Event):
        if not self._can_play_sound("piece_command"):
            return
            
        description = event.data.get("description", "").lower()
        print(f"🎵 Piece command: {description}")
        
        if "jump" in description:
            self.play_sound(self.jump_sounds, volume=0.6)
        elif "move" in description:
            self.play_sound(self.move_sounds, volume=0.5)
    
    def handle_piece_captured(self, event: Event):
        if self._can_play_sound("piece_captured"):
            print("⚔️ Piece captured sound triggered!")
            self.play_sound(self.capture_sounds, volume=0.7)
    
    def handle_piece_move(self, event: Event):
        if self._can_play_sound("piece_move"):
            print("👣 Piece move sound triggered!")
            self.play_sound(self.move_sounds, volume=0.5)
    
    def handle_piece_jump(self, event: Event):
        if self._can_play_sound("piece_jump"):
            print("🦘 Piece jump sound triggered!")
            self.play_sound(self.jump_sounds, volume=0.6)
    
    def cleanup(self):
        if self.sound_enabled:
            pygame.mixer.quit()
            print("🔇 Sound system cleaned up")
