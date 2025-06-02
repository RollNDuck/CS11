import random
import os
from argparse import ArgumentParser
from worderly_classes import GameGrid, GameState, LevelConfig, Leaderboard, StreakTracker

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
    for row in grid:
        print(' '.join(row))

def make_grid():
    """Create a new game grid"""
    return GameGrid()

def main_word_diagonal(word, grid, game_state):
    """Place the main word diagonally on the grid"""
    config = LevelConfig()
    
    positions = [] # Keep track of positions
    for i, letter in enumerate(word): # Index calculation           
        row_0 = config.center_row + (i * 2)
        col_0 = config.center_col + (i * 2)
        
        grid.set_cell(row_0, col_0, letter.upper()) # Place leter
        positions.append((row_0, col_0)) # Tracker
    
    game_state.add_word(word.upper(), positions, is_main_word=True, direction="diagonal") # Tracker
    return grid, game_state

def place_main_subwords(word, subwords, grid, game_state):
    """Place subwords horizontally intersecting with the main word"""
    config = LevelConfig()
    
    for i, main_letter in enumerate(word): # Index calculation
        row_0 = config.center_row + (i * 2)
        col_0 = config.center_col + (i * 2)

        for subword in subwords[:]:
            if main_letter in subword:
                positions = []
                for j, letter in enumerate(subword): # Index offset per letter
                    loc = subword.index(main_letter) # Index of main letter in subword
                    hor_off = (j - loc) # Index offset per letter
                    col_1 = col_0 + hor_off
                    
                    positions.append((row_0, col_1)) # Keep track of word and index

                    if hor_off == 0: # Retain main word
                        grid.set_cell(row_0, col_1, letter.upper())
                    elif 0 <= row_0 < config.rows and 0 <= col_1 < config.columns: # Set index limits (not off grid)
                        grid.set_cell(row_0, col_1, letter)

                game_state.add_word(subword, positions, direction="horizontal")
                subwords.remove(subword)
                break

    return grid, game_state

def place_vertical_subwords(word, subwords, grid, game_state, vertical_count):
    """Place vertical subwords that intersect with letters from the main word."""
    
    config = LevelConfig()
    
    # Get the grid positions of each letter in the main word
    word_positions = game_state.get_word_positions(word)
    if not word_positions:
        return grid, game_state, vertical_count
    
    # Randomly select a letter from the main word and get its grid coordinates
    r_int = random.randint(0, len(word) - 1)
    main_letter = word[r_int]
    (row_0, col_0) = word_positions[r_int]

    # Try to find a subword that can intersect with the main word at the selected letter
    for subword in subwords[:]:  # iterate over a shallow copy to allow removal
        if main_letter in subword:
            loc = subword.index(main_letter)  # position of shared letter in the subword

            # Check if the subword can be placed vertically with alignment at the shared letter
            if ver_can_be_placed(grid, subword, row_0, col_0, loc):
                positions = []  # track all placed letter positions

                for j, letter in enumerate(subword):
                    ver_off = j - loc
                    row_1 = row_0 + ver_off  # compute target row

                    # No placement for the shared letter (already exists)
                    if ver_off == 0:
                        pass
                    # Place other letters vertically if within bounds
                    elif 0 <= row_1 < config.rows:
                        grid.set_cell(row_1, col_0, letter)

                    # Save the position of each letter placed
                    positions.append((row_1, col_0))

                # Register the placed subword and its positions in game state
                game_state.add_word(subword, positions, direction="vertical")

                # Update vertical word count and remove subword to prevent reuse
                vertical_count += 1
                subwords.remove(subword)
                break  # Exit after placing one valid subword

    return grid, game_state, vertical_count

def ver_can_be_placed(grid, subword, row_0, col_0, loc):
    """Check if a vertical word can be placed at the specified position on the grid."""
    config = LevelConfig()
    
    # Check the cell immediately above the top of the word to avoid adjacency
    top_row = row_0 - loc - 1
    if 0 <= top_row < config.rows:
        if grid.get_cell(top_row, col_0) != '.':
            return False

    # Check the cell immediately below the bottom of the word to avoid adjacency
    bottom_row = row_0 + (len(subword) - loc)
    if 0 <= bottom_row < config.rows:
        if grid.get_cell(bottom_row, col_0) != '.':
            return False
        
    # Check each letter position of the subword vertically
    for i, letter in enumerate(subword):
        offset = i - loc  # Distance from main letter
        row = row_0 + offset
        col = col_0

        # Verify position is within grid bounds
        if not (0 <= row < config.rows and 0 <= col < config.columns):
            return False
        
        # Allow placement if cell is empty or already contains the correct letter
        if grid.get_cell(row, col) != '.' and grid.get_cell(row, col) != letter:
            return False
        
        # For letters other than the main intersection letter,
        # ensure adjacent cells do not conflict with existing words
        if offset != 0:
            for s in (-1, 0, 1):
                # Check cells around the top letter of the subword
                if i == 0:
                    for t in (-1, 0):
                        if row + t >= 0:
                            if 0 <= col + s < config.columns and 0 <= row + t < config.rows:
                                if grid.get_cell(row + t, col + s) != '.':
                                    return False
                # Check cells around the bottom letter of the subword
                elif i == len(subword) - 1:
                    for b in (0, 1):
                        if row + b < config.rows:
                            if 0 <= col + s < config.columns and 0 <= row + b < config.rows:
                                if grid.get_cell(row + b, col + s) != '.':
                                    return False
                # Check cells around intermediate letters of the subword
                else:
                    if 0 <= col + s < config.columns:
                        if grid.get_cell(row, col_0 + s) != '.':
                            return False
    return True

def place_horizontal_subwords(word, subwords, grid, game_state, horizontal_count):
    """Place horizontal subwords that intersect with an existing word on the grid."""
    config = LevelConfig()
    
    # Get the positions of each letter in the current word from the game state
    word_positions = game_state.get_word_positions(word)
    if not word_positions:
        return grid, game_state, horizontal_count
    
    # Randomly select a letter and its position from the word
    c_int = random.randint(0, len(word) - 1)
    main_letter = word[c_int]
    (row_0, col_0) = word_positions[c_int]
    
    for subword in subwords[:]:
        # Check if the main letter is in the subword
        if main_letter in subword:
            loc = subword.index(main_letter)
            # Check if the subword can be placed horizontally at the position
            if hor_can_be_placed(grid, subword, row_0, col_0, loc):
                positions = []
                for j, letter in enumerate(subword):
                    hor_off = j - loc
                    col_1 = col_0 + hor_off

                    # Skip the main intersection letter as it is already placed
                    if hor_off == 0:
                        pass
                    elif 0 <= col_1 < config.columns:
                        # Place letter on the grid
                        grid.set_cell(row_0, col_1, letter)

                    # Track the position of each letter placed
                    positions.append((row_0, col_1))

                # Add the subword to the game state with its letter positions
                game_state.add_word(subword, positions, direction="horizontal")
                horizontal_count += 1
                subwords.remove(subword)
                break
            
    return grid, game_state, horizontal_count

def hor_can_be_placed(grid, subword, row_0, col_0, loc):
    """Check if a horizontal word can be placed at the specified position on the grid."""
    config = LevelConfig()

    # Check the cell immediately left of the word to avoid adjacency
    left_col = col_0 - loc - 1
    if 0 <= left_col < config.columns:
        if grid.get_cell(row_0, left_col) != '.':
            return False

    # Check the cell immediately right of the word to avoid adjacency
    right_col = col_0 + (len(subword) - loc)
    if 0 <= right_col < config.columns:
        if grid.get_cell(row_0, right_col) != '.':
            return False

    # Check each letter position of the subword horizontally
    for i, letter in enumerate(subword):
        offset = i - loc  # Distance from main letter
        col = col_0 + offset
        row = row_0

        # Verify position is within grid bounds
        if not (0 <= row < config.rows and 0 <= col < config.columns):
            return False
        
        # Allow placement if cell is empty or already contains the correct letter
        if grid.get_cell(row, col) != '.' and grid.get_cell(row, col) != letter:
            return False
        
        # For letters other than the main intersection letter,
        # ensure adjacent cells do not conflict with existing words
        if offset != 0:
            for s in (-1, 0, 1):
                # Check cells around the leftmost letter of the subword
                if i == 0:
                    for j in (-1, 0):
                        if 0 <= col + j < config.columns and 0 <= row + s < config.rows:
                            if grid.get_cell(row + s, col + j) != '.':
                                return False
                # Check cells around the rightmost letter of the subword
                elif i == len(subword) - 1:
                    for r in (0, 1):
                        if 0 <= col + r < config.columns and 0 <= row + s < config.rows:
                            if grid.get_cell(row + s, col + r) != '.':
                                return False
                # Check cells around intermediate letters of the subword
                else:
                    if 0 <= row + s < config.rows:
                        if grid.get_cell(row + s, col) != '.':
                            return False
    return True

def place_remaining_subwords_until_20(grid, subwords, game_state, vertical_count, horizontal_count):
    """Attempt to place remaining subwords until the target word count or max attempts are reached."""
    config = LevelConfig()
    
    # Initial count includes already placed vertical and horizontal words plus initial 7 words
    count = vertical_count + horizontal_count + 7
    
    # Randomly start placing either vertical or horizontal words
    direction = random.choice(("vertical", "horizontal"))
    attempts = 0
    
    while count < config.max_total_words and attempts < config.max_attempts:
        # Get lists of currently placed horizontal and vertical words
        horizontal_words = [word for word, game_word in game_state.game_words.items() if game_word.direction == "horizontal"]
        vertical_words = [word for word, game_word in game_state.game_words.items() if game_word.direction == "vertical"]
        
        if direction == "vertical" and horizontal_words:
            word = random.choice(horizontal_words)
            grid, game_state, vertical_count = place_vertical_subwords(word, subwords, grid, game_state, vertical_count)
        elif direction == "horizontal" and vertical_words:
            word = random.choice(vertical_words)
            grid, game_state, horizontal_count = place_horizontal_subwords(word, subwords, grid, game_state, horizontal_count)
        else:
            # Cannot place more words in the chosen direction
            break

        # Update count and alternate direction for next attempt
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
    # Convert correct guess to uppercase if it matches main word 
    if correct_guess.upper() in correct_guesses and guess.lower() == correct_guess.lower():
        correct_guess = correct_guess.upper()
        
    # Return early if the correct guess is not found
    if correct_guess not in correct_guesses:
        return grid, guessed_words, points, revealed_positions

    # Get letter positions for the correct guess
    index = correct_guesses[correct_guess]

    for i, letter in enumerate(correct_guess):
        row, col = index[i]

        # Skip if this position was already guessed
        if index[i] in guessed_words:
            continue

        # Decide if the letter should be uppercase
        should_capitalize = (
            correct_guess.isupper() or
            (main_word_upper and correct_guess.upper() == main_word_upper) or
            (row, col) in revealed_positions or
            (row, col) in SPECIAL_POSITIONS
        )
        
        # Add new revealed positions to the list
        if (row, col) not in revealed_positions:
            revealed_positions.append((row, col))
        
        # Update the grid letter with proper case
        display_letter = letter.upper() if should_capitalize else letter
        grid[row] = grid[row][:col] + [display_letter] + grid[row][col + 1:]

        # Increment points for revealed letters
        points += 1

        # Mark position as guessed
        guessed_words.append((row, col))

    return grid, guessed_words, points, revealed_positions

#--------------------------------------------------------------------------------------------#
# # # MAIN GAME LOGIC WITH LEADERBOARD
#--------------------------------------------------------------------------------------------#

def display_menu():
    """Display the main menu"""
    print("\n" + "="*50)
    print(" " * 7 + "₊✩‧₊˚WIZARDS OF WORDERLY PALACE˚₊✩‧₊")
    print("="*50)
    print("1. Play Game")
    print("2. View Leaderboard")
    print("3. Quit")
    print("="*50)

def get_player_name():
    """Get player name for leaderboard tracking"""
    while True:
        name = input("What is your name? : ").strip()
        if name and len(name) <= 20:
            return name
        print("Please enter a valid name (1-20 characters)")

def play_game(wordlist, streak_tracker, leaderboard):
    """Main game function with streak and leaderboard tracking"""
    global main_word  # Make main_word accessible globally
    
    print("Loading word list...")  # Start level generation
    config = LevelConfig()  # Load level config constants
    
    # Generate level until valid grid is created
    while True:
        grid = make_grid()  # Create empty grid
        game_state = GameState(main_word="", subwords=[])  # Initialize game state
        
        main_word, subwords = pick_valid_main_word(wordlist)  # Pick main and subwords
        game_state.main_word = main_word
        game_state.subwords = subwords.copy()
        
        random.shuffle(subwords)  # Shuffle subwords randomly
        grid, game_state = main_word_diagonal(main_word, grid, game_state)  # Place main word diagonally
        grid, game_state = place_main_subwords(main_word, subwords, grid, game_state)  # Place horizontal subwords
        
        horizontal_words = [w for w, gw in game_state.game_words.items() if gw.direction == "horizontal"]
        if not horizontal_words:  # Restart if no horizontal words placed
            continue
        
        word1 = random.choice(horizontal_words)  # Pick random horizontal word
        grid, game_state, vertical_count = place_vertical_subwords(word1, subwords, grid, game_state, 0)  # Place vertical subwords
        
        attempts = 0
        # Try to place enough vertical words or reach max attempts
        while vertical_count < config.min_vertical_words and attempts < config.max_attempts//5:
            horizontal_words = [w for w, gw in game_state.game_words.items() if gw.direction == "horizontal"]
            if not horizontal_words:
                break
            word1 = random.choice(horizontal_words)
            grid, game_state, vertical_count = place_vertical_subwords(word1, subwords, grid, game_state, vertical_count)
            attempts += 1
        
        grid, game_state = place_remaining_subwords_until_20(grid, subwords, game_state, vertical_count, 0)  # Fill grid up to 20 words
        
        if len(game_state.game_words) >= 21:  # Valid level generated
            break
    
    # Setup game variables for play
    level_grid = grid
    
    level_words = {word: [(pos.row, pos.col) for pos in gw.positions] for word, gw in game_state.game_words.items()}
    
    shuffle_six_letter_word = shuffle_main(main_word)  # Shuffle main word letters
    upper_spacing_six_letter_word = upper_spacing(shuffle_six_letter_word)  # Format letters for display
    
    correct_guesses = level_words.copy()  # Words player must guess
    hide_the_letters_grid = hide_letters(level_grid)  # Hide letters in grid
    
    lives = 5
    points = 0
    guessed_words = []
    last_guessed_word = "None"
    revealed_positions = []
    found_words = set()  # Track found words
    
    clear_screen()  # Clear terminal before game starts
    
    # Main gameplay loop
    while lives > 0:
        # Display player streak if available
        if streak_tracker.player_name:
            print(f"{'='*49}\nPlayer: {streak_tracker.player_name}")
            print(f"Current Streak: {streak_tracker.current_streak}{" "*15}Streak Points: {streak_tracker.current_points}\n{'='*49}")

        display_grid(hide_the_letters_grid)  # Show grid to player
        print(f"{'='*49}\nLetters: {upper_spacing_six_letter_word}    |    Last guess: {last_guessed_word}")
        print(f"Lives left: {lives} | Points: {points} | Words found: {len(found_words)}/{len(correct_guesses)}\n{'='*49}")
        print(f"{" "*10}Letter Commands | 'R' to start new game \n{" "*26}| 'L' for leaderboard\n{" "*26}| 'E' to quit \n{'='*49}")

        print("\nSubwords placed in the grid:")
        print(", ".join(sorted(game_state.game_words.keys())))
        
        # Check win condition (all words found)
        if len(found_words) == len(correct_guesses):
            print("Congratulations! You've revealed all words!")
            streak_tracker.add_win(points)  # Update streak points
            
            # Notify new record if applicable
            if streak_tracker.is_new_record(leaderboard):
                print("🎉 NEW PERSONAL RECORD! 🎉")
                print(f"Streak: {streak_tracker.current_streak} games")
                print(f"Total Points: {streak_tracker.current_points}")
            
            choice = input("Continue playing to extend your streak? (y/n): ").strip().lower()
            if choice == 'y':
                return "R"  # Restart game, keep streak
            else:
                # Save streak and reset
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
        
        # Handle special commands
        if guess.upper() == "R":  # Restart game
            if streak_tracker.player_name and streak_tracker.current_streak > 0:
                leaderboard.add_entry(
                    streak_tracker.player_name,
                    streak_tracker.current_streak,
                    streak_tracker.current_points
                )
                print(f"Your streak of {streak_tracker.current_streak} games has been saved!")
            streak_tracker.reset_streak()
            return "R"
        elif guess.upper() == "E":  # Exit game
            if streak_tracker.player_name and streak_tracker.current_streak > 0:
                leaderboard.add_entry(
                    streak_tracker.player_name,
                    streak_tracker.current_streak,
                    streak_tracker.current_points
                )
                print(f"Your streak of {streak_tracker.current_streak} games has been saved!")
            return "E"
        elif guess.upper() == "L":  # Show leaderboard
            clear_screen()
            leaderboard.display_leaderboard()
            input("Press Enter to continue...")
            clear_screen()
            continue
        
        clear_screen()
        
        # Check if main word guessed
        if guess == main_word.lower():
            if main_word.upper() in found_words:
                lives -= 1  # Already found, lose life
                last_guessed_word = f"{guess} (already found)"
            else:
                # Reveal main word letters
                hide_the_letters_grid, guessed_words, points, revealed_positions = update_hidden_grid(
                    guess, hide_the_letters_grid, correct_guesses, main_word.upper(), 
                    guessed_words, points, revealed_positions, main_word.upper()
                )
                found_words.add(main_word.upper())
                last_guessed_word = guess
        else:
            # Check other words
            matching_word = None
            for word in correct_guesses:
                if guess == word.lower():
                    matching_word = word
                    break
            
            if matching_word:
                if matching_word in found_words:
                    lives -= 1  # Already found, lose life
                    last_guessed_word = f"{guess} (already found)"
                else:
                    # Reveal guessed word letters
                    hide_the_letters_grid, guessed_words, points, revealed_positions = update_hidden_grid(
                        guess, hide_the_letters_grid, correct_guesses, matching_word, 
                        guessed_words, points, revealed_positions, main_word.upper()
                    )
                    found_words.add(matching_word)
                    last_guessed_word = guess
            else:
                lives -= 1  # Incorrect guess, lose life
                last_guessed_word = f"{guess} (not found)"
        
        # Check lose condition
        if lives == 0:
            display_grid(hide_the_letters_grid)
            print(f"Lives left: {lives}")
            print(f"Points: {points}")
            print(f"Last guess: {last_guessed_word}")
            print("Game over! You ran out of lives.")
            print(f"You found {len(found_words)}/{len(correct_guesses)} words.")
            
            # Save streak on loss
            if streak_tracker.player_name and streak_tracker.current_streak > 0:
                leaderboard.add_entry(
                    streak_tracker.player_name,
                    streak_tracker.current_streak,
                    streak_tracker.current_points
                )
                print(f"Your streak of {streak_tracker.current_streak} games has been saved!")
            
            # Save current game's score separately
            if streak_tracker.player_name:
                leaderboard.add_entry(
                    streak_tracker.player_name,
                    0,  # Single game streak
                    points
                )
                print(f"Your game score of {points} points has been saved to the leaderboard!")
            
            streak_tracker.reset_streak()
            choice = input("Play again? (y/n): ").strip().lower()
            return "R" if choice == 'y' else "M"

    return "M"

def main():
    """Main function with menu system"""
    stage_file = 'corncob-lowercase.txt'  # Default word list file
    
    try:
        # Attempt to parse optional command line argument for a custom stage file
        parser = ArgumentParser()
        parser.add_argument('stage_file', nargs='?', default=stage_file)
        args = parser.parse_args()
        stage_file = args.stage_file
    except SystemExit:
        # If parsing fails, continue with default file
        pass
    
    try:
        # Load the word list from the specified file
        with open(stage_file, encoding='utf-8') as f:
            wordlist = f.readlines()
    except FileNotFoundError:
        # Handle missing file error gracefully
        print(f"Error: Could not find the word list file '{stage_file}'")
        print("Make sure the file is in the same directory as this script.")
        return

    # Initialize leaderboard and streak tracker for game progress tracking
    leaderboard = Leaderboard()
    streak_tracker = StreakTracker()

    # Main menu loop
    while True:
        clear_screen()
        display_menu()
        
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == "1":
            # Start playing the game
            if not streak_tracker.player_name:
                clear_screen()
                print(f"{'='*49}\n ₊✩‧₊˚Welcome to Wizards of Worderly Palace!\n{'='*49}")
                streak_tracker.player_name = get_player_name()
                print(f"Hello {streak_tracker.player_name}!")
                input("Press Enter to start...")
            
            action = "R"
            while action == "R":
                action = play_game(wordlist, streak_tracker, leaderboard)
            
            if action == "E":
                # Exit game loop to quit
                break
                
        elif choice == "2":
            # Show the leaderboard
            clear_screen()
            leaderboard.display_leaderboard()
            input("Press Enter to return to menu...")
            
        elif choice == "3":
            # Quit the game
            print("Thanks for playing!")
            break
        else:
            # Handle invalid menu input
            print("Invalid choice. Please enter 1, 2, or 3.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()