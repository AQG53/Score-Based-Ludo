# player.py

import random
import pygame
from config import PLAYER_COLORS, TILE_SIZE

class Token:
    def __init__(self, player_id, token_id, position=None):
        self.player_id = player_id
        self.token_id = token_id
        self.position = position  # Index in the board tile list
        self.in_home = True  # Initially in home
        self.captures = 0  # Track how many opponent tokens this player has captured
        self.tokens_finished = 0  # Track how many tokens reached the goal 
        self.loops_completed = 0
        self.ready_for_straight = False
        self.ready_for_final = False     
        self.steps_moved = 0


    def draw(self, screen, tile, color):
        if tile:
            offset = TILE_SIZE // 4
            offsets = [
                (-offset, -offset),
                (offset, -offset),
                (-offset, offset),
                (offset, offset)
            ]
            dx, dy = offsets[self.token_id % 4]
            center_x = tile.x + TILE_SIZE // 2 + dx
            center_y = tile.y + TILE_SIZE // 2 + dy
            radius = TILE_SIZE // 5
            pygame.draw.circle(screen, color, (center_x, center_y), radius)

    def update_status(self):
        """Update token's path access flags"""
        self.ready_for_straight = self.loops_completed >= 1
        self.ready_for_final = self.captures >= 1


class Player:
    def __init__(self, player_id, is_ai=False, color=(0, 0, 0)):
        self.id = player_id
        self.is_ai = is_ai
        self.color = color
        self.tokens = [Token(player_id, i) for i in range(4)]
        self.base_positions = []  # will be filled later
        self.captures = 0
        self.score = 0

    def get_valid_moves(self, board, dice_roll):
        """Get all valid moves considering new rules"""
        valid_moves = []
        for token in self.tokens:
            if not token.in_home:
                new_pos = (token.position + dice_roll) % board.total_outer_tiles
                if board.is_valid_move(self.id, token, new_pos):
                    valid_moves.append((token, new_pos))
        return valid_moves

