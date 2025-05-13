import random
import pygame
from board import Board
from player import Player
from dice import Dice
import math
from config import BOARD_WIDTH, BOARD_HEIGHT, BACKGROUND_COLOR, TILE_SIZE
from config import PLAYER_COLORS

WINNING_SCORE = 5

def get_players():
    print("Select number of human players (1 to 4): ")
    while True:
        try:
            human_count = int(input("> "))
            if 1 <= human_count <= 4:
                break
        except ValueError:
            print("Invalid input. Enter a number.")

    total_players = human_count + 1 # Always 1 AI
    players = []

    available_colors = list(PLAYER_COLORS.values())[:total_players]

    for i in range(human_count):
        players.append(Player(player_id=i, is_ai=False, color=available_colors[i]))

    players.append(Player(player_id=human_count, is_ai=True, color=available_colors[human_count]))

    return players

def init_game():
    pygame.init()
    screen = pygame.display.set_mode((BOARD_WIDTH, BOARD_HEIGHT))
    pygame.display.set_caption("Ludo: Capture Edition")
    return screen

def assign_base_positions(players):
    center_x, center_y = 400, 400
    radius = 300
    offset = 25    # Adjust spacing for 5 players

    for i, player in enumerate(players):
        angle_deg = 90 + i * (360 / len(players))
        angle_rad = math.radians(angle_deg)

        base_x = center_x + radius * math.cos(angle_rad)
        base_y = center_y - radius * math.sin(angle_rad)

        # Distribute 4 tokens somewhat around the base center
        player.base_positions = [
            (int(base_x - offset * 0.7), int(base_y - offset * 0.7)),
            (int(base_x + offset * 0.7), int(base_y - offset * 0.7)),
            (int(base_x - offset * 0.7), int(base_y + offset * 0.7)),
            (int(base_x + offset * 0.7), int(base_y + offset * 0.7)),
        ]

def check_winner(players):
    for player in players:
        if player.score >= WINNING_SCORE:
            return player
    return None

def evaluate_token_moves(current_player, board, players, steps):
    best_token = None
    best_score = -float('inf')

    for token in current_player.tokens:
        if token.in_home or token.position is None:
            continue

        new_pos = (token.position + steps) % board.total_outer_tiles
        score = 0

        # Score for capturing
        for other in players:
            if other.id == current_player.id:
                continue
            for t in other.tokens:
                if t.position == new_pos and not t.in_home:
                    if new_pos not in board.player_start_tiles.values():  # not a safe zone
                        score += 10

        # Score for warp zone
        if board.tiles[new_pos].is_warp:
            score += 5

        # Add steps as minor progress
        score += steps

        if score > best_score:
            best_score = score
            best_token = token

    return best_token

def game_loop(screen):
    running = True
    clock = pygame.time.Clock()
    board = Board()
    board.update_warp_zones()
    dice = Dice()
    current_player_index = 0
    space_pressed = False
    rolled = False
    log_messages = []
    turns_played = 0
    selected_token = None
    possible_moves = []
    remaining_steps = 0
    show_trail = False
    home_token_positions = {}
    token_placed_this_turn = False
    AI_DELAY_EVENT = pygame.USEREVENT + 1
    used_six = False

    players = get_players()
    assign_base_positions(players)

    for player in players:
        for token in player.tokens:
            token.in_home = True

    capture_occurred_this_turn = False

    while running:
        screen.fill(BACKGROUND_COLOR)
        current_player = players[current_player_index]
        is_human = not current_player.is_ai

        winner = check_winner(players)
        if winner:
            font = pygame.font.SysFont(None, 72)
            win_text = font.render(f"Player {winner.id + 1} wins!", True, winner.color)
            screen.blit(win_text, (BOARD_WIDTH//2 - win_text.get_width()//2, 
                                  BOARD_HEIGHT//2 - win_text.get_height()//2))
            pygame.display.flip()
            pygame.time.delay(3000)
            running = False
            break

        if current_player.id in board.player_trail_positions:
            for idx in board.player_trail_positions[current_player.id]:
                if 0 <= idx < len(board.tiles):
                    board.tiles[idx].has_trail = False
            board.player_trail_positions[current_player.id] = []
            
        can_move_from_home = any(t.in_home for t in current_player.tokens)
        has_tokens_on_board = any(not t.in_home for t in current_player.tokens)
        rolled_a_six = rolled and (6 in dice.values)
        

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                space_pressed = True
            elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
                space_pressed = False
            elif event.type == pygame.MOUSEBUTTONDOWN and is_human and rolled:
                mouse_pos = event.pos
                token_clicked = False

                if show_trail and selected_token is not None and selected_token.position is not None:
                    # Check if clicked on an available move
                    for move, step in possible_moves:
                        tile = board.tiles[move]
                        tile_rect = pygame.Rect(tile.x, tile.y, TILE_SIZE, TILE_SIZE)
                        if tile_rect.collidepoint(mouse_pos):
                            # Move the token to the selected spot
                            old_pos = selected_token.position
                            selected_token.position = move
                            remaining_steps -= step
                            
                            # Check for completed loops
                            if board.check_loop_completion(current_player.id, selected_token, old_pos, move):
                                selected_token.loops_completed += 1
                                selected_token.update_status()
                                log_messages.append(f"Token completed a full loop around the board!")
                            
                            # Capture check
                            for other in players:
                                if other.id != current_player.id:
                                    for t in other.tokens:
                                        if not t.in_home and t.position == move:
                                            # Skip capture if the tile is a base/start tile (safe zone)
                                            if move in board.player_start_tiles.values():
                                                continue
                                            t.in_home = True
                                            t.position = None
                                            current_player.score += 1
                                            capture_occurred_this_turn = True
                                            log_messages.append(f"Player {current_player.id + 1} captured Player {other.id + 1}'s token!")

                            # Warp zone logic
                            if board.tiles[move].is_warp:
                                old = move
                                selected_token.position = board.get_next_warp(move)
                                log_messages.append(f"WARP! {old} → {selected_token.position}")

                            # If there are no remaining steps, reset the token selection
                            if remaining_steps == 0:
                                if capture_occurred_this_turn:
                                    rolled = False
                                    log_messages.append(f"Player {current_player.id + 1} gets an extra roll for capturing!")
                                    capture_occurred_this_turn = False
                                else:
                                    selected_token = None
                                    possible_moves = []
                                    show_trail = False
                                    rolled = False
                                    current_player_index = (current_player_index + 1) % len(players)
                                    turns_played += 1
                                    token_placed_this_turn = False

                            else:
                                # In possible moves calculation:
                                possible_moves = []
                                if selected_token.position is not None:
                                    for step in range(1, remaining_steps + 1):
                                        new_pos = (selected_token.position + step) % board.total_outer_tiles
                                        possible_moves.append((new_pos, step))
                                show_trail = True
                            break

                if has_tokens_on_board:
                    for token in current_player.tokens:
                        if not token.in_home and token.position is not None:
                            tile = board.tiles[token.position]
                            tile_rect = pygame.Rect(tile.x, tile.y, TILE_SIZE, TILE_SIZE)
                            if tile_rect.collidepoint(mouse_pos):
                                selected_token = token
                                # In possible moves calculation:
                                possible_moves = []
                                for step in range(1, remaining_steps + 1):
                                    new_pos = (token.position + step) % board.total_outer_tiles
                                    possible_moves.append((new_pos, step))
                                show_trail = True
                                token_clicked = True
                                break

                if not token_clicked and rolled_a_six and can_move_from_home and not token_placed_this_turn:
                    six_index = 0 if dice.values[0] == 6 else 1
                    other_die = dice.values[1] if six_index == 0 else dice.values[0]
                    # First check if clicked on home token to bring it in
                    for idx, token in enumerate(current_player.tokens):
                        if token.in_home and (current_player.id, idx) in home_token_positions:
                            draw_x, draw_y = home_token_positions[(current_player.id, idx)]
                            token_rect = pygame.Rect(draw_x - TILE_SIZE // 5, draw_y - TILE_SIZE // 5, 
                                                   TILE_SIZE // 2, TILE_SIZE // 2)
                            if token_rect.collidepoint(mouse_pos):
                                token.in_home = False
                                token.position = board.player_start_tiles[current_player.id]
                                selected_token = token
                                remaining_steps = other_die
                                used_six = True
                                token_placed_this_turn = True
                                log_messages.append(f"Player {current_player.id + 1} placed new token using six")
                                if remaining_steps > 0:
                                    # In possible moves calculation:
                                    possible_moves = []
                                    for step in range(1, remaining_steps + 1):
                                        new_pos = (token.position + step) % board.total_outer_tiles
                                        possible_moves.append((new_pos, step))
                                    show_trail = True
                                break
                    
                    # If not placing new token, check if clicking on existing board token
                    if not token_placed_this_turn:
                        for token in current_player.tokens:
                            if not token.in_home and token.position is not None:
                                tile = board.tiles[token.position]
                                tile_rect = pygame.Rect(tile.x, tile.y, TILE_SIZE, TILE_SIZE)
                                if tile_rect.collidepoint(mouse_pos):
                                    selected_token = token
                                    possible_moves = [((token.position + step) % board.total_outer_tiles, step) 
                                                    for step in range(1, dice.total() + 1)]
                                    show_trail = True
                                    log_messages.append(f"Player {current_player.id + 1} selected token at {token.position}")
                                    break


                # Handle moving home token onto the board
                elif rolled_a_six and can_move_from_home and not has_tokens_on_board:
                    for idx, token in enumerate(current_player.tokens):
                        if token.in_home and (current_player.id, idx) in home_token_positions and not token_placed_this_turn:
                            draw_x, draw_y = home_token_positions[(current_player.id, idx)]
                            token_rect = pygame.Rect(draw_x - TILE_SIZE // 5, draw_y - TILE_SIZE // 5, TILE_SIZE // 2, TILE_SIZE // 2)
                            if token_rect.collidepoint(mouse_pos):
                                token.in_home = False
                                token.position = board.player_start_tiles[current_player.id]
                                selected_token = token
                                remaining_steps = dice.total() - 6
                                if remaining_steps > 0:
                                    possible_moves = [((token.position + step) % board.total_outer_tiles, step) for step in range(1, remaining_steps + 1)]
                                    show_trail = True
                                token_placed_this_turn = True  # Set the flag
                                break

                # Handle moving an existing token on the board
                elif has_tokens_on_board and not rolled_a_six:
                    for token in current_player.tokens:
                        if not token.in_home and token.position is not None:
                            tile = board.tiles[token.position]
                            tile_rect = pygame.Rect(tile.x, tile.y, TILE_SIZE, TILE_SIZE)
                            if tile_rect.collidepoint(mouse_pos):
                                # Select a new token and calculate the new possible moves
                                selected_token = token
                                possible_moves = [((token.position + step) % board.total_outer_tiles, step) for step in range(1, remaining_steps + 1)]
                                show_trail = True
                                break

        # Draw board and tokens
        board.draw(screen)
        for player in players:
            for token in player.tokens:
                if not token.in_home and token.position is not None:
                    tile = board.tiles[token.position]
                    token.draw(screen, tile, player.color)

        # Draw home tokens
        token_offset = 15
        base_radius = 320
        for i, player in enumerate(players):
            tokens_in_home = [t for t in player.tokens if t.in_home]
            angle_deg = 90 + player.id * (360 / len(PLAYER_COLORS))
            angle_rad = math.radians(angle_deg)
            base_x = 400 + base_radius * math.cos(angle_rad)
            base_y = 400 - base_radius * math.sin(angle_rad)
            for j, token in enumerate(tokens_in_home):
                dx = int(base_x - token_offset + (j % 2) * 2 * token_offset)
                dy = int(base_y - token_offset + (j // 2) * 2 * token_offset)
                pygame.draw.circle(screen, player.color, (dx, dy), TILE_SIZE // 5)
                home_token_positions[(player.id, j)] = (dx, dy)

        if show_trail:
            for move, _ in possible_moves:
                tile = board.tiles[move % board.total_outer_tiles]
                pos = (tile.x + TILE_SIZE//2, tile.y + TILE_SIZE//2)
                pygame.draw.circle(screen, (180, 180, 180), pos, 6)

        # Draw labels and scores
        font = pygame.font.SysFont(None, 24)
        for player in players:
            angle_deg = 90 + player.id * (360 / len(PLAYER_COLORS))
            angle_rad = math.radians(angle_deg)
            lx = 400 + 380 * math.cos(angle_rad)
            ly = 400 - 380 * math.sin(angle_rad)
            label = f"Player {player.id + 1}" + (" (AI)" if player.is_ai else "") + f": {player.score}"
            text = font.render(label, True, (0, 0, 0))
            screen.blit(text, (int(lx - text.get_width() // 2), int(ly - text.get_height() // 2)))

        # Dice & logs
        dice_text = pygame.font.SysFont(None, 36).render(f"Roll: {dice.values[0]} + {dice.values[1]}", True, (0, 0, 0))
        screen.blit(dice_text, (20, 20))
        for i, msg in enumerate(log_messages[-8:]):
            text = font.render(msg, True, (0, 0, 0))
            screen.blit(text, (20, 60 + i * 20))

        # Handle dice roll
        if is_human and space_pressed and not rolled:
            dice.roll()
            rolled = True
            remaining_steps = dice.total()
            used_six = False
            capture_occurred_this_turn = False
            log_messages.append(f"Player {current_player.id + 1} rolled {remaining_steps}")
            if (6 not in dice.values and not has_tokens_on_board) or (not can_move_from_home and not has_tokens_on_board):
                log_messages.append(f"Player {current_player.id + 1} can't move. Turn skipped.")
                rolled = False
                current_player_index = (current_player_index + 1) % len(players)
                turns_played += 1
                token_placed_this_turn = False

        # AI turn logic
        if not is_human and not rolled:
            pygame.time.delay(500)
            dice.roll()
            rolled = True
            remaining_steps = dice.total()
            used_six = False
            capture_occurred_this_turn = False
            log_messages.append(f"AI Player {current_player.id + 1} rolled: {remaining_steps}")
            pygame.time.delay(300)

            if (6 not in dice.values and not has_tokens_on_board) or (not can_move_from_home and not has_tokens_on_board):
                log_messages.append(f"AI Player {current_player.id + 1} can't move. Turn skipped.")
                rolled = False
                current_player_index = (current_player_index + 1) % len(players)
                turns_played += 1
                token_placed_this_turn = False
                pygame.time.delay(400)
                continue

            moved = False
            die1, die2 = dice.values
            other_die = die2 if die1 == 6 else die1

            # Step 1: Check all tokens for capture opportunities within remaining_steps
            capture_made = False

            for token in current_player.tokens:
                if token.in_home or token.position is None:
                    continue

                for step in range(1, remaining_steps + 1):
                    target_pos = (token.position + step) % board.total_outer_tiles

                    for opponent in players:
                        if opponent.id == current_player.id:
                            continue
                        for enemy_token in opponent.tokens:
                            if (
                                not enemy_token.in_home
                                and enemy_token.position == target_pos
                                and target_pos not in board.player_start_tiles.values()  # Skip safe zones
                            ):
                                # Capture logic
                                enemy_token.in_home = True
                                enemy_token.position = None
                                current_player.score += 1
                                capture_occurred_this_turn = True
                                log_messages.append(
                                    f"AI Player {current_player.id + 1} captured Player {opponent.id + 1}'s token at {target_pos}"
                                )

                                # Move token to capture position
                                old_pos = token.position
                                token.position = target_pos
                                capture_made = True
                                moved = True
                                remaining_steps -= step

                                # Loop completion
                                if board.check_loop_completion(current_player.id, token, old_pos, target_pos):
                                    token.loops_completed += 1
                                    token.update_status()
                                    log_messages.append("Token completed a full loop!")

                                # Warp
                                if board.tiles[token.position].is_warp:
                                    warp_from = token.position
                                    token.position = board.get_next_warp(warp_from)
                                    log_messages.append(f"AI WARP! From {warp_from} to {token.position}")

                                break
                        if capture_made:
                            break
                    if capture_made:
                        break
                if capture_made:
                    break

            # Step 2: No capture, place new token if 6 rolled
            just_placed_token = None
            if not capture_made and 6 in dice.values and can_move_from_home and not used_six:
                for token in current_player.tokens:
                    if token.in_home:
                        token.in_home = False
                        token.position = board.player_start_tiles[current_player.id]
                        remaining_steps = other_die
                        used_six = True
                        token_placed_this_turn = True
                        has_tokens_on_board = any(not t.in_home for t in current_player.tokens)
                        just_placed_token = token
                        log_messages.append(f"AI Player {current_player.id + 1} placed a token.")
                        break  # Don’t mark moved = True yet, we want to move this token

            # Step 3: Move placed token (or best token) with remaining steps
            if has_tokens_on_board and remaining_steps > 0:
                token_to_move = just_placed_token or evaluate_token_moves(current_player, board, players, remaining_steps)
                if token_to_move:
                    old_pos = token_to_move.position
                    new_pos = (old_pos + remaining_steps) % board.total_outer_tiles

                    # Check for capture
                    for other in players:
                        if other.id != current_player.id:
                            for t in other.tokens:
                                if not t.in_home and t.position == new_pos:
                                    if new_pos not in board.player_start_tiles.values():
                                        t.in_home = True
                                        t.position = None
                                        current_player.score += 1
                                        capture_occurred_this_turn = True
                                        log_messages.append(f"AI Player {current_player.id + 1} captured Player {other.id + 1}'s token at {new_pos}!")

                    token_to_move.position = new_pos
                    moved = True
                    remaining_steps = 0
                    log_messages.append(f"AI Player {current_player.id + 1} ended move at {token_to_move.position}")

                    if board.check_loop_completion(current_player.id, token_to_move, old_pos, new_pos):
                        token_to_move.loops_completed += 1
                        token_to_move.update_status()
                        log_messages.append("Token completed a full loop!")

                    if board.tiles[token_to_move.position].is_warp:
                        old = token_to_move.position
                        token_to_move.position = board.get_next_warp(old)
                        log_messages.append(f"AI WARP! From {old} to {token_to_move.position}")

            # End turn
            if moved or (not can_move_from_home and not has_tokens_on_board):
                if remaining_steps == 0:
                    if capture_occurred_this_turn:
                        rolled = False
                        log_messages.append(f"AI Player {current_player.id + 1} gets an extra roll for capturing!")
                        capture_occurred_this_turn = False
                    else:
                        rolled = False
                        current_player_index = (current_player_index + 1) % len(players)
                        turns_played += 1
                        token_placed_this_turn = False
                        pygame.time.delay(400)


        pygame.display.flip()
        clock.tick(30)

    pygame.quit()

if __name__ == "__main__":
    screen = init_game()
    game_loop(screen)

