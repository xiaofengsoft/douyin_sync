import threading
import pygame
def play_sound():
    """
    播放提示音
    """
    def _play():
        pygame.mixer.init()
        pygame.mixer.music.load('data/sound.mp3')
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.quit()
    threading.Thread(target=_play, daemon=True).start()
    
if __name__ == "__main__":
    play_sound()