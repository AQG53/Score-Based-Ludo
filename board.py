import pygame
import random
import math
from config import TILE_SIZE, PLAYER_COLORS
from pygame.color import Color

class Tile:
    def __init__(self, x, y, index):
        self.x = x
        self.y = y
        self.index = index
        self.is_warp = False
        self.is_path = False
        self.path_color = None
        self.has_trail = False
        self.trail_color = None
        self.rect = pygame.Rect(x+4, y+4, TILE_SIZE-8, TILE_SIZE-8)

    def draw(self, screen, goal_index=None):
        # Draw trail first (if exists)
        if self.has_trail and self.trail_color:
            pygame.draw.rect(screen, self.trail_color, self.rect, border_radius=4)
        
        # Rest of your existing draw code...
        if self.index == goal_index:
            color = (255, 215, 0)  # Gold for center goal
        elif self.is_warp:
            color = (255, 192, 203)
        elif self.is_path and self.path_color is not None:
            color = self.path_color
        else:
            color = (200, 200, 200)

        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 1)


class Board:
    def __init__(self):
        self.tiles = []
        self.player_start_tiles = {}
        self.player_base_tiles = {}
        self.player_entry_tiles = {}
        self.center_goal_index = None
        self.warp_indices = []
        self.goal_tile_index = None
        self.player_trail_positions = {}
        self._initialize_board()
        self.total_outer_tiles = 40
        self.straight_path_length = 6

    def update_trail(self, player_id, position):
        """Update the trail for a player moving along their straight path"""
        # Clear previous trail for this player
        if player_id in self.player_trail_positions:
            for idx in self.player_trail_positions[player_id]:
                if 0 <= idx < len(self.tiles):
                    self.tiles[idx].has_trail = False
            
        # If position is in the player's straight path, set trail
        if player_id in self.player_entry_tiles and position in self.player_entry_tiles[player_id]:
            path_index = self.player_entry_tiles[player_id].index(position)
            # Mark all tiles from start of path up to current position
            trail_indices = self.player_entry_tiles[player_id][:path_index + 1]
            self.player_trail_positions[player_id] = trail_indices
            for idx in trail_indices:
                if 0 <= idx < len(self.tiles):
                    self.tiles[idx].has_trail = True
                    self.tiles[idx].trail_color = list(PLAYER_COLORS.values())[player_id]
        else:
            self.player_trail_positions[player_id] = []

    def _initialize_board(self):
        """Initialize all board components"""
        self._create_pentagon_path()
        self._create_base_tiles()
        self._create_center_tile()
        self._create_entry_paths()
        self.update_warp_zones()  # Initialize warp zones

    def _create_pentagon_path(self):
        """Create the outer pentagon path"""
        center_x, center_y = 400, 400
        radius_outer = 250
        side_length = 8
        index = 0

        def get_point_on_pentagon(angle_deg, radius):
            angle_rad = math.radians(angle_deg)
            x = center_x + radius * math.cos(angle_rad)
            y = center_y - radius * math.sin(angle_rad)
            return int(x), int(y)

        outer_corners = [get_point_on_pentagon(90 + i * 72, radius_outer) for i in range(5)]

        for i in range(5):
            start_point = outer_corners[i]
            end_point = outer_corners[(i + 1) % 5]
            for j in range(side_length):
                t = j / side_length
                x = int((1 - t) * start_point[0] + t * end_point[0])
                y = int((1 - t) * start_point[1] + t * end_point[1])
                self.tiles.append(Tile(x, y, index))
                index += 1
            self.player_start_tiles[i] = self.tiles[i * side_length].index

    def _create_base_tiles(self):
        """Create base tiles for each player"""
        base_offset = 2
        for i in range(5):
            start_index = i * 8  # 8 tiles per side
            base_x = self.tiles[start_index + base_offset].x
            base_y = self.tiles[start_index + base_offset].y
            self.player_base_tiles[i] = (base_x, base_y)

    def _create_center_tile(self):
        """Create the center goal tile"""
        center_x, center_y = 400, 400
        self.center_goal_index = len(self.tiles)
        center_tile = Tile(center_x, center_y, self.center_goal_index)
        self.tiles.append(center_tile)
        self.goal_tile_index = self.center_goal_index

    def _create_entry_paths(self):
        """Create straight paths from each base to center"""
        center_x, center_y = 400, 400
        path_length = 6  # Number of tiles in the straight path
        player_colors = list(PLAYER_COLORS.values())
        
        for player_id in range(5):
            # Get the actual starting tile (corner of pentagon)
            start_index = self.player_start_tiles[player_id]
            start_tile = self.tiles[start_index]
            start_x, start_y = start_tile.x, start_tile.y
            
            # Create lighter version of player color
            original_color = Color(player_colors[player_id])
            light_color = Color(
                min(255, original_color.r + 150),
                min(255, original_color.g + 150),
                min(255, original_color.b + 150)
            )
            
            # Calculate direction vector from start to center
            dx = (center_x - start_x) / (path_length - 1)
            dy = (center_y - start_y) / (path_length - 1)
            
            entry_path = []
            
            # Create path tiles starting from the corner tile
            for step in range(path_length):
                x = start_x + dx * step
                y = start_y + dy * step
                
                # For the first tile (step 0), mark the existing corner tile
                if step == 0:
                    start_tile.is_path = True
                    start_tile.path_color = light_color
                    entry_path.append(start_index)
                else:
                    # For other path tiles
                    existing_tile = next((t for t in self.tiles 
                                        if abs(t.x - x) < 2 and abs(t.y - y) < 2), None)
                    if existing_tile:
                        existing_tile.is_path = True
                        existing_tile.path_color = light_color
                        entry_path.append(existing_tile.index)
                    else:
                        new_index = len(self.tiles)
                        path_tile = Tile(int(x), int(y), new_index)
                        path_tile.is_path = True
                        path_tile.path_color = light_color
                        self.tiles.append(path_tile)
                        entry_path.append(new_index)
            
            self.player_entry_tiles[player_id] = entry_path

    def is_valid_move(self, player_id, token, new_position):
        """Check if move follows all the new rules"""
        wrapped_pos = new_position % self.total_outer_tiles
        # Can't move to other players' straight paths
        for pid, path in self.player_entry_tiles.items():
            if pid != player_id and new_position in path:
                return False
        
        # Can only enter own straight path after 1 loop and 1 capture
        if wrapped_pos in self.player_entry_tiles.get(player_id, []):
            if not (token.loops_completed >= 1 and token.captures >= 1):
                return False
        
        return True

    # In the Board class (board.py), modify check_loop_completion:
    def check_loop_completion(self, player_id, token, old_pos, new_pos):
        if old_pos is None or token.in_home:
            return False

        total = self.total_outer_tiles
        start_tile = self.player_start_tiles[player_id]

        old_relative = (old_pos - start_tile) % total
        new_relative = (new_pos - start_tile) % total

        # Detect wrapping around player's path (loop completion)
        if new_relative < old_relative:
            return True

        return False


    def has_completed_loop(self, player_id, token, current_pos, steps_ahead):
        if token.in_home or current_pos is None:
            return False

        total = self.total_outer_tiles
        start_tile = self.player_start_tiles[player_id]

        cur_rel = (current_pos - start_tile) % total
        future_rel = (current_pos + steps_ahead - start_tile) % total

        # Predict wraparound
        return future_rel < cur_rel
    
    def can_enter_straight_path(self, player_id, token, current_pos):
        # Check if we're within 5 tiles of start tile and have captures
        return (token.captures >= 1)

    def draw(self, screen):
        """Draw all board components"""
        # Draw all tiles
        for tile in self.tiles:
            tile.draw(screen, goal_index=self.goal_tile_index)

    def update_warp_zones(self):
        """Update warp zone locations"""
        for tile in self.tiles:
            tile.is_warp = False

        possible_indices = [
            i for i, tile in enumerate(self.tiles)
            if tile.index != self.center_goal_index and not tile.is_path
        ]
        
        if len(possible_indices) >= 4:
            self.warp_indices = random.sample(possible_indices, 4)
            for idx in self.warp_indices:
                self.tiles[idx].is_warp = True

    def get_next_warp(self, current_index):
        warp_list = sorted(self.warp_indices)
        for warp in warp_list:
            if warp > current_index:
                return warp
        return warp_list[0]  # wrap around
