# config.py

# Number of players in the game (can be dynamically set later)
MAX_PLAYERS = 5

# Dice rolls per turn
DICE_PER_TURN = 2

# How often warp zones should change (in turns)
WARP_REFRESH_TURNS = 3

# Board size (custom board later)
BOARD_WIDTH = 1000
BOARD_HEIGHT = 800

# Colors (RGB)
PLAYER_COLORS = {
    0: (255, 0, 0),     # Red
    1: (0, 255, 0),     # Green
    2: (0, 0, 255),     # Blue
    3: (255, 255, 0),   # Yellow
    4: (128, 0, 128),   # Purple
}

BACKGROUND_COLOR = (250, 250, 250)
TILE_SIZE = 40
