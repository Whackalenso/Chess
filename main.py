import os
from abc import abstractmethod
from enum import IntEnum
import math

from pygame_tool import *
import pygame

WIN_SIZE = (700, 750)

BOARD_SIZE = (600, 600)
BOARD_OFFSET = (50, 50)

CAPTURED_PIECE_PADDING = 5
CAPTURED_PIECE_ROW_SPACING = 8

#region Util

def inCheck(pos, side):
  _otherSide = game.sides[abs(int(side.color)-1)]

  for p in _otherSide.pieces:
    if p.canMoveTo(pos, kingCheck=False, castling=False):
      return True
  return False

def emptyPath(piece, relPos):
  length = abs(relPos[0 if relPos[0] != 0 else 1])
  for i in range(1, int(length)):
    square = (i/length * relPos[0] + piece.boardPosition[0], i/length * relPos[1] + piece.boardPosition[1])
    if game.squares.get(square):
      return False
  return True

def pixelToBoardPos(position):
    column = math.floor((position[0]-BOARD_OFFSET[0])/BOARD_SIZE[0] * 8)
    row = math.floor((position[1]-BOARD_OFFSET[0])/BOARD_SIZE[1] * 8)

    for i in [column, row]:
      if not (0 <= i <= 7):
        return None
    return (column, row)

def boardToPixelPos(position):
    return (position[0]/8 * BOARD_SIZE[0] + BOARD_OFFSET[0], position[1]/8 * BOARD_SIZE[1] + BOARD_OFFSET[1])

def capturedPieceRows():
  rowsMidpoint = (BOARD_SIZE[1] + WIN_SIZE[1] + BOARD_OFFSET[1])/2
  return [rowsMidpoint-(CAPTURED_PIECE_ROW_SPACING/2)-capturedPieceSquareSize(), rowsMidpoint+(CAPTURED_PIECE_ROW_SPACING/2)]

def capturedPieceSquareSize():
  return int(WIN_SIZE[0]/16) - CAPTURED_PIECE_PADDING

def squareSize():
    return (int(BOARD_SIZE[0]/8), int(BOARD_SIZE[1]/8))

def isLine(relPos):
  return (abs(relPos[0]) == abs(relPos[1])) or ((relPos[0] == 0) ^ (relPos[1] == 0))

def otherSide():
  return game.sides[0] if game.currentSide == game.sides[1] else game.sides[1]

def colorToRgb(color, opposite=False):
  if opposite:
    color = {Color.WHITE:Color.BLACK, Color.BLACK: Color.WHITE}[color]

  return {Color.WHITE: (248, 188, 58), Color.BLACK: (140, 91, 62)}[color] #(255, 215, 36) (113, 82, 0)

def centerBotText(botText):
  botText.position = (WIN_SIZE[0]/2 - botText.size[0]/2, (BOARD_SIZE[1]+BOARD_OFFSET[1]+WIN_SIZE[1])/2 - botText.surface.get_height()/2)

#endregion

#region Classes

class Side:
  def __init__(self, color, game):
    self.color = color
    self.moveDirection = [1, -1][int(color)]
    self.capturedPieces = {}
    self._capturedPiecesPositions = {}
    self.game = game
    self.init()

  def init(self, positions=None, piecesMoved=[], capturedPieces=None):
    if positions == None:
      positions = STARTING_POSITIONS

    for piece, _positions in positions[self.color].items():
      for position in _positions:
        pos = position
        if self.moveDirection != [1, -1][int(self.color)]:
          pos = (7-pos[0], 7-pos[1])
        self.game.addGameObject(piece(self, pos, self.game, moved=(position in piecesMoved)))

    if capturedPieces != None:
      for p, gObj in self.capturedPieces.copy().items():
        if p not in capturedPieces.keys():
          self.game.removeGameObject(gObj)
          self.capturedPieces.pop(p)
      for p, gObj in capturedPieces.items():
        if p not in self.capturedPieces.keys():
          self.game.addGameObject(gObj)
          self.capturedPieces[p] = gObj
          self._capturedPiecesPositions[p] = gObj

  @property
  def pieces(self):
    _pieces = []
    for sqr in game.squares.values():
      if sqr != None:
        if sqr.color == self.color:
          _pieces.append(sqr)
    return _pieces

  @property
  def kingPos(self):
    for pos, piece in game.squares.items():
      if piece.color == self.color:
        if isinstance(piece, King):
          return pos
    return None

class ChessVersion:
  def __init__(self, _game):
    normalized = _game.squares.copy()
    if _game.sides[0].moveDirection != 1:
      normalizedCopy = normalized.copy()
      normalized = {}
      for pos, piece in normalizedCopy.items():
        normalized[(7-pos[0], 7-pos[1])] = piece

    self.positions = {Color.WHITE: {}, Color.BLACK: {}}
    self.piecesMoved = []
    for pos, piece in normalized.items():
      if self.positions[piece.color].get(type(piece)) == None:
        self.positions[piece.color][type(piece)] = [pos]
      else:
        self.positions[piece.color][type(piece)].append(pos)

      if piece.moved:
        self.piecesMoved.append(pos)

    self.capturedPieces = {s.color:{k : v.position for k, v in s.capturedPieces.items()} for s in _game.sides}
    self.currentSide = _game.sides.index(_game.currentSide)
    self.gameOver = _game.gameOver

    self.promotionPawn = _game.promotionPawn
    if self.promotionPawn != None:
      promoPos = self.promotionPawn.boardPosition
      if _game.sides[0].moveDirection != 1:
        promoPos = (7-promoPos[0], 7-promoPos[1])
      self.promotionPawn = promoPos

    self.enPassant = _game.enPassant
    if self.enPassant != None:
      if _game.sides[0].moveDirection != 1:
        self.enPassant = (7-self.enPassant[0], 7-self.enPassant[1])

class Chess(Game):
  def __init__(self):
    super().__init__(WIN_SIZE, windowTitle="Chess")
    self._buttons = []
    self.init()

  def init(self):
    self._gameObjects.clear()

    background = GameObject(pygame.image.load(os.path.join('Assets', 'Chess Board v3.png')), size=BOARD_SIZE, position=BOARD_OFFSET)
    self.addGameObject(background)
    self.addGameObject(redClick)

    self.squares = {}
    self.selectedPiece = None
    self.flippingBoard = False
    self.sides = [Side(c, self) for c in [Color.WHITE, Color.BLACK]]
    self.currentSide = self.sides[0]
    self.enPassant = None
    self._gameOver = False
    self._promotionPawn = None

    self.updateColor()

    super().addButtons(self._buttons)

    self.history = [self.version()] # list of HistoryObject
    self._historyIndex = 0

  def version(self):
    return ChessVersion(self)

  @property
  def historyIndex(self):
    return self._historyIndex

  @historyIndex.setter
  def historyIndex(self, index):
    version = self.history[index]

    for piece in self.squares.values():
      self.removeGameObject(piece)
    self.squares = {}
    for s in self.sides:
      s.init(positions=version.positions, piecesMoved=version.piecesMoved, capturedPieces={k : s._capturedPiecesPositions[v] for k, v in version.capturedPieces[s.color].items()})
    self.currentSide = self.sides[version.currentSide]

    self.gameOver = version.gameOver

    promoPawn = version.promotionPawn
    if promoPawn != None:
      if self.sides[0].moveDirection != 1:
        promoPawn = (7-promoPawn[0], 7-promoPawn[1])
      promoPawn = self.squares[promoPawn]
    self.promotionPawn = promoPawn

    self.enPassant = version.enPassant
    if self.enPassant != None:
      if self.sides[0].moveDirection != 1:
        self.enPassant = (7-self.enPassant[0], 7-self.enPassant[1])

    self.updateColor()

    self._historyIndex = index
    self.onHistoryChange()

  def updateHistory(self):
    self.history = self.history[self.historyIndex:]
    self.history.insert(0, self.version())
    self._historyIndex = 0
    self.onHistoryChange()

  def onHistoryChange(self):
    if len(self.history) > self.historyIndex+1:
      if not undoButton.inGame:
        undoButton.add(game)
    else:
      if undoButton.inGame:
        undoButton.remove(game)

    if self.historyIndex > 0:
      if not redoButton.inGame:
        redoButton.add(game)
    else:
      if redoButton.inGame:
        redoButton.remove(game)

  def updateColor(self):
    self.backgroundColor = colorToRgb(self.currentSide.color)

  def addButtons(self, buttons):
    super().addButtons(buttons)
    self._buttons.extend(buttons)

  @property
  def gameOver(self):
    return self._gameOver

  @gameOver.setter
  def gameOver(self, value):
    global gameOverTextObj
    gameOverTextObj = self._botText(gameOverText, gameOverTextObj, self.gameOver, value)
    self._gameOver = value

  @property
  def promotionPawn(self):
    return self._promotionPawn

  @promotionPawn.setter
  def promotionPawn(self, value):
    global promotionTextObj
    promotionTextObj = self._botText(promotionText, promotionTextObj, self.promotionPawn != None, value != None)
    self._promotionPawn = value
    
  #if theres every problems it might be cuz the text only gets changed locally in the function
  def _botText(self, text, textObj, oldBool, newBool):
    if newBool and not oldBool:
      text.text = text.text.format(["Black", "White"][int(self.currentSide.color)])
      text.color = colorToRgb(otherSide().color)
      textObj = GameObject(text.render())
      centerBotText(textObj)
      self.addGameObject(textObj)

      for s in self.sides:
        for p in s.capturedPieces.values():
          self.removeGameObject(p)

    if not newBool and oldBool:
      self.removeGameObject(textObj)

      for s in self.sides:
        for p in s.capturedPieces.values():
          self.addGameObject(p)

    return textObj

class Color(IntEnum):
  WHITE = 0
  BLACK = 1

class Piece(GameObject):
    def __init__(self, side, boardPosition, game, moved=False):
        self.side = side
        self.game = game
        self.color = side.color

        colorValue = {Color.WHITE: 255, Color.BLACK: 0}[self.color]
        colorName = {Color.WHITE: 'White', Color.BLACK: 'Black'}[self.color]
        try:
          surface = pygame.image.load(os.path.join('Assets/Pieces', f'{self.name()}_{colorName}.png'))
        except:
          surface = pygame.Color(colorValue, colorValue, colorValue)
        GameObject.__init__(self, surface, size=squareSize())

        self.boardPosition = boardPosition
        self.moved = moved

    def name(self):
      return "Piece"

    def canMoveTo(self, position, kingCheck=True, castling=True):
        relPos = self.relativeBoardPos(position)
        canMove = self._canMoveTo(position, relPos, castling=castling)

        if canMove:
          if isLine(relPos):
            if emptyPath(self, relPos) == False:
              canMove = False

        if canMove and kingCheck:
          oldSquares = self.game.squares.copy()
          self.game.squares.pop(self.boardPosition)
          self.game.squares[position] = self
          if inCheck(game.currentSide.kingPos, game.currentSide):
            canMove = False
          self.game.squares = oldSquares

        return canMove

    @abstractmethod
    def _canMoveTo(self, position, relativePosition, **kwargs):
        return True

    @property
    def boardPosition(self):
        return pixelToBoardPos(self.position)

    @boardPosition.setter
    def boardPosition(self, newPos):
        oldPos = self.boardPosition
        if self.game.squares.get(oldPos) == self:
          self.game.squares.pop(oldPos)
        self.game.squares[newPos] = self

        self.position = boardToPixelPos(newPos)

    def relativeBoardPos(self, boardPos):
        return (boardPos[0]-self.boardPosition[0], boardPos[1]-self.boardPosition[1])

    def onMoveTo(self, pos):
      postMove()

    def move(self, pos):
      currentPiece = self.game.squares.get(pos)
      if currentPiece:
        if currentPiece.color != self.game.currentSide.color:
          capture(currentPiece)

      self.boardPosition = pos
      changeSelection(None)

      self.moved = True

      if pos != self.game.enPassant:
        self.game.enPassant = None

      self.onMoveTo(pos)

class Rook(Piece):
    def _canMoveTo(self, pos, relPos, **kwargs):
        return (relPos[0] == 0) ^ (relPos[1] == 0)

    def name(self):
      return "Rook"

class Knight(Piece):
    def _canMoveTo(self, pos, relPos, **kwargs):
        horizontalL = ((abs(relPos[0]) == 2) and (abs(relPos[1]) == 1))
        verticalL = ((abs(relPos[0]) == 1) and (abs(relPos[1]) == 2))
        return horizontalL or verticalL

    def name(self):
      return "Knight"

class Bishop(Piece):
    def _canMoveTo(self, pos, relPos, **kwargs):
      return abs(relPos[0]) == abs(relPos[1])

    def name(self):
      return "Bishop"

class Queen(Piece):
    def _canMoveTo(self, pos, relPos, **kwargs):
      return isLine(relPos)

    def name(self):
      return "Queen"

class King(Piece):
    def _canMoveTo(self, pos, relPos, **kwargs):
      normalMovement = (abs(relPos[0]) <= 1) and (abs(relPos[1]) <= 1)

      if kwargs['castling'] and (abs(relPos[0]) == 2) and (relPos[1] == 0):

        xPos = [None, 7, 0][int(relPos[0]/abs(relPos[0]))]
        self.castleRook = self.game.squares.get((xPos, self.boardPosition[1]))

        def anySquaresInCheck():
          length = abs(relPos[0 if relPos[0] != 0 else 1])
          for i in range(1, int(length)+1):
            square = (i/length * relPos[0] + self.boardPosition[0], i/length * relPos[1] + self.boardPosition[1])
            if inCheck(square, self.side):
              return True
          return False

        if self.castleRook != None:
          castleMovement = (not self.castleRook.moved) and (not self.moved) and (not anySquaresInCheck()) and emptyPath(self, self.relativeBoardPos(self.castleRook.boardPosition)) and not inCheck(self.boardPosition, self.side)

        else:
          castleMovement = False
      else:
        castleMovement = False

      return normalMovement or castleMovement

    def move(self, pos):
      try:
        if self.castleRook != None:
          self.castleRook.boardPosition = ((self.boardPosition[0]+pos[0])/2, self.castleRook.boardPosition[1])
      except AttributeError:
        pass

      super().move(pos)

    def name(self):
      return "King"

class Pawn(Piece):
    def _canMoveTo(self, pos, relPos, **kwargs):
      dir = self.side.moveDirection
      square = self.game.squares.get(pos)
      if pos == self.game.enPassant:
        square = True

      if square == None:
        if self.boardPosition[1] == [None, 6, 1][dir]:
          return (relPos == (0, -1 * dir)) or (relPos == (0, -2 * dir))
        else:
          return relPos == (0, -1 * dir)
      else:
        return (abs(relPos[0]) == 1) and (relPos[1] == -1 * dir)

    def name(self):
      return "Pawn"

    def move(self, pos):
      self._oldPos = self.boardPosition

      super().move(pos)

    def onMoveTo(self, pos):
      if abs(pos[1]-self._oldPos[1]) == 2:
        self.game.enPassant = (pos[0], (pos[1]+self._oldPos[1])/2)

      if pos[1] == [None, 0, 7][self.side.moveDirection]:
        game.promotionPawn = self

        game.updateHistory()

      else:

        postMove()

#endregion

STARTING_POSITIONS = {
    Color.BLACK: {
        Rook: [(0, 0), (7, 0)],
        Knight: [(1, 0), (6, 0)],
        Bishop: [(2, 0), (5, 0)],
        Queen: [(3, 0)],
        King: [(4, 0)],
        Pawn: [(i, 1) for i in range(8)]
    },
    Color.WHITE: {
        Rook: [(0, 7), (7, 7)],
        Knight: [(1, 7), (6, 7)],
        Bishop: [(2, 7), (5, 7)],
        Queen: [(3, 7)],
        King: [(4, 7)],
        Pawn: [(i, 6) for i in range(8)]
    }
}

#region UI

pygame.font.init()

#spaceToFlipText = 'Press space to flip the board'
#promotionText = "Type Q, K, R, or B to promote your pawn (Queen, Knight, Rook, Bishop)"
#topTipText = Text(spaceToFlipText, 'Assets/Fonts/Montserrat/Montserrat-Regular.ttf', 16, colorToRgb(Color.BLACK), True)
#topTip = GameObject(topTipText.render())
#centerTopTip()

selectionOutline = GameObject(pygame.image.load(os.path.join('Assets', 'Selection Outline.png')), size=squareSize())

redClick = GameObject(pygame.Color(255, 0, 0), size=squareSize())
redClick.surface.set_alpha(0)

gameOverText = Text("{} Wins", 'Assets/Fonts/Montserrat/Montserrat-Bold.ttf', 40, colorToRgb(Color.BLACK), True)
gameOverTextObj = None

promotionText = Text(
  "Type Q, K, R, or B to promote your pawn (Queen, Knight, Rook, Bishop)",
  'Assets/Fonts/Montserrat/Montserrat-Medium.ttf',
  18, colorToRgb(Color.BLACK), True
)
promotionTextObj = None

#endregion

game = Chess()

#region Main Game Logic

def promoteTo(pieceType):
  if game.promotionPawn == None:
    return

  newPiece = pieceType(game.promotionPawn.side, game.promotionPawn.boardPosition, game)
  game.removeGameObject(game.promotionPawn)
  game.addGameObject(newPiece)
  game.promotionPawn = None

  postMove()

def changeSelection(piece):
  if piece == None:
    game.removeGameObject(selectionOutline)
  else:
    selectionOutline.position = piece.position
    if game.selectedPiece == None:
        game.addGameObject(selectionOutline)
  game.selectedPiece = piece

def postMove():
  game.currentSide = otherSide()

  game.backgroundColor = colorToRgb(game.currentSide.color)

  if endGameCheck():
    game.gameOver = True

  game.updateHistory()

@game.event(pygame.MOUSEBUTTONDOWN)
def onMouseDown(data):
    if (data['button'] != 1) or game.gameOver:
      return

    if game.promotionPawn == None:

      boardPos = pixelToBoardPos(data['pos'])
      if boardPos == None:
        return

      changedSelection = False
      piece = game.squares.get(boardPos)
      if piece: # and (changeSide not in game._waits):
        if piece.color == game.currentSide.color:
          changeSelection(piece)
          changedSelection = True

      if (game.selectedPiece != None) and not changedSelection:
        if game.selectedPiece.canMoveTo(boardPos):
          game.selectedPiece.move(boardPos)
        else:
          redClick.position = boardToPixelPos(boardPos)
          redClick.surface.set_alpha(200)
          redClick.fadeTo(0, 15)

@game.event(pygame.KEYDOWN)
def onKeyDown(data):
  if (data['unicode'] == ' ') and not game.flippingBoard:
    flipBoard()

  if game.gameOver:
    return

  if game.promotionPawn != None:
    if data['unicode'] == 'q':
      promoteTo(Queen)
    if data['unicode'] == 'k':
      promoteTo(Knight)
    if data['unicode'] == 'r':
      promoteTo(Rook)
    if data['unicode'] == 'b':
      promoteTo(Bishop)

def flipBoard():
  game.flippingBoard = True

  oldSquares = game.squares.copy()
  game.squares.clear()

  for piece in oldSquares.values():
    newPos = (7-piece.boardPosition[0], 7-piece.boardPosition[1])
    piece.boardPosition = newPos

  selectionBoardPos = pixelToBoardPos(selectionOutline.position)
  if selectionBoardPos != None:
    selectionOutline.position = boardToPixelPos((7-selectionBoardPos[0], 7-selectionBoardPos[1]))

  for side in game.sides:
    side.moveDirection = -side.moveDirection

  game.flippingBoard = False

def endGameCheck():
  for p in game.currentSide.pieces:
    for row in range(8):
      for column in range(8):
        sqr = game.squares.get((row, column))
        if sqr != None:
          if sqr.color == game.currentSide.color:
            continue

        if p.canMoveTo((row, column)):
          return False
  return True
  
def capture(piece):
  side = game.sides[abs(int(piece.color)-1)]

  game.removeGameObject(piece)

  size = capturedPieceSquareSize()
  capPieceGameObject = GameObject(piece.surface, size=(size, size), position=(len(side.capturedPieces)*size + CAPTURED_PIECE_PADDING, capturedPieceRows()[int(piece.color)]))
  game.addGameObject(capPieceGameObject)

  side.capturedPieces[type(piece)] = capPieceGameObject # might not type()
  side._capturedPiecesPositions[capPieceGameObject.position] = capPieceGameObject

def restartGame():
  if undoButton.inGame:
    undoButton.remove(game)
  if redoButton.inGame:
    redoButton.remove(game)
  game.init()

def undo():
  game.historyIndex += 1

def redo():
  game.historyIndex -= 1

#endregion

#region Buttons

restartButton = Button((80, 40), (WIN_SIZE[0]-80, 0), Text("Restart", 'Assets/Fonts/Montserrat/Montserrat-Regular.ttf', 14, (0, 0, 0), True).render(), (255, 255, 255), (255, 0, 0), (175, 0, 0), restartGame)
undoButton = Button((40, 40), (0, 0), pygame.transform.scale(pygame.image.load('Assets/Undo Arrow.png'), (25, 25)), (255, 255, 255), (210, 210, 210), (150, 150, 150), undo)
redoButton = Button((40, 40), (40, 0), pygame.transform.flip(pygame.transform.scale(pygame.image.load('Assets/Undo Arrow.png'), (25, 25)), True, False), (255, 255, 255), (210, 210, 210), (150, 150, 150), redo)
game.addButtons([restartButton])

#endregion

game.start()