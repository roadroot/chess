from game.piece import Piece
from game.game import Game

class MinMax:
    def __init__(self, game: Game) -> None:
        self.game = game

    def generate(self, game: Game = None, isMax: bool = True, depth: int = 2, move = None):
        game = game if game else self.game
        sign = -1 if isMax else 1
        score = 0
        scores = []
        avm = []
        for k in game.map:
            avm += self.game.getAvailableMoves(*k)

        if move:
            if game.map[move[1]].hasSameTypeAs(Piece.P1_PAWN):
                score += sign * 20
            elif game.map[move[1]].hasSameTypeAs(Piece.P1_BISHOP):
                score += sign * 70
            elif game.map[move[1]].hasSameTypeAs(Piece.P1_KNIGHT):
                score += sign * 80
            elif game.map[move[1]].hasSameTypeAs(Piece.P1_ROOK):
                score += sign * 120
            elif game.map[move[1]].hasSameTypeAs(Piece.P1_QUEEN):
                score += sign * 300
            elif game.map[move[1]].hasSameTypeAs(Piece.P1_KING):
                score += sign * 999999999
            game.move(frm=move[0], to=move[1], do=False)

        if not depth:
            return score

        for mv in avm:
            ng = Game(lambda _: None, 9999)
            ng.logs = game.logs.copy()
            ng.map = game.map.copy()
            ng.player = game.player
            scores.append(self.generate(game=ng, isMax= not isMax, move=mv, depth=depth-1))

        nsc = max(scores) if isMax else min(scores)
        if not move:
            return avm[scores.index(nsc)]

        return nsc + score if mv else 0


