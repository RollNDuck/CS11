from dataclasses import dataclass, field
import json
import os

@dataclass
class GridPosition:
    """Represents a position on the game grid"""
    row: int
    col: int
    
    def __iter__(self):
        """Allow unpacking like (row, col) = position"""
        yield self.row
        yield self.col

@dataclass
class GameWord:
    """Represents a word in the game with its positions"""
    word: str
    positions: list = field(default_factory=list)
    is_main_word: bool = False
    direction: str = "horizontal"  # "horizontal", "vertical", or "diagonal"
    
    def __post_init__(self):
        """Convert tuple positions to GridPosition objects if needed"""
        if self.positions and isinstance(self.positions[0], tuple):
            self.positions = [GridPosition(row, col) for row, col in self.positions]

@dataclass
class GameGrid:
    """Represents the game grid"""
    rows: int = 15
    columns: int = 25
    grid: list = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize empty grid if not provided"""
        if not self.grid:
            self.grid = ['.' * self.columns for _ in range(self.rows)]
    
    def get_cell(self, row: int, col: int) -> str:
        """Get character at specific position"""
        if 0 <= row < self.rows and 0 <= col < self.columns:
            return self.grid[row][col]
        return '.'
    
    def set_cell(self, row: int, col: int, char: str):
        """Set character at specific position"""
        if 0 <= row < self.rows and 0 <= col < self.columns:
            self.grid[row] = self.grid[row][:col] + char + self.grid[row][col + 1:]

@dataclass
class GameState:
    """Represents the current state of the game"""
    main_word: str
    subwords: list
    lives: int = 5
    points: int = 0
    guessed_words: list = field(default_factory=list)
    last_guessed_word: str = "None"
    revealed_positions: list = field(default_factory=list)
    game_words: dict = field(default_factory=dict)
    
    def add_word(self, word: str, positions: list, 
                 is_main_word: bool = False, direction: str = "horizontal"):
        """Add a word to the game state"""
        grid_positions = [GridPosition(row, col) for row, col in positions]
        self.game_words[word] = GameWord(
            word=word, 
            positions=grid_positions, 
            is_main_word=is_main_word, 
            direction=direction
        )
    
    def remove_word(self, word: str):
        """Remove a word from the game state"""
        if word in self.game_words:
            del self.game_words[word]
    
    def get_word_positions(self, word: str) -> list:
        """Get positions of a word as tuples for backward compatibility"""
        if word in self.game_words:
            return [(pos.row, pos.col) for pos in self.game_words[word].positions]
        return []

@dataclass
class LevelConfig:
    """Configuration for level generation"""
    rows: int = 15
    columns: int = 25
    word_length: int = 6
    min_subwords: int = 20
    min_vertical_words: int = 4
    max_total_words: int = 25
    max_attempts: int = 100
    
    @property
    def center_row(self) -> int:
        """Get center row for main word placement"""
        return -(-self.rows // 2) - self.word_length
    
    @property
    def center_col(self) -> int:
        """Get center column for main word placement"""
        return -(-self.columns // 2) - self.word_length

@dataclass
class WordPlacementResult:
    """Result of attempting to place a word"""
    success: bool
    grid: object = None  # Changed from Optional[GameGrid]
    positions: list = field(default_factory=list)
    error_message: str = ""

@dataclass
class LeaderboardEntry:
    """Represents a single leaderboard entry"""
    player_name: str
    streak_length: int
    total_points: int
    timestamp: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'player_name': self.player_name,
            'streak_length': self.streak_length,
            'total_points': self.total_points,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LeaderboardEntry':
        """Create LeaderboardEntry from dictionary"""
        return cls(
            player_name=data['player_name'],
            streak_length=data['streak_length'],
            total_points=data['total_points'],
            timestamp=data.get('timestamp', '')
        )

class Leaderboard:
    """Manages the game leaderboard with persistent storage"""
    
    def __init__(self, filename: str = "leaderboard.json"):
        """Initialize leaderboard with specified filename"""
        self.filename = filename
        self.entries: list = []
        self.load_leaderboard()
    
    def load_leaderboard(self) -> None:
        """Load leaderboard data from file"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entries = [LeaderboardEntry.from_dict(entry) for entry in data]
                    self._sort_entries()
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            print(f"Warning: Could not load leaderboard from {self.filename}: {e}")
            self.entries = []
    
    def save_leaderboard(self) -> None:
        """Save leaderboard data to file"""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                data = [entry.to_dict() for entry in self.entries]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save leaderboard to {self.filename}: {e}")
    
    def add_entry(self, player_name: str, streak_length: int, total_points: int) -> None:
        """Add a new entry to the leaderboard"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        entry = LeaderboardEntry(
            player_name=player_name,
            streak_length=streak_length,
            total_points=total_points,
            timestamp=timestamp
        )
        
        self.entries.append(entry)
        self._sort_entries()
        self.save_leaderboard()
    
    def _sort_entries(self) -> None:
        """Sort entries by streak length (descending), then by total points (descending)"""
        self.entries.sort(key=lambda x: (x.streak_length, x.total_points), reverse=True)
    
    def get_top_entries(self, limit: int = 10) -> list:
        """Get top N entries from leaderboard"""
        return self.entries[:limit]
    
    def display_leaderboard(self, limit: int = 10) -> None:
        """Display the leaderboard in a formatted way"""
        print("\n" + "─"*60)
        print(" " * 18 + "₊✩‧₊˚LEADERBOARD˚₊✩‧₊")
        print("─"*60)
        
        if not self.entries:
            print("No entries yet. Be the first to set a record!")
            print("─"*60)
            return
        
        print(f"{'Rank':<6}{'Name':<15}{'Streak':<8}{'Points':<8}{'Date':<15}")
        print("─" * 60)
        
        top_entries = self.get_top_entries(limit)
        for i, entry in enumerate(top_entries, 1):
            date_str = entry.timestamp.split()[0] if entry.timestamp else "Unknown"
            print(f"{i:<6}{entry.player_name[:14]:<15}{entry.streak_length:<8}{entry.total_points:<8}{date_str:<15}")
        
        print("─"*60)
    
    def get_personal_best(self, player_name: str):
        """Get the best entry for a specific player"""
        player_entries = [entry for entry in self.entries if entry.player_name.lower() == player_name.lower()]
        if player_entries:
            # Sort by streak length, then by points
            player_entries.sort(key=lambda x: (x.streak_length, x.total_points), reverse=True)
            return player_entries[0]
        return None

@dataclass
class StreakTracker:
    """Tracks current winning streak"""
    current_streak: int = 0
    current_points: int = 0
    player_name: str = ""
    
    def reset_streak(self) -> None:
        """Reset the current streak"""
        self.current_streak = 0
        self.current_points = 0
    
    def add_win(self, points: int) -> None:
        """Add a win to the current streak"""
        self.current_streak += 1
        self.current_points += points
    
    def is_new_record(self, leaderboard: Leaderboard) -> bool:
        """Check if current streak is a new personal record"""
        if not self.player_name:
            return False
        
        personal_best = leaderboard.get_personal_best(self.player_name)
        if not personal_best:
            return self.current_streak > 0
        
        return (self.current_streak > personal_best.streak_length or 
                (self.current_streak == personal_best.streak_length and 
                 self.current_points > personal_best.total_points))
