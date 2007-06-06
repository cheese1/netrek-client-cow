#!/usr/bin/python
import sys, socket, struct, pygame

verbose = 0

def strnul(input):
    """ convert a NUL terminated string to a normal string
    """
    return input.split('\000')[0]

def scale(x, y):
    """ temporary coordinate scaling, galactic to screen
    """
    return (x/100, y/100)

class IC:
    """ an image cache
    """
    def __init__(self):
        self.cache = {}

    def read(self, name):
        image = pygame.image.load(name)
        return pygame.Surface.convert_alpha(image)

    def get(self, name):
        if name not in self.cache:
            self.cache[name] = self.read(name)
        return self.cache[name]
        
ic = IC()
    
class Planet:
    """ netrek planets
    """
    def __init__(self, n):
        self.n = n
        self.x = -10000
        self.y = -10000
        self.name = ''
        self.image = ic.get("romulus-1.png")
        self.rect = self.image.get_rect()

    def sp_planet_loc(self, x, y, name):
        self.x = x
        self.y = y
        # FIXME: use name
        
    def sp_planet(self, owner, info, flags, armies):
        # FIXME: use args
        pass

    def draw(self):
        global screen
        self.rect.center = scale(self.x, self.y)
        screen.blit(self.image, self.rect)

class Ship:
    """ netrek ships
    """
    def __init__(self, n):
        self.n = n
        self.x = -10000
        self.y = -10000
        self.image = ic.get("netrek.png")
        self.rect = self.image.get_rect()

    def sp_player(self, dir, speed, x, y):
        self.dir = dir
        self.speed = speed
        self.x = x
        self.y = y

    def draw(self):
        global screen
        # FIXME: rotate image according to self.dir
        self.rect.center = scale(self.x, self.y)
        screen.blit(self.image, self.rect)

class Galaxy:
    def __init__(self):
        self.planets = {}
        self.ships = {}

    def planet(self, n):
        if not self.planets.has_key(n):
            planet = Planet(n)
            self.planets[n] = planet
        return self.planets[n]

    def ship(self, n):
        if not self.ships.has_key(n):
            self.ships[n] = Ship(n)
        return self.ships[n]

    def draw(self):
        for n, planet in self.planets.iteritems():
            planet.draw()
        for n, ship in self.ships.iteritems():
            ship.draw()

galaxy = Galaxy()
me = None

FED=0x1
ROM=0x2
KLI=0x4
ORI=0x8

def team_decode(input):
    """ convert a team mask to a list
    """
    x = []
    if input & FED: x.append('F')
    if input & ROM: x.append('R')
    if input & KLI: x.append('K')
    if input & ORI: x.append('O')
    return x

""" client originated packets
"""

class CP:
    def tabulate(self, number, format):
        global cp_table
        cp_table[number] = (struct.calcsize(format), format)

cp_table = {}

class CP_SOCKET(CP):
    def __init__(self):
        self.code = 27
        self.format = '!bbbxI'
        self.tabulate(self.code, self.format)

    def data(self):
        if verbose: print "CP_SOCKET"
        return struct.pack(self.format, self.code, 4, 10, 0)

cp_socket = CP_SOCKET()

class CP_BYE(CP):
    def __init__(self):
        self.code = 29
        self.format = '!bxxx'
        self.tabulate(self.code, self.format)

    def data(self):
        print "CP_BYE"
        return struct.pack(self.format, self.code)

cp_bye = CP_BYE()

class CP_LOGIN(CP):
    def __init__(self):
        self.code = 8
        self.format = '!bbxx16s16s16s' 
        self.tabulate(self.code, self.format)

    def data(self, query, name, password, login):
        print "CP_LOGIN query=",query,"name=",name
        return struct.pack(self.format, self.code, query, name, password, login)

cp_login = CP_LOGIN()

class CP_OUTFIT(CP):
    def __init__(self):
        self.code = 9
        self.format = '!bbbx'
        self.tabulate(self.code, self.format)

    def data(self, team, ship):
        print "CP_OUTFIT team=",team_decode(team),"ship=",ship
        return struct.pack(self.format, self.code, team, ship)

cp_outfit = CP_OUTFIT()

class CP_SPEED(CP):
    def __init__(self):
        self.code = 2
        self.format = '!bbxx'
        self.tabulate(self.code, self.format)

    def data(self, speed):
        print "CP_SPEED speed=",speed
        return struct.pack(self.format, self.code, speed)

cp_speed = CP_SPEED()

class CP_DIRECTION(CP):
    def __init__(self):
        self.code = 3
        self.format = '!bBxx'
        self.tabulate(self.code, self.format)

    def data(self, direction):
        print "CP_DIRECTION direction=",direction
        return struct.pack(self.format, self.code, direction)

cp_direction = CP_DIRECTION()

""" server originated packets
"""

class SP:
    def tabulate(self, number, format, instance):
        global sp_table
        sp_table[number] = (struct.calcsize(format), instance)

    def find(self, number):
        """ given a packet type return a tuple consisting of
            (size, instance)
        """
        global sp_table
        if not sp_table.has_key(number):
            return (1, self)
        return sp_table[number]

sp_table = {}
sp = SP()

class SP_MOTD(SP):
    def __init__(self):
        self.code = 11
        self.format = '!bxxx80s'
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, message) = struct.unpack(self.format, data)
        print strnul(message)

sp_motd = SP_MOTD()

class SP_YOU(SP):
    def __init__(self):
        self.code = 12
        self.format = '!bbbbbbxxIlllhhhh'
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, pnum, hostile, swar, armies, tractor, flags, damage,
         shield, fuel, etemp, wtemp, whydead, whodead) = struct.unpack(self.format, data)
        if verbose: print "SP_YOU pnum=",pnum,"hostile=",team_decode(hostile),"swar=",team_decode(swar),"armies=",armies,"tractor=",tractor,"flags=",flags,"damage=",damage,"shield=",shield,"fuel=",fuel,"etemp=",etemp,"wtemp=",wtemp,"whydead=",whydead,"whodead=",whodead
        me = galaxy.ship(pnum)
        ## FIXME: handle the packet

sp_you = SP_YOU()

class SP_PL_LOGIN(SP):
    def __init__(self):
        self.code = 24
        self.format = "!bbbx16s16s16s" 
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, pnum, rank, name, monitor,
         login) = struct.unpack(self.format, data)
        if verbose: print "SP_PL_LOGIN pnum=",pnum,"rank=",rank,"name=",strnul(name),"monitor=",strnul(monitor),"login=",strnul(login)

sp_pl_login = SP_PL_LOGIN()

class SP_HOSTILE(SP):
    def __init__(self):
        self.code = 22
        self.format = "!bbbb"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, pnum, war, hostile) = struct.unpack(self.format, data)
        if verbose: print "SP_HOSTILE pnum=",pnum,"war=",team_decode(war),"hostile=",team_decode(hostile)

sp_hostile = SP_HOSTILE()

class SP_PLAYER_INFO(SP):
    def __init__(self):
        self.code = 2
        self.format = "!bbbb"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, pnum, shiptype, team) = struct.unpack(self.format, data)
        if verbose: print "SP_PLAYER_INFO pnum=",pnum,"shiptype=",shiptype,"team=",team_decode(team)

sp_player_info = SP_PLAYER_INFO()

class SP_KILLS(SP):
    def __init__(self):
        self.code = 3
        self.format = "!bbxxI"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, pnum, kills) = struct.unpack(self.format, data)
        if verbose: print "SP_KILLS pnum=",pnum,"kills=",kills

sp_kills = SP_KILLS()

class SP_PSTATUS(SP):
    def __init__(self):
        self.code = 20
        self.format = "!bbbx"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, pnum, status) = struct.unpack(self.format, data)
        if verbose: print "SP_PSTATUS pnum=",pnum,"status=",status

sp_pstatus = SP_PSTATUS()

class SP_PLAYER(SP):
    def __init__(self):
        self.code = 4
        self.format = "!bbBbll"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, pnum, dir, speed, x, y) = struct.unpack(self.format, data)
        if verbose: print "SP_PLAYER pnum=",pnum,"dir=",dir,"speed=",speed,"x=",x,"y=",y
        ship = galaxy.ship(pnum)
        ship.sp_player(dir, speed, x, y)

sp_player = SP_PLAYER()

class SP_FLAGS(SP):
    def __init__(self):
        self.code = 18
        self.format = "!bbbxI"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, pnum, tractor, flags) = struct.unpack(self.format, data)
        if verbose: print "SP_FLAGS pnum=",pnum,"tractor=",tractor,"flags=",flags

sp_flags = SP_FLAGS()

class SP_PLANET_LOC(SP):
    def __init__(self):
        self.code = 26
        self.format = "!bbxxll16s" 
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, pnum, x, y, name) = struct.unpack(self.format, data)
        if verbose: print "SP_PLANET_LOC pnum=",pnum,"x=",x,"y=",y,"name=",strnul(name)
        planet = galaxy.planet(pnum)
        planet.sp_planet_loc(x, y, name)

sp_planet_loc = SP_PLANET_LOC()

class SP_LOGIN(SP):
    def __init__(self):
        self.code = 17
        self.format = "!bbxxl96s"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, accept, flags, keymap) = struct.unpack(self.format, data)
        if verbose: print "SP_LOGIN accept=",accept,"flags=",flags

sp_login = SP_LOGIN()

class SP_MASK(SP):
    def __init__(self):
        self.code = 19
        self.format = "!bbxx"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, mask) = struct.unpack(self.format, data)
        if verbose: print "SP_MASK mask=",team_decode(mask)

sp_mask = SP_MASK()

class SP_PICKOK(SP):
    def __init__(self):
        self.code = 16
        self.format = "!bbxx"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, state) = struct.unpack(self.format, data)
        if verbose: print "SP_PICKOK state=",state

sp_pickok = SP_PICKOK()

class SP_RESERVED(SP):
    def __init__(self):
        self.code = 25
        self.format = "!bxxx16s"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, data) = struct.unpack(self.format, data)
        data = struct.unpack('16b', data)
        if verbose: print "SP_RESERVED data=",data

sp_reserved = SP_RESERVED()

class SP_TORP_INFO(SP):
    def __init__(self):
        self.code = 5
        self.format = "!bbbxhxx"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, war, status, tnum) = struct.unpack(self.format, data)
        if verbose: print "SP_TORP_INFO war=",team_decode(war),"status=",status,"tnum=",tnum

sp_torp_info = SP_TORP_INFO()

class SP_TORP(SP):
    def __init__(self):
        self.code = 6
        self.format = "!bBhll"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, dir, tnum, x, y) = struct.unpack(self.format, data)
        if verbose: print "SP_TORP dir=",dir,"tnum=",tnum,"x=",x,"y=",y

sp_torp = SP_TORP()

class SP_PLASMA_INFO(SP):
    def __init__(self):
        self.code = 8
        self.format = "!bbbxhxx"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, war, status, pnum) = struct.unpack(self.format, data)
        if verbose: print "SP_PLASMA_INFO war=",team_decode(war),"status=",status,"pnum=",pnum

sp_plasma_info = SP_PLASMA_INFO()

class SP_PLASMA(SP):
    def __init__(self):
        self.code = 9
        self.format = "!bxhll"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, pnum, x, y) = struct.unpack(self.format, data)
        if verbose: print "SP_PLASMA pnum=",pnum,"x=",x,"y=",y

sp_plasma = SP_PLASMA()

class SP_STATUS(SP):
    def __init__(self):
        self.code = 14
        self.format = "!bbxxIIIIIL"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, tourn, armsbomb, planets, kills, losses, time, timeprod) = struct.unpack(self.format, data)
        if verbose: print "SP_STATUS tourn=",tourn,"armsbomb=",armsbomb,"planets=",planets,"kills=",kills,"losses=",losses,"time=",time,"timepro=",timeprod

sp_status = SP_STATUS()

class SP_PHASER(SP):
    def __init__(self):
        self.code = 7
        self.format = "!bbbBlll" 
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, pnum, status, dir, x, y, target) = struct.unpack(self.format, data)
        if verbose: print "SP_PHASER pnum=",pnum,"status=",status,"dir=",dir,"x=",x,"y=",y,"target=",target

sp_phaser = SP_PHASER()

class SP_PLANET(SP):
    def __init__(self):
        self.code = 15
        self.format = "!bbbbhxxl" 
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, pnum, owner, info, flags, armies) = struct.unpack(self.format, data)
        if verbose: print "SP_PLANET pnum=",pnum,"owner=",owner,"info=",info,"flags=",flags,"armies=",armies
        planet = galaxy.planet(pnum)
        planet.sp_planet(owner, info, flags, armies)

sp_planet = SP_PLANET()

class SP_MESSAGE(SP):
    def __init__(self):
        self.code = 1
        self.format = "!bBBB80s"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, m_flags, m_recpt, m_from, mesg) = struct.unpack(self.format, data)
        if verbose: print "SP_MESSAGE m_flags=",m_flags,"m_recpt=",m_recpt,"m_from=",m_from,"mesg=",strnul(mesg)

sp_message = SP_MESSAGE()

class SP_STATS(SP):
    def __init__(self):
        self.code = 23
        self.format = "!bbxx13l"
        self.tabulate(self.code, self.format, self)

    def handler(self, data):
        (ignored, pnum, tkills, tlosses, kills, losses, tticks, tplanets, tarmies, sbkills, sblosses, armies, planets, maxkills, sbmaxkills) = struct.unpack(self.format, data)
        if verbose: print "SP_STATS pnum=",pnum,"tkills=",tkills,"tlosses=",tlosses,"kills=",kills,"losses=",losses,"tticks=",tticks,"tplanets=",tplanets,"tarmies=",tarmies,"sbkills=",sbkills,"sblosses=",sblosses,"armies=",armies,"planets=",planets,"maxkills=",maxkills,"sbmaxkills=",sbmaxkills

sp_stats = SP_STATS()

##
## progress report, all packet types handled to the point of team selection
##

""" Netrek TCP
"""

s = None

def nt_connect(host, port):
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    #s.setblocking(0)
    s.settimeout(0.1)

def nt_send(data):
    global s
    s.send(data)

def nt_recv():
    global s
    try:
        byte = s.recv(1)
    except:
        return
    # FIXME: when server closes connection, we get something other than a byte
    number = struct.unpack('b', byte[0])[0]
    (size, instance) = sp.find(number)
    if size == 1:
        print "\n#### FIXME: UnknownPacketType ", number, "####\n"
        raise "UnknownPacketType, a packet was received from the server that is not known to this program, and since packet lengths are determined by packet types there is no reasonably way to continue operation"
        return
    if verbose: print "packet type=", number, "size=", size
    instance.handler(byte + s.recv(size-1))

def kb(key):
    if event.key == pygame.K_SPACE:
        nt_send(cp_login.data(0, 'guest', '', 'try'))
    elif event.key == pygame.K_TAB:
        nt_send(cp_outfit.data(0, 0))
    elif event.key == pygame.K_q:
        screen.fill(black)
        pygame.display.flip()
        nt_send(cp_bye.data())
        sys.exit()
    elif event.key == pygame.K_0:
        nt_send(cp_speed.data(0))
    elif event.key == pygame.K_1:
        nt_send(cp_speed.data(1))
    elif event.key == pygame.K_6:
        nt_send(cp_speed.data(6))
    elif event.key == pygame.K_9:
        nt_send(cp_speed.data(9))

def mb(position, button):
    """ mouse button down event handler
    position is a list of (x, y) screen coordinates
    button is a mouse button number
    """
    global me
    print position, button
    if button == 3 and me != None:
        print me.x, me.y
        nt_send(cp_direction.data(0))
    pass

# socket http://docs.python.org/lib/socket-objects.html
# struct http://docs.python.org/lib/module-struct.html
# built-ins http://docs.python.org/lib/built-in-funcs.html

# packages the may do network in pygame
# python-poker2d
# http://www.linux-games.com/castle-combat/

# send CP_SOCKET version=4, udp_version=10, socket=20380,
# TODO: send CP_FEATURE
# receive SP_MOTD
# receive SP_YOU
# send C->S CP_LOGIN     query=0, name="guest", password="", login="james",
# receive S->C SP_LOGIN     accept=1, flags=0xAF, keymap=" !"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~",
# S->C SP_YOU
# SP_PLAYER_INFO
# S->C SP_MASK      mask=1,
# C->S CP_OUTFIT    team=0, ship=2,
# S->C SP_PICKOK    state=1,
# ... play ...
# C->S CP_QUIT      no args,

# need sizes of each packet type, make a c program to dump the sizes,
# need structure definitions for each

pygame.init()

size = width, height = 1000, 1000
speed = [2, 2]
black = 0, 0, 0

screen = pygame.display.set_mode(size)
nt_connect(sys.argv[1], 2592)
if sys.argv[2] == 'verbose':
    verbose = 1
nt_send(cp_socket.data())

ball = ic.get("netrek.png")
ballrect = ball.get_rect()
while 1:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            nt_send(cp_bye.data())
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            kb(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mb(event.pos, event.button)

    ballrect = ballrect.move(speed)
    if ballrect.left < 0 or ballrect.right > width:
        speed[0] = -speed[0]
    if ballrect.top < 0 or ballrect.bottom > height:
        speed[1] = -speed[1]

    screen.fill(black)
    nt_recv()
    galaxy.draw()
#    screen.blit(ball, ballrect)
    pygame.display.flip()
    
