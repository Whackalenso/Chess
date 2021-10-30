from pygame_tool import *
import math

class Clock:
    def __init__(self, game, win_size, historyButtons):
        self._lastTicks = pygame.time.get_ticks()

        self.time = [1800 for _ in range(2)]
        self.boxes = [None, None]
        self.text = [GameObject(pygame.Surface(size=(0, 0))) for _ in range(2)]

        BOX_WIDTH, BOX_HEIGHT = 80, 30
        self.boxes[0] = GameObject(pygame.Color(255, 255, 255), position=(win_size[0]/2 - BOX_WIDTH, 0), size=(BOX_WIDTH, BOX_HEIGHT))
        self.boxes[1] = GameObject(pygame.Color(0, 0, 0), position=(win_size[0]/2, 0), size=(BOX_WIDTH, BOX_HEIGHT))

        self.game = game
        self.timeOut = False
        self.enabled = True

        self._timeText = Text('', "Assets\\Fonts\\Montserrat\\Montserrat-Regular.ttf", 16, (0, 0, 0), True)
        self._update()

        game.addGameObject(self.text[0])
        game.addGameObject(self.text[1])

        game.event(pygame.MOUSEBUTTONDOWN)(self._onMouseDown)
        game.event(pygame.MOUSEMOTION)(self._onMouseMotion)
        game.update(self._update)

        self.historyButtons = historyButtons
        self._gameOverTextObj = None
        self._subtitleTextObj = None

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, newBool):
        self._enabled = newBool
        
        if newBool:
            for b in self.boxes:
                if b not in self.game._gameObjects:
                    self.game.addGameObject(b)
        else:
            for b in self.boxes:
                if b in self.game._gameObjects:
                    self.game.removeGameObject(b)

        for t in self.text:
            if t in self.game._gameObjects:
                self.game.removeGameObject(t)
                self.game.addGameObject(t)

        if self.timeOut:
            self._gameOverTextObj = self.game._botText(None, self._gameOverTextObj, True, False)
            self._subtitleTextObj = self.game._botText(None, self._subtitleTextObj, True, False, ignoreCapPieces=True)

            self.timeOut = False
            self.game._gameOver = False

            self.game.onHistoryChange() # So the history buttons come back
    
    def _onMouseDown(self, data):
        if data['button'] != 1:
            return

        if any([b.rect.collidepoint(data['pos']) for b in self.boxes]):
            self.enabled = not self.enabled

    def _onMouseMotion(self, data):
        if not self.enabled:
            if any([b.rect.collidepoint(data['pos']) for b in self.boxes]):
                for t in self.text:
                    if t not in self.game._gameObjects:
                        self.game.addGameObject(t)
            else:
                for t in self.text:
                    if t in self.game._gameObjects:
                        self.game.removeGameObject(t)

    def _update(self):
        if self.timeOut or self.game.gameOver:
            return

        currentSide = int(self.game.currentSide.color)
        
        if pygame.time.get_ticks() - self._lastTicks >= 1000:
            self._updateTime(currentSide)

        for side in range(2):
            self._timeText.text = self._formatTime(self.time[side])
            colors = [(0, 0, 0), (255, 255, 255)] if self.enabled else [(0, 0, 0), (0, 0, 0)]
            self._timeText.color = colors[side]
            self.text[side]._surface = self._timeText.render()

            self._positionText(self.text[side], self.boxes[side])

    def _updateTime(self, side):
        self.time[side] -= 1
        self._lastTicks = pygame.time.get_ticks()

        if (self.time[side] <= 0) and not self.timeOut:
            self.timeOut = True
            if self.enabled:
                
                enemyPieces = []
                for p in self.game.squares.values():
                    if int(p.color) != side:
                        enemyPieces.append(type(p).__name__)

                # insufficient mating material
                immList = [['King'], ['King', 'Knight'], ['King', 'Bishop']]
                imm = False
                for i in immList:
                    if all([p in i for p in enemyPieces]):
                        imm = True
                        break

                title = Text("", "Assets/Fonts/Montserrat/Montserrat-Bold.ttf", 40, (0, 0, 0), True)
                subtitle = Text(
                    "Disable the clock if you wish to continue",
                    "Assets/Fonts/Montserrat/Montserrat-Medium.ttf", 16, (0, 0, 0), True
                )
                if imm:
                    title.text = 'Draw'
                else:
                    title.text = ['Black', 'White'][side] + ' wins'
                self._gameOverTextObj = self.game._botText(title, self._gameOverTextObj, False, True, offset=(0, -10))
                self._subtitleTextObj = self.game._botText(subtitle, self._subtitleTextObj, False, True, offset=(0, 20), ignoreCapPieces=True)
                self.game._gameOver = True
                
                for b in self.historyButtons:
                    if b.inGame:
                        b.remove(self.game)

            else:

                self.remove()

    def remove(self):
        for t in self.text: 
            if t in self.game._gameObjects:
                self.game.removeGameObject(t)

        self.game.removeEvent(pygame.MOUSEBUTTONDOWN, self._onMouseDown)
        self.game.removeEvent(pygame.MOUSEMOTION, self._onMouseMotion)
        self.game._updateCallbacks.remove(self._update)

    def _formatTime(self, seconds):
        return f"{math.floor(seconds/60)}:{seconds%60}"

    def _positionText(self, text, box):
        text.position = (box.size[0]/2 - text.size[0]/2 + box.position[0], box.size[1]/2 - text.surface.get_height()/2 + box.position[1])