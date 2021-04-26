from IA import MinMax
from typing import List
import PySide6

from PySide6.QtGui import QGuiApplication, QResizeEvent
from game.piece import Piece
from game.game import Game, Result
import sys
from PySide6.QtCore import QSize, QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QMainWindow, QMenuBar, QMessageBox, QPushButton, QWidget
import functools
from enum import Enum

class ColorPalette(Enum):
    ACTIVE_COLOR = "#605050"
    TILE_ONE = "#400000"
    TILE_TWO = "#FFFFFF"
    SUGGESTED_MOVE = "#808080"
    ATTACK = "#905060"
    CHECK = "#B05080"
    CHOICES_BACKGROUND = "#F0FFFFFF"

class MainUI(QApplication):
    def __init__(self, saveDefaultPath: List[str] = None, loadFile: List[str] = None, time: float = None, enableIa:bool = None):
        super(MainUI, self).__init__(sys.argv)
        if loadFile:
            self.game = Game.loadJson(loadFile[0], self.trigger, allowedTime=time)
        else:
            self.game = Game(self.trigger, allowedTime=time)
        self.enableIa = enableIa
        self.saveDefaultPath = None if not saveDefaultPath or saveDefaultPath.__class__ != list else saveDefaultPath[0]
        self.ia = MinMax(game=self.game)

    def initialize(self):
        screen = QGuiApplication.primaryScreen().size()
        size = screen.height()*0.7
        self.window = QMainWindow()
        self.window.setAutoFillBackground(True)
        self.window.setWindowFlag(PySide6.QtCore.Qt.WindowType.WindowMaximizeButtonHint, False)
        self.window.setWindowTitle('Chess')
        self.window.resize(size, size)
        self.window.move((screen.width() - self.window.width())//2, (screen.height() - self.window.height())//2)
        self.window.show()
        self.margin = 10
        self.button_size = (size- 2*self.margin)//8

    def construct(self):
        self.container = QWidget()
        self.content = QWidget(parent=self.container)
        # self.content = QWidget()
        self.window.setCentralWidget(self.container)
        self.constructMenu()
        self.constructButtons()
        self.constructChoices()
        self.createClock()
        self.updateView()
        self.window.resizeEvent = self.onResize

    @staticmethod
    def originalTileColor(i: int, j: int) -> ColorPalette:
        return ColorPalette.TILE_ONE if i % 2 == j % 2 else ColorPalette.TILE_TWO

    def onGridClicked(self, i, j):
        if self.selected != None and (self.selected, (i, j)) in self.previousSuggestions:
            self.game.move(self.selected, (i, j))
            if self.enableIa and not self.game.player:
                move = self.ia.generate()
                self.game.move(frm=move[0], to=move[1])

        self.selected = None
        self.previousSuggestions = None

        if self.game.map[i, j] != Piece.EMPTY:
            self.selected = (i, j)
            self.previousSuggestions = self.game.getAvailableMoves(i, j)

        self.updateView()

    def onUpgrade(self, pieceIndex):
        self.game.choice(self.getChoices()[pieceIndex])

    def updateView(self, event: QResizeEvent = None):
        self.content.setEnabled(self.game.winner() == Result.RUNNING)
        if self.game.upgrade:
            self.choicesView.show()
            self.content.setDisabled(True)
        else:
            self.choicesView.hide()
            self.content.setDisabled(False)

        if not event or event.oldSize().width() - event.size().width():
            self.button_size = (self.window.width() - 2 * self.margin) // 8
        elif not event or event.oldSize().height() - event.size().height():
            self.button_size = (self.window.height() - 2 * self.margin - self.window.menuBar().height() - self.clockContainer.height()) // 8
        boardSize = 2*self.margin + 8 * self.button_size

        self.container.resize(boardSize, boardSize + self.clockContainer.height())
        self.window.resize(self.container.width() , self.container.height() + self.window.menuBar().height())
        self.choicesView.resize(len(self.choicesButtons)*(self.margin+self.button_size)+self.margin, self.margin*2+self.button_size)
        self.choicesView.move((boardSize - self.choicesView.width()) // 2, (self.content.height() - self.choicesView.height()) // 2)
        self.content.resize(boardSize, boardSize)
        self.clockContainer.resize(boardSize, self.clockContainer.height())
        self.content.move(0, self.clockContainer.height())
        self.clockB.move(boardSize - self.clockB.width() - self.margin, self.margin)

        for i, j in self.buttons:
            self.buttons[i, j].resize(self.button_size, self.button_size)
            self.buttons[i, j].move(self.button_size * j + self.margin,  self.button_size * i + self.margin)
            self.buttons[i, j].setIcon(self.game.map[i, j].getIcon())
            self.setBackgourdColor(self.buttons[i, j], self.originalTileColor(i, j))
            self.buttons[i, j].setIconSize(QSize(self.buttons[i, j].width()*2/3, self.buttons[i, j].height()*2/3))


        winner = self.game.winner()

        if winner != Result.RUNNING:
            self.showDialog(str(winner)+"\nPlease start a new game.", "Info", QMessageBox.Ok, lambda _: None)
            return

        for i in range(len(self.choicesButtons)):
            self.choicesButtons[i].setIcon(self.getChoices()[i].getIcon())
            self.choicesButtons[i].setIconSize(QSize(self.button_size*2/3, self.button_size*2/3))
            self.choicesButtons[i].resize(self.button_size, self.button_size)
            btnW=self.button_size + self.margin
            self.choicesButtons[i].move(self.margin//2 + (self.choicesView.width()- btnW*len(self.choicesButtons))//2 + btnW*i, (self.choicesView.height()-self.button_size)//2)

        if self.selected:
            self.setBackgourdColor(
                self.buttons[self.selected[0], self.selected[1]], ColorPalette.ACTIVE_COLOR)

        if(self.previousSuggestions):
            for (_, (mi, mj)) in self.previousSuggestions:
                self.setBackgourdColor(
                    self.buttons[mi, mj], ColorPalette.ATTACK if self.game.map[mi, mj] != Piece.EMPTY else ColorPalette.SUGGESTED_MOVE)

        if self.game.check():
            self.setBackgourdColor(self.buttons[self.game.getPiece(
                Piece.P1_KING if self.game.player else Piece.P2_KING)], ColorPalette.CHECK)
        self.undo.setEnabled(len(self.game.undoes)>0)
        self.redo.setEnabled(len(self.game.redos)>0)

    @staticmethod
    def setBackgourdColor(widget: QWidget, color: ColorPalette):
        if 'background-color' in widget.styleSheet():
            bk_index_start = widget.styleSheet().index('background-color')
            bk_index_end = widget.styleSheet().index(';', bk_index_start) + 1
            widget.setStyleSheet(widget.styleSheet()[
                                 :bk_index_start]+widget.styleSheet()[bk_index_end:]+'background-color: '+color.value+';')
        else:
            widget.setStyleSheet(widget.styleSheet() + 'background-color: '+color.value+';')

    def onResize(self, event: QResizeEvent):
        self.updateView(event)

    def getChoices(self) -> List[Piece]:
        return [Piece(choice.value%Piece.P2_PAWN.value + (0 if self.game.player else Piece.P2_PAWN.value)) for choice in [Piece.P1_ROOK, Piece.P1_KNIGHT, Piece.P1_BISHOP, Piece.P1_QUEEN]]

    def trigger(self):
        self.updateView()

    def constructChoices(self):
        self.game.trigger= self.trigger
        self.choicesView: QWidget = QWidget(parent=self.container)
        # self.choicesBackground: QWidget = QWidget(parent=self.choicesView)
        self.choicesButtons: list[QPushButton] = []
        self.choicesView.setStyleSheet("border: solid;border-width: 2;")
        self.setBackgourdColor(widget=self.choicesView, color=ColorPalette.CHOICES_BACKGROUND)

        for i in range(len(self.getChoices())):
            self.choicesButtons.append(QPushButton(self.choicesView))
            self.choicesButtons[i].clicked.connect(functools.partial(self.onUpgrade, i))

    def constructButtons(self):
        self.buttons: List[QPushButton] = {}
        self.selected = None
        self.previousSuggestions = None
        for i in range(8):
            for j in range(8):
                self.buttons[i, j] = QPushButton(self.content)
                self.buttons[i, j].clicked.connect(functools.partial(self.onGridClicked, i, j))
                self.buttons[i, j].setStyleSheet(f"background-color: {self.originalTileColor(i, j).value};")

    def constructMenu(self):
        menuBar= QMenuBar()
        self.window.setMenuBar(menuBar)
        file = menuBar.addMenu('File')
        edit = menuBar.addMenu('Edit')
        file.addAction('New Game').triggered.connect(functools.partial(self.newGame,))
        self.undo = edit.addAction('Undo')
        self.undo.triggered.connect(lambda _: self.game.undo())
        self.redo = edit.addAction('Redo')
        self.redo.triggered.connect(lambda _: self.game.redo())
        sv = file.addMenu('Save')
        sv.addAction('as text').triggered.connect(functools.partial(self.save, self.game.saveAsText))
        sv.addAction('as PGN').triggered.connect(functools.partial(self.save, self.game.saveAsPGN))
        sv.addAction('as JSON').triggered.connect(functools.partial(self.save, self.game.saveAsJSON))
        sva = file.addMenu('Save As')
        sva.addAction('as text').triggered.connect(functools.partial(self.saveAs, self.game.saveAsText))
        sva.addAction('as PGN').triggered.connect(functools.partial(self.saveAs, self.game.saveAsPGN))
        sva.addAction('as JSON').triggered.connect(functools.partial(self.saveAs, self.game.saveAsJSON))
        file.addAction('Load Game').triggered.connect(functools.partial(self.load, self.game.loadJson))
        file.addAction('Abandon').triggered.connect(functools.partial(self.showDialog, "Do you want really to abandon?", "Warning", QMessageBox.No | QMessageBox.Yes, self.abandon))
        file.addAction('Draw').triggered.connect(functools.partial(self.showDialog, ("White" if self.game.player else "Black") + " is proposing draw", "Info", QMessageBox.No | QMessageBox.Yes, self.proposeDraw))
        file.addAction('Quit').triggered.connect(lambda _: exit(0))

    def save(self, f):
        if self.saveDefaultPath:
            f(self.saveDefaultPath)
        else:
            self.saveAs(f)

    def saveAs(self, f):
        saveAs = QFileDialog()
        saveAs.setDefaultSuffix('.json')
        self.timer.stop()
        fileName, _ = saveAs.getSaveFileName(parent=self.window, filter="JSON (*.json)", caption="Save as json file.")
        self.timer.start(1)
        if fileName:
            self.saveDefaultPath = fileName
            self.save(f)

    def load(self, f):
        self.timer.stop()
        fileName, _ = QFileDialog.getOpenFileName(parent=self.window, filter="JSON (*.json)")
        self.timer.start()
        if fileName:
            self.saveDefaultPath = fileName
            self.game: Game = f(fileName, trigger=self.trigger, maxTime=self.game.allowedTime)
            self.updateView()

    def newGame(self):
        self.game: Game = Game(self.trigger, allowedTime=self.game.allowedTime)
        self.construct()

    def createClock(self):
        self.clockContainer = QWidget(self.container)
        self.clockW: QLabel = QLabel(parent=self.clockContainer, text=self.format(self.game.getRemainingTime(True)))
        self.clockB: QLabel = QLabel(parent=self.clockContainer, text=self.format(self.game.getRemainingTime(False)))
        self.clockW.move(self.margin, self.margin)
        self.timer: QTimer = QTimer(self.clockContainer)
        self.timer.timeout.connect(self.updateTime)
        self.timer.start(1000)

    def showDialog(self, text: str, title: str, buttons, callback):
        dialog = QMessageBox(self.window)
        dialog.setWindowTitle(title)
        dialog.setText(text)
        dialog.setStandardButtons(buttons)
        dialog.buttonClicked.connect(callback)
        dialog.exec_()

    def abandon(self, value: QPushButton):
        if value.text().lower().count('yes'):
            self.game.abandon = self.game.player
            self.updateView()

    def proposeDraw(self, value: QPushButton):
        if value.text().lower().count('yes'):
            self.game.draw = True
            self.updateView()

    def updateTime(self):
        wr = self.game.getRemainingTime(True)
        br = self.game.getRemainingTime(False)
        if self.game.winner() == Result.RUNNING:
            c = wr if self.game.player else br
            self.timer.start(c-int(c) if c>0 else 1)
        else:
            self.timer.stop()
            self.updateView()
        self.clockW.setText(self.format(wr))
        self.clockB.setText(self.format(br))

    def format(self, time: float):
        if time <= 0:
            return "tmout"
        st = ""
        if time >= 3600:
            st += f"{time//3600}:"
            time = time % 3600
        st += '0' if time//60 < 10 else ''
        st += f"{time//60}:"
        time = time % 60
        st += '0' if time < 10 else ''
        st += f"{int(time)}"
        return st