import sys
import procgame
import pinproc
from threading import Thread
import random
import string
import time
import locale
import math
import copy
import ctypes
import itertools
from procgame.events import EventManager
import os
import logging

try:
    import pygame
    import pygame.locals
except ImportError:
    print "Error importing pygame; ignoring."
    pygame = None

if hasattr(ctypes.pythonapi, 'Py_InitModule4'):
   Py_ssize_t = ctypes.c_int
elif hasattr(ctypes.pythonapi, 'Py_InitModule4_64'):
   Py_ssize_t = ctypes.c_int64
else:
   raise TypeError("Cannot determine type of Py_ssize_t")

PyObject_AsWriteBuffer = ctypes.pythonapi.PyObject_AsWriteBuffer
PyObject_AsWriteBuffer.restype = ctypes.c_int
PyObject_AsWriteBuffer.argtypes = [ctypes.py_object,
                                  ctypes.POINTER(ctypes.c_void_p),
                                  ctypes.POINTER(Py_ssize_t)]

def array(surface):
   buffer_interface = surface.get_buffer()
   address = ctypes.c_void_p()
   size = Py_ssize_t()
   PyObject_AsWriteBuffer(buffer_interface,
                          ctypes.byref(address), ctypes.byref(size))
   bytes = (ctypes.c_byte * size.value).from_address(address.value)
   bytes.object = buffer_interface
   return bytes


class Desktop():
    """The :class:`Desktop` class helps manage interaction with the desktop, providing both a windowed
    representation of the DMD, as well as translating keyboard input into pyprocgame events."""

    exit_event_type = 99
    """Event type sent when Ctrl-C is received."""

    key_map = {}

    def __init__(self):
        self.log = logging.getLogger('scoredisplay.virtual_display')
        self.log.debug("Init Color Desktop")
        self.ctrl = 0
        self.i = 0

        self.add_key_map(pygame.locals.K_LSHIFT, 3)
        self.add_key_map(pygame.locals.K_RSHIFT, 1)


    def draw_window(self):
        if 'pygame' in globals():
            self.log.debug("Drawing Window")
            self.setup_window()
        else:
            self.log.debug('Desktop init skipping setup_window(); pygame does not appear to be loaded.')

    def load_images(self,dots_path):
        ## dot images
        self.top_bar = pygame.image.load(dots_path+ 'top-bar.png')
        self.top_bar_on = pygame.image.load(dots_path+ 'top-bar-on.png')
        self.vert_bar = pygame.image.load(dots_path+ 'vert-bar.png')
        self.vert_bar_on = pygame.image.load(dots_path+ 'vert-bar-on.png')
        self.backslash = pygame.image.load(dots_path+ 'backslash.png')
        self.backslash_on = pygame.image.load(dots_path+ 'backslash-on.png')
        self.slash = pygame.image.load(dots_path+ 'slash.png')
        self.slash_on = pygame.image.load(dots_path+ 'slash-on.png')
        self.horiz_bar = pygame.image.load(dots_path+ 'horiz-bar.png')
        self.horiz_bar_on = pygame.image.load(dots_path+ 'horiz-bar-on.png')
        self.bottom_bar = pygame.image.load(dots_path+ 'bottom-bar.png')
        self.bottom_bar_on = pygame.image.load(dots_path+ 'bottom-bar-on.png')
        self.period = pygame.image.load(dots_path+ 'period.png')
        self.period_on = pygame.image.load(dots_path+ 'period-on.png')
        self.comma_on = pygame.image.load(dots_path+'comma-on.png')
        self.blank = pygame.image.load(dots_path+'off-digit.png')
        ##
        ## This is the map of character to bits to turn on so
        ## you can customize how each character looks
        ##
                          # ~ | \ | / | - - | / | \ | _
        self.chars = { '0':[1,1,0,0,0,1,0,0,1,0,0,0,1,1,],
                       '1':[0,0,0,1,0,0,0,0,0,0,1,0,0,0,],
                       '2':[1,0,0,0,0,1,1,1,1,0,0,0,0,1,],
                       '3':[1,0,0,0,0,1,0,1,0,0,0,0,1,1,],
                       '4':[0,1,0,0,0,1,1,1,0,0,0,0,1,0,],
                       '5':[1,1,0,0,0,0,1,1,0,0,0,0,1,1,],
                       '6':[1,1,0,0,0,0,1,1,1,0,0,0,1,1,],
                       '7':[1,0,0,0,1,0,0,0,0,0,1,0,0,0,],
                       '8':[1,1,0,0,0,1,1,1,1,0,0,0,1,1,],
                       '9':[1,1,0,0,0,1,1,1,0,0,0,0,1,1,],
                       'A':[1,1,0,0,0,1,1,1,1,0,0,0,1,0,],
                       'B':[1,0,0,1,0,1,1,1,0,0,1,0,1,1,],
                       'C':[1,1,0,0,0,0,0,0,1,0,0,0,0,1,],
                       'D':[1,0,0,1,0,1,0,0,0,0,1,0,1,1,],
                       'E':[1,1,0,0,0,0,1,0,1,0,0,0,0,1,],
                       'F':[1,1,0,0,0,0,1,0,1,0,0,0,0,0,],
                       'G':[1,1,0,0,0,0,0,1,1,0,0,0,1,1,],
                       'H':[0,1,0,0,0,1,1,1,1,0,0,0,1,0,],
                       'I':[1,0,0,1,0,0,0,0,0,0,1,0,0,1,],
                       'J':[0,0,0,0,0,1,0,0,1,0,0,0,1,1,],
                       'K':[0,1,0,0,1,0,1,0,1,0,0,1,0,0,],
                       'L':[0,1,0,0,0,0,0,0,1,0,0,0,0,1,],
                       'M':[0,1,1,0,1,1,0,0,1,0,0,0,1,0,],
                       'N':[0,1,1,0,0,1,0,0,1,0,0,1,1,0,],
                       'O':[1,1,0,0,0,1,0,0,1,0,0,0,1,1,],
                       'P':[1,1,0,0,0,1,1,1,1,0,0,0,0,0,],
                       'Q':[1,1,0,0,0,1,0,0,1,0,0,1,1,1,],
                       'R':[1,1,0,0,0,1,1,1,1,0,0,1,0,0,],
                       'S':[1,1,0,0,0,0,1,1,0,0,0,0,1,1,],
                       'T':[1,0,0,1,0,0,0,0,0,0,1,0,0,0,],
                       'U':[0,1,0,0,0,1,0,0,1,0,0,0,1,1,],
                       'V':[0,0,1,0,0,1,0,0,0,0,0,1,1,0,],
                       'W':[0,1,0,0,0,1,0,0,1,1,0,1,1,0,],
                       'X':[0,0,1,0,1,0,0,0,0,1,0,1,0,0,],
                       'Y':[0,0,1,0,1,0,0,0,0,0,1,0,0,0,],
                       'Z':[1,0,0,1,0,0,0,0,0,1,0,0,0,1,],
                       'a':[1,1,0,0,0,1,1,1,1,0,0,0,1,0,],
                       'b':[1,0,0,1,0,1,1,1,0,0,1,0,1,1,],
                       'c':[1,1,0,0,0,0,0,0,1,0,0,0,0,1,],
                       'd':[1,0,0,1,0,1,0,0,0,0,1,0,1,1,],
                       'e':[1,1,0,0,0,0,1,0,1,0,0,0,0,1,],
                       'f':[1,1,0,0,0,0,1,0,1,0,0,0,0,0,],
                       'g':[1,1,0,0,0,0,0,1,1,0,0,0,1,1,],
                       'h':[0,1,0,0,0,1,1,1,1,0,0,0,1,0,],
                       'i':[1,0,0,1,0,0,0,0,0,0,1,0,0,1,],
                       'j':[0,0,0,0,0,1,0,0,1,0,0,0,1,1,],
                       'k':[0,1,0,0,1,0,1,0,1,0,0,1,0,0,],
                       'l':[0,1,0,0,0,0,0,0,1,0,0,0,0,1,],
                       'm':[0,1,1,0,1,1,0,0,1,0,0,0,1,0,],
                       'n':[0,1,1,0,0,1,0,0,1,0,0,1,1,0,],
                       'o':[1,1,0,0,0,1,0,0,1,0,0,0,1,1,],
                       'p':[1,1,0,0,0,1,1,1,1,0,0,0,0,0,],
                       'q':[1,1,0,0,0,1,0,0,1,0,0,1,1,1,],
                       'r':[1,1,0,0,0,1,1,1,1,0,0,1,0,0,],
                       's':[1,1,0,0,0,0,1,1,0,0,0,0,1,1,],
                       't':[1,0,0,1,0,0,0,0,0,0,1,0,0,0,],
                       'u':[0,1,0,0,0,1,0,0,1,0,0,0,1,1,],
                       'v':[0,0,1,0,0,1,0,0,0,0,0,1,1,0,],
                       'w':[0,1,0,0,0,1,0,0,1,1,0,1,1,0,],
                       'x':[0,0,1,0,1,0,0,0,0,1,0,1,0,0,],
                       'y':[0,0,1,0,1,0,0,0,0,0,1,0,0,0,],
                       'z':[1,0,0,1,0,0,0,0,0,1,0,0,0,1,],
                       '.':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,],
                       '-':[0,0,0,0,0,0,1,1,0,0,0,0,0,0,],
                       ';':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,],
                       ':':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,],
                       ')':[0,0,1,0,0,0,0,0,0,1,0,0,0,0,],
                       '(':[0,0,0,0,1,0,0,0,0,0,0,1,0,0,],
                       '!':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,],
                       '?':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,],
                       '#':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,],
                       '*':[0,0,1,1,1,0,1,1,0,1,1,1,0,0,],
                       '@':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,],
                       '$':[1,1,0,1,0,1,1,1,0,0,1,0,1,1,],
                       '%':[0,1,0,0,1,0,0,0,0,1,0,0,1,0,],
                       '<':[0,0,0,0,1,0,0,0,0,0,0,1,0,0,],
                       '=':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,],
                       '>':[0,1,0,0,0,0,0,0,0,1,0,0,0,0,],
                       '"':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,],
                       '&':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,],
                       '+':[0,0,0,1,0,0,1,1,0,0,1,0,0,0,],
                       ',':[0,0,0,0,0,0,0,0,0,0,0,0,0,0,],
                       '/':[0,0,0,0,1,0,0,0,0,1,0,0,0,0,],
                       '^':[0,0,0,0,1,1,0,0,0,0,0,0,0,0,]}
                          # ~ | \ | / | - - | / | \ | _


    def add_key_map(self, key, switch_number):
        """Maps the given *key* to *switch_number*, where *key* is one of the key constants in :mod:`pygame.locals`."""
        self.key_map[key] = switch_number

    def clear_key_map(self):
        """Empties the key map."""
        self.key_map = {}

    def get_keyboard_events(self):
        """Asks :mod:`pygame` for recent keyboard events and translates them into an array
        of events similar to what would be returned by :meth:`pinproc.PinPROC.get_events`."""
        key_events = []
        for event in pygame.event.get():
            EventManager.default().post(name=self.event_name_for_pygame_event_type(event.type), object=self, info=event)
            key_event = {}
            if event.type == pygame.locals.KEYDOWN:
                if event.key == pygame.locals.K_RCTRL or event.key == pygame.locals.K_LCTRL:
                    self.ctrl = 1
                if event.key == pygame.locals.K_c:
                    if self.ctrl == 1:
                        key_event['type'] = self.exit_event_type
                        key_event['value'] = 'quit'
                elif (event.key == pygame.locals.K_ESCAPE):
                    key_event['type'] = self.exit_event_type
                    key_event['value'] = 'quit'
                elif event.key in self.key_map:
                    key_event['type'] = pinproc.EventTypeSwitchClosedDebounced
                    key_event['value'] = self.key_map[event.key]
            elif event.type == pygame.locals.KEYUP:
                if event.key == pygame.locals.K_RCTRL or event.key == pygame.locals.K_LCTRL:
                    self.ctrl = 0
                elif event.key in self.key_map:
                    key_event['type'] = pinproc.EventTypeSwitchOpenDebounced
                    key_event['value'] = self.key_map[event.key]
            if len(key_event):
                key_events.append(key_event)
        return key_events


    event_listeners = {}

    def event_name_for_pygame_event_type(self, event_type):
        return 'pygame(%s)' % (event_type)

    screen = None
    """:class:`pygame.Surface` object representing the screen's surface."""
    screen_multiplier = 4

    def setup_window(self):
        #os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (100,100)
        #pygame.init()
        # This draws the window size -- if you want to change the arrangement of digits,
        # You would want to change this
        self.screen = pygame.display.set_mode(((660),(136)))
        self.log.debug("Setting Caption")
        pygame.display.set_caption('Alpha Display')

    def draw(self, strings):
        """Draw the given :class:`~procgame.dmd.Frame` in the window."""
        # Use adjustment to add a one pixel border around each dot, if
        # the screen size is large enough to accomodate it.

        x = 10
        y = 10
        # fill the screen grey
        self.screen.fill((60,60,60))

        # step through the strings
        for n in (0,1):
            if len(strings[n]) <16:
                count = len(strings[n])
                while count < 16:
                    string = " " + strings[n]
                    strings[n] = string
                    count += 1

            self.log.debug("Rendering |" + str(strings[n]) + "|")
            # step through the chars
            for num in range(0,len(strings[n]),1):
                char = strings[n][num]
                if char == ' ':
                    self.screen.blit(self.blank,(x,y))
                else:
                    # Top bar
                    image = self.set_top_bar(self.chars[char][0])
                    self.screen.blit(image,(x,y))
                    # left top vert
                    image=self.set_vert_bar(self.chars[char][1])
                    self.screen.blit(image,(x,y+7))
                    # top left backslash
                    image=self.set_backslash(self.chars[char][2])
                    self.screen.blit(image,(x+5,y+7))
                    # top middle vertical bar
                    image = self.set_vert_bar(self.chars[char][3])
                    self.screen.blit(image,(x+15,y+7))
                    # top right slash
                    image = self.set_slash(self.chars[char][4])
                    self.screen.blit(image,(x+20,y+7))
                    # top right vert bar
                    image = self.set_vert_bar(self.chars[char][5])
                    self.screen.blit(image,(x+30,y+7))
                    # left horizontal
                    image = self.set_horiz(self.chars[char][6])
                    self.screen.blit(image,(x,y+24))
                    # right horizontal
                    image = self.set_horiz(self.chars[char][7])
                    self.screen.blit(image,(x+17,y+24))
                    # lower left vert
                    image = self.set_vert_bar(self.chars[char][8])
                    self.screen.blit(image,(x,y+29))
                    # lower left slash
                    image = self.set_slash(self.chars[char][9])
                    self.screen.blit(image,(x+5,y+29))
                    # lower center vert bar
                    image = self.set_vert_bar(self.chars[char][10])
                    self.screen.blit(image,(x+15,y+29))
                    # lower right backslash
                    image = self.set_backslash(self.chars[char][11])
                    self.screen.blit(image,(x+20,y+29))
                    # lower right vert bar
                    image = self.set_vert_bar(self.chars[char][12])
                    self.screen.blit(image,(x+30,y+29))
                    # bottom bar
                    image = self.set_bottom_bar(self.chars[char][13])
                    self.screen.blit(image,(x,y+46))
                    # Look ahead to handle the period and comma if possible
                    if num < 15:
                        comma_dot = strings[n][num+1]
                    else:
                        comma_dot = " "
                    if comma_dot != "." and comma_dot != ",":
                        self.screen.blit(self.period,(x+35,y))
                    elif comma_dot == ".":
                        self.screen.blit(self.period_on,(x+35,y))
                        strings[n] = strings[n].replace(".","",1)
                        strings[n] = strings[n] + " "
                    else:
                        self.screen.blit(self.period_on,(x+35,y))
                        self.screen.blit(self.comma_on,(x+35,y+50))
                        strings[n] = strings[n].replace(",","",1)
                        strings[n] = strings[n] + " "

                x += 40
            # after each string, adjustments to position
            if n == 0:
                x = 10
                y = 73

        pygame.display.update()

    def set_top_bar(self,input):
        if input == 1:
            return self.top_bar_on
        else:
            return self.top_bar

    def set_vert_bar(self,input):
        if input == 1:
            return self.vert_bar_on
        else:
            return self.vert_bar

    def set_backslash(self,input):
        if input == 1:
            return self.backslash_on
        else:
            return self.backslash

    def set_slash(self,input):
        if input == 1:
            return self.slash_on
        else:
            return self.slash

    def set_horiz(self,input):
        if input == 1:
            return self.horiz_bar_on
        else:
            return self.horiz_bar

    def set_bottom_bar(self,input):
        if input == 1:
            return self.bottom_bar_on
        else:
            return self.bottom_bar

    def set_period(self,input):
        if input == 1:
            return self.period_on
        else:
            return self.period



    def __str__(self):
        return '<Desktop pygame>'

