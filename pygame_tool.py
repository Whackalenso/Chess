import pygame
from typing import Union
from enum import Enum
import time

def transform(surface, **kwargs):
    rotation = kwargs.get('rotation')
    scale = kwargs.get('scale')
    flip = kwargs.get('flip')

    if rotation != None:
        surface = pygame.transform.rotate(surface, rotation)
    if scale != None:
        surface = pygame.transform.scale(surface, scale)
    if flip != None:
        surface = pygame.transform.flip(surface, flip[0], flip[1])

    return surface

class SizeNotGivenError(Exception):
    pass

class GameObject:
    def __init__(self, surface:Union[pygame.Surface, pygame.Color], size=None, position=(0, 0), gravity=False, mass=1, collidable=False, pushable=False): # Surface can be an image path, pygame.Surface
        if isinstance(surface, pygame.Color):
            if size == None:
                raise SizeNotGivenError("The size parameter needs to be provided if surface is pygame.Color")

            color = surface
            surface = pygame.Surface(size)
            pygame.draw.rect(surface, color, pygame.Rect((0, 0), size))
        
        self.position = position
        self.gravity = gravity
        self.mass = mass
        self.collidable = collidable
        self.pushable = pushable

        self.velocity = (0, 0)

        self._originalSurface = surface
        self._surface = surface
        #self._size = surface.get_size()
        if size != None:
            self.size = size
        self._rotation = 0

        self._touchCallbacks = {}
        self._collideCallbacks = {}
        self._touching = []
        self.lastPos = position

        self._fade = None

    #region transform()

    # def transform(self, **kwargs):
    #     rotation = kwargs.get('rotation')
    #     scale = kwargs.get('scale')
    #     flip = kwargs.get('flip')

    #     if rotation != None:
    #         self.surface = pygame.transform.rotate(self.surface, rotation)
    #     if scale != None:
    #         self.surface = pygame.transform.scale(self.surface, scale)
    #     if flip != None:
    #         self.surface = pygame.transform.flip(self.surface, flip[0], flip[1])

    #endregion

    def fadeTo(self, target, duration):
      if target == self.surface.get_alpha():
        return
      self._fade = {'target':target, 'duration':duration, 'start':self.surface.get_alpha()}

    def update(self, game):
      if self._fade:
        self.surface.set_alpha(self.surface.get_alpha() + (self._fade['target']-self.surface.get_alpha()) * game.deltaTime * 1/self._fade['duration'])
        if self._fade['target'] > self._fade['start']:
          if self.surface.get_alpha() >= self._fade['target']:
            self.surface.set_alpha(self._fade['target'])
            self._fade = None
        elif self._fade['target'] < self._fade['start']:
          if self.surface.get_alpha() <= self._fade['target']:
            self.surface.set_alpha(self._fade['target'])
            self._fade = None

    #region Properties

    @property
    def rect(self):
        return pygame.Rect(self.xPos, self.yPos, self.size[0], self.size[1])

    @property
    def surface(self):
        return self._surface
    
    @surface.setter
    def surface(self, new_surface):
        self._originalSurface = new_surface

    @property
    def size(self):
        return self.surface.get_size() #self._size

    @property
    def rotation(self):
        return self._rotation

    @size.setter
    def size(self, new_size):
        #self._size = new_size
        self._surface = pygame.transform.scale(self._originalSurface, new_size)

    @rotation.setter
    def rotation(self, new_rotation):
        self._rotation = new_rotation
        self._surface = pygame.transform.rotate(self._originalSurface, new_rotation)

    @property
    def xPos(self):
        return self.position[0]

    @property
    def yPos(self):
        return self.position[1]

    @xPos.setter
    def xPos(self, value):
        self.position = (value, self.yPos)

    @yPos.setter
    def yPos(self, value):
        self.position = (self.xPos, value)

    @property
    def xVelocity(self):
        return self.velocity[0]

    @property
    def yVelocity(self):
        return self.velocity[1]

    @xVelocity.setter
    def xVelocity(self, value):
        self.velocity = (value, self.yVelocity)

    @yVelocity.setter
    def yVelocity(self, value):
        self.velocity = (self.xVelocity, value)

    @property
    def touching(self):
        return self._touching

    #endregion

    #region Events

    def touch(self, gameObject=None):
        def _touch(callback):
            self._touchCallbacks.update({gameObject: callback})
        return _touch

    def collide(self, gameObject=None):
        def _collide(callback):
            self._collideCallbacks.update({gameObject: callback})
        return _collide

    #endregion

class Text:
    def __init__(self, text, fontPath, size, color, antialias):
        self.text = text
        self.size = size
        self.font = fontPath
        self.color = color
        self.antialias = antialias

        self._fontPath = fontPath

    @property
    def font(self):
        return self._font
    
    @font.setter
    def font(self, path):
        self._font = pygame.font.Font(path, self.size)

    def render(self):
        self.font = self._fontPath
        return self.font.render(self.text, self.antialias, self.color)

class ButtonMode(Enum):
    PRESS = 0
    RELEASE = 1

class Button:
    def __init__(self, size, position, content, idleColor, hoverColor, clickColor, callback, buttonMode=ButtonMode.RELEASE, enabled=True):
        self._background = GameObject(pygame.Color(idleColor), size, position)
        self.idleColor = idleColor
        self.hoverColor = hoverColor
        self.clickColor = clickColor
        self.enabled = enabled
        
        self._content = GameObject(content)
        self._positionContent()

        self.callback = callback
        self.buttonMode = buttonMode
        
        self._pressed = False

        self.inGame = False

    def add(self, game):
        game.addGameObject(self._background)
        game.addGameObject(self._content)

        game.event(pygame.MOUSEBUTTONDOWN)(self.onMouseDown)
        game.event(pygame.MOUSEBUTTONUP)(self.onMouseUp)
        game.event(pygame.MOUSEMOTION)(self.onMouseMotion)

        self.inGame = True

    def remove(self, game):
        game.removeGameObject(self._background)
        game.removeGameObject(self._content)

        game.removeEvent(pygame.MOUSEBUTTONDOWN, self.onMouseDown)
        game.removeEvent(pygame.MOUSEBUTTONUP, self.onMouseUp)
        game.removeEvent(pygame.MOUSEMOTION, self.onMouseMotion)

        self._updateBackground(self.idleColor)

        self.inGame = False

    @property
    def pressed(self):
        return self._pressed

    @property
    def size(self):
        return self._background.size

    @size.setter
    def size(self, newSize):
        self._background.size = newSize
        self._positionContent()

    @property
    def position(self):
        return self._background.position

    @position.setter
    def position(self, newPosition):
        self._background.position = newPosition
        self._positionContent()

    def _updateBackground(self, color):
        surface = pygame.Surface(self.size)
        pygame.draw.rect(surface, color, pygame.Rect((0, 0), self.size))
        self._background._surface = surface

    @property
    def content(self):
        return self._content.surface

    @content.setter
    def content(self, newContent):
        self._content._surface = newContent

    def _positionContent(self):
        self._content.position = (self.size[0]/2 - self._content.size[0]/2 + self.position[0], self.size[1]/2 - self._content.surface.get_height()/2 + self.position[1])

    def onMouseDown(self, data):
        if (data['button'] != 1) or (not self._background.rect.collidepoint(data['pos'])) or (not self.enabled):
            return

        self._updateBackground(self.clickColor)
        self._pressed = True

        if self.buttonMode == ButtonMode.PRESS:
            self.callback()

    def onMouseUp(self, data):
        if (data['button'] != 1) or (not self.pressed) or (not self.enabled):
            return

        self._notPressed(data)
        self._pressed = False

        if self.buttonMode == ButtonMode.RELEASE:
            self.callback()

    def onMouseMotion(self, data):
        if (self.pressed) or (not self.enabled):
            return

        self._notPressed(data)

    def _notPressed(self, data):
        if self._background.rect.collidepoint(data['pos']):
            self._updateBackground(self.hoverColor)
        else:
            self._updateBackground(self.idleColor)

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        # if value:
        #     #self._notPressed({'pos':pygame.mouse.get_pos()})
        #     self._updateBackground(self.idleColor)
        # else:
        #     self._updateBackground((100, 100, 100))

class Game:
    def __init__(self, size, **options): # fps=60, backgroundColor=(0, 0, 0), windowTitle=None, gravityScale=.3
        self.size = size
        self.fps = options.get('fps', 60)
        self.backgroundColor = options.get('backgroundColor', (0, 0, 0))
        self.windowTitle = options.get('windowTitle')
        self.gravityScale = options.get('gravityScale', .3)

        self._updateCallbacks = []
        # I should do lists for other callbacks too
        self._touchCallback = None
        self._collideCallback = None
        self._keyEventCallback = None
        self._events = {}
        self._gameObjects = []
        self._deltaTime = 0
        self._waits = {}

        self._BASE_FRAMERATE = 60

    @property
    def deltaTime(self):
        return float(self._deltaTime)

    def runAfterWait(self, callback, duration):
        self._waits[callback] = [time.time(), duration]
    
    def start(self):
        if self.windowTitle:
            pygame.display.set_caption(self.windowTitle)
        self.win = pygame.display.set_mode(self.size)

        clock = pygame.time.Clock()
        lastFrameTicks = 0

        running = True
        while running:
            self._deltaTime = clock.tick(self.fps)
            t = pygame.time.get_ticks()
            self._deltaTime = ((t - lastFrameTicks) / 1000) * self._BASE_FRAMERATE
            lastFrameTicks = t

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if (event.type == pygame.KEYDOWN) or (event.type == pygame.KEYUP):
                    if self._keyEventCallback != None:
                        self._keyEventCallback(event)

                eventCallbacks = self._events.get(event.type)
                if eventCallbacks != None:
                    for c in eventCallbacks:
                        c(event.__dict__)

            if running:
                self._update()
            
        pygame.quit()

    def update(self, callback):
        self._updateCallbacks.append(callback)

    def event(self, eventType):
        def _event(callback):
            if self._events.get(eventType) != None:
                self._events[eventType].append(callback)
            else:
                self._events[eventType] = [callback]
        return _event

    def removeEvent(self, eventType, callback):
        self._events[eventType].remove(callback)

    def keyEvent(self, callback):
        self._keyEventCallback = callback

    def gObjTouch(self, callback):
        self._touchCallback = callback

    def gObjCollide(self, callback):
        self._collideCallback = callback

    def addGameObject(self, gameObject):
        self._gameObjects.append(gameObject)
        return gameObject

    def removeGameObject(self, gameObject):
        self._gameObjects.remove(gameObject)
        return gameObject

    def addButtons(self, buttons):
        for b in buttons:
            b.add(self)

    def removeButtons(self, buttons):
        for b in buttons:
            b.remove(self)

    def _update(self):
        for c in self._updateCallbacks:
            c()

        self.win.fill(self.backgroundColor)

        #region GameObjects

        for gObj1 in self._gameObjects:

            if gObj1.gravity:
                gObj1.yVelocity += self.gravityScale * gObj1.mass

            gObj1.position = (
                gObj1.xPos + gObj1.xVelocity * self.deltaTime, 
                gObj1.yPos + gObj1.yVelocity * self.deltaTime
            )

            for gObj2 in self._gameObjects:
                if self._gameObjects.index(gObj2) <= self._gameObjects.index(gObj1):
                    continue

                if gObj1.rect.colliderect(gObj2.rect):
                    
                    if (gObj2 not in gObj1._touching) and (gObj1 not in gObj2._touching):

                        gObj1._touching.append(gObj2)
                        gObj2._touching.append(gObj1)

                        if gObj1._touchCallbacks.get(None): gObj1._touchCallbacks[None](gObj2)
                        if gObj1._touchCallbacks.get(gObj2): gObj1._touchCallbacks[gObj2]()
                        
                        if gObj2._touchCallbacks.get(None): gObj2._touchCallbacks[None](gObj1)
                        if gObj2._touchCallbacks.get(gObj1): gObj2._touchCallbacks[gObj1]()

                        if self._touchCallback != None:
                            self._touchCallback(gObj1, gObj2)

                        if gObj1.collidable and gObj2.collidable:

                            

                            if gObj1._collideCallbacks.get(None): gObj1._collideCallbacks[None](gObj2)
                            if gObj1._collideCallbacks.get(gObj2): gObj1._collideCallbacks[gObj2]()
                            
                            if gObj2._collideCallbacks.get(None): gObj2._collideCallbacks[None](gObj1)
                            if gObj2._collideCallbacks.get(gObj1): gObj2._collideCallbacks[gObj1]()

                            if self._collideCallback != None:
                                self._collideCallback(gObj1, gObj2)

                else:

                    if (gObj2 in gObj1._touching) and (gObj1 in gObj2._touching):
                        gObj1._touching.remove(gObj2)
                        gObj2._touching.remove(gObj1)

                        
            self.win.blit(gObj1.surface, gObj1.position)

            gObj1.update(self)

        #endregion
        
        #region Waits
    
        waitsCompleted = []
        for k, v in self._waits.items():
            if time.time()-v[0] >= v[1]:
                waitsCompleted.append(k)
                k()
        for k in waitsCompleted:
            self._waits.pop(k)

        #endregion

        pygame.display.update()