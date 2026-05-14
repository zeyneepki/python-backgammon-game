import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MoveResult:
    captured_color: Optional[str] = None  # "WHITE" veya "BROWN"


@dataclass
class GameBoard:

    board: list[int] = field(default_factory=lambda: [0] * 25)
    current_player: int = 1
    dice1: int = 0
    dice2: int = 0

    # GameBoard oluşturulunca başlangıç taşlarını otomatik yerleştirir.
    def __post_init__(self) -> None:
        self.initialize_board()

    # Tavlanın başlangıç dizilimini board listesine yazar.
    def initialize_board(self) -> None:
        self.board = [0] * 25

        # Kahverengi taşlar, oyuncu 2
        self.board[24] = -2
        self.board[13] = -5
        self.board[8] = -3
        self.board[6] = -5

        # Beyaz taşlar, oyuncu 1
        self.board[1] = 2
        self.board[12] = 5
        self.board[17] = 3
        self.board[19] = 5

    # İki adet 1-6 arası zar üretir ve sonucu döndürür.
    def roll_dice(self) -> tuple[int, int]:
        self.dice1 = random.randint(1, 6)
        self.dice2 = random.randint(1, 6)
        return self.dice1, self.dice2

    # Sıradaki oyuncuyu 1 ve 2 arasında değiştirir.
    def switch_player(self) -> None:
        self.current_player = 2 if self.current_player == 1 else 1

    # İstenen tahta noktasındaki taş değerini döndürür.
    def get_board_value(self, index: int) -> int:
        return self.board[index]

    # İstenen tahta noktasına yeni taş değeri yazar.
    def set_board_value(self, index: int, value: int) -> None:
        self.board[index] = value

    # Tahta dışına çıkmadan ve doğru renkten taş seçilip seçilmediğini basitçe kontrol eder.
    def is_move_valid_basic(self, from_index: int, to_index: int, player_role: int) -> bool:
        if from_index < 1 or from_index > 24 or to_index < 1 or to_index > 24:
            return False
        piece = self.board[from_index]
        if player_role == 1 and piece <= 0:
            return False
        if player_role == 2 and piece >= 0:
            return False
        return True

    # Taşı kaynaktan hedefe taşır; tek rakip taş varsa kırma sonucunu döndürür.
    def make_move(self, from_index: int, to_index: int, player_role: int) -> MoveResult:

        if to_index < 1 or to_index > 24:
            raise ValueError("Normal hamlede hedef 1-24 aralığında olmalıdır")

        if from_index == -1:
            moving_piece = 1
        elif from_index == -2:
            moving_piece = -1
        else:
            moving_piece = 1 if self.board[from_index] > 0 else -1
            self.board[from_index] -= moving_piece

        result = MoveResult()
        if player_role == 1 and self.board[to_index] == -1:
            self.board[to_index] = 0
            result.captured_color = "BROWN"
        elif player_role == 2 and self.board[to_index] == 1:
            self.board[to_index] = 0
            result.captured_color = "WHITE"

        self.board[to_index] += moving_piece
        return result
