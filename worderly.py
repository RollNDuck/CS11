# python3 worderly.py
import random
import os
from argparse import ArgumentParser
from worderly_classes import (
    GameGrid, GameState, GameWord, LevelConfig, GridPosition,
    Leaderboard, LeaderboardEntry, StreakTracker
)

#--------------------------------------------------------------------------------------------#
# # # GETTING OF MAIN WORD AND SUBWORDS
#--------------------------------------------------------------------------------------------#

def valid_subword(word, main_word):
    """Check if a word is a valid subword of the main word"""
    main_word = main_word.lower()
    if word == main_word:
        return False
    for letter in word:
        if word.count(letter) > main_word.count(letter):
            return False
    return True

def get_subsets(main_word, wordlist):
    """Get all valid subwords (3-6 letters) from the main word"""
    three_to_six = [word.strip() for word in wordlist if 3 <= len(word.strip()) <= 6]
    subsets_of_main_word = []
    for word in three_to_six:
        if valid_subword(word, main_word):
            subsets_of_main_word.append(word)
    return subsets_of_main_word

def six_letter_wordlist(wordlist):
    """Get all 6-letter words from the wordlist"""
    return [word.strip() for word in wordlist if len(word.strip()) == 6]

def pick_valid_main_word(wordlist):
    """Pick a random 6-letter word that has at least 20 valid subwords"""
    config = LevelConfig()
    six_letter_words = six_letter_wordlist(wordlist)
    random.shuffle(six_letter_words)
    for possible_valid in six_letter_words:
        subsets_main = get_subsets(possible_valid, wordlist)
        if len(subsets_main) >= config.min_subwords:
            return possible_valid, subsets_main

#--------------------------------------------------------------------------------------------#
# # # LEVEL GENERATION
#--------------------------------------------------------------------------------------------#

def display_grid(grid):
    """Display the game grid"""
    if isinstance(grid, GameGrid):
        for row in grid.grid:
            print(' '.join(row))
    else:
        # Backward compatibility for list of lists or strings
        for row in grid:
            if isinstance(row, str):
                print(' '.join(row))
            else:
                print(' '.join(row))

def make_grid():
    """Create a new game grid"""
    return GameGrid()

def main_word_diagonal(word, grid, game_state):
    """Place the main word diagonally on the grid"""
    config = LevelConfig()
    
    positions = []
    for i, letter in enumerate(word):           
        row_0 = config.center_row + (i * 2)
        col_0 = config.center_col + (i * 2)
        
        grid.set_cell(row_0, col_0, letter.upper())
        positions.append((row_0, col_0))
    
    game_state.add_word(word.upper(), positions, is_main_word=True, direction="diagonal")
    return grid, game_state

def place_main_subwords(word, subwords, grid, game_state):
    """Place subwords horizontally intersecting with the main word"""
    config = LevelConfig()
    
    for i, main_letter in enumerate(word):
        row_0 = config.center_row + (i * 2)
        col_0 = config.center_col + (i * 2)

        for subword in subwords[:]:
            if main_letter in subword:
                positions = []
                for j, letter in enumerate(subword):
                    loc = subword.index(main_letter)
                    hor_off = (j - loc)
                    col_1 = col_0 + hor_off
                    
                    positions.append((row_0, col_1))

                    if hor_off == 0:
                        grid.set_cell(row_0, col_1, letter.upper())
                    elif 0 <= row_0 < config.rows and 0 <= col_1 < config.columns:
                        grid.set_cell(row_0, col_1, letter)

                game_state.add_word(subword, positions, direction="horizontal")
                subwords.remove(subword)
                break

    return grid, game_state

def ver_can_be_placed(grid, subword, row_0, col_0, loc):
    """Check if a vertical word can be placed at the given position"""
    config = LevelConfig()
    
    # Check top boundary
    top_row = row_0 - loc - 1
    if 0 <= top_row < config.rows:
        if grid.get_cell(top_row, col_0) != '.':
            return False

    # Check bottom boundary
    bottom_row = row_0 + (len(subword) - loc)
    if 0 <= bottom_row < config.rows:
        if grid.get_cell(bottom_row, col_0) != '.':
            return False
        
    # Check all positions of the subword
    for i, letter in enumerate(subword):
        offset = i - loc
        row = row_0 + offset
        col = col_0

        if not (0 <= row < config.rows and 0 <= col < config.columns):
            return False
        
        if grid.get_cell(row, col) != '.' and grid.get_cell(row, col) != letter:
            return False
        
        if offset != 0:
            for s in (-1, 0, 1):
                if i == 0:
                    for t in (-1, 0):
                        if row + t >= 0:
                            if 0 <= col + s < config.columns and 0 <= row + t < config.rows:
                                if grid.get_cell(row + t, col + s) != '.':
                                    return False
                elif i == len(subword) - 1:
                    for b in (0, 1):
                        if row + b < config.rows:
                            if 0 <= col + s < config.columns and 0 <= row + b < config.rows:
                                if grid.get_cell(row + b, col + s) != '.':
                                    return False
                else:
                    if 0 <= col + s < config.columns:
                        if grid.get_cell(row, col_0 + s) != '.':
                            return False
    return True

def place_vertical_subwords(word, subwords, grid, game_state, vertical_count):
    """Place vertical subwords intersecting with existing words"""
    config = LevelConfig()
    
    word_positions = game_state.get_word_positions(word)
    if not word_positions:
        return grid, game_state, vertical_count
    
    r_int = random.randint(0, len(word) - 1)
    main_letter = word[r_int]
    (row_0, col_0) = word_positions[r_int]
    
    for subword in subwords[:]:
        if main_letter in subword:
            loc = subword.index(main_letter)
            if ver_can_be_placed(grid, subword, row_0, col_0, loc):
                
                positions = []
                for j, letter in enumerate(subword):
                    ver_off = j - loc
                    row_1 = row_0 + ver_off

                    if ver_off == 0:
                        pass
                    elif 0 <= row_1 < config.rows:
                        grid.set_cell(row_1, col_0, letter)

                    positions.append((row_1, col_0))

                game_state.add_word(subword, positions, direction="vertical")
                vertical_count += 1
                subwords.remove(subword)
                break
            
    return grid, game_state, vertical_count

def hor_can_be_placed(grid, subword, row_0, col_0, loc):
    """Check if a horizontal word can be placed at the given position"""
    config = LevelConfig()

    left_col = col_0 - loc - 1
    if 0 <= left_col < config.columns:
        if grid.get_cell(row_0, left_col) != '.':
            return False

    right_col = col_0 + (len(subword) - loc)
    if 0 <= right_col < config.columns:
        if grid.get_cell(row_0, right_col) != '.':
            return False

    for i, letter in enumerate(subword):
        offset = i - loc
        col = col_0 + offset
        row = row_0

        if not (0 <= row < config.rows and 0 <= col < config.columns):
            return False
        
        if grid.get_cell(row, col) != '.' and grid.get_cell(row, col) != letter:
            return False
        
        if offset != 0:
            for s in (-1, 0, 1):
                if i == 0:
                    for l in (-1, 0):
                        if 0 <= col + l < config.columns and 0 <= row + s < config.rows:
                            if grid.get_cell(row + s, col + l) != '.':
                                return False
                elif i == len(subword) - 1:
                    for r in (0, 1):
                        if 0 <= col + r < config.columns and 0 <= row + s < config.rows:
                            if grid.get_cell(row + s, col + r) != '.':
                                return False
                else:
                    if 0 <= row + s < config.rows:
                        if grid.get_cell(row + s, col) != '.':
                            return False
    return True

def place_horizontal_subwords(word, subwords, grid, game_state, horizontal_count):
    """Place horizontal subwords intersecting with existing words"""
    config = LevelConfig()
    
    word_positions = game_state.get_word_positions(word)
    if not word_positions:
        return grid, game_state, horizontal_count
    
    c_int = random.randint(0, len(word) - 1)
    main_letter = word[c_int]
    (row_0, col_0) = word_positions[c_int]
    
    for subword in subwords[:]:
        if main_letter in subword:
            loc = subword.index(main_letter)
            if hor_can_be_placed(grid, subword, row_0, col_0, loc):

                positions = []
                for j, letter in enumerate(subword):
                    hor_off = j - loc
                    col_1 = col_0 + hor_off

                    if hor_off == 0:
                        pass
                    elif 0 <= col_1 < config.columns:
                        grid.set_cell(row_0, col_1, letter)

                    positions.append((row_0, col_1))

                game_state.add_word(subword, positions, direction="horizontal")
                horizontal_count += 1
                subwords.remove(subword)
                break
            
    return grid, game_state, horizontal_count

def place_remaining_subwords_until_20(grid, subwords, game_state, vertical_count, horizontal_count):
    """Continue placing words until we reach the target number"""
    config = LevelConfig()
    
    count = vertical_count + horizontal_count + 7
    direction = random.choice(("vertical", "horizontal"))
    attempts = 0
    
    while count < config.max_total_words and attempts < config.max_attempts:
        horizontal_words = [word for word, game_word in game_state.game_words.items() 
                          if game_word.direction == "horizontal"]
        
        vertical_words = [word for word, game_word in game_state.game_words.items() 
                         if game_word.direction == "vertical"]
        
        if direction == "vertical" and horizontal_words:
            word = random.choice(horizontal_words)
            grid, game_state, vertical_count = place_vertical_subwords(word, subwords, grid, game_state, vertical_count)
        elif direction == "horizontal" and vertical_words:
            word = random.choice(vertical_words)
            grid, game_state, horizontal_count = place_horizontal_subwords(word, subwords, grid, game_state, horizontal_count)
        else:
            break 

        count = vertical_count + horizontal_count + 7
        direction = "horizontal" if direction == "vertical" else "vertical"
        attempts += 1

    return grid, game_state

#--------------------------------------------------------------------------------------------#
# # # GAMEPLAY MECHANICS
#--------------------------------------------------------------------------------------------#

def shuffle_main(main_word):
    """Shuffle the letters of the main word"""
    shuffle_word = list(main_word)
    random.shuffle(shuffle_word)
    return shuffle_word

def upper_spacing(shuffle_six_letter_word):
    """Format shuffled word with uppercase and spacing"""
    return ' '.join(letter.upper() for letter in shuffle_six_letter_word)

def hide_letters(grid):
    """Hide all letters in the grid with hearts"""
    hidden = []
    grid_data = grid.grid if isinstance(grid, GameGrid) else grid
    for row in grid_data:
        hiding_letters = []
        for letter in row:
            if letter == ".":
                hiding_letters.append(".")
            else:
                hiding_letters.append("♥")
        hidden.append(hiding_letters)
    return hidden

def clear_screen():
    """Clear the terminal screen"""
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

# Define special positions that should be capitalized (main word positions)
SPECIAL_POSITIONS = [(2, 7), (4, 9), (6, 11), (8, 13), (10, 15), (12, 17)]

def update_hidden_grid(guess, grid, correct_guesses, correct_guess, guessed_words, points, revealed_positions, main_word_upper=None):
    """Update the hidden grid when a correct word is guessed"""
    if correct_guess.upper() in correct_guesses and guess.lower() == correct_guess.lower():
        correct_guess = correct_guess.upper()
        
    if correct_guess not in correct_guesses:
        return grid, guessed_words, points, revealed_positions

    index = correct_guesses[correct_guess]

    for i, letter in enumerate(correct_guess):
        row, col = index[i]

        if index[i] in guessed_words:
            continue

        should_capitalize = (correct_guess.isupper() or 
                             (main_word_upper and correct_guess.upper() == main_word_upper) or 
                             (row, col) in revealed_positions or
                             (row, col) in SPECIAL_POSITIONS)
        
        if (row, col) not in revealed_positions:
            revealed_positions.append((row, col))
        
        display_letter = letter.upper() if should_capitalize else letter
        grid[row] = grid[row][:col] + [display_letter] + grid[row][col + 1:]
        points += 1
        guessed_words.append((row, col))

    return grid, guessed_words, points, revealed_positions

#--------------------------------------------------------------------------------------------#
# # # MAIN GAME LOGIC WITH LEADERBOARD
#--------------------------------------------------------------------------------------------#

def display_menu():
    """Display the main menu"""
    print("\n" + "─"*50)
    print(" " * 7 + "₊✩‧₊˚WIZARDS OF WORDERLY PALACE˚₊✩‧₊")
    print("─"*50)
    print("1. Play Game")
    print("2. View Leaderboard")
    print("3. Quit")
    print("─"*50)

def get_player_name():
    """Get player name for leaderboard tracking"""
    while True:
        name = input("What is your name? : ").strip()
        if name and len(name) <= 20:
            return name
        print("Please enter a valid name (1-20 characters)")

def play_game(wordlist, streak_tracker, leaderboard):
    """Main game function with streak and leaderboard tracking"""
    global main_word
    
    print("Loading word list...")
    config = LevelConfig()
    
    # Level generation loop
    while True:
        grid = make_grid()
        game_state = GameState(main_word="", subwords=[])

        main_word, subwords = pick_valid_main_word(wordlist)
        game_state.main_word = main_word
        game_state.subwords = subwords.copy()
        subwords_copy = subwords.copy()

        random.shuffle(subwords)
        grid, game_state = main_word_diagonal(main_word, grid, game_state)
        grid, game_state = place_main_subwords(main_word, subwords, grid, game_state)

        horizontal_words = [word for word, game_word in game_state.game_words.items() 
                          if game_word.direction == "horizontal"]
        
        if not horizontal_words:
            continue
            
        word1 = random.choice(horizontal_words)
        grid, game_state, vertical_count = place_vertical_subwords(word1, subwords, grid, game_state, 0)

        attempts = 0
        while vertical_count < config.min_vertical_words and attempts < config.max_attempts//5:
            horizontal_words = [word for word, game_word in game_state.game_words.items() 
                              if game_word.direction == "horizontal"]
            if not horizontal_words:
                break
            word1 = random.choice(horizontal_words)
            grid, game_state, vertical_count = place_vertical_subwords(word1, subwords, grid, game_state, vertical_count)
            attempts += 1

        grid, game_state = place_remaining_subwords_until_20(grid, subwords, game_state, vertical_count, 0)
        
        if len(game_state.game_words) >= 21: 
            break
    
    # Game setup
    level_grid = grid
    all_subwords = subwords_copy
    
    level_words = {}
    for word, game_word in game_state.game_words.items():
        level_words[word] = [(pos.row, pos.col) for pos in game_word.positions]
    
    # Gameplay setup
    shuffle_six_letter_word = shuffle_main(main_word)
    upper_spacing_six_letter_word = upper_spacing(shuffle_six_letter_word)

    correct_guesses = level_words.copy()  # Keep original for checking
    hide_the_letters_grid = hide_letters(level_grid)

    lives = 5
    points = 0
    guessed_words = []
    last_guessed_word = "None"
    revealed_positions = []
    found_words = set()  # Track already found words

    clear_screen()

    # Game loop
    while lives > 0:
        # Display streak info
        if streak_tracker.player_name:
            print(f"{"─"*49}\nPlayer: {streak_tracker.player_name}")
            print(f"Current Streak: {streak_tracker.current_streak}{" "*15}Streak Points: {streak_tracker.current_points}\n{"─"*49}")

        display_grid(hide_the_letters_grid)
        print(f"{"─"*49}\nLetters: {upper_spacing_six_letter_word}    |    Last guess: {last_guessed_word}")
        print(f"Lives left: {lives} | Points: {points} | Words found: {len(found_words)}/{len(correct_guesses)}\n{"─"*49}")
        print(f"{" "*10}Letter Commands | 'R' to start new game \n{" "*26}| 'L' for leaderboard\n{" "*26}| 'E' to quit \n{"─"*49}")

        print("\nSubwords placed in the grid:")
        print(", ".join(sorted(game_state.game_words.keys())))

        # Win condition - check if all words are found
        if len(found_words) == len(correct_guesses):
            print("Congratulations! You've revealed all words!")
            
            # Update streak
            streak_tracker.add_win(points)
            
            # Check for new record
            if streak_tracker.is_new_record(leaderboard):
                print(f"🎉 NEW PERSONAL RECORD! 🎉")
                print(f"Streak: {streak_tracker.current_streak} games")
                print(f"Total Points: {streak_tracker.current_points}")
            
            choice = input("Continue playing to extend your streak? (y/n): ").strip().lower()
            if choice == 'y':
                return "R"  # Continue streak
            else:
                # Save to leaderboard and end streak
                if streak_tracker.player_name and streak_tracker.current_streak > 0:
                    leaderboard.add_entry(
                        streak_tracker.player_name,
                        streak_tracker.current_streak,
                        streak_tracker.current_points
                    )
                    print(f"Your streak of {streak_tracker.current_streak} games has been saved to the leaderboard!")
                
                streak_tracker.reset_streak()
                return "M"  # Return to menu
        
        guess = input("Enter guess: ").strip().lower()
        
        if guess.upper() == "R":
            # End current streak and start new game
            if streak_tracker.player_name and streak_tracker.current_streak > 0:
                leaderboard.add_entry(
                    streak_tracker.player_name,
                    streak_tracker.current_streak,
                    streak_tracker.current_points
                )
                print(f"Your streak of {streak_tracker.current_streak} games has been saved!")
            streak_tracker.reset_streak()
            return "R"
        elif guess.upper() == "E":
            # Save streak before quitting
            if streak_tracker.player_name and streak_tracker.current_streak > 0:
                leaderboard.add_entry(
                    streak_tracker.player_name,
                    streak_tracker.current_streak,
                    streak_tracker.current_points
                )
                print(f"Your streak of {streak_tracker.current_streak} games has been saved!")
            return "E"
        elif guess.upper() == "L":
            clear_screen()
            leaderboard.display_leaderboard()
            input("Press Enter to continue...")
            clear_screen()
            continue
        
        clear_screen()
        
        # Process guess - Check if word was already found
        word_found = False
        
        # Check main word
        if guess == main_word.lower():
            if main_word.upper() in found_words:
                # Already found, deduct life
                lives -= 1
                last_guessed_word = f"{guess} (already found)"
            else:
                # New find
                hide_the_letters_grid, guessed_words, points, revealed_positions = update_hidden_grid(
                    guess, hide_the_letters_grid, correct_guesses, main_word.upper(), 
                    guessed_words, points, revealed_positions, main_word.upper()
                )
                found_words.add(main_word.upper())
                last_guessed_word = guess
                word_found = True
        else:
            # Check other words
            matching_word = None
            for word in correct_guesses:
                if guess == word.lower():
                    matching_word = word
                    break
            
            if matching_word:
                if matching_word in found_words:
                    # Already found, deduct life
                    lives -= 1
                    last_guessed_word = f"{guess} (already found)"
                else:
                    # New find
                    hide_the_letters_grid, guessed_words, points, revealed_positions = update_hidden_grid(
                        guess, hide_the_letters_grid, correct_guesses, matching_word, 
                        guessed_words, points, revealed_positions, main_word.upper()
                    )
                    found_words.add(matching_word)
                    last_guessed_word = guess
                    word_found = True
            else:
                # Word not in the puzzle
                lives -= 1
                last_guessed_word = f"{guess} (not found)"
            
        # Check lose condition
        if lives == 0:
            display_grid(hide_the_letters_grid)
            print(f"Lives left: {lives}")
            print(f"Points: {points}")
            print(f"Last guess: {last_guessed_word}")
            print("Game over! You ran out of lives.")
            print(f"You found {len(found_words)}/{len(correct_guesses)} words.")
            
            # Save streak to leaderboard even on loss (if there was a streak)
            if streak_tracker.player_name and streak_tracker.current_streak > 0:
                leaderboard.add_entry(
                    streak_tracker.player_name,
                    streak_tracker.current_streak,
                    streak_tracker.current_points
                )
                print(f"Your streak of {streak_tracker.current_streak} games has been saved!")
            
            # Always save current game score to leaderboard (even single games)
            if streak_tracker.player_name:
                # Save current game as a 1-game streak
                leaderboard.add_entry(
                    streak_tracker.player_name,
                    1,  # Single game
                    points  # Just this game's points
                )
                print(f"Your game score of {points} points has been saved to the leaderboard!")
            
            streak_tracker.reset_streak()
            
            choice = input("Play again? (y/n): ").strip().lower()
            return "R" if choice == 'y' else "M"

    return "M"

def main():
    """Main function with menu system"""
    stage_file = 'corncob-lowercase.txt'
    
    try:
        parser = ArgumentParser()
        parser.add_argument('stage_file', nargs='?', default=stage_file)
        args = parser.parse_args()
        stage_file = args.stage_file
    except:
        pass
    
    try:
        with open(stage_file, encoding='utf-8') as f:
            wordlist = f.readlines()
    except FileNotFoundError:
        print(f"Error: Could not find the word list file '{stage_file}'")
        print("Make sure the file is in the same directory as this script.")
        return

    # Initialize leaderboard and streak tracker
    leaderboard = Leaderboard()
    streak_tracker = StreakTracker()

    while True:
        clear_screen()
        display_menu()
        
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == "1":
            # Start playing
            if not streak_tracker.player_name:
                clear_screen()
                print(f"{"─"*49}\n ₊✩‧₊˚Welcome to Wizards of Worderly Palace!\n{"─"*49}")
                streak_tracker.player_name = get_player_name()
                print(f"Hello {streak_tracker.player_name}!")
                input("Press Enter to start...")
            
            action = "R"
            while action == "R":
                action = play_game(wordlist, streak_tracker, leaderboard)
            
            if action == "E":
                break
                
        elif choice == "2":
            # View leaderboard
            clear_screen()
            leaderboard.display_leaderboard()
            input("Press Enter to return to menu...")
            
        elif choice == "3":
            # Quit
            print("Thanks for playing!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()