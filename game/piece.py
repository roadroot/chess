from enum import Enum
from os.path import join
from typing import List, Tuple

from PySide6.QtGui import QIcon, QPixmap

import json

class Piece(Enum):
    EMPTY = -1
    P1_PAWN = 0
    P1_BISHOP = 1
    P1_KNIGHT = 2
    P1_ROOK = 3
    P1_QUEEN = 4
    P1_KING = 5

    P2_PAWN = 6
    P2_BISHOP = 7
    P2_KNIGHT = 8
    P2_ROOK = 9
    P2_QUEEN = 10
    P2_KING = 11

    def __str__(self) -> str:
        return 'empty' if self == self.EMPTY else super(Piece, self).__str__().replace('P1_', 'w').replace('P2_', 'b').lower()[len(self.__class__.__name__) + 1:]

    def getIcon(self) -> QIcon:
        assets = 'JohnPablok Cburnett Chess set/SVG with shadow/'
        return QIcon(QPixmap(join(assets, str(self))))

    def isPlayers(self, player: bool) -> bool:
        return not self.isEmpty() and (self.value in range(self.P1_PAWN.value, self.P1_KING.value + 1)) == player

    def isEmpty(self) -> bool:
        return self == self.EMPTY

    def hasSameTypeAs(self, other) -> bool:
        return  not self.isEmpty() and not other.isEmpty() and self.value % Piece.P2_PAWN.value == other.value % Piece.P2_PAWN.value

    def isMoved(self, logs):
        return self in [log.piece for log in logs]

    def isEnemy(self, other):
        return self.isPlayers(False) != other.isPlayers(False)

    @staticmethod
    def isAttacked(tile: Tuple, map: list, player: bool, logs: list):
        return tile in [move for x in range(8) for y in range(8) for (_, move) in Piece.getMoves(x=x, y=y, map=map, player=not player, logs=logs)]

    @staticmethod
    def getMoves(x: int, y: int, map: dict, logs: list, player: bool = None, casteling: bool = False) -> List:
        player = Piece.isPlayers(map[x, y], True) if player == None else player
        if not Piece._inBoard(x, y) or not map[x, y].isPlayers(player):
            return []

        rec = [(i, j) for i in range(-1, 2) for j in range(-1, 2)\
            if abs(i) != abs(j) and map[x, y].hasSameTypeAs(Piece.P1_ROOK)\
            or abs(i) * abs(j) == 1 and map[x, y].hasSameTypeAs(Piece.P1_BISHOP)\
            or abs(i) + abs(j) != 0 and map[x, y].hasSameTypeAs(Piece.P1_QUEEN)]

        checkByTile = [(x + i, y + j) for i in range(-2, 3) for j in range(-2, 3) if abs(i) + abs(j) == 3 and map[x, y].hasSameTypeAs(Piece.P1_KNIGHT)] +\
            [(x + i, y + j) for i in range(-1, 2) for j in range(-1, 2) if abs(i) + abs(j) != 0 and map[x, y].hasSameTypeAs(Piece.P1_KING)]


        return Piece._getPawnMoves(x=x, y=y, map=map, player=player, logs=logs) +\
            Piece._explore(x, y, map, player, direction = rec) +\
            [((x, y), (nx, ny)) for nx, ny in checkByTile if Piece.isValidFor(nx, ny, map, player)] +\
            ([] if not casteling or not map[x, y].hasSameTypeAs(Piece.P1_KING) else Piece._getCastlingMoves(map=map, player=player, logs=logs))

    @staticmethod
    def _explore(x: int, y: int, map: dict, player: bool, stepx: int = None, stepy: int = None, direction: list = None) -> List:
        moves = []
        if direction:
            for sx, sy in direction:
                moves += [((x, y), (nx, ny)) for nx, ny in Piece._explore(x + sx, y + sy, map, player, sx, sy)]
            return moves
        if stepx == None or stepy == None or not Piece._inBoard(x, y) or map[x, y].isPlayers(player):
            return []

        return [(x, y)] if not map[x, y].isEmpty() else ([(x, y)] + Piece._explore(x + stepx, y + stepy, map, player, stepx, stepy))

    @staticmethod
    def _getCastlingMoves(map: dict, player, logs):
        x = 7 if player else 0
        return ([] if map[x, 0].isMoved(logs) or map[x, 4].isEmpty() or map[x, 4].isMoved(logs) or [y for y in range(1, 4) if not map[x, y].isEmpty()] or [y for y in range(1, 5) if Piece.isAttacked(tile=(x, y), map=map, player=player, logs=logs)] else [((x, 4), (x, 2))])+\
            ([] if map[x, 7].isMoved(logs) or map[x, 4].isEmpty() or map[x, 4].isMoved(logs) or [y for y in range(5, 7) if not map[x, y].isEmpty()] or [y for y in range(4, 7) if Piece.isAttacked(tile=(x, y), map=map, player=player, logs=logs)] else [((x, 4), (x, 6))])

    @staticmethod
    def _getPawnMoves(x: int, y: int, map, player: bool, logs: list):
        moves = []
        if not Piece._inBoard(x, y) or not Piece.isPlayers(map[x, y], player) or not map[x, y].hasSameTypeAs(Piece.P1_PAWN):
            return moves

        d = 1 if map[x, y].isPlayers(False) else -1
        if Piece._inBoard(x + d, y) and map[x + d, y].isEmpty():
            moves.append(((x, y), (x + d, y)))
            if Piece._inBoard(x + d * 2, y) and map[x + d * 2, y].isEmpty() and x == (6 if player else 1):
                moves.append(((x, y), (x + d * 2, y)))

        if Piece._inBoard(x + d, y + 1) and Piece.isPlayers(map[x + d, y + 1], not player):
            moves.append(((x, y), (x + d, y + 1)))

        if Piece._inBoard(x + d, y - 1) and Piece.isPlayers(map[x + d, y - 1], not player):
            moves.append(((x, y), (x + d, y - 1)))

        return moves + Piece.getEnPassant(x=x, y=y, map=map, logs=logs)

    @staticmethod
    def _inBoard(x: int, y: int) -> bool:
        return x in range(8) and y in range(8)

    @staticmethod
    def isValidFor(x: int, y: int, map: list, player: bool):
        return Piece._inBoard(x, y) and(map[x, y].isPlayers(not player) or map[x, y].isEmpty())

    @staticmethod
    def getEnPassant(x: int, y: int, map: list, logs: list):
        if logs:
            frm = logs[-1].sp
            to = logs[-1].ep
            pp = map[x, y]
            ep = map.get(to)
            if not abs(to[0] - frm[0]) == 2 or to[0] != x or abs(y - to[1]) != 1 or not pp.hasSameTypeAs(Piece.P1_PAWN) or not ep.hasSameTypeAs(Piece.P1_PAWN) or not pp.isEnemy(ep):
                return []
            else:
                return [((x, y), (to[0] + (frm[0] - to[0]) // 2, to[1]))]
        else:
            return []

    @staticmethod
    def toPGN(log, map):
        other = map[log.ep]
        slf = log.piece
        x, y = log.ep
        if slf.hasSameTypeAs(Piece.P1_KING) and abs(log.sp[1] - y) == 2:
            return 'O-O' if y > 4 else 'O-O-O'
        fr = '' if other.isEmpty() or not slf.hasSameTypeAs(Piece.P1_PAWN) else chr(ord('a')+log.sp[1])
        return fr+ slf.toPGNName() + ('' if other.isEmpty() else 'x') + chr(ord('a')+y) + str(8-x) + (log.promoted.toPGNName() if log.promoted else '')

# self, other, x, y, _, sy, promotion
    def toPGNName(self):
        return '' if self.hasSameTypeAs(Piece.P1_PAWN) else ('N' if self.hasSameTypeAs(Piece.P1_KNIGHT) else str(self)[1].upper())

    def toJson(self):
        return self.value
