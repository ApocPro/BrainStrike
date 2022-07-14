import pygame, sys, random
import pygame.event as GAME_EVENTS
import pygame.locals as GAME_GLOBALS
import pygame.time
import time

import argparse
import math

from threading import Thread
from queue import LifoQueue

from pythonosc import dispatcher
from pythonosc import osc_server

def soundServer(queue, ip_addr, port, AttentionAvg, MeditationAvg):

  # better handler function for the loading of values into the queue
  # if the OSC sends the same value about 30 times a second this puts into
  # the queue only unique values about once a second.
  
  def attention_handler(action, value):
    global AttentionAvg
    AttentionAvg.append(value)
    if len(AttentionAvg) == 30:
      y = 0
      for x in AttentionAvg:
        y += x
      y = y // 30
      #print(AttentionAvg)
      #print ('attention:', y)
      atnAvg = ('/attention', y)
      queue.put(atnAvg)
      AttentionAvg = []
      time.sleep(.01)

  def meditation_handler(action, value):
    
    global MeditationAvg
    
    MeditationAvg.append(value)
    if len(MeditationAvg) == 30:
      y=0
      for x in MeditationAvg:
        y += x
      y = y // 30
      #print ('meditation:',y)
      MeditationAvg = []
      medAvg = ('/meditation', y)
      queue.put(medAvg)
      time.sleep(.01)
  
  parser = argparse.ArgumentParser()
  parser.add_argument("--ip",
                      default=ip_addr, help="The ip to listen on")
  parser.add_argument("--port",
                      type=int, default=port, help="The port to listen on")
  args = parser.parse_args()
  dispatcher1 = dispatcher.Dispatcher()
  dispatcher1.map("/attention", attention_handler) 
  dispatcher1.map("/meditation", meditation_handler)
  server = osc_server.ThreadingOSCUDPServer(
    (args.ip, args.port), dispatcher1)
  print("Serving on {}".format(server.server_address))
  server.serve_forever()

#---------------------------------------------------
# this is to attach a secondary bluetooth headset
# tried doing this as one function and info go intermixed

def soundServer2(queue,ip_addr,port,AttentionAvg, MeditationAvg):
  
  def attention_handler(action, value):
    
    global AttentionAvg
    
    eventMessage = (action, value)
    if action == "/attention":
      AttentionAvg.append(value)
      if len(AttentionAvg) == 30:
        y = 0
        for x in AttentionAvg:
          y += x
        y = y // 30
        #print ('attention2:', y)
        atnAvg = ('/attention', y)
        queue.put(atnAvg)
        AttentionAvg = []
        time.sleep(.01)
        
  def meditation_handler(action, value):

    global MeditationAvg

    MeditationAvg.append(value)
    if len(MeditationAvg) == 30:
      y=0
      for x in MeditationAvg:
        y += x
      y = y // 30
      #print ('meditation2:',y)
      MeditationAvg = []
      medAvg = ('/meditation', y)
      queue.put(medAvg)
      time.sleep(.01)
  
  parser = argparse.ArgumentParser()
  parser.add_argument("--ip",
                      default=ip_addr, help="The ip to listen on")
  parser.add_argument("--port",
                      type=int, default=port, help="The port to listen on")
  args = parser.parse_args()
  dispatcher2 = dispatcher.Dispatcher()
  dispatcher2.map("/attention", attention_handler) 
  dispatcher2.map("/meditation", meditation_handler)
  server = osc_server.ThreadingOSCUDPServer(
    (args.ip, args.port), dispatcher2)
  print("Serving on {}".format(server.server_address))
  server.serve_forever()

#---------------------------------------------------

AttentionAvg = []
MeditationAvg = []
AttentionAvg2 = []
MeditationAvg2 = []
ip_addr1 = "127.0.0.1"
ip_addr2 = "0.0.0.0"
port1 = 7771
port2 = 7772

queueP1 = LifoQueue()       
thread1 = Thread(target=soundServer, args=(queueP1,ip_addr1,port1,AttentionAvg,MeditationAvg))

queueP2 = LifoQueue()       
thread2 = Thread(target=soundServer2, args=(queueP2,ip_addr2,port2,AttentionAvg2, MeditationAvg2))

thread2.start()
thread1.start()

pygame.init()
pygame.mixer.init()
pygame.joystick.init()

joystick1 = pygame.joystick.Joystick(0)
joystick1.init()
joystick2 = pygame.joystick.Joystick(1)
joystick2.init()

myfont = pygame.font.SysFont("sanserif", 20)
myfont2 = pygame.font.SysFont("sanserif", 30)

fight = pygame.mixer.Sound("sounds/battle2.ogg")
winner = pygame.mixer.Sound("sounds/winner-short.ogg")

title_image = pygame.image.load("images/title.png")
game_winnerP1_image = pygame.image.load("images/blueWins.png")
game_winnerP2_image = pygame.image.load("images/p2winner.png")
p1rect = pygame.image.load("images/p1winnerRect.png")

size = width, height = 1379, 900
black = 0,0,0
white = 255, 255, 255
screen = pygame.display.set_mode((size), pygame.FULLSCREEN)

gameStarted = False
gameWinnerP1 = False
gameWinnerP2 = False
leftDown = False             #boolean value holders for key strokes
rightDown = False            #would be better to just use them as pygame registers keyup
aDown = False                #not always having to listen for them to be down
sDown = False                #this is the last one that is important
pDown = False                #this will be used to show troubleshoot values on screen
volume = 0.5

BASELINEMEDITATION = 40       #Constant to compare the meditation variable against
BASELINECONCENTRATION = 30    #Constant to compare the concentration variable against

# Continent defines the various regions and keeps track of if they are selected and if they have already been won

class Continent:
    def __init__(self, name, value):
        self.name = name
        self.isSelP1 = False      #keeping track of which continent the player's
        self.isSelP2 = False      #cursor is on
        self.influenceP1 = 0      # how much has P1 gained in this continent
        self.influenceP2 = 0      # how much does P2 own this continent
        self.P1won = False
        self.P2won = False
        self.value = value

    # function to increment the influence of each player inside the the parameter of 100% opacity
    def P1Control(self):
        #check that the total influence for that continent is < 255
        if (self.influenceP1 + self.influenceP2) < 255:
            self.influenceP1 += 1
        # keeping the total influence to 100%
        if ((self.influenceP1 + self.influenceP2) >= 255) and ((self.influenceP1 < 255) or (self.influenceP2 < 255)):
            self.influenceP1 += 1
            self.influenceP2 -= 1
        return self.influenceP1
    def P2Control(self):
        #check that the total influence for that continent is < 255
        if (self.influenceP1 + self.influenceP2) < 255:
            self.influenceP2 += 1
        # keeping the total influence to 100%
        if ((self.influenceP1 + self.influenceP2) >= 255) and ((self.influenceP1 < 255) or (self.influenceP2 < 255)):
            self.influenceP2 += 1
            self.influenceP1 -= 1
        return self.influenceP2

    def P1winner(self):
        global P1Tally, P1Score, seconds, winText, start_ticks
        self.P1won = True
        P1Score += self.value
        P1Tally += 1
        winText = myfont2.render("Player1 wins {0}".format(self.name), 1, (0,0,0))
        start_ticks = pygame.time.get_ticks()
        return self.P1won
      
    def P2winner(self):
        global P2Tally, P2Score, seconds, winText, start_ticks
        self.P2won = True
        P2Score += self.value
        P2Tally += 1
        winText = myfont2.render("Player2 wins {0}".format(self.name), 1, (0,0,0))
        start_ticks = pygame.time.get_ticks()
        return self.P2won

    def whoWon(self):
        if self.P1won:
          who = "Player 1", self.value
          return who
        if self.P2won:
          who = "Player 2", self.value
          return who
        
# Map is for all the elements that need to be drawn onto the screen

class Map:
    def __init__(self):
        self.world = pygame.image.load("images/world.png")   #background image to be draw everytime
        
        # images to highlight player1's selection
        self.selection1 = {0 : pygame.image.load("images/naBlueGlow.png"), \
                           1 : pygame.image.load("images/euBlueGlow.png"), \
                           2 : pygame.image.load("images/rusBlueGlow.png"), \
                           3 : pygame.image.load("images/saBlueGlow.png"), \
                           4 : pygame.image.load("images/afriBlueGlow.png"), \
                           5 : pygame.image.load("images/mideastBlueGlow.png"), \
                           6 : pygame.image.load("images/indoBlueGlow.png"), \
                           7 : pygame.image.load("images/asiaBlueGlow.png"), \
                           8 : pygame.image.load("images/ausBlueGlow.png")}
        
        # images to highlight player2's selection
        self.selection2 = {0 : pygame.image.load("images/naRedGlow.png"), \
                           1 : pygame.image.load("images/euRedGlow.png"), \
                           2 : pygame.image.load("images/rusRedGlow.png"), \
                           3 : pygame.image.load("images/saRedGlow.png"), \
                           4 : pygame.image.load("images/afriRedGlow.png"), \
                           5 : pygame.image.load("images/mideastRedGlow.png"), \
                           6 : pygame.image.load("images/indoRedGlow.png"), \
                           7 : pygame.image.load("images/asiaRedGlow.png"), \
                           8 : pygame.image.load("images/ausRedGlow.png")}
        
        # images to highlight when both have selected the same region
        self.selection3 = {0 : pygame.image.load("images/naBattleGlow.png"), \
                           1 : pygame.image.load("images/euBattleGlow.png"), \
                           2 : pygame.image.load("images/rusBattleGlow.png"), \
                           3 : pygame.image.load("images/saBattleGlow.png"), \
                           4 : pygame.image.load("images/afriBattleGlow.png"), \
                           5 : pygame.image.load("images/mideastBattleGlow.png"), \
                           6 : pygame.image.load("images/indoBattleGlow.png"), \
                           7 : pygame.image.load("images/asiaBattleGlow.png"), \
                           8 : pygame.image.load("images/ausBattleGlow.png")}
        
        # delete the grey from the background map and allow the blue and red to be drawn over the top
        self.white = {0 : pygame.image.load("images/naWhite.png"), \
                      1 : pygame.image.load("images/euWhite.png"), \
                      2 : pygame.image.load("images/rusWhite.png"), \
                      3 : pygame.image.load("images/saWhite.png"), \
                      4 : pygame.image.load("images/afriWhite.png"), \
                      5 : pygame.image.load("images/mideastWhite.png"), \
                      6 : pygame.image.load("images/indoWhite.png"), \
                      7 : pygame.image.load("images/asiaWhite.png"), \
                      8 : pygame.image.load("images/ausWhite.png")}
        
        # images for the continents that player 1 is winning or has already won
        self.winner1 = {0 : pygame.image.load("images/naBlueCrop.png"), \
                        1 : pygame.image.load("images/euBlueCrop.png"), \
                        2 : pygame.image.load("images/rusBlueCrop.png"), \
                        3 : pygame.image.load("images/saBlueCrop.png"), \
                        4 : pygame.image.load("images/afriBlueCrop.png"), \
                        5 : pygame.image.load("images/mideastBlueCrop.png"), \
                        6 : pygame.image.load("images/indoBlueCrop.png"), \
                        7 : pygame.image.load("images/asiaBlueCrop.png"), \
                        8 : pygame.image.load("images/ausBlueCrop.png")}
        
        # images for the continents that player2 is winning or has already won
        self.winner2 = { 0 : pygame.image.load("images/naRedCrop.png"), \
                         1 : pygame.image.load("images/euRedCrop.png"), \
                         2 : pygame.image.load("images/rusRedCrop.png"), \
                         3 : pygame.image.load("images/saRedCrop.png"), \
                         4 : pygame.image.load("images/afriRedCrop.png"), \
                         5 : pygame.image.load("images/mideastRedCrop.png"), \
                         6 : pygame.image.load("images/indoRedCrop.png"), \
                         7 : pygame.image.load("images/asiaRedCrop.png"), \
                         8 : pygame.image.load("images/ausRedCrop.png")}
        
    # function to create tranparency for the countries without blacking out the rest
    # of the world while changing the alpha.  Blits to a temporary surface the create
    # the alpha of the image above it's transparent per pixel background
    def blit_alpha(self, target, source, location, opacity):
        x = location[0]
        y = location[1]
        temp = pygame.Surface((source.get_width(), source.get_height())).convert()
        temp.blit(target, (-x, -y))
        temp.blit(source, (0, 0))
        temp.set_alpha(opacity)
        target.blit(temp, location)

    # the actual drawing function that draws the map and each player's influence to the screen
    def draw(self):
        global white, player1cursor, player2cursor
        screen.fill(white)
        screen.blit(self.world, (0,0))   # draws the rest of the world not in play

        # draw function of regions under influence of one player or the other
        if not regions[0].P1won and not regions[0].P2won and (regions[0].influenceP1 > 15 or regions[0].influenceP2 > 15):
            screen.blit(world.white[0], (0,0))
            world.blit_alpha(screen, world.winner1[0], (0,0), regions[0].influenceP1)
            world.blit_alpha(screen, world.winner2[0], (0,0), regions[0].influenceP2)
        if not regions[1].P1won and not regions[1].P2won and (regions[1].influenceP1 > 15 or regions[1].influenceP2 > 15):
            screen.blit(world.white[1], (0,0))
            world.blit_alpha(screen, world.winner1[1], (460,0), regions[1].influenceP1)
            world.blit_alpha(screen, world.winner2[1], (460,0), regions[1].influenceP2)
        if not regions[2].P1won and not regions[2].P2won and (regions[2].influenceP1 > 15 or regions[2].influenceP2 > 15):
            screen.blit(world.white[2], (0,0))
            world.blit_alpha(screen, world.winner1[2], (740,0), regions[2].influenceP1)
            world.blit_alpha(screen, world.winner2[2], (743,0), regions[2].influenceP2)
        if not regions[3].P1won and not regions[3].P2won and (regions[3].influenceP1 > 15 or regions[3].influenceP2 > 15):
            screen.blit(world.white[3], (0,0))
            world.blit_alpha(screen, world.winner1[3], (320,433), regions[3].influenceP1)
            world.blit_alpha(screen, world.winner2[3], (321,432), regions[3].influenceP2)
        if not regions[4].P1won and not regions[4].P2won and (regions[4].influenceP1 > 15 or regions[4].influenceP2 > 15):
            screen.blit(world.white[4], (0,0))
            world.blit_alpha(screen, world.winner1[4], (583,319), regions[4].influenceP1)
            world.blit_alpha(screen, world.winner2[4], (582,323), regions[4].influenceP2)
        if not regions[5].P1won and not regions[5].P2won and (regions[5].influenceP1 > 15 or regions[5].influenceP2 > 15):
            screen.blit(world.white[5], (0,0))
            world.blit_alpha(screen, world.winner1[5], (784,311), regions[5].influenceP1)
            world.blit_alpha(screen, world.winner2[5], (784,310), regions[5].influenceP2)
        if not regions[6].P1won and not regions[6].P2won and (regions[6].influenceP1 > 15 or regions[6].influenceP2 > 15):
            screen.blit(world.white[6], (0,0))
            world.blit_alpha(screen, world.winner1[6], (826,216), regions[6].influenceP1)
            world.blit_alpha(screen, world.winner2[6], (824,220), regions[6].influenceP2)
        if not regions[7].P1won and not regions[7].P2won and (regions[7].influenceP1 > 15 or regions[7].influenceP2 > 15):
            screen.blit(world.white[7], (0,0))
            world.blit_alpha(screen, world.winner1[7], (935,203), regions[7].influenceP1)
            world.blit_alpha(screen, world.winner2[7], (933,203), regions[7].influenceP2)
        if not regions[8].P1won and not regions[8].P2won and (regions[8].influenceP1 > 15 or regions[8].influenceP2 > 15):
            screen.blit(world.white[8], (0,0))
            world.blit_alpha(screen, world.winner1[8], (1046,391), regions[8].influenceP1)
            world.blit_alpha(screen, world.winner2[8], (1045,395), regions[8].influenceP2)

            
        if player1cursor != player2cursor:
            screen.blit(self.selection1[player1cursor], (0,0))   # highlights player1's selection
            screen.blit(self.selection2[player2cursor], (0,0))   # highlights player2's selection
        else:
            screen.blit(self.selection3[player1cursor], (0,0))   # highlights in purple when both are selected

        # draws the solid color image of the regions once they have been won by the player
        if regions[0].P1won:
            screen.blit(self.winner1[0], (0,0))
        if regions[0].P2won:
            screen.blit(self.winner2[0], (0,0))        
        if regions[1].P1won:
            screen.blit(self.winner1[1], (460,0))
        if regions[1].P2won:
            screen.blit(self.winner2[1], (460,0))
        if regions[2].P1won:
            screen.blit(self.winner1[2], (740,1))
        if regions[2].P2won:
            screen.blit(self.winner2[2], (743,1))
        if regions[3].P1won:
            screen.blit(self.winner1[3], (320,433))
        if regions[3].P2won:
            screen.blit(self.winner2[3], (321,432))
        if regions[4].P1won:
            screen.blit(self.winner1[4], (583,319))
        if regions[4].P2won:
            screen.blit(self.winner2[4], (582,323))
        if regions[5].P1won:
            screen.blit(self.winner1[5], (784,311))
        if regions[5].P2won:
            screen.blit(self.winner2[5], (784,310))        
        if regions[6].P1won:
            screen.blit(self.winner1[6], (826,216))
        if regions[6].P2won:
            screen.blit(self.winner2[6], (824,220))
        if regions[7].P1won:
            screen.blit(self.winner1[7], (934,203))
        if regions[7].P2won:
            screen.blit(self.winner2[7], (932,203))
        if regions[8].P1won:
            screen.blit(self.winner1[8], (1046,391))
        if regions[8].P2won:
            screen.blit(self.winner2[8], (1045,395))

# Function to draw the labels at the bottom of the screen
def drawText(concentration1,concentration2,meditation1,meditation2,P1Score,P2Score):
  # render text
  label1 = myfont.render("Concentration", 1, (0,0,255))
  label2 = myfont.render("Meditation", 1, (0,0,255))
  label3 = myfont.render("Concentration", 1, (255,0,0))
  label4 = myfont.render("Meditation", 1, (255,0,0))

  screen.blit(label1, (50, 850))
  screen.blit(label2, (150, 850))
  screen.blit(label3, (1120, 850))
  screen.blit(label4, (1220, 850))
  
  if pDown:
    label5 = myfont.render("Concentration: {0}".format(concentration1), 1, (0,0,255))
    label6 = myfont.render("Meditation: {0}".format(meditation1), 1, (0,0,255))
    label7 = myfont.render("Concentration: {0}".format(concentration2), 1, (0,0,255))
    label8 = myfont.render("Meditation: {0}".format(meditation2), 1, (0,0,255))

    screen.blit(label5, (50, 440))
    screen.blit(label6, (50, 460))
    screen.blit(label7, (50, 480))
    screen.blit(label8, (50, 500))

  Ply1 = myfont2.render("Player 1 Score: {0}".format(P1Score), 1, (0,0,255))
  Ply2 = myfont2.render("Player 2 Score: {0}".format(P2Score), 1, (255,0,0))

  screen.blit(Ply1, (50, 520))
  screen.blit(Ply2, (50, 540))  

# Function to draw the life bars at the bottom of the screen when in combat  
def lifeBar():
    global p1Life, p2Life, concentration1, concentration2, meditation1, meditation2
    pygame.draw.rect(screen, (0,0,255), (305, 800, (p1Life * 3), 20))
    pygame.draw.rect(screen, (255,0,0), (1074, 800, (p2Life * -3), 20))

    pygame.draw.rect(screen, (255,0,0), (95, 840, 20, (concentration2 * -2)))
    pygame.draw.rect(screen, (0,0,255), (90, 840, 20, (concentration1 * -2)))
    pygame.draw.rect(screen, (0,0,0), (160, (840 - (BASELINEMEDITATION*2)), 40, 3))
    pygame.draw.rect(screen, (0,0,255), (170, 840, 20, (meditation1 * -2)))
    pygame.draw.rect(screen, (0,0,255), (1165, 840, 20, (concentration1 * -2)))
    pygame.draw.rect(screen, (255,0,0), (1160, 840, 20, (concentration2 * -2)))
    pygame.draw.rect(screen, (0,0,0), (1230, (840 - (BASELINEMEDITATION*2)), 40, 3))
    pygame.draw.rect(screen, (255,0,0), (1240, 840, 20, (meditation2 * -2)))

                  
# set up all of the global variables at the start of the game once the spacebar has been pressed                  
def startGame():
    global player1cursor, player2cursor, P1Tally, P2Tally, p1Life, p2Life, meditation1
    global concentration1, meditation2, concentration2, regions, player1cursor, player2cursor
    global gameWinnerP1, gameWinnerP2, P1Score, P2Score, playedOnce

    pygame.mixer.music.load('sounds/play2.ogg')
    pygame.mixer.music.play(-1)
    
    gameWinnerP1 = False
    gameWinnerP2 = False
    playedOnce = False
    P1Tally = 0                   #to determine the end of the game
    P2Tally = 0
    P1Score = 0
    P2Score = 0
    p1Life = 0                    #for use in combat function
    p2Life = 0                    #for use in combat function
    meditation1 = 0               #variable for the meditation level of player 1
    concentration1 = 0            #variable for the concentration of player 1
    prevConcentration1 = 0
    meditation2 = 0               #variable for player2
    concentration2 = 0            #variable for the concentration of player2
    regions = []                  #list to hold all of the combat places (continents)
    player1cursor = 0             #variable for what region P1 has chosen
    player2cursor = 2             #variable for P2's choice

    
    # just append all the continents to the list
    northAmerica = Continent("North America", 10)
    regions.append(northAmerica)
    europe = Continent("Europe", 9)
    regions.append(europe)
    russia = Continent("Russia", 8)
    regions.append(russia)
    southAmerica = Continent("South America", 6)
    regions.append(southAmerica)
    africa = Continent("Africa", 6)
    regions.append(africa)
    mideast = Continent("Middle East", 13)
    regions.append(mideast)
    indo = Continent("Central Asia", 7)
    regions.append(indo)
    asia = Continent("East Asia", 7)
    regions.append(asia)
    australia = Continent("Australia", 5)
    regions.append(australia)

    #turn on selection cursor
    regions[player1cursor].isSelP1 = True
    regions[player2cursor].isSelP2 = True
            
def selector(): 

    global player1cursor, player2cursor
    
    regions[player2cursor].isSelP2 = True
    regions[(player2cursor + 1) % 9].isSelP2 = False
    regions[(player2cursor - 1) % 9].isSelP2 = False
    regions[player1cursor].isSelP1 = True
    regions[(player1cursor + 1) % 9].isSelP1 = False
    regions[(player1cursor - 1) % 9].isSelP1 = False

def combat(concentration1, concentration2):
    global player1cursor, player2cursor, p1Life, p2Life

    fightLabel = myfont2.render("Fight", 1, (0,0,0))
    screen.blit(fightLabel, (670, 770))
      
    #print(concentration1, concentration2)
    p1Life = regions[player1cursor].influenceP1
    #print (p1Life)
    p2Life = regions[player2cursor].influenceP2
    #print (p2Life)
    if p1Life >= 255:
        regions[player1cursor].P1winner()
        player1cursor = (player1cursor + 1) % 9
        player2cursor = (player2cursor - 1) % 9
        if regions[player2cursor].P1won or regions[player2cursor].P2won:
            player2cursor = (player2cursor - 1) % 9
            if regions[player2cursor].P1won or regions[player2cursor].P2won:
                player2cursor = (player2cursor - 1) % 9
                if regions[player2cursor].P1won or regions[player2cursor].P2won:
                    player2cursor = (player2cursor - 1) % 9
                    if regions[player2cursor].P1won or regions[player2cursor].P2won:
                        player2cursor = (player2cursor - 1) % 9
                        if regions[player2cursor].P1won or regions[player2cursor].P2won:
                            player2cursor = (player2cursor - 1) % 9
                            if regions[player2cursor].P1won or regions[player2cursor].P2won:
                                player2cursor = (player2cursor - 1) % 9
                                if regions[player2cursor].P1won or regions[player2cursor].P2won:
                                    player2cursor = (player2cursor - 1) % 9
    elif p2Life >= 255:
        regions[player2cursor].P2winner()
        player2cursor = (player2cursor + 1) % 9
        player1cursor = (player1cursor - 1) % 9
        if regions[player1cursor].P1won or regions[player1cursor].P2won:
            player1cursor = (player1cursor - 1) % 9
            if regions[player1cursor].P1won or regions[player1cursor].P2won:
                player1cursor = (player1cursor - 1) % 9
                if regions[player1cursor].P1won or regions[player1cursor].P2won:
                    player1cursor = (player1cursor - 1) % 9
                    if regions[player1cursor].P1won or regions[player1cursor].P2won:
                        player1cursor = (player1cursor - 1) % 9
                        if regions[player1cursor].P1won or regions[player1cursor].P2won:
                            player1cursor = (player1cursor - 1) % 9
                            if regions[player1cursor].P1won or regions[player1cursor].P2won:
                                player1cursor = (player1cursor - 1) % 9
                                if regions[player1cursor].P1won or regions[player1cursor].P2won:
                                    player1cursor = (player1cursor - 1) % 9
        
    else:
        if p1Life + p2Life < 255:
            if concentration1 > BASELINECONCENTRATION:
                regions[player1cursor].P1Control()
            if concentration2 > BASELINECONCENTRATION:
                regions[player2cursor].P2Control()
        if p1Life + p2Life >= 255:
            if concentration1 > concentration2:
                regions[player1cursor].P1Control()
            if concentration2 > concentration1:
                regions[player2cursor].P2Control()

# function to determine players influence in a region when not in combat
def influence(meditation1, meditation2):
    global player1cursor, player2cursor, p1Life, p2Life

    p1Life = 0
    p2Life = 0
     
    # don't allow players to fight over previously won regions
    if regions[player1cursor].P1won or regions[player1cursor].P2won:
        player1cursor = (player1cursor + 1) % 9
    else:
        #check which region is selected by player one and that it is not sel by P2
        if regions[player1cursor].isSelP1:

            #check if player1's meditation is above 50%
            if meditation1 >= BASELINEMEDITATION:
    
                # increment player 1's influence
                regions[player1cursor].P1Control()

                # declare player 1 the winner of the region and move to the next
                if regions[player1cursor].influenceP1 >= 255:
                    regions[player1cursor].P1winner()
                    player1cursor = (player1cursor + 1) % 9

    if regions[player2cursor].P1won == True or regions[player2cursor].P2won == True:
        player2cursor = (player2cursor + 1) % 9
    else:    
        #check everything for player 2
        if regions[player2cursor].isSelP2:

            #check if player 2's meditation is above 50%
            if meditation2 >= BASELINEMEDITATION:

                # increment player 2's influence
                regions[player2cursor].P2Control()

                if regions[player2cursor].influenceP2 >= 255:
                    regions[player2cursor].P2winner()
                    player2cursor = (player2cursor + 1) % 9

def gameOver():
    global P1Tally, P2Tally, gameStarted, gameWinnerP1, gameWinnerP2, P1Score, P2Score, regions

   #   currently determines the winner, needs to be changed to show the weighting of different regions
    if (P1Tally + P2Tally) == 9:
        if P1Score > P2Score:
            gameStarted = False
            print (P1Score)
            print (P2Score)
            gameWinnerP1 = True
        if P2Score > P1Score:
            gameStarted = False
            print (P1Score)
            print (P2Score)
            gameWinnerP2 = True
        
        
def quitGame():
    #global server
    #server.shutdown()
    print("Remember to ctrl c to stop other threads that are running!")
    pygame.quit()
    sys.exit()
    thread1.terminate()
    thread2.terminate()

world = Map()
winText = myfont2.render("", 1, (0,0,0))
start_ticks = pygame.time.get_ticks()

while True:

    if gameStarted is True:  #begin game play
      
        #print ("check")
        while not queueP1.empty():
            name, value = queueP1.get(False)
            queueP1.task_done()
    
            if name == '/attention':
                concentration1 = value
                #print (name, value)
            if name == '/meditation':
                meditation1 = value
                #print (name, value)

        while not queueP2.empty():
            name, value = queueP2.get()
            queueP2.task_done()
            if name == '/attention':
              concentration2 = value
              #print(name, value)
            if name == '/meditation':
              meditation2 = value
              #print (name, value)
              
        world.draw()
        selector()
        # to activate the combat
        if player1cursor == player2cursor:
            if not playedOnce:
              fight.set_volume(volume)
              fight.play()
              playedOnce = True
            combat(concentration1, concentration2)
        else:
            playedOnce = False
            influence(meditation1, meditation2)
        seconds=(pygame.time.get_ticks()-start_ticks)/1000
        if seconds < 5:
          screen.blit(winText, (600, 700))
        drawText(concentration1, concentration2, meditation1, meditation2,P1Score,P2Score)
        lifeBar()
        gameOver()
        
    elif gameWinnerP1 is True:
 #       world.blit_alpha(screen, p1rect, (0,0), 50)
        NA = myfont2.render("North America: {0}".format(regions[0].whoWon()), 1, (0,0,0))
        EU = myfont2.render("Europe: {0}".format(regions[1].whoWon()), 1, (0,0,0))
        RU = myfont2.render("Russia: {0}".format(regions[2].whoWon()), 1, (0,0,0))
        SA = myfont2.render("South America: {0}".format(regions[3].whoWon()), 1, (0,0,0))
        AF = myfont2.render("Africa: {0}".format(regions[4].whoWon()), 1, (0,0,0))
        ME = myfont2.render("Middle East: {0}".format(regions[5].whoWon()), 1, (0,0,0))
        IS = myfont2.render("Central Asia: {0}".format(regions[6].whoWon()), 1, (0,0,0))
        CH = myfont2.render("East Asia: {0}".format(regions[7].whoWon()), 1, (0,0,0))
        AU = myfont2.render("Australia: {0}".format(regions[8].whoWon()), 1, (0,0,0))
        P1 = myfont2.render("Player 1 Score: {0}".format(P1Score), 1, (0,0,255))
        P2 = myfont2.render("Player 2 Score: {0}".format(P2Score), 1, (255,0,0))

        pygame.draw.rect(screen, (255,255,255), (500, 660, 400, 130))
        screen.blit(NA, (500, 660))
        screen.blit(EU, (500, 680))
        screen.blit(RU, (500, 700))
        screen.blit(SA, (500, 720))
        screen.blit(AF, (500, 740))
        screen.blit(ME, (850, 680))
        screen.blit(IS, (850, 700))
        screen.blit(CH, (850, 720))
        screen.blit(AU, (850, 740))
        
        screen.blit(game_winnerP1_image, (0,0))
        if not playedOnce2:
            winner.set_volume(.3)
            winner.play()
            playedOnce2 = True
              
        
    elif gameWinnerP2 is True:
 #       world.blit_alpha(screen, p1rect, (0,0), 50)
        NA = myfont2.render("North America: {0[0]}, {0[1]}".format(regions[0].whoWon()), 1, (0,0,0))
        EU = myfont2.render("Europe: {0}".format(regions[1].whoWon()), 1, (0,0,0))
        RU = myfont2.render("Russia: {0}".format(regions[2].whoWon()), 1, (0,0,0))
        SA = myfont2.render("South America: {0}".format(regions[3].whoWon()), 1, (0,0,0))
        AF = myfont2.render("Africa: {0}".format(regions[4].whoWon()), 1, (0,0,0))
        ME = myfont2.render("Middle East: {0}".format(regions[5].whoWon()), 1, (0,0,0))
        IS = myfont2.render("Central Asia: {0}".format(regions[6].whoWon()), 1, (0,0,0))
        CH = myfont2.render("East Asia: {0}".format(regions[7].whoWon()), 1, (0,0,0))
        AU = myfont2.render("Australia: {0}".format(regions[8].whoWon()), 1, (0,0,0))
        P1 = myfont2.render("Player 1 Score: {0}".format(P1Score), 1, (0,0,255))
        P2 = myfont2.render("Player 2 Score: {0}".format(P2Score), 1, (255,0,0))

        pygame.draw.rect(screen, (255,255,255), (500, 660, 400, 130))
        screen.blit(NA, (500, 660))
        screen.blit(EU, (500, 680))
        screen.blit(RU, (500, 700))
        screen.blit(SA, (500, 720))
        screen.blit(AF, (500, 740))
        screen.blit(ME, (850, 680))
        screen.blit(IS, (850, 700))
        screen.blit(CH, (850, 720))
        screen.blit(AU, (850, 740))
        screen.blit(game_winnerP2_image, (0,0))
        if not playedOnce2:
            winner.set_volume(.3)
            winner.play()
            playedOnce2 = True
 
        
    else:
        # Welcome screen
        screen.blit(title_image, (0,0))
        
    pygame.display.update()

    if joystick1.get_button(0) == 1 or joystick1.get_button(4) == 1 or joystick1.get_button(6) == 1 or joystick1.get_hat(0)[0] == -1:
        player2cursor = (player2cursor - 1) % 9
        # checking to make sure that it hasn't already been won
        if regions[player2cursor].P1won or regions[player2cursor].P2won:
          player2cursor = (player2cursor - 1) % 9
          if regions[player2cursor].P1won or regions[player2cursor].P2won:
            player2cursor = (player2cursor - 1) % 9
            if regions[player2cursor].P1won or regions[player2cursor].P2won:
              player2cursor = (player2cursor - 1) % 9
              if regions[player2cursor].P1won or regions[player2cursor].P2won:
                player2cursor = (player2cursor - 1) % 9
                if regions[player2cursor].P1won or regions[player2cursor].P2won:
                  player2cursor = (player2cursor - 1) % 9
                  if regions[player2cursor].P1won or regions[player2cursor].P2won:
                    player2cursor = (player2cursor - 1) % 9
                    if regions[player2cursor].P1won or regions[player2cursor].P2won:
                      player2cursor = (player2cursor - 1) % 9
        regions[player2cursor].isSelP2 = True
        regions[(player2cursor + 1) % 9].isSelP2 = False
        time.sleep(.05)
    if joystick1.get_button(2) == 1 or joystick1.get_button(5) == 1 or joystick1.get_button(7) == 1 or joystick1.get_hat(0)[0] == 1: 
        player2cursor = (player2cursor + 1) % 9
        if regions[player2cursor].P1won or regions[player2cursor].P2won:
          player2cursor = (player2cursor + 1) % 9
          if regions[player2cursor].P1won or regions[player2cursor].P2won:
            player2cursor = (player2cursor + 1) % 9
            if regions[player2cursor].P1won or regions[player2cursor].P2won:
              player2cursor = (player2cursor + 1) % 9
              if regions[player2cursor].P1won or regions[player2cursor].P2won:
                player2cursor = (player2cursor + 1) % 9
                if regions[player2cursor].P1won or regions[player2cursor].P2won:
                  player2cursor = (player2cursor + 1) % 9
                  if regions[player2cursor].P1won or regions[player2cursor].P2won:
                    player2cursor = (player2cursor + 1) % 9
                    if regions[player2cursor].P1won or regions[player2cursor].P2won:
                      player2cursor = (player2cursor + 1) % 9
        regions[player2cursor].isSelP2 = True
        regions[(player2cursor - 1) % 9].isSelP2 = False
        time.sleep(.05)
    if joystick2.get_button(0) == 1 or joystick2.get_button(4) == 1 or joystick2.get_button(6) == 1 or joystick2.get_hat(0)[0] == -1:
        player1cursor = (player1cursor - 1) % 9
        if regions[player1cursor].P1won or regions[player1cursor].P2won:
          player1cursor = (player1cursor - 1) % 9
          if regions[player1cursor].P1won or regions[player1cursor].P2won:
            player1cursor = (player1cursor - 1) % 9
            if regions[player1cursor].P1won or regions[player1cursor].P2won:
              player1cursor = (player1cursor - 1) % 9
              if regions[player1cursor].P1won or regions[player1cursor].P2won:
                player1cursor = (player1cursor - 1) % 9
                if regions[player1cursor].P1won or regions[player1cursor].P2won:
                  player1cursor = (player1cursor - 1) % 9
                  if regions[player1cursor].P1won or regions[player1cursor].P2won:
                    player1cursor = (player1cursor - 1) % 9
                    if regions[player1cursor].P1won or regions[player1cursor].P2won:
                      player1cursor = (player1cursor - 1) % 9
        regions[player1cursor].isSelP1 = True
        regions[(player1cursor + 1) % 9].isSelP1 = False
        time.sleep(.05)
    if joystick2.get_button(2) == 1 or joystick2.get_button(5) == 1 or joystick2.get_button(7) == 1 or joystick2.get_hat(0)[0] == 1:
        player1cursor = (player1cursor + 1) % 9
        if regions[player1cursor].P1won or regions[player1cursor].P2won:
          player1cursor = (player1cursor + 1) % 9
          if regions[player1cursor].P1won or regions[player1cursor].P2won:
            player1cursor = (player1cursor + 1) % 9
            if regions[player1cursor].P1won or regions[player1cursor].P2won:
              player1cursor = (player1cursor + 1) % 9
              if regions[player1cursor].P1won or regions[player1cursor].P2won:
                player1cursor = (player1cursor + 1) % 9
                if regions[player1cursor].P1won or regions[player1cursor].P2won:
                  player1cursor = (player1cursor + 1) % 9
                  if regions[player1cursor].P1won or regions[player1cursor].P2won:
                    player1cursor = (player1cursor + 1) % 9
                    if regions[player1cursor].P1won or regions[player1cursor].P2won:
                      player1cursor = (player1cursor + 1) % 9

        regions[player1cursor].isSelP1 = True
        regions[(player1cursor - 1) % 9].isSelP1 = False
        time.sleep(.05)
    
    for event in GAME_EVENTS.get():
        # print ("Got Event", event.type)
        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_p:
                pDown = True

            if event.key == pygame.K_ESCAPE:
                quitGame()
                
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_LEFT:

                # movement of the player selection 
                player2cursor = (player2cursor - 1) % 9
                # checking to make sure that it hasn't already been won
                if regions[player2cursor].P1won or regions[player2cursor].P2won:
                    player2cursor = (player2cursor - 1) % 9
                    if regions[player2cursor].P1won or regions[player2cursor].P2won:
                        player2cursor = (player2cursor - 1) % 9
                        if regions[player2cursor].P1won or regions[player2cursor].P2won:
                            player2cursor = (player2cursor - 1) % 9
                            if regions[player2cursor].P1won or regions[player2cursor].P2won:
                                player2cursor = (player2cursor - 1) % 9
                                if regions[player2cursor].P1won or regions[player2cursor].P2won:
                                    player2cursor = (player2cursor - 1) % 9
                                    if regions[player2cursor].P1won or regions[player2cursor].P2won:
                                        player2cursor = (player2cursor - 1) % 9
                                        if regions[player2cursor].P1won or regions[player2cursor].P2won:
                                            player2cursor = (player2cursor - 1) % 9
                regions[player2cursor].isSelP2 = True
                regions[(player2cursor + 1) % 9].isSelP2 = False
                
            if event.key == pygame.K_RIGHT:
 
                player2cursor = (player2cursor + 1) % 9
                if regions[player2cursor].P1won or regions[player2cursor].P2won:
                    player2cursor = (player2cursor + 1) % 9
                    if regions[player2cursor].P1won or regions[player2cursor].P2won:
                        player2cursor = (player2cursor + 1) % 9
                        if regions[player2cursor].P1won or regions[player2cursor].P2won:
                            player2cursor = (player2cursor + 1) % 9
                            if regions[player2cursor].P1won or regions[player2cursor].P2won:
                                player2cursor = (player2cursor + 1) % 9
                                if regions[player2cursor].P1won or regions[player2cursor].P2won:
                                    player2cursor = (player2cursor + 1) % 9
                                    if regions[player2cursor].P1won or regions[player2cursor].P2won:
                                        player2cursor = (player2cursor + 1) % 9
                                        if regions[player2cursor].P1won or regions[player2cursor].P2won:
                                            player2cursor = (player2cursor + 1) % 9
                regions[player2cursor].isSelP2 = True
                regions[(player2cursor - 1) % 9].isSelP2 = False
                
            if event.key == pygame.K_a:

                player1cursor = (player1cursor - 1) % 9
                if regions[player1cursor].P1won or regions[player1cursor].P2won:
                    player1cursor = (player1cursor - 1) % 9
                    if regions[player1cursor].P1won or regions[player1cursor].P2won:
                        player1cursor = (player1cursor - 1) % 9
                        if regions[player1cursor].P1won or regions[player1cursor].P2won:
                            player1cursor = (player1cursor - 1) % 9
                            if regions[player1cursor].P1won or regions[player1cursor].P2won:
                                player1cursor = (player1cursor - 1) % 9
                                if regions[player1cursor].P1won or regions[player1cursor].P2won:
                                    player1cursor = (player1cursor - 1) % 9
                                    if regions[player1cursor].P1won or regions[player1cursor].P2won:
                                        player1cursor = (player1cursor - 1) % 9
                                        if regions[player1cursor].P1won or regions[player1cursor].P2won:
                                            player1cursor = (player1cursor - 1) % 9
                regions[player1cursor].isSelP1 = True
                regions[(player1cursor + 1) % 9].isSelP1 = False
                
            if event.key == pygame.K_s:

                player1cursor = (player1cursor + 1) % 9   
                if regions[player1cursor].P1won or regions[player1cursor].P2won:
                    player1cursor = (player1cursor + 1) % 9
                    if regions[player1cursor].P1won or regions[player1cursor].P2won:
                        player1cursor = (player1cursor + 1) % 9
                        if regions[player1cursor].P1won or regions[player1cursor].P2won:
                            player1cursor = (player1cursor + 1) % 9
                            if regions[player1cursor].P1won or regions[player1cursor].P2won:
                                player1cursor = (player1cursor + 1) % 9
                                if regions[player1cursor].P1won or regions[player1cursor].P2won:
                                    player1cursor = (player1cursor + 1) % 9
                                    if regions[player1cursor].P1won or regions[player1cursor].P2won:
                                        player1cursor = (player1cursor + 1) % 9
                                        if regions[player1cursor].P1won or regions[player1cursor].P2won:
                                            player1cursor = (player1cursor + 1) % 9

                regions[player1cursor].isSelP1 = True
                regions[(player1cursor - 1) % 9].isSelP1 = False
                
            if event.key == pygame.K_p:
                pDown = False
                
            if event.key == pygame.K_SPACE:
                if gameStarted == False:
                    startGame()
                    gameStarted = True
                    playedOnce2 = False

        if event.type == GAME_GLOBALS.QUIT:
            quitGame()

    time.sleep(.01)   
