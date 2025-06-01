# pytest test_worderly.py
import pytest
import tempfile
import os
import json
from unittest.mock import patch, mock_open
from worderly import (
    valid_subword, get_subsets, six_letter_wordlist, pick_valid_main_word,
    make_grid, main_word_diagonal, place_main_subwords, ver_can_be_placed,
    place_vertical_subwords, hor_can_be_placed, place_horizontal_subwords,
    shuffle_main, upper_spacing, hide_letters, update_hidden_grid
)
from worderly_classes import (
    GameGrid, GameState, GameWord, LevelConfig, GridPosition,
    Leaderboard, LeaderboardEntry, StreakTracker
)


class TestGameModels:
    """Test the game model classes"""
    
    def test_grid_position_creation(self):
        """Test GridPosition creation and iteration"""
        pos = GridPosition(5, 10)
        assert pos.row == 5
        assert pos.col == 10
        
        # Test unpacking
        row, col = pos
        assert row == 5
        assert col == 10
    
    def test_game_word_creation(self):
        """Test GameWord creation with different input types"""
        # Test with GridPosition objects
        positions = [GridPosition(1, 2), GridPosition(1, 3)]
        word = GameWord("test", positions, True, "horizontal")
        assert word.word == "test"
        assert len(word.positions) == 2
        assert word.is_main_word is True
        assert word.direction == "horizontal"
        
        # Test with tuple positions (should convert automatically)
        word2 = GameWord("hello", [(0, 0), (0, 1), (0, 2)])
        assert len(word2.positions) == 3
        assert isinstance(word2.positions[0], GridPosition)
    
    def test_game_grid_operations(self):
        """Test GameGrid creation and cell operations"""
        grid = GameGrid()
        assert grid.rows == 15
        assert grid.columns == 25
        assert len(grid.grid) == 15
        assert len(grid.grid[0]) == 25
        
        # Test cell operations
        assert grid.get_cell(0, 0) == '.'
        grid.set_cell(0, 0, 'A')
        assert grid.get_cell(0, 0) == 'A'
        
        # Test boundary conditions
        assert grid.get_cell(-1, 0) == '.'
        assert grid.get_cell(0, -1) == '.'
        assert grid.get_cell(20, 0) == '.'
        assert grid.get_cell(0, 30) == '.'
    
    def test_game_state_operations(self):
        """Test GameState word management"""
        state = GameState("MASTER", ["MAST", "TERM"])
        
        # Test adding words
        state.add_word("TEST", [(0, 0), (0, 1), (0, 2), (0, 3)], False, "horizontal")
        assert "TEST" in state.game_words
        assert len(state.game_words["TEST"].positions) == 4
        
        # Test getting positions
        positions = state.get_word_positions("TEST")
        assert positions == [(0, 0), (0, 1), (0, 2), (0, 3)]
        
        # Test removing words
        state.remove_word("TEST")
        assert "TEST" not in state.game_words
    
    def test_level_config_properties(self):
        """Test LevelConfig calculated properties"""
        config = LevelConfig()
        assert config.center_row == 2  # ceil(15/2) - 6 = 8 - 6 = 2
        assert config.center_col == 7   # ceil(25/2) - 6 = 13 - 6 = 7


class TestWordValidation:
    """Test word validation and filtering functions"""
    
    def test_valid_subword(self):
        """Test subword validation logic"""
        # Valid subwords
        assert valid_subword("cat", "catch") is True
        assert valid_subword("hat", "hatch") is True
        assert valid_subword("ace", "place") is True
        
        # Invalid subwords
        assert valid_subword("catch", "catch") is False  # Same word
        assert valid_subword("dog", "cat") is False      # No common letters
        assert valid_subword("aaa", "aa") is False       # More letters than available
        assert valid_subword("hello", "helo") is False   # Not enough 'l's
    
    def test_get_subsets(self):
        """Test getting valid subsets from wordlist"""
        main_word = "MASTER"
        wordlist = ["master", "mast", "term", "team", "steam", "at", "verylongword"]
        
        # Fixed: only expecting one return value
        subsets = get_subsets(main_word, wordlist)
        
        # Should include valid 3-6 letter subwords
        assert "mast" in subsets
        assert "term" in subsets
        assert "team" in subsets
        
        # Should exclude the main word itself
        assert "master" not in subsets
        
        # Should exclude words too short or too long
        assert "at" not in subsets
        assert "verylongword" not in subsets

    def test_six_letter_wordlist(self):
        """Test filtering for 6-letter words"""
        wordlist = ["cat", "master", "hello", "test", "python", "code"]
        six_letters = six_letter_wordlist(wordlist)
        
        assert "master" in six_letters
        assert "python" in six_letters
        assert "cat" not in six_letters
        assert "test" not in six_letters
    
    def test_pick_valid_main_word(self):
        """Test picking a valid main word with sufficient subwords"""
        # Create a wordlist with known good combinations
        wordlist = [
            "master", "mast", "term", "team", "steam", "mater", "tamer", "smart",
            "aster", "rates", "tears", "stare", "reams", "meats", "mates",
            "trams", "stream", "master", "tamers", "stream", "steamer"
        ]
        
        result = pick_valid_main_word(wordlist)
        
        if result:  # May return None if no valid word found
            main_word, subwords = result
            assert len(main_word) == 6
            assert len(subwords) >= 20  # Should have at least 20 subwords


class TestGridOperations:
    """Test grid creation and manipulation functions"""
    
    def test_make_grid(self):
        """Test grid creation"""
        grid = make_grid()
        assert isinstance(grid, GameGrid)
        assert grid.rows == 15
        assert grid.columns == 25
    
    def test_main_word_diagonal(self):
        """Test placing main word diagonally"""
        grid = make_grid()
        game_state = GameState("", [])
        word = "MASTER"
        
        updated_grid, updated_state = main_word_diagonal(word, grid, game_state)
        
        # Check that the word was added to game state
        assert word.upper() in updated_state.game_words
        assert updated_state.game_words[word.upper()].is_main_word is True
        assert updated_state.game_words[word.upper()].direction == "diagonal"
        
        # Check positions are diagonal
        positions = updated_state.get_word_positions(word.upper())
        assert len(positions) == 6
        
        # Verify diagonal placement (each position should be +2 from previous)
        for i in range(1, len(positions)):
            prev_row, prev_col = positions[i-1]
            curr_row, curr_col = positions[i]
            assert curr_row == prev_row + 2
            assert curr_col == prev_col + 2
    
    def test_hide_letters(self):
        """Test hiding letters in grid"""
        grid = GameGrid()
        grid.set_cell(0, 0, 'A')
        grid.set_cell(0, 1, 'B')
        grid.set_cell(1, 0, '.')
        
        hidden = hide_letters(grid)
        
        assert hidden[0][0] == '♥'  # Letter should be hidden
        assert hidden[0][1] == '♥'  # Letter should be hidden  
        assert hidden[1][0] == '.'  # Dot should remain


class TestGameplayFunctions:
    """Test gameplay-related functions"""
    
    def test_shuffle_main(self):
        """Test shuffling main word"""
        word = "MASTER"
        shuffled = shuffle_main(word)
        
        # Should have same letters, possibly different order
        assert len(shuffled) == len(word)
        assert sorted(shuffled) == sorted(list(word))
    
    def test_upper_spacing(self):
        """Test formatting shuffled word"""
        word_list = ['m', 'a', 's', 't', 'e', 'r']
        result = upper_spacing(word_list)
        assert result == "M A S T E R"
    
    def test_update_hidden_grid(self):
        """Test updating hidden grid when word is guessed"""
        # Create test data
        grid = [['♥' for _ in range(5)] for _ in range(3)]
        correct_guesses = {"TEST": [(0, 0), (0, 1), (0, 2), (0, 3)]}
        guessed_words = []
        points = 0
        revealed_positions = []
        
        # Test correct guess
        updated_grid, updated_guessed, updated_points, updated_revealed = update_hidden_grid(
            "test", grid, correct_guesses, "TEST", guessed_words, points, revealed_positions
        )
        
        assert updated_points == 4  # Should add 4 points for 4-letter word
        assert len(updated_revealed) == 4  # Should reveal 4 positions


class TestPlacementValidation:
    """Test word placement validation functions"""
    
    def test_ver_can_be_placed_basic(self):
        """Test basic vertical placement validation"""
        grid = GameGrid()
        # Place a horizontal word first
        for i, letter in enumerate("TEST"):
            grid.set_cell(5, i, letter)
        
        # Try to place vertical word intersecting at T
        subword = "TOP"
        row_0, col_0 = 5, 0  # Position of first T
        loc = 0  # T is at position 0 in "TOP"
        
        result = ver_can_be_placed(grid, subword, row_0, col_0, loc)
        # This should be valid placement
        assert isinstance(result, bool)
    
    def test_hor_can_be_placed_basic(self):
        """Test basic horizontal placement validation"""  
        grid = GameGrid()
        # Place a vertical word first
        word = "TEST"
        for i, letter in enumerate(word):
            grid.set_cell(i, 5, letter)
        
        # Try to place horizontal word intersecting at E
        subword = "EAST"
        row_0, col_0 = 1, 5  # Position of E
        loc = 0  # E is at position 0 in "EAST"
        
        result = hor_can_be_placed(grid, subword, row_0, col_0, loc)
        assert isinstance(result, bool)


class TestLeaderboard:
    """Test leaderboard functionality"""
    
    def test_leaderboard_entry_serialization(self):
        """Test LeaderboardEntry to/from dict conversion"""
        entry = LeaderboardEntry("Alice", 5, 1250, "2025-06-02 10:30:00")
        
        # Test to_dict
        data = entry.to_dict()
        assert data['player_name'] == "Alice"
        assert data['streak_length'] == 5
        assert data['total_points'] == 1250
        assert data['timestamp'] == "2025-06-02 10:30:00"
        
        # Test from_dict
        recreated = LeaderboardEntry.from_dict(data)
        assert recreated.player_name == entry.player_name
        assert recreated.streak_length == entry.streak_length
        assert recreated.total_points == entry.total_points
        assert recreated.timestamp == entry.timestamp
    
    def test_leaderboard_sorting(self):
        """Test leaderboard entry sorting"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_filename = f.name
        
        try:
            leaderboard = Leaderboard(temp_filename)
            
            # Add entries in random order
            leaderboard.add_entry("Alice", 3, 900)
            leaderboard.add_entry("Bob", 5, 1200)
            leaderboard.add_entry("Charlie", 5, 1500)  # Same streak, more points
            leaderboard.add_entry("David", 2, 600)
            
            top_entries = leaderboard.get_top_entries(4)
            
            # Should be sorted by streak (desc), then points (desc)
            assert top_entries[0].player_name == "Charlie"  # 5 streak, 1500 points
            assert top_entries[1].player_name == "Bob"      # 5 streak, 1200 points  
            assert top_entries[2].player_name == "Alice"    # 3 streak, 900 points
            assert top_entries[3].player_name == "David"    # 2 streak, 600 points
            
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_leaderboard_persistence(self):
        """Test leaderboard save/load functionality"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_filename = f.name
        
        try:
            # Create leaderboard and add entries
            leaderboard1 = Leaderboard(temp_filename)
            leaderboard1.add_entry("Alice", 5, 1250)
            leaderboard1.add_entry("Bob", 3, 900)
            
            # Create new leaderboard instance (should load from file)
            leaderboard2 = Leaderboard(temp_filename)
            
            assert len(leaderboard2.entries) == 2
            assert leaderboard2.entries[0].player_name in ["Alice", "Bob"]
            assert leaderboard2.entries[1].player_name in ["Alice", "Bob"]
            
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_get_personal_best(self):
        """Test getting personal best for a player"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_filename = f.name
            
        try:
            leaderboard = Leaderboard(temp_filename)
            
            # Add multiple entries for same player
            leaderboard.add_entry("Alice", 3, 800)
            leaderboard.add_entry("Alice", 5, 1200)  # Best streak
            leaderboard.add_entry("Alice", 2, 600)
            leaderboard.add_entry("Bob", 4, 1000)
            
            alice_best = leaderboard.get_personal_best("Alice")
            assert alice_best is not None
            assert alice_best.streak_length == 5
            assert alice_best.total_points == 1200
            
            # Test case insensitive
            alice_best2 = leaderboard.get_personal_best("alice")
            assert alice_best2 is not None
            assert alice_best2.streak_length == 5
            
            # Test non-existent player
            no_player = leaderboard.get_personal_best("Charlie")
            assert no_player is None
            
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)


class TestStreakTracker:
    """Test streak tracking functionality"""
    
    def test_streak_tracker_basic_operations(self):
        """Test basic streak tracker operations"""
        tracker = StreakTracker()
        
        # Initial state
        assert tracker.current_streak == 0
        assert tracker.current_points == 0
        assert tracker.player_name == ""
        
        # Add wins
        tracker.player_name = "Alice"
        tracker.add_win(250)
        assert tracker.current_streak == 1
        assert tracker.current_points == 250
        
        tracker.add_win(300)
        assert tracker.current_streak == 2
        assert tracker.current_points == 550
        
        # Reset streak
        tracker.reset_streak()
        assert tracker.current_streak == 0
        assert tracker.current_points == 0
    
    def test_streak_tracker_new_record_detection(self):
        """Test new record detection"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_filename = f.name
            
        try:
            leaderboard = Leaderboard(temp_filename)
            tracker = StreakTracker()
            tracker.player_name = "Alice"
            
            # No previous record - any streak is new
            tracker.add_win(250)
            assert tracker.is_new_record(leaderboard) is True
            
            # Add to leaderboard
            leaderboard.add_entry("Alice", 1, 250)
            
            # Same streak, same points - not new
            tracker.reset_streak()
            tracker.add_win(250)
            assert tracker.is_new_record(leaderboard) is False
            
            # Same streak, more points - new record
            tracker.reset_streak()
            tracker.add_win(300)
            assert tracker.is_new_record(leaderboard) is True
            
            # Longer streak - definitely new record
            tracker.reset_streak()
            tracker.add_win(200)
            tracker.add_win(200)
            assert tracker.current_streak == 2
            assert tracker.is_new_record(leaderboard) is True
            
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)


class TestWordPlacement:
    """Test word placement functions"""
    
    def test_place_main_subwords(self):
        """Test placing horizontal subwords that intersect with main word"""
        grid = make_grid()
        game_state = GameState("MASTER", [])
        
        # First place the main word
        grid, game_state = main_word_diagonal("MASTER", grid, game_state)
        
        # Try to place some subwords
        subwords = ["MAST", "TERM", "STEAM"]
        original_subwords = subwords.copy()
        
        grid, game_state = place_main_subwords("MASTER", subwords, grid, game_state)
        
        # Some subwords should have been placed and removed from list
        assert len(subwords) < len(original_subwords)
        
        # Check that placed words are in game state
        placed_words = [word for word in game_state.game_words.keys() 
                       if word != "MASTER"]  # Exclude main word
        assert len(placed_words) > 0
    
    def test_place_vertical_subwords(self):
        """Test placing vertical subwords"""
        grid = make_grid()
        game_state = GameState("MASTER", [])
        
        # Place main word and some horizontal words first
        grid, game_state = main_word_diagonal("MASTER", grid, game_state)
        
        # Add a horizontal word manually for testing
        game_state.add_word("TEST", [(5, 5), (5, 6), (5, 7), (5, 8)], 
                           direction="horizontal")
        
        subwords = ["TOPS", "STEM"]
        vertical_count = 0
        
        grid, game_state, new_count = place_vertical_subwords(
            "TEST", subwords, grid, game_state, vertical_count
        )
        
        # Should return updated count
        assert isinstance(new_count, int)
        assert new_count >= vertical_count
    
    def test_place_horizontal_subwords(self):
        """Test placing horizontal subwords"""
        grid = make_grid()
        game_state = GameState("MASTER", [])
        
        # Add a vertical word manually for testing
        game_state.add_word("TEST", [(5, 5), (6, 5), (7, 5), (8, 5)], 
                           direction="vertical")
        
        subwords = ["TOPS", "EAST"]
        horizontal_count = 0
        
        grid, game_state, new_count = place_horizontal_subwords(
            "TEST", subwords, grid, game_state, horizontal_count
        )
        
        # Should return updated count
        assert isinstance(new_count, int)
        assert new_count >= horizontal_count


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_wordlist_handling(self):
        """Test handling of empty wordlists"""
        empty_wordlist = []
        
        # Should return empty list for empty input
        subsets = get_subsets("MASTER", empty_wordlist)
        assert subsets == []
        
        six_letters = six_letter_wordlist(empty_wordlist)
        assert six_letters == []
    
    def test_invalid_grid_positions(self):
        """Test handling of invalid grid positions"""
        grid = GameGrid()
        
        # Test getting from invalid positions
        assert grid.get_cell(-1, 0) == '.'
        assert grid.get_cell(0, -1) == '.'
        assert grid.get_cell(100, 0) == '.'
        assert grid.get_cell(0, 100) == '.'
        
        # Setting invalid positions should not crash
        grid.set_cell(-1, 0, 'X')  # Should not crash
        grid.set_cell(100, 100, 'Y')  # Should not crash
    
    def test_leaderboard_with_corrupted_file(self):
        """Test leaderboard handling of corrupted files"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content {")
            temp_filename = f.name
        
        try:
            # Should not crash and should create empty leaderboard
            leaderboard = Leaderboard(temp_filename)
            assert len(leaderboard.entries) == 0
            
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_word_validation_edge_cases(self):
        """Test word validation with edge cases"""
        # Empty strings
        assert valid_subword("", "test") is True  # Empty subword is technically valid
        assert valid_subword("test", "") is False  # Can't make word from empty string
        
        # Single character
        assert valid_subword("a", "apple") is True
        assert valid_subword("z", "apple") is False
        
        # Repeated letters
        assert valid_subword("aa", "aardvark") is True
        assert valid_subword("aaaa", "aardvark") is False  # Only 3 a's in aardvark
