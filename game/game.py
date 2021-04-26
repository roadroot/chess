from enum import Enum
from game.piece import Piece
from typing import Dict, List, Tuple
from time import time
from datetime import datetime
import json

class Result(Enum):
    RUNNING = 0
    P1 = 1
    P2 = 2
    DRAW = 3
    P1_TIMEOUT = 4,
    P2_TIMEOUT = 5
    P1_ABANDON = 6
    P2_ABANDON = 7

    def __str__(self) -> str:
        if self == Result.RUNNING:
            return "Game is still running"
        elif self == Result.P1:
            return "White won the game"
        elif self == Result.P2:
            return "Black won the game"
        elif self == Result.P1_TIMEOUT:
            return "White lost: timeout"
        elif self == Result.P2_TIMEOUT:
            return "Black lost: timeout"
        elif self == Result.P1_ABANDON:
            return "White abandoned the game"
        elif self == Result.P2_ABANDON:
            return "Black abandoned the game"
        elif self == Result.DRAW:
            return "Draw"

class LogEntry:
    def __init__(self, sp: Tuple[int, int], ep: Tuple[int, int], piece: Piece, attacked: Piece, moveCost: float, dt: float = time()) -> None:
        self.dt: float = dt
        self.sp: Tuple[int, int] = sp
        self.ep: Tuple[int, int] = ep
        self.piece: Piece = piece
        self.attacked: Piece = attacked
        self.promoted: Piece = None
        self.moveCost: float = moveCost

    def __str__(self):
        return f"{datetime.fromtimestamp(self.dt)}: went from {self.sp} to {self.ep} with {self.piece}"
    def __unicode__(self):
        return f"{datetime.fromtimestamp(self.dt)}: went from {self.sp} to {self.ep} with {self.piece}"
    def __repr__(self):
        return f"{datetime.fromtimestamp(self.dt)}: went from {self.sp} to {self.ep} with {self.piece}" + ("" if self.attacked.hasSameTypeAs(Piece.P1_PAWN) else f" and captured {self.attacked}" )

    @staticmethod
    def fromPGN(pgn: str):
        return

    def toJSON(self) -> Dict:
        return {'dt': self.dt, 'moveCost': self.moveCost, 'sp': self.sp, 'ep': self.ep, 'piece': self.piece.toJson(), 'attacked': self.attacked.toJson(), 'promoted': self.promoted.toJson() if self.promoted else None}

    @staticmethod
    def fromJSON(jsonDict: dict, offset):
        le = LogEntry(moveCost=jsonDict['moveCost'], dt=jsonDict['dt']+offset, ep=tuple(jsonDict['ep']), piece=Piece(jsonDict['piece']), attacked=Piece(jsonDict['attacked']), sp=tuple(jsonDict['sp']))
        return le

class Player:
    def __init__(self,score: int = 0, name = "Player") -> None:
        self.score: int = score
        self.name = name
        self.time: float = 0

class Game:
    def __init__(self, trigger, allowedTime: int) -> None:
        self.allowedTime = allowedTime if allowedTime else 1800
        self.startTime:datetime = datetime.now()
        self.time:float = time()
        self.round: int = 0
        self.playerW: Player = Player(name="Player White")
        self.playerB: Player = Player(name="Player Black")
        self.upgrade = None
        self.map: dict[tuple[int, int], Piece] = self.generateMap()
        self.player = True
        self.logs: list[LogEntry] = []
        self.trigger: function[None, None] = trigger
        self.undoes = []
        self.redos = []
        self.abandon: bool = None
        self.draw: bool = None

    def log(self, sp: Tuple, ep: Tuple, piece: Piece, attacked: Piece, moveCost: float, dt: float = time()):
        self.logs.append(LogEntry(sp=sp, ep=ep, piece=piece, dt=dt, attacked=attacked, moveCost=moveCost))

    def getAvailableMoves(self, x: int, y: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        piece: Piece = self.map[x, y]
        moves = []
        if self.playable(x, y):
            moves = piece.getMoves(x=x, y=y, map=self.map, logs=self.logs, casteling = True)
        return [move for move in moves if not self.check(move=move)]

    def playable(self, x, y) -> bool:
        return self.map[x, y].isPlayers(self.player)

    def check(self, map: dict = None, player: bool = None, move: Tuple = None) -> bool:
        map = map if map else self.map
        player = self.player if player == None else player

        if move != None:
            map = map.copy()
            map[move[1][0], move[1][1]] = map[move[0][0], move[0][1]]
            map[move[0][0], move[0][1]] = Piece.EMPTY

        return len([move for x, y in map for move in [(_, (ax, ay)) for (_, (ax, ay)) in Piece.getMoves(x=x, y=y, map=map, player=not player, logs=self.logs, casteling=False) if map[ax, ay].hasSameTypeAs(Piece.P1_KING)]])>0

    def getPiece(self, piece: Piece) -> Tuple:
        for i, j in self.map:
            if self.map[i, j] == piece:
                return i, j
        return None

    def winner(self) -> Result:
        if self.abandon != None:
            return Result.P1_ABANDON if self.abandon else Result.P2_ABANDON

        if self.draw:
            return Result.DRAW

        if self.getRemainingTime(True)<=0:
            return Result.P1_TIMEOUT

        if self.getRemainingTime(False)<=0:
            return Result.P2_TIMEOUT

        for i, j in self.map:
            if self.getAvailableMoves(i, j) != []:
                return Result.RUNNING
        return Result.DRAW if not self.check() else Result.P2 if self.player else Result.P1

    def isAttaced(self, x: int, y: int, defender: bool = None):
        defender = self.player if defender == None else defender
        map = self.map.copy()
        if map[x, y] == Piece.EMPTY:
            map[x, y] = Piece.P1_PAWN if defender else Piece.P2_PAWN
        for i, j in map:
            if map[i, j].isP1s() and not defender or map[i, j].isP2s() and defender:
                if len([((si, sj), (ei, ej)) for ((si, sj), (ei, ej)) in map[i, j].getMoves(i, j, map) if (ei, ej) == (x, y)]) > 0:
                    return True
        return False

    def __switch(self, d: Tuple[int, int], s: Tuple[int, int], map: Dict[Tuple[int, int], Piece] = None):
        map = map if map else self.map
        map[tuple(d)] = map[tuple(s)]
        map[tuple(s)] = Piece.EMPTY

    def move(self, frm: Tuple[int, int], to: Tuple[int, int], promoted: Piece = None, dt: float = None, do: bool = True, moveCost: float = None) -> None:
        dt = dt if dt != None else time()
        moveCost = moveCost if moveCost != None else (dt - (self.logs[-1].dt if self.logs else self.time))
        (self.playerW if self.player else self.playerB).time += moveCost
        attacked = self.map[to]
        enPassant = Piece.getEnPassant(*frm, map=self.map, logs=self.logs)
        if enPassant and enPassant[0] == (frm, to):
            self.map[frm[0], to[1]] = Piece.EMPTY
        self.__switch(to, frm)
        self.player = not self.player
        direction = (to[1] - frm[1]) / 2
        if to[0] == frm[0] and abs(direction) == 1 and self.map.get(to).hasSameTypeAs(Piece.P1_KING):
            direction = int(direction)
            y = 0 if direction == -1 else 7
            self.__switch((frm[0], direction + 4), (frm[0], y))
        if self.map[tuple(to)].hasSameTypeAs(Piece.P1_PAWN) and to[0] in [0, 7]:
            self.upgrade = to
            self.player = not self.player
            if promoted:
                self.choice(promoted)
        if do:
            self.undoes.append(self.toJSON())
            self.redos.clear()
        self.log(sp=frm, ep=to, piece=self.map[to], attacked=attacked, dt=dt, moveCost=moveCost)

    def choice(self, piece: Piece):
        if self.upgrade:
            self.map[self.upgrade] = piece
            self.player = not self.player
            self.upgrade = None
            self.trigger()
            self.logs[-1].promoted = piece

    def saveAsText(self, path: str):
        with open(path, 'w') as save:
            for st in [str(move) + '\n' for move in self.logs]:
                save.write(st)

    def saveAsPGN(self, path: str):
        with open(path, 'w') as save:
            map = Game.generateMap()
            save.write('[Event "Chess Project"]\n')
            save.write('[Site "University of Paris (Descartes)"]\n')
            save.write(f'[DATE "{self.startTime.date().strftime("%Y.%m.%d")}"]')
            save.write(f'[Round "{self.round}"]\n')
            save.write(f'[White "{self.playerW.name}"]\n')
            save.write(f'[Black "{self.playerB.name}"]\n')
            save.write(f'[Result "{"*" if self.winner()==Result.RUNNING else f"{self.playerW.score}/{self.playerW.score + self.playerB.score}-/{self.playerB.score}/{self.playerW.score + self.playerB.score}"}"]\n')
            for i in  range(len(self.logs)//2):
                save.write(f'{i+1}. ' + Piece.toPGN(self.logs[2*i], map) + ' ')
                self.__switch(self.logs[2*i].ep, self.logs[2*i].sp, map)
                save.write(Piece.toPGN(self.logs[2*i+1], map) + '\n')
                self.__switch(self.logs[2*i+1].ep, self.logs[2*i+1].sp, map)
            if len(self.logs)%2:
                save.write(f'{len(self.logs)//2+1}. ' + Piece.toPGN(self.logs[-1], map))

    def saveAsJSON(self, path: str):
        with open(path, 'w') as save:
            save.write(json.dumps(self.toJSON()))

    @staticmethod
    def generateMap():
        map = {}
        for i in range(8):
            for j in range(8):
                if i == 1:
                    map[i, j] = Piece.P2_PAWN
                elif i == 6:
                    map[i, j] = Piece.P1_PAWN
                elif i == 0 or i == 7:
                    if j == 0 or j == 7:
                        map[i, j] = Piece(Piece.P1_ROOK.value + (Piece.P2_PAWN.value if i < 4 else 0))
                    elif j == 1 or j == 6:
                        map[i, j] = Piece(Piece.P1_KNIGHT.value + (Piece.P2_PAWN.value if i < 4 else 0))
                    elif j == 2 or j == 5:
                        map[i, j] = Piece(Piece.P1_BISHOP.value + (Piece.P2_PAWN.value if i < 4 else 0))
                    elif j == 3:
                        map[i, j] = Piece(Piece.P1_QUEEN.value + (Piece.P2_PAWN.value if i < 4 else 0))
                    elif j == 4:
                        map[i, j] = Piece(Piece.P1_KING.value + (Piece.P2_PAWN.value if i < 4 else 0))
                else:
                    map[i, j] = Piece.EMPTY
        return map

    @staticmethod
    def loadJson(file: str, trigger, maxTime):
        g: Game = Game(trigger, allowedTime=maxTime)
        with open(file, 'r') as pgn:
            pgn = json.load(pgn)
            g.time = pgn['time'] + time() - pgn['save']
            g.logs = [LogEntry.fromJSON(log, offset =  g.time - pgn['time']) for log in pgn['log']]
            g.playLog()
        return g

    def toJSON(self):
        log = {'log' : [move.toJSON() for move in self.logs]}
        log['time'] = self.time
        log['save'] = time()
        return log

    def undo(self):
        self.redos.append(self.toJSON())
        gs = self.undoes.pop()
        offset = time() - gs['save']
        self.time = gs['time'] + offset
        logs = [LogEntry.fromJSON(log, offset = offset) for log in gs['log']]
        self.playLog(logs, do=False)
        self.trigger()

    def redo(self):
        self.undoes.append(self.toJSON())
        gs = self.redos.pop()
        offset = time() - gs['save']
        self.time = gs['time'] + offset
        logs = [LogEntry.fromJSON(log, offset = offset) for log in gs['log']]
        self.playLog(logs, do=False)
        self.trigger()

    def playLog(self, logs: List[LogEntry] = None, do = True):
        logs = logs.copy() if logs != None else self.logs.copy()
        self.playerB.time = 0
        self.playerW.time = 0
        self.logs.clear()
        self.map.clear()
        self.player = True
        nm = self.generateMap()
        for k in nm:
            self.map[k] = nm[k]
        for move in logs:
            self.move(frm=move.sp, to=move.ep, promoted = move.promoted, do = do, dt=move.dt, moveCost=move.moveCost)

    def getRemainingTime(self, player: bool) -> int:
        reference = time() - (self.logs[-1].dt if self.logs else self.time)
        ptime = reference if player == self.player else 0
        remainingTime = self.allowedTime - ptime - (self.playerW if player else self.playerB).time
        return int(remainingTime)
