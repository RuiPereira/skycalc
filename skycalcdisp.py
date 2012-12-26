#!/usr/bin/env python

# Oh, this is sneaky -- this one can pop a window linking to my
# very own annotated DScat ... 

# skycalcgui.py - a GUI version of skycalc which can display
# a map of the sky built with PGPLOT graphics. 
#
# copyright John Thorstensen, Dartmouth College, 2005 January.
# 
# Anyone may use this program for non-commercial purposes, 
# and copy it and alter it as they like,  but this banner must 
# be preserved, and my name must be preserved in window titles,
# i.e. proper credit must be given. 

BRIGHTSTARFILE = "/usr/local/share/skycalc/brightest.dat"

ppgplot_failure_msg = """Sorry, skycalcdisp.py isn't going to run.

It was unable to import the ppgplot and/or numarray modules.
These must be installed and accessible in order for the display to
run.  The non-display version, skycalcgui.py,  doesn't use these 
two modules, and may work.

Depending on how ppgplot was compiled, it may be possible to 
run this by changing the "from numarray import *" to "from
Numeric import *".  It's worth a try, anyway.

The program will now stop.
"""

import sys
import string
import _skysub
from cooclasses import *
try :
   from ppgplot import *
   from numarray import *
except :
   print ppgplot_failure_msg
   sys.exit()
from Tkinter import *
from tkFileDialog import askopenfilename
from copy import deepcopy 

# from pyraf import iraf  # this breaks the connection between the main
			# window and its variables.  Too bad!
# from iraf import imred,specred,splot
import os

# Graphics section .... needs to be included to get all those
# global classes into the namespace.

def skyproject(ha,dec,lat) :

# does tan z/2 projection. 
# ha -> hrs, dec, lat -> deg
# returns x, y for plot.

   alt = _skysub.altit(dec,ha,lat)
   coalt = (90 - alt[0]) / _skysub.DEG_IN_RADIAN
   r = tan(coalt/2.)
   az = alt[1] / _skysub.DEG_IN_RADIAN
   y = r * cos(az)
   x = r * sin(az)
   if lat > 0. :
     return [x,y]
   else :
     return [-1.*x,-1.*y]   # reverse in south.

# bright = []   # define this globally to avoid reading it over and
              # over.
def readbright() :

   brlist = []
   inf = open(BRIGHTSTARFILE,"r")
   for l in inf.readlines() :
      x = string.split(l)
      ra = float(x[0])
      dec = float(x[1])
      mag = float(x[2])
      name = l[27:37]
      brlist = brlist + [[name,ra,dec,mag]]
   return brlist

bright = readbright() # execute it.

def plotstars(bright,location,sidt) :
 
# Given a previously created plot for location and JD, plots the
# bright stars, which are handed in as name, ra, and dec.

   starx = []
   stary = []    # to hand back for a cursor find ...
   for o in bright :
      ha = sidt - o[1]
      xy = skyproject(ha,o[2],location[1])
      starx = starx + [xy[0]]
      stary = stary + [xy[1]]
      size = 0.1 + 0.3 * (4.5 - o[3])
      pgsch(size)
      pgpt(array([xy[0]]),array([xy[1]]),17)
   pgsch(1.)
   return [starx,stary]

def findnearest(x,y,xar,yar) :
    # routine finds nearest star to given coords
    # doesn't rescale axes, so not perfect.
    # Sure is easy to code in Python ...
    dists = []
    if len(xar) == 0 :
       print "Can't find nearest -- empty list!"
       return None
    for i in range(0,len(xar)) :
        dists = dists + [sqrt((xar[i] - x)**2 + (yar[i] - y)**2)]
    dmin = min(dists)
    return dists.index(dmin)

def drawclock(time,x,y,radius,zabr,dst_inuse) :

# uses pgplot to draw a little clock face for time in decimal
# hours.  Clock is centered at x, y, with radius. 
# For application here, x-axis parity is assumed reversed, i.e.
# large x to left.  High y is assumed to be up.

   while time < 0. :
      time = time + 24.
   while time > 24. :
      time = time - 24.

   if time >= 12. :
      pm = 1
   else :
      pm = 0
   while time > 12. :
      time = time - 12.
   
   circx = []
   circy = []
   for t in arange(0.,60.0001,2.) :
      circx = circx + [-1. * sin(t / _skysub.TWOPI)]
      circy = circy + [cos(t/_skysub.TWOPI)]

   circx = array(circx) * radius
   circy = array(circy) * radius
  
   circx = circx + x
   circy = circy + y

   pgline(circx,circy)

   hhandx = -0.55 * radius * sin((time / 12.) * _skysub.TWOPI)
   hhandy = 0.55 * radius * cos((time / 12.) * _skysub.TWOPI)

   min = 60. * (time - int(time))
#   print "min = %f" % min
   mhandx = -0.85 * radius * sin((min / 60.) * _skysub.TWOPI)
   mhandy = 0.85 * radius * cos((min / 60.) * _skysub.TWOPI)

   pgmove(x,y)
   pgslw(3)
   pgdraw(x + hhandx, y + hhandy)
   pgslw(1)
   pgmove(x,y)
   pgdraw(x + mhandx, y + mhandy)
   pgline(circx,circy)

   for i in range(0,12) :
     ang = _skysub.TWOPI * (i / 12.)
     sa = sin(ang)
     ca = cos(ang)
     pgmove(x + -0.91 * radius * sa, y + 0.91 * radius * ca)
     pgdraw(x + -1. * radius * sa, y + radius * ca)

   # make description string for label
   if dst_inuse  == 1 :
       decstr = zabr + "DT "
   else :
       decstr = zabr + "ST "
   if pm == 0 :
       decstr = decstr + "AM"
   else :
       decstr = decstr + "PM"
   pgptxt(x,y-1.35 * radius,0.,0.5,decstr)

def mooncirc(jd,lat,longit) :

# computes topocentric ra, dec, illumination angle, and PA of 
# the cusps of the moon's illumination.

   sidt = _skysub.lst(jd,longit)
   moonpos = _skysub.lpmoon(jd,lat,sidt)
#   print "moon: ",
#   print moonpos
   sunpos = _skysub.lpsun(jd)
#   print " sun: ",
#   print sunpos
   codecsun = (90. - sunpos[1]) / _skysub.DEG_IN_RADIAN
   codecmoon = (90. - moonpos[1]) / _skysub.DEG_IN_RADIAN
   dra = sunpos[0] - moonpos[0]
   while dra < -12. :
     dra = dra + 24.
   while dra > 12. :
     dra = dra - 24.
   dra = dra / _skysub.HRS_IN_RADIAN

   # Spherical law of cosines gives moon-sun separation
   moonsun = arccos(cos(codecsun) * cos(codecmoon) + 
       sin(codecsun) * sin(codecmoon) * cos(dra))
   # spherical law of sines + law of cosines needed to get
   # sine and cosine of pa separately; this gets quadrant etc.!
   pasin = sin(dra) * sin(codecsun) / sin(moonsun)
   pacos = (cos(codecsun) - cos(codecmoon) * cos(moonsun)) / \
      (sin(codecmoon) * sin(moonsun))
   pa = arctan2(pasin,pacos)

#   print "pa of arc from moon to sun is %5.2f deg." % (pa * _skysub.DEG_IN_RADIAN)

   cusppa = pa - _skysub.PI/2.  # line of cusps ... 

   luna = _skysub.lun_age(jd)
   jdfull = _skysub.flmoon(luna[1],2)  # jd of full on this lunation
#   print "lunation %d, jdfull %f" % (luna[1],jdfull)
#   print "moonsun before ... %f, lunar age %f" % (moonsun,luna[0])
   if jd > jdfull :
      moonsun = moonsun * -1.
   
#   print "moonsun after %6.2f, cusp pa %5.1f" % \
#      (moonsun * _skysub.DEG_IN_RADIAN, cusppa * _skysub.DEG_IN_RADIAN) 
   return [moonpos[0],moonpos[1],moonsun,cusppa,pa]
 #  print "moonsun %6.2f deg, pa of arc from moon to sun = %6.2f\n" % \
 #     (moonsun * _skysub.DEG_IN_RADIAN, pa * DEG_IN_RADIAN)

def roughradectoxy(racent,deccent,x,y,scale) :
 # takes a central ra and dec, and a set of x y offsets along
 # ra and dec respectively, together with a scale factor (how many 
 # degrees to a unit), and delivers a list of ra and decs corresponding
 # to x and y.  Uses crude "graph paper" approximation, not tangent plane.

  cosdec = cos(deccent / _skysub.DEG_IN_RADIAN) 
  raout = []
  decout = []
  for i in range(0,len(x)) :
    raout = raout + [racent + scale * x[i] / (15. * cosdec)]
    decout = decout + [deccent + scale * y[i]]
  
  return [raout,decout]
   
def moonedges(jd, lat, longit) :
  
 # delivers a list of two lists -- one is ra,decs of a set of points on the
 # illuminated lunar limb, the other is the ra, decs of a set of points on 
 # the terminator. 
# revision uses a different approach -- compute
# the limb and terminator in a system which is aligned with the
# line of cusps, and then rotate the resulting arrays into 
# position using matrix multiplication.  Much cleaner.  


   mooninfo = mooncirc(jd,lat,longit) 
   
#   pgbeg("/xterm")
#   pgsvp(0.1,0.9,0.1,0.9)
#   pgwnad(1.,-1.,-1.,1.)
   
   moonsun = mooninfo[2]
   while moonsun < 0. :
      moonsun = moonsun + _skysub.TWOPI
#   print "moonsun = %f" % moonsun

   limbx = []
   limby = []
   termx = []
   termy = []
   
   drange = _skysub.PI / 10.  
   for p in arange(0.,_skysub.PI+0.001,drange) :
      # set up limb and terminator with x-axis along cusp line,
      # limb of moon in top half-plane
      limbx = limbx + [cos(p)]
      limby = limby + [sin(p)]
      termx = termx + [cos(p)]  # need a 2nd copy later
      termy = termy + [sin(p) * cos(moonsun)]
      # cos(moonsun) takes care of phase angle 
   
   pa = mooninfo[4]  # pa from moon to sun 
#   print "moonsun %f = %f deg" % (moonsun, moonsun * _skysub.DEG_IN_RADIAN)
#   print "pa = %f = %f deg" % (pa, pa * _skysub.DEG_IN_RADIAN)
   turnmoon = array([[cos(pa),sin(pa)],[-1. * sin(pa),cos(pa)]])
   # rotation matrix to turn moon to appropriate pa

   limb = array([limbx,limby])
   # this is easy!  Just lay the x and y on top of each other in a 
   # matrix, and ... 

   # multiply them and 
   limb = matrixmultiply(turnmoon, limb)
   # strip out the x and y as separate arrays and 
   limbx = limb[0]
   limby = limb[1]

   # do the same for the terminator, and finally 
   term = array([termx,termy])
   term = matrixmultiply(turnmoon,term)
   termx = term[0]
   termy = term[1]

   # Now, how large to draw the moon symbol?  Unfortunately,
   # scaling this with zenith distance requires us to know the 
   # zenith dist of the moon right here ... 

   coszover2 = cos((90. - obs.altmoon) / (2. * _skysub.DEG_IN_RADIAN))
   moonscale = 3. * coszover2
#   print "scale ... %f" % moonscale
   
   limbradec = roughradectoxy(mooninfo[0],mooninfo[1],limbx,limby,moonscale)
   termradec = roughradectoxy(mooninfo[0],mooninfo[1],termx,termy,moonscale)
#   print "limbx" 
#   print limbx
#   print "limby" 
#   print limby
#   print "termx"
#   print termx
#   print "termy"
#   print termy
#
#   print "limbradec:"
#   print limbradec
#   print "termradec:"
#   print termradec

#   hamoon = sidt - mooninfo[0]
   xlimb = []
   ylimb = []
   xterm = []  # x of terminator, not the computer terminal type!
   yterm = [] 
  
   for i in range(0,len(limbradec[0])) :
      ha = obs.sidereal.val - limbradec[0][i]
      xy = skyproject(ha,limbradec[1][i],lat) 
      xlimb = xlimb + [xy[0]]
      ylimb = ylimb + [xy[1]]
   for i in range(0,len(termradec[0])) :
      ha = obs.sidereal.val - termradec[0][i]
      xy = skyproject(ha,termradec[1][i],lat) 
      xterm = xterm + [xy[0]]
      yterm = yterm + [xy[1]]

   return [xlimb,ylimb,xterm,yterm]

def has_index(item,list) :  # Python doesn't have this obvious function.
   try :
      n = list.index(item)
      return 1
   except ValueError : 
      return 0 

def planetmags(jd) :

# **** NOTE NOTE NOTE **** comp_el(jd) must be called before this
# routine.

# returns the magnitudes of the planets in a list;
# [merc,venus,earth,mars,jupiter,saturn]
# Does position calculations in ecliptic, since only
# relative positions matter.  Somewhat approximate.

   earthxyz = array(_skysub.planetxyz(3,jd))
#   print "earthxyz:",earthxyz

   V0 = [None,-0.42,-4.40,-3.86,-1.52,-9.40,-9.22,-7.19,-6.87,-1.0]
   # From Astronomical Almanac, 2003, p. E88.  V mag of planet when
   # full face on at unit distance from both sun and earth.  Saturn
   # has been goosed up a bit b/c Almanac quantity didn't have rings
   # in it ... 

   mags = [None]  # leave a blank at zeroth index

   for i in range(1,10) :
      if i != 3 :   # skip the earth
         xyz = array(_skysub.planetxyz(i,jd))
         xyzmodulus = sqrt(dot(xyz,xyz))
         pl2earth = earthxyz - xyz
         pl2earthmodulus = sqrt(dot(pl2earth,pl2earth))
         xyznegnorm = -1. * xyz / xyzmodulus
         pl2earthnorm = pl2earth / pl2earthmodulus
         phasefac =  0.5 * (dot(xyznegnorm,pl2earthnorm) + 1.)
         # we want the cosine of the phase ultimately, and the dot gives it...
         # actually, 1/2 of cosine phase plus one.  This is simply the
         # illuminated fraction, nothing more elaborate.
         mag = V0[i] + 2.5*log10(phasefac) + 5*log10(xyzmodulus*pl2earthmodulus)
         mags = mags + [mag]
      else :
         mags = mags + [None]   # not doing earth.    
     
   return mags 
         
def computeplanets_mag(jd,longit,lat,doprint = 0) :

   label = [None,'Mercury','Venus',None,'Mars','Jupiter','Saturn',
        'Uranus','Neptune','Pluto']
   _skysub.comp_el(jd)
   if doprint == 1 :
      print "Planets for ",
      print_all(jd)
      print "UT."
   mags = planetmags(jd) 
   planetpos = py_get_planets(jd,longit,lat,doprint) 
   planets = [None]  # blank for position zero
   for i in range(1,10) :
      if i != 3 :
         planets = planets + [[label[i],planetpos[i][0],planetpos[i][1],mags[i]]]
      else :
         planets = planets + [None]
   return planets
     
def plotplanets(planets,location,sidt) :

   planx = []
   plany = []    # to hand back for a cursor find ...
   pgsci(7)   # yellow
   for i in range(1,7) :
      if i != 3 :
         o = planets[i]
         ha = sidt - o[1]
         xy = skyproject(ha,o[2],location[1])
         planx = planx + [xy[0]]
         plany = plany + [xy[1]]
         size = 0.1 + 0.3 * (4.5 - o[3])
         pgsch(size)
         pgpt(array([xy[0]]),array([xy[1]]),17)
         pgsch(0.8)
         pgptxt(xy[0]+0.03,xy[1]+0.01,0,0.5,o[0])
   pgsch(1.)
   pgsci(1)   # white
   return [planx,plany]

def localtime(jd,stdz,use_dst) :

# does what it says, returns zone time in hours.
   date = _skysub.new_date_time()
   dow = _skysub.caldat(jd,date)
   yr = _skysub.date_time_y_get(date)
   jdbe = _skysub.find_dst_bounds(yr,stdz,use_dst)
#   print "jdbe: ",jdbe
   z = _skysub.zone(use_dst,stdz,jd,jdbe[0],jdbe[1])
#   print "z = ",z
   if z == stdz :
      dst_in_use = 0
   else :
      dst_in_use = 1
#   print "dst in use: ",dst_in_use
   jdloc = jd - z / 24.
#   print "jd ",jd," jdloc ",jdloc
   dow = _skysub.caldat(jdloc,date)
   time = _skysub.date_time_h_get(date) + _skysub.date_time_mn_get(date) / 60. + \
      _skysub.date_time_s_get(date) / 3600.
#   print "returning local time ",time
   return [time,dst_in_use]

def twilightcolor(altsun, ztwilight)  :

   # pgscr(0,R,G,B) sets background color for plot -- use it
   # to indicate twilight.   Routine hands back a tuple of 
   # (R,G,B) normalized 0 to 1.
   # The formulae below give a little step at 18 degree twilight,
   # followed by a steep ramp to 5 mag of twilight, followed by a
   # gentler ramp up to full daylight.

   if altsun < -18. :  # total darkness
      return (0.,0.,0.)  # black
   if altsun > -0.8 :  # sun is UP
      return (0.24, 0.48, 0.55)   # bluish.
   if ztwilight > 5. :
      fac = (ztwilight - 5) / 10.
      return (0.2 + fac * 0.04 ,0.27 + fac * .21, 0.44 + fac * 0.11)
   else :
      fac = (ztwilight+4) / 9. 
      return (0.20 * fac, 0.27 * fac, 0.44 * fac)
   
 
def plotsky(plotter, buttonpush = 0) :

# if buttonpush is 1, and the plotter is off, it opens;
# if buttonpush is 1, and the plotter is on, it closes.

   date = _skysub.new_date_time()  # used for some stuff
 
   planets = computeplanets_mag(obs.jd,obs.longit,obs.lat,0)  
   if pgqinf('state') == 'CLOSED' :
       pgbeg(plotter) 
       pgask(1)
       pgscr(0,0.,0.,0.)  # force a black border ... 
       pgeras()           # key is to pgscr and then erase.
   elif buttonpush == 1 :  # toggle to off
       pgask(0)
       pgend()
       return

   #(rback,gback,bback) = twilightcolor(obs.altsun,obs.ztwilight)
   #pgscr(0.,rback,gback,bback)

   pgsvp(0.00,1.00,0.00,1.00)

   asp = 1.30
#   pgsclp(0)
   ymin = -0.8
   ymax = 0.8
   xmin = ymin * asp  # horizontal rectangle
   xmax = ymax * asp 
   xcen = 0.
   ycen = 0.
   pgwnad(xmax,xmin,ymin,ymax)
       # don't need the whole sky

   x = arange(0.,2.*_skysub.PI+0.05,0.05)
   circx = sin(x)
   circy = cos(x)
   halfwid = (ymax - ymin) / 2.
   pgwnad(xmax,xmin,ymin,ymax)

   (rback,gback,bback) = twilightcolor(obs.altsun,obs.ztwilight)
   pgscr(0.,rback,gback,bback)

   if plotter == "/xterm" :
      pgpage()
   elif plotter == "/xwin" :
      pgeras()


   # location[2] = stdz, location[3] = use_dst
#      print "jd passed to localtime -> ",
#      print_all(jd)
#      print ""
   localt = localtime(obs.jd, obs.stdz, obs.use_dst)
#      print "localtime returns ", localt
   pgsci(5)
   drawclock(localt[0],xcen - 1.1 * halfwid, 
		ycen + 0.8125 * halfwid, 0.15 * halfwid,obs.zone_abbrev,localt[1])
   # location[8] is zabr, localt[1] is 1/0 for dst.
   pgsci(2)
   pgscr(18,0.6,0.0,0.)  # dark red circles to avoid busy-ness
   pgsci(18)
   if halfwid > 0.5 :  # Don't try to put direction labels on zooms ... yet
      pgsch(2)
      if obs.lat > 0. :
         toptext = 'N'
         bottext = 'S'
         lefttext = 'E'
         rightext = 'W'
      else :
         toptext = 'S'
         bottext = 'N'
         lefttext = 'W'
         rightext = 'E'
      pgptxt(xcen,ycen - 0.98 * halfwid,0.,0.5,bottext)
      pgptxt(xcen,ycen + 0.94 * halfwid,0.,0.5,toptext)
      pgptxt(xcen + 1.2 * halfwid,ycen,0.,0.5,lefttext)
      pgptxt(xcen - 1.2 * halfwid,ycen,0.,0.5,rightext)
   pgsch(1)
   pgline(circx,circy)
   pgline(circx,circy)
   pgsls(4)
   pgline(0.57735 * circx, 0.57735 * circy)  # 2 airmasses
   pgline(0.70711 * circx, 0.70711 * circy)  # 3 airmasses
   pgline(0.7746 * circx, 0.7746 * circy)    # 4 airmasses (sec z actually) 
  # pgsls(4)
   pgsls(1)

   for h in arange(-6.,6.5,2.) :  # hour angle marks 
      xarr = []
      yarr = []
      for d in arange(90.,-90.1,-5.) : # every 5 deg in dec
         alt = _skysub.altit(d,h,obs.lat)  # clip it ...
         if alt[0] > 0. :
            xy = skyproject(h,d,obs.lat)
            xarr = xarr + [xy[0]]
            yarr = yarr + [xy[1]]
      pgline(array(xarr),array(yarr))
   
   xarr = []    # plot equator  
   yarr = []
   for h in arange(-6.,6.01,0.5) : 
      xy = skyproject(h,0.,obs.lat)
      xarr = xarr + [xy[0]]
      yarr = yarr + [xy[1]]
   pgline(array(xarr),array(yarr))
   pgsls(1)
  
   pgsci(3)

   xobj = []
   yobj = []

   sidt = obs.sidereal.val    # just for shorthand 

   pgsch(0.8)
   for o in objs2000.keys() :
      ha = sidt - objs2000[o][0]
      xy = skyproject(ha,objs2000[o][1],obs.lat)
      xobj = xobj + [xy[0]]
      yobj = yobj + [xy[1]]
      pgptxt(xy[0],xy[1],0.,0.5,o)
   pgsch(1.)
   pgsci(1)

#  bright = readbright()   # now done globally 
   starxy = plotstars(bright,[obs.longit,obs.lat],sidt)
   planxy = plotplanets(planets,[obs.longit,obs.lat],sidt)

# draw in an actual moon!
   stuff = moonedges(obs.jd,obs.lat,obs.longit)
   pgsci(7)
   pgline(array(stuff[0]),array(stuff[1]))
   pgline(array(stuff[2]),array(stuff[3]))
   pgsci(1)

   xysun = skyproject(obs.hasun.val,obs.SunCoords.dec.val,obs.lat)

   # put day, twilight, time orientation under clock.
   if obs.altsun > -0.8 :
      statstring = "DAYTIME"
   elif obs.altsun > -18. :
      statstring = "TWILIGHT"
   else :
      statstring = "NIGHTTIME"
   pgsci(5)
   pgptxt(xcen - 1.1*halfwid, ycen + 0.55*halfwid,0.,0.5,statstring)
#   locald = localdatestr(obs.jd,obs.longit,obs)
   locald = obs.calstring(stdz = obs.stdz,
	use_dst = obs.use_dst, style = 1, \
	print_day = 1, daycomma = 0, dayabbrev = 1)
   pgptxt(xcen - 1.2*halfwid,ycen - 0.9*halfwid,0.,1.0,locald)
   pgptxt(xcen - 1.2*halfwid,ycen - 0.95 * halfwid,0.,1.0,obs.obs_name)
   pgsci(1)
   
   # plot the sun
   pgsch(2.0)
   pgsci(7)  # yellow
   pgpt(array([xysun[0]]),array([xysun[1]]),9)
   pgsci(1)
   pgsch(1.)

   # plot the current position - in blue.
   pgsch(4.0)
   pgsci(11)
   xy = skyproject(obs.hanow.val,obs.CoordsOfDate.dec.val,obs.lat)
   pgpt(array([xy[0]]),array([xy[1]]))
   pgsch(1.0)
   pgsci(1)

#### END end End of Graphics graphics GRAPHICS section #####

infields = ('objname','RA','dec','equinox','date','time','Time is:',\
   'timestep','obs_name','longit','lat', \
	'stdz', 'use_dst', 'zone_name', 'zone_abbrev',  \
         'elevsea','elevhoriz', 'siteabbrev')

# 0 = objname,
# 1 = RA; 2 = dec; 3 = equinox; date = 4, time = 5, 
# Time is: = 6, timestep = 7,
# 8 = obs_name, 9 = longit, 10 = lat, 11 = stdz, 12 = use_dst, 
# 13 = zone_name, 14 = zone_abbrev, 
# 15 = elevsea, 16 = elevhoriz, 17 = siteabbrev

# These are all in text-entry widgets EXCEPT: 
#  - 'Time is:' is controlled by a radio button
#  - site_abbrev is controlled by a separate radio-button panel

outfields = ('sidereal','ha','airmass','alt_az','parallactic','jd', \
	'sunradec','sunaltaz','ztwilight','moonphase','moonradec','moonaltaz', \
        'illumfrac','lunsky','moon-obj ang.','baryjd','baryvcor','constel',
	'planet_proxim')

# 0 = sidereal; 1 = ha; 2 = airmass; 3 = alt_az; 4 = parallactic; 
# 5 = jd; 6 = sunradec; 7 = sunaltaz; 8 = ztwilight; 
# 9 = moonphase; 10 = moonradec; 11 = moonaltaz; 12 = illumfrac; 
# 13 = lunsky; 14 = moon-obj angle; 15 = baryjd; 16 = baryvcor
# 17 = constel; 18 = planet proximity flag

almfields = ('Sunset','Twilight Ends','Night center','Twilight Begins','Sunrise',\
		'Moon:','Moon:')

# 0 = sunset, 1 = eve twi, 3 = night center, 4 = morn. twilight, 5 = sunrise,
# 6, 7 = moon rise and/or set in time order.

coofields = ('Current RA:','Current dec:','equinox:',
  'Proper motion','PM is:','input epoch','RA (pm only)',
  'Dec (pm only)','equinox:',
  'Ecliptic latitude','Ecliptic longitude','Galactic latitude',
  'Galactic longitude','parallax factors') 

# 0, 1, 2 -> Current RA, dec, and equinox
# 3 -> proper motion (two fields)
# 4 -> 1 = proper motion is dX/dt, 0 = proper motion is dalpha/dt
# 5 -> actual epoch of input coords
# 6, 7, 8 -> PM adjusted RA, and dec, and input equinox repeated
# 9, 10 -> ecliptic latitude and longitude
# 11, 12 -> Galactic latitude and longitude
# 13 -> parallax factors in X and Y

helptext = """ 

GENERAL

This program computes astronomical circumstances, given
the target's celestial location, the date and time, and
the site parameters.  The graphical user interface (GUI) 
is a front end for routines taken from the text-based
'skycalc' program.  The program is intended for users
who are familiar with the concepts involved; it is 
not intended as a tutorial on time-and-the-sky. 

Most input parameters are read from the fields in the 
left-hand column of the main window.  Parameters which
can be straightforwardly used as input are rendered in 
white.  All the output parameters are refreshed whenever 
a calculation is made. 

At startup, the program sets the input date and time using
the computer's clock, and sets the coordinates to the
zenith at the default site (presently Kitt Peak).

MAKING COMPUTATION HAPPEN

You can refresh all the output fields by:

(a) Typing a carriage return in an input field;
(b) Stepping the time forward or backward with
   the left and right arrow keys (or a carriage
   return in the "timestep" field;
(c) Pressing 'Refresh output', 'Set to now', 
   or 'UT <-> Local'.  This last converts the 
   input time format but leaves the time unchanged;
(d) Selecting a new object from the (optional) target
   list menu;
(e) Selecting a new site from the site menu.

SPECIFYING A SITE

The site menu has parameters for several major
observatories.  But note:

- If you want a site NOT on the menu, you must first 
  select "Other (allow user entries)" on the site menu.
  Otherwise, the site parameters are overwritten when you 
  refresh.  Site parameters are rendered with a slight
  pink tinge to draw attention to this distinction.

  Once you've done this, simply enter your site's
  parameters.  NOTE: the longitude units default to HMS 
  positive westward, which is NOT STANDARD.  You can
  specify units and direction explicitly, for example 
  "-111 36.9 d e" will enter Kitt Peak's longitude 
  in the form used in the "Astronomical Almanac".

LOADING TARGETS BY NAME FROM A LIST

It can be very handy to select objects by name from an 
(optional) object list.  To do this, prepare a file with 
one object per line in this form:

  name_no_blanks  rahh mm ss  decdd mm ss  equinox

for example,

  4U2129+47  21 29 36.2  47 04 08  1950

The 'read object list' button will pop up the list. 
Select the object by double-clicking on its name.
The "dismiss" button clears the list and destroys
the window.  You can load multiple target lists;
dismissing a list dismisses only the objects on that
list.  Overlapping names are checked for and handled.

WHAT'S WITH THE COLORS?

Data fields which can be used for input are rendered
in off-white.  Pale pink is for site parameters, which 
can be adjusted when the site menu enables it.

Other than that, color is used to draw attention to 
various conditions:

- yellow, orange, red : these indicate increasingly 
        problematic conditions (twilight, hour angle, 
        airmass, or proximity to the moon).  The Reference 
        Manual gives details.  For the moon, these colors are 
	used when the moon is < 25 degrees from the
	input position (i.e., it means the moon's proximity 
	may be a problem).

- Light blue means daylight for the sun.  For the moon it
	signals that the moonlight prediction is between non-
        negligible and fairly strong.  It is only used when the 
    	moon is more than 25 degrees from the object.

- Light purple is used to flag quite bright moonlight (more
	than 19.5 V mag per square arcsec) at angles more than 
	25 degrees from the moon.

The reason for not using yellow, orange, and red in 
these moonlit conditions is to reserve these colors for
when the moon is close to the object -- easy to overlook
in planning.  Since the sky is always bright around full moon, 
using red for the ordinary bright sky would be "crying wolf".


STUFF TO KEEP IN MIND:

- If a window has a "Hide" button, use it when you want 
  to close the window.  Windows with "Hide" buttons have 
  processes which are always running, and killing the window 
  destroys the process.

- For most windows, if they get "buried alive" behind 
  another window, clicking their button on the main window 
  will raise them.  Exceptions are object lists and text 
  output windows, for which you can have more than one at 
  a time.

- The Hourly Airmass window has a "Dump to file" button, 
  which appends a text version of the information to a 
  text file called "skycalc.out".  The file will appear
  in whatever directory the program started in, probably
  your top directory if you launched with a pull-down menu.  

- The "Step time" button advances the input time by the
  "timestep" parameter and refreshes the output.  Left 
  and Right arrow keys typed anywhere in the main window
  move the time backward and forward.  Typing a carriage
  return into the "timestep" field also advances the time.

  A variety of units are recognized for the timestep:

	5 s    - 5 seconds
	10 m   - 10 minutes  [minutes are the default]
	1.5 h  - an hour and a half
	2 d    - 2 days
	1 t    - 1 sidereal day, think "transit" for mnemonic
	2 w    - 2 weeks
	1 l    - one lunation (mean synodic month).  This is 
              useful for examining conditions at e.g. successive
	      new moon dates.  The jump is 29.53 days.

- The "Time is: UT  Local" radiobuttons affect how the 
  input time is interpreted when the computation is done.
  Switching this doesn't have any effect until the output is
  refreshed.  Switching this and refreshing will change the
  output values, unless UT and local time are identical.

  The "UT <-> local" button, by contrast, converts the 
  input time fields to the SAME time in the other system 
  (and switches the radiobutton so the change will stick).  
  The output is refreshed, but nothing should change (except 
  for tiny roundoff effects, e.g. azimuth at zenith).

- The "objname" field is updated when an object is loaded
  from the menu, or you can change it by hand.  It is not
  changed automatically when you change the RA and dec;
  in that case it's up to you to change it.  If you do have
  an object list loaded, you can enter an object's name
  in this field to load its coordinates if it's easier than
  finding it on the list and double-clicking.  

- You can input RA, dec, etc. with or without colons (":")
  separating the field, or as decimal hours or degrees.
  If there are two or more fields the input is interepreted 
  as sexigesimal (i.e., 60-based like HH MM SS).   If you 
  enter a negative dec, you must not leave any space between 
  the minus sign and the first digit of the degrees.
  You can enter RA as degrees, minutes, and seconds, or as
  decimal degrees, if you put a "d" at the end, separated by
  a space, e.g. "275.3828 d" or "275 22 58 d".

- Entering a jd in the "jd" field and hitting return will
  set the time to agree with the entered JD.  This is a 
  rare exception to the distinction between input and 
  output variables.  The field is whitened for this reason.

OTHER WINDOWS ...

- The "Nightly almanac" window displays times of sunrise
  and -set, twilight, and moonrise and set.

- The "Alt. Coords" window displays current coords and 
  optionally computes a proper motion correction.  See
  the reference manual for details.

- The 'Planets' window gives low-precision planetary positions.

- The Planetarium display (toggled on and off with the 
  Planetarium button) generates a map of the sky.

- The 'Text Tasks' window handles several calculations which
  can produce tables, including seasonal observability and
  generating ephemerides for periodic phenomena (e.g. binary
  star eclipses).

MORE INFORMATION

If you want more detail, pop up the Reference Manual
window.  It has detailed descriptions of the various
fields, explains the warning color scheme, and so on.
There is also a cursory HTML manual, and a very detailed
manual for the text-based skycalc program, which shares 
much code with this version.

OTHER FORMS OF THIS PROGRAM

This program encapsulates some of the most widely-used 
functionality of the text-based "skycalc" program.  Many 
features have been left out; if you need some other 
time-and-the-sky calculation, it may be in skycalc.

LEGALITIES. 

This program is copyright 2005, by the author, John 
Thorstensen (Dartmouth College).  Permission is hereby 
granted for all non-profit use, especially educational 
and scientific users.  I do ask that my credit line
remain prominently displayed.

Portions of the interface code are adapted from 
"Programming Python" by Mark Lutz (O'Reilly).

There are no warranties of any kind.

John Thorstensen, Dartmouth College

john dot thorstensen at dartmouth dot edu

"""

referenceman = """

---- REFERENCE MANUAL ----

ALL THE FIELDS:

--- INPUT VARIABLES ---

objname - Used to label text-file output and for the 
  user's benifit.  Loads automatically when objects are 
  double-clicked on the object list, or can be set by 
  hand.  When an object list has been loaded, you can 
  fetch an object's coordinates by entering its name here 
  with a carriage return; if the object isn't on the list, a
  "NOT FOUND" will appear in the objname field.

RA - Right ascension, defaults to hours, minutes, and
  seconds.  Fields can be delineated by spaces or colons.
  You can also enter plain decimal hours.  If there are
  two fields or more, it is interpreted as HH:MM:SS.
  You can enter RA in degrees if you put a " d" (space
  and d) at the end of the input, e.g. "275.3828 d" or
  "275 22 58.1 d"

dec - Declination, generally in degrees, minutes, and
  seconds separated by colons or spaces.  The same input
  apply as for RA.  For negative declinations there cannot
  be any space between the negative sign and the first 
  digit of the degrees.

equinox - The equinox (often incorrectly called "epoch")
  of the input coordinates, in decimal years.  One special
  hook -- if you enter "date", the equinox is forced to
  agree with the date and time (will change the direction
  of the input coordinates, unless they're already in the
  equinox of date).  This feature enables a 
  backdoor computation of the Julian epoch (which is
  2000.0 + the number of 365.25 day intervals since
  J2000 = JD 2451545.0).

date - The input date as year, month, day.  The day of
  the week is not used on input, but when a refresh happens
  it is forced to agree with the year, month, and day.
  The month can be specified as e.g. "Apr", "April", or
  "4".  Dates outside of the range 1901 to 2099 are rejected.

time - The time in hours, minutes, and seconds.  The same
  formats are acceptable here as for RA and dec, e.g.
  17 32 33, 17:32:33, 17.53, 17:32, and so on.  However,
  entering e.g. "3.25" for 3:15  will truncate to 
  "3 00 00".  

  NOTE ON DAYLIGHT SAVINGS TIME:  If the "use_dst" flag 
  lower down is not zero, local time will be interpreted
  as daylight savings when it is in effect.  See the 
  notes on the "use_dst" flag below.

Time is: - A button which controls whether the input time
  will be interpreted as local time or UT.  Changing this
  does not cause a refresh.  Use the control button 
  "UT <-> local" to convert the time and switch the input 
  values to specify the same actual time in the other system.

timestep - How far to step the time when the "Step the time"
  button is pressed, a right- or left-arrow key is pressed, 
  or when a carriage return is typed in this particular input 
  field.  Note that typing a left-arrow key will step the 
  time backward, and a right-arrow key will step the time 
  forward.

  Default units are minutes.  You can specify the unit by 
  leaving a space and entering the unit explicitly, e.g. 
  "1.5 h".  The units recognized are:
  
	s  seconds
	m  minutes
	h  hours 
	d  days
	t  sidereal days (mnemonic: successive Transits).
	w  weeks
	l  lunations (29.5307 d)
 
  Only the first character of the units field is used, and 
  case is ignored.  

  The "lunation" option makes it easy to step through and 
  look at circumstances for a given target on successive
  bright or dark runs on the Hourly Airmass display.

-- SITE PARAMETERS --

Selecting an observatory on the site menu sets the site 
parameters and refreshes the output.  

The site paramters are reloaded from the observatory menu
every time the output is refreshed, UNLESS the last item on 
the menu, "Other", is selected.  If "Other" is selected
the user is free to adjust the values by hand, for example to
compute for a site which isn't on the menu, and the user-
entered values will not immediately be overwritten.  The
parameters are:

obs_name - The name of the observatory, for your information.

longit - The observatory longitude as hours, minutes, and 
  seconds WEST, which are also the default input units.  

  To specify a longitude in another system you need to 
  specify the UNIT (d or h) and the POSITIVE DIRECTION
  (e or w) explicitly, for example as 
	
	-111 37.0  d  e
 
  For -111 degrees, 37.0 minutes east longitude (which is
  Kitt Peak).  The input format is fairly flexible - the
  direction can be left out (defaults to W), decimals
  can be used in any field, colons can be used, and so on.
  If the direction is specified, it must be in the last field.

lat - The latitude in degrees, minutes, and seconds.

stdz - Offset between local standard time and UT, in hours,
  positive westward.  

use_dst - A flag controlling whether daylight savings time
  will be used.  Note that the 1-hour DST offset is applied
  AUTOMATICALLY based on a limited number of prescriptions
  for the dates the time changes.  These  are specified by 
  integer codes:

	0 - Standard time in use all year.
  Positive number codes are used in the northern hemisphere:
	1 - United States convention (last Sunday in April,
		last Sunday
	2 - Spanish convention.
  Negative number codes are used for the southern hemisphere:
       -1 - Chilean convention
       -2 - Australian convention.

  Around the hour the time switches between daylight and 
  standard, some deeply confusing ambiguities occur.  If this
  is a problem you can always switch to UT input to avoid 
  these issues; alternately, enable site parameter changes
  on the site menu (last button), then manually set 
  use_dst to zero, to force the use of standard time.
  Careful examination of the times in the Hourly Airmass
  table may help clear up confusion.

zone_name - The name of the time zone, for your information 
  only.

zone_abbrev - The 1-character abbreviation, which may be used
  in the future to label output.

elevsea - The elevation of the observatory above sea level,
  in meters.  Used when the spatial location of the 
  site must be known precisely (e.g., lunar parallax).

elevhoriz - The elevation of the observatory above the 
  terrain forming its horizon, in meters.  Used to adjust
  rise and set times for the sun and moon to account for
  the depression of the horizon.

-- OUTPUT VARIABLES ---

These are all refreshed when calculations occur.  
Changing them by hand has no effect.

sidereal -  The local mean sidereal time, in hours,
  minutes, and seconds. 

ha - The hour angle in hours, minutes, and seconds.  This
  is adjusted to be in the range -12 to +12 hours.

airmass - The airmass.  If the zenith distance is less
  than 85 degrees, this is computed from a polynomial
  approximation (it's a real airmass, not secant z).  
  For zenith distance > 85 degrees "> 10" is output,  
  and for zenith distances > 90 degrees this lists 
  "(Down)".  Color is used to alert the user of possibly 
  problematic conditions:
	Yellow - airmass 2 to 3
	Orange - airmass 3 to 4
	Red    - airmass greater than 4, or down.

alt_az - The altitude above the horizon, and the azimuth
  (measured from north through east), in degrees.

parallactic - The parallactic angle (crudely, position
  angle of "straight up"), in degrees.  The 180-degree 
  opposite is also given.  The parallactic angle is 
  important because it is the direction along which
  atmospheric refraction and dispersion act.  See
  A. Filippenko, 1982, PASP, 94, 715 for more detail.

jd - The Julian Day number of the input date and time.

  One can use this as an INPUT field by entering
  a jd and hitting carriage return ("Enter"), which 
  forces the date and time to agree with the given JD.
  Julian dates outside of 1901 to 1899 are rejected,
  because of the calendrical limitations of the program.

  Times and dates are passed internally in the program 
  as JDs.  The numerical resolution of the double-precision 
  floating point value is typically a few milliseconds.

sunradec - The RA and dec of the sun.  The equinox of the
  coordinates is that of the input time.  Accuracy is 
  around 1 arcsecond.  The RA and dec are "topocentric", 
  i.e., corrected for the observer's location with respect
  to the earth's center.

sunaltz - Altitude and azimuth of the sun in degrees.

ztwilight - If during twilight (sun angle between 0 and
  -18 degrees), this field displays a rough estimate of how 
  bright the twilight is at the zenith.  It is 
  approximately how many more magnitudes of surface 
  brightness there are compared to the dark night sky,
  as measured in blue light.  When the sun's altitude is
  outside this range, it displays "No twilight" or "Daytime".

  Color is used for warnings.  Light blue indicates that 
  the sun is up (so the sky is blue).  Different levels of 
  twilight are flagged as follows:
	0 to 4 mag: yellow
	4 to 8 mag: orange
	8 and more: red

moonphase - A verbal description of the moon phase.

moonradec - RA and dec of the moon. The coordinates are 
  in the equinox of the input date.  The coordinates
  do account for the huge horizontal parallax of the moon,
  i.e. you should see the center of the moon if you aim 
  at them.  Accuracy is a few arcseconds.

moonaltaz - Altitude and azimuth of the moon, in degrees.

illumfrac - The fraction of the moon's visible face which is
  illuminated.  If the moon is down, you're informed of this
  here.

lunsky - If the moon and the object are both up and the sun 
  is more than 12 degrees below the horizon, this field gives 
  an estimate of the moon's contribution to the sky brightness 
  at the specified celestial location and time, in V magnitudes 
  per square arcsec.  This is computed using the prescription of 
  Krisciunas and Schaefer, 1991, PASP, 103, 1033.  

  Color is used as follows:
      - If the sun is higher than -12 degrees altitude, the
          field is not colored in, since twilight will usually 
          be a more important consideration.
      - If the position is within 10 degrees of the moon
          the field is colored red.  Even if the moon is not
	  bright this can cause special difficulties because 
          of reflections and so on.
      - If the position is more than 25 degrees from the moon,
 	  the following color scheme is used:
	   - light blue: 19.5 to 21.5 mag per sq. arcsec
	   - light purple : brighter than 19.5 mag per square 
			arcsec.
	   (The blue color appears when the moon roughly doubles
	    the sky brightness).
      - Between 10 and 25 degrees from the moon, warning colors are
          as follows:
             yellow : 19.5 to 21.5  mag per square arcsec
             orange : 18 to 19.5 mag per square arcsec
             red    : Brighter than 18th.
   
     Note that this scheme preserves the yellow-orange-red colors
      to warn of PROXIMITY TO THE MOON, which is easily overlooked
      in planning.  Using the same scheme at greater moon-object
      separations would de-value their alarm value (i.e., it
      would be "crying wolf").  It's always bright at full moon!

moon-obj ang. - Angle subtended by the moon and the object,
  in degrees.  Color is used as above to warn of proximity.

baryjd - The barycentric Julian Day.  This is the time at
  which the light from an event observed in this direction
  and at this time will arrive at the solar system center of
  mass, or barycenter.  The barycenter is always close to the 
  sun, so it's nearly the same as the heliocentric Julian date,
  but the barycenter is a more nearly inertial frame.  Accuracy
  is around 1/10 of a second.  The barycentric time correction
  (i.e., amount added to the JD) is also displayed, in brackets.

baryvcor - The amount to add to an observed radial velocity
  to correct it to the solar system barycenter.  Accuracy is
  around 0.01 km/s.

constel - The constellation of the input coordinates, given by
  the standard 3-letter code.  This is from a prescription  
  invented by Barry Rappaport and Nancy Roman (see Roman,
  1987, PASP, 99, 695) and coded in C by Francois Ochsenbein
  of CDS, Strasbourg and used with his permission.

planet_prox - This item prints the name(s) of any planet(s) 
  within 1 degree of the target.  If there is a planet, the 
  box is colored orange to attract the user's attention.

THE HOURLY AIRMASS WINDOW

This window is popped up on startup, since it is especially 
useful.  It gives the circumstances for the specified oject,
every hour, on the hour, through the night.

If the input time is before noon, data for the previous night
are displayed, and if it is after noon, the next night is
displayed.  The output starts the first hour that the sun is
less than 8 degrees above the horizon, and ends when the sun
rises above 8 degrees, or when all the rows are filled.  
Enough rows are given to accomodate a quite long night.

Columns are as follows:

Local -  Local time and date, using daylight savings if it
  is in effect.

UT    - The universal time, in hours and minutes.  Note that 
  the UT date is not displayed, and may disagree with the local
  date.

LST - The local sidereal time.

HA - The hour angle.  If this is greater than 6 hours, it is
  flagged as orange since some telescope mounts are constrained 
  to less than 6 hours.

Airmass - The airmass.  The warning colors are used the same
  as described earlier.

moonalt - The altitude of the moon.  The warning color scheme
  is the same as described earlier; the proximity to the moon
  and lunar sky brightness are not displayed, but are computed 
  internally and used to set the warning colors.  When the moon 
  is down, dashes are printed and the warning colors are not
  used (the object's position must be above the horizon for the
  lunar sky brightness calculation to be valid).

sunalt - The altitude of the sun.  The warning color scheme
  is the same as described earlier.  When there is no twilight,
  dashes are printed.

Two buttons appear at the bottom of the display:

The "Dump to file" button - This appends a version of the 
  hourly airmass information to a file named 'skycalc.out',
  creating the file if it doesn't exist.  The output is labeled
  with the "objname" field and the coordinates are also
  given.  The file is closed after each "Dump to file" so
  it can be accessed while the sky calculator windows are
  still up.

The "Hide" button hides (withdraws) the window.  NOTE that 
  closing the window with window manager's button may destroy 
  the process, in which case you can't get it back.

THE NIGHTLY ALMANAC WINDOW

This is hidden at startup but can be popped up using a button 
in the main window.

This window displays the time of sunset and sunrise, twilight,
night center, and moon rise and set.  For times before
noon the previous night is displayed, for times after noon
the next night.  

Times are local, and are adjusted for daylight savings if it 
is selected and in effect.  Rising and setting times for the 
sun and moon should apply to the upper limb and are adjusted 
for the horizon depression using the "elevhoriz" parameter.  

Moon rise and set are presented in the order they occur.  
They are only given if they occur within about 12 hours of 
night center.  Dashes may be printed if the time of moonrise
or moonset is around mid-day; the criterion used is 
imperfect so not too much should be read into this.

Note that if daylight savings time is used, there is some
confusion and ambiguity on the night it switches, especially
on the return to standard time (when the local time is
double-valued for an hour).  Correlating the nightly almanac 
with the Hourly Airmass window should clarify ambiguities.

The "Hide" button withdraws the window without destroying
the process; the window can be popped up again with the 
"Show nightly almanac" button.

THE ALT COORDS WINDOW 

This is hidden at startup and popped up by a button if
desired.  It displays several other forms of coordinates
not available in the other windows.  Proper motion can
be applied in this window.  Note, however, that values 
displayed in the other windows aside from this one 
are not updated for proper motion (though they are 
precessed properly); the proper motion corrections
are local to this window only.  The proper motion 
corrections are not fully rigorous and break down 
at the poles.

There are three new INPUT variables in this window:

Proper motion: - Two numbers separated by whitespace 
  giving the proper motion in milliarcsec/yr.  The
  interpretation of these is controlled by the radiobutton
  just below, which is

PM is:  - There are three choices for interpreting the
  pair of proper motion numbers.  

  dX/dt : The first number is the annual eastward proper 
          motion at the object's location - it's how fast 
          an object will appear to move on a set of images.  

  d(alpha)/dt : The first number is the annual change in
          the object's right ascension (thus an object
          near the pole will tend to have a large number 
          in the first field, since a small motion there
          projects to a large arc at the equator).  This 
          is the convention used in the UCAC2.

  (For both of these, the second number is the proper motion 
  in dec, which is uncomplicated.)

  mu/theta : The first number is the total proper motion
          in mas/yr, and the second is the position angle
          of the proper motion in degrees (i.e. 0 = due
          north, 90 = due east, and so on).

input epoch - When proper motions are involved we need to
  distinguish the "epoch" from the "equinox".  The 
  "equinox" is the date of the coordinate system -- it
  defines the pole and equinox used to set up RA and dec.
  The "epoch" is the date that the star is at the input
  position.  Thus if the position of a moving star were 
  measured in 1980 and that position were precessed forward 
  to the J2000 coordinate system, the epoch of the position 
  would be 1980 and the equinox would be 2000.  

Whenever the window is refreshed, these three input values
are read and used, together with input values from the main
window, to compute the following:

Current RA --  RA for the date and time specified in the main
  window, updated for precession and proper motion (if any).
  The precession routine is a rigorous matrix formulation, 
  using the IAU 1976 formulae, which are now superseded but
  which are accurate enough for nearly all optical-astronomy
  purposes.

Current dec -- same, for declination

equinox    -- the equinox of these coordinates, i.e. the current
  time expressed as decimal years.  Technically this is the 
  'julian epoch', which is 2000 + (jd - J2000) / 365.25, where
  J2000 is 2451545.0.

[The next three fields are INPUT fields described earlier, and
 are omitted from this list of outputs.]

RA (pm only). -- The input RA taken from the main window, updated
  for proper motion but left in the equinox of the input 
  coordinates.

dec -- same, but now the dec.

equinox -- the equinox of these coordinates, which will always be
  identical to the input coordinates' equinox.

Ecliptic latitude -- Ecliptic latitude, in degrees.

Ecliptic longitude -- Ecliptic longitude, in degrees.

Galactic latitude -- Galactic latitude, in degrees.  The
  routine which computes the Galactic coordinates conforms 
  to the IAU definition, which is based in the RA and dec
  for 1950; coordinates are internally precessed to 1950 
  before the transformation into Galactic.

Galactic longitude -- Galactic longitude in degrees.

There is a special hook here -- if you enter Galactic
coordinates with a carriage return, the position in the
main window is set to agree with the Galactic coordinates.
Thus the program can serve as a Galactic-to-equatorial
converter.

As usual, the "Hide" button takes the window down so that
it can still be brought back up.

THE PLANETS WINDOW 

This prints low-precision coordinates of the planets.  The
inner planets are the best, better than an arcmin, and then
the outer planets become worse.  Coordinates are in the epoch
of date.  If a planet is computed to lie within 1 degree of
the input coordinates from the main window, its line is
colored in orange to alert the reader.

Tabulated in the window are:

Name - name of the planet (duh).

RA   - Right ascension in the epoch of date.

Dec  - Declination in the epoch of date.

HA   - Hour angle.

airmass - airmass, if less than 10.

proximity - Angular separation between the planet and the 
  coordinates of the object, in decimal degrees.

Again, there is a "Hide" button to put the window away.

THE SITE WINDOW

This is used to select an observatory.  The window is
displayed when the program starts up. 

The behavior is less than optimal and may be improved in
subsequent releases.  Every time the output is refreshed,
the variable set by this window is read and the site 
parameters are set to the standard values for the 
selected site.  This reloading is passed over ONLY
if you select the last button on the menu, labeled
"Other (allow user entries)".  Thus if you want to 
customize your site by entering its parameters by hand,
you must first select the last button on the site menu.
If you don't, the first time you refresh the output,
the fields you've entered will revert to the standard
values for the selected site.

Other sites can be added in the source code if needed -
just use the existing sites as a guide.

The "Hide" button withdraws the menu window without 
destroying it.  The "Show site menu" button in the
main window pops the menu back up.

THE OBJECT LIST WINDOW

The "Read object list" button lets you load an object
list using a file-selection dialog.  The object list
needs to have one object per line in the format:

  name_no_blanks   rahh mm ss   decdd mm ss  equinox
  
For example:

  4U2129+47     21 29 36.2   47 04 08  1950

The list is free-format, but whitespace (not colons) must
be used to delineate fields.  A little window pops up,
and double-clicking a name sets the name, RA, dec, and
equinox.  

You can open more than one list at a time, which appear
in separate windows.  If identically-named objects
appear on more than one list, the object's name will
be bracketed by vertical bars on the second list.  
When a list is loaded, the objects will appear on the
planetarium display (if open) as soon as output is 
refreshed, and disappear when the list is dismissed.

Buttons control the order in which the list is presented:

- in the original order it was read from the file
- alphabetically
- ordered by RA
- ordered by proximity to the current coordinates
  (e.g. "I need something nearby!, or "I remember 
   vaguely where this is but don't remember what
   I named it", or you can set to the zenith and
   get objects sorted by airmass, etc.) 

BUGS, UNIMPLIMENTED FEATURES etc. --

- There are some unresolved issues around reporting
  phenomena at very high latitudes, especially moonrise
  and moonset.  At temperate latitudes it seems fine.

- Eclipses are not taken into account in the lunar sky 
  brightness calculations.     

For more detail on the algorithms used, see the skycalc
documentation. 

"""

# Some utility routines adapted from Mark Lutz' *Programming Python*,
# published by O'Reilly.


# Adapted from Mark Lutz' "Programming in Python", O'Reilly

class ScrolledList(Frame) : 
	def __init__(self, options, parent=None, kill=1) :
		Frame.__init__(self,parent)
		self.pack(expand=YES, fill=BOTH)
		self.makeWidgets(options)
		self.val = 0
		self.onepass = kill
	def handleList(self,event) :
		index = self.listbox.curselection()
		self.val = self.listbox.get(index)
		# if self.onepass == 1: 
		#  	self.quit()  # kill box after any selection.
	def makeWidgets(self,options) :
		sbar = Scrollbar(self)
		list = Listbox(self,relief=SUNKEN)
		sbar.config(command=list.yview)
		list.config(yscrollcommand=sbar.set)
		sbar.pack(side=RIGHT, fill=Y)
		list.pack(side=LEFT,expand=YES, fill=BOTH)
		pos = 0
#		print "options %s" % options
		for label in options:
#			print "label %s" % label
			list.insert(pos,label)
			pos = pos + 1
		list.bind('<Double-1>', self.handleList)
		self.listbox=list
		self.sb = sbar

# Largely from Lutz' Programming Python book, with some
# enhancements I added.

class ScrolledText(Frame) :
	def __init__(self, parent = None, text = '', file = None, width=80, height=24) :
		Frame.__init__(self, parent)   # make me expendable
		self.pack(expand = YES, fill=BOTH)
		self.makewidgets(width=width, height=height)
		self.settext(text,file)
	def makewidgets(self,width=80,height=24) :
		sbar = Scrollbar(self)
		text = Text(self, relief = SUNKEN,width=width,height=height,
			bg="#330066",fg="yellow",font="7x13")
		sbar.config(command=text.yview)      # xlink sbar and text
		text.config(yscrollcommand=sbar.set) # each moves the other
		sbar.pack(side=LEFT, fill=Y)
		text.pack(side=LEFT, expand=YES, fill=BOTH)
		self.text = text
	def settext(self, text='', file = None) :
		if file:
			text = open(file, 'r').read()
		self.text.delete('1.0',END)  # delete current text
		self.text.insert('1.0',text) # add at line 1, col 0
		self.text.mark_set(INSERT, '1.0')
		self.text.focus()            # save user a click
	def gettext(self) :
		return self.text.get('1.0', END+'-1c')  
	def getsel(self) :
		return self.text.selection_get()
	def appendline(self,line='\n',maxlines = 10000) :
		self.text.insert(END,line + "\n")
		if float(self.text.index(END)) > maxlines :
			#print maxlines, self.text.index(END), \
			#	 self.text.index(END) > float(maxlines)
			self.text.delete('1.0','2.0')
		self.text.see(END)
	def erasetext(self) :
		self.text.delete('1.0',END) 
	def dumptext(self,filename) :
		# outstuff = self.text.selection_get() 
		outf = open(filename,"a")
		outf.write(self.gettext())
		outf.close()

# quitter widget is a direct copy of Lutz' routine, except without the 
# __name__ == '__main__' trick.

#############################################
# a quit button that verifies exit requests;
# to reuse, attach an instance to other guis
#############################################

from Tkinter import *                          # get widget classes
from tkMessageBox import askokcancel           # get canned std dialog

class Quitter(Frame):                          # subclass our GUI
    def __init__(self, parent=None):           # constructor method
        Frame.__init__(self, parent)
        self.pack()
      #  widget = Button(self, text='Quit', command=self.quit, bg="#ffaa75")
        widget = Button(self, text='Quit', command=self.quit)
        widget.pack(expand=YES, fill=BOTH, side=LEFT)
    def quit(self):
        ans = askokcancel('Verify exit', "Really quit?")
        if ans: Frame.quit(self)

# if __name__ == '__main__':  Quitter().mainloop()

# Routines to create windows and so on ... 

def makehelpframe(parentwin, intext = helptext) :

	textfr = Frame(parentwin)
	textfr.pack()
	scrtxt = ScrolledText(textfr,text = intext)
	
	Button(textfr, text = 'Hide',command = (lambda: parentwin.withdraw())).pack(side = TOP)
	
obs = observation()

obs.setsite('k')   # THIS SETS THE DEFAULT SITE - to Kitt Peak.
		   # to change, refer to cooclasses.py for codes or to 
		   # customize for another site not already coded.
obs.setlocal('NOW')
obs.setcelest('ZENITH')

# print "Set the obs, obs.ra.val = ",obs.ra.val
# print "summarystring",obs.summarystring()

def stripdayname(inputdate) :
   x = string.split(inputdate)  # strips fourth field = day of week.
   xout = x[0] + " " + x[1] + " " + x[2]
   return xout

def moonwarningcolor(lunskybright, altsun, objmoondist, moonalt, objalt = 90.) :
	if moonalt < 0. or objalt < 0. : return normalentry  
	if altsun > -12. : return normalentry  # twilight dominates
	if objmoondist > 25. :
		if lunskybright > 21.5 : return normalentry
		elif lunskybright > 19.5 : 
			return "lightblue"
		else : return "#DD88FF"  # a light purple
	if objmoondist < 10. : return "red"  # always flag this ...
	if lunskybright > 21.5 : return normalentry
	if lunskybright > 19.5 : return "yellow"
	if lunskybright > 18. : return "orange"
	else : return "red"

def twilightwarningcolor(altsun,ztwilight) :
	if altsun > 0. : return "lightblue"
	if altsun < -18. : return normalentry
	if ztwilight < 4. : return "yellow"
	if ztwilight < 8. : return "orange"
	return "red"

def airmasswarningcolor(altit,airmass,down_is_red = 1) :
	
	if altit < 0. : 
		if down_is_red == 0 :
			return "lightgreen"
		else :
			return "red"
	if airmass <= 2. : return normalentry
	if airmass > 4. : return "red"
	if airmass > 3. : return "orange"
	else : return "yellow"

def hawarningcolor(ha, limit) :
	
	if abs(ha) < limit : return normalentry
	else : return "orange"

def ymd_hms_string(calstr) :  # calstring has style = 1, printday = 1
	# Puts out ["yyyy month dd, dow","hh mm ss"]
	x = string.split(calstr)
	ymd = x[0] + " " + x[1] + " " + x[2] + ", " + x[6]
	hms = x[3] + " " + x[4] + " " + x[5]
	return [ymd,hms]

def planetwarning(planets, ra, dec, tolerance) :
	
	warning = ""
	for i in range(1,10) :
		if i != 3 :
			ang = subtendang(planets[i][1],planets[i][2],ra,dec) \
				* 57.2957795130823
			if ang < tolerance :
				warning = warning + " " + planets[i][0]
	if warning == "" :
		warning = " --- "
		return [warning,normalentry]
	else :
		return [warning,"orange"]
			
# Circumstances computes and refreshes almost everything.

def circumstances(variables,outvars,havars,almvars,coovars,planetvars,
		boxes,haboxes,planetboxes) :

	# Need to do things in the order site, time, then celestial position,
	# sine the equinox can be "NOW".

	abbrev = variables[17].get()   # site
	if abbrev == 'x' :
		obs.longit = getlongit(variables[9].get())
		templong = coord(obs.longit)  # refresh output as hms W
		variables[9].set(templong.tripletstring(places=1) + " hms W")
		obs.lat = todeci(variables[10].get())
		obs.stdz = float(variables[11].get())
		obs.use_dst = int(variables[12].get())
		obs.elevsea = float(variables[15].get())
		obs.elevhoriz = float(variables[16].get())
		obs.obs_name = variables[8].get()
		obs.zone_name = variables[13].get()
		obs.zone_abbrev = variables[14].get()
	else : 
		obs.setsite(abbrev)
		templong = coord(obs.longit)
		variables[9].set(templong.tripletstring(places=1) + " hms W")
		templat = coord(obs.lat)
		variables[10].set(templat.tripletstring(places=0,showsign=1))
		variables[11].set("%5.2f" % obs.stdz)
		variables[12].set("%d" % obs.use_dst)
		variables[15].set("%4.0f" % obs.elevsea)
		variables[16].set("%4.0f" % obs.elevhoriz)
		variables[8].set(obs.obs_name)
		variables[13].set(obs.zone_name)
		variables[14].set(obs.zone_abbrev)

	time1 = variables[4].get()    
	time1 = stripdayname(time1)
	time2 = variables[5].get()
	timestr = time1 + " " + time2
	localfl = variables[6].get()
	if localfl == 'y' or localfl == 'Y' :
		obs.setlocal(timestr)
	else :
		obs.setlocal(timestr)
		obs.setut(timestr)
	outvars[5].set("%15.5f" % obs.jd)
	boxes[5].config(bg = incolor1)

	obs.ra.val = getradec(variables[1].get(),"h")
	variables[1].set(obs.ra.tripletstring(places=2,showsign=0) + "     hms")
	obs.dec.val = getradec(variables[2].get(),"d")
	variables[2].set(obs.dec.tripletstring(places=1,showsign=1) + "     dms")
	eqstr = string.upper(variables[3].get())
	if eqstr == "DATE" :
		eqtmp = julian_ep(obs.jd)	
	else : eqtmp = float(variables[3].get())
	variables[3].set("%8.3f" % eqtmp)
	obs.setcelest([obs.ra.val,obs.dec.val,eqtmp])

	obs.computesky()
	obs.computesunmoon()

	# check for planet warnings ... 

	planets = fillplform(planetvars,planetboxes)
	warning = planetwarning(planets, obs.CoordsOfDate.ra.val, 
		obs.CoordsOfDate.dec.val, 1.)
	outvars[18].set(warning[0])
	boxes[18].configure(bg = warning[1])

#outfields = ('sidereal','ha','airmass','alt_az','parallactic','jd', \
#	'sunradec','sunaltaz','ztwilight','moonphase','moonradec','moonaltaz', \
#        'illumfrac','lunsky','moon-obj ang.','baryjd','baryvcor','constel',
#	'planet_proxim')

# 0 = sidereal; 1 = ha; 2 = airmass; 3 = alt_az; 4 = parallactic; 
# 5 = jd; 6 = sunradec; 7 = sunaltaz; 8 = ztwilight; 
# 9 = moonphase; 10 = moonradec; 11 = moonaltaz; 12 = illumfrac; 
# 13 = lunsky; 14 = moon-obj angle; 15 = baryjd; 16 = baryvcor
# 17 = constel; 18 = planet proximity flag

	# Need to explicitly reset the time variable to catch day-of-week changes
	if variables[6].get() == 'y' :
		calstr = obs.calstring(style = 1, stdz = obs.stdz, use_dst = obs.
			use_dst, print_day = 1, daycomma = 0,secdigits = 1) 
	else :
		calstr = obs.calstring(style = 1, print_day = 1, daycomma = 0,
			secdigits = 1)

	[ymd,hms] = ymd_hms_string(calstr)
	variables[4].set(ymd)
	variables[5].set(hms)

	outvars[0].set(obs.sidereal.tripletstring(places = 0,showsign = 0))
	hawarn = hawarningcolor(obs.hanow.val,6.)
	boxes[1].configure(bg = hawarn)
	outvars[1].set(obs.hanow.tripletstring(places=0))		

	airmasswarn = airmasswarningcolor(obs.altit,obs.airmass, down_is_red=1)

	boxes[2].configure(bg = airmasswarn)
	if obs.altit > 0. :
		if obs.airmass < 10. :
			outvars[2].set("%6.3f" % obs.airmass)
		else :
			outvars[2].set("More than 10")
	else :
		outvars[2].set("(Down.)")

	if obs.altit < 0. or obs.airmass > 4. :
		boxes[2].configure(bg = "red")
	elif obs.airmass > 3. :
		boxes[2].configure(bg = "orange")
	elif obs.airmass > 2. :
		boxes[2].configure(bg = "yellow")
	else :  boxes[2].configure(bg = normalentry)
#	if obs.altit > 0. :
#		outvars[3].set("%6.3f" % obs.secz)
#	else :
#		outvars[3].set("---")
	outvars[3].set("%5.2f    az %5.2f" % (obs.altit,obs.az))
	outvars[4].set("%5.1f [%5.1f]  deg" % (obs.parang,opposite_angle(obs.parang)))
	outvars[6].set(obs.SunCoords.summarystring(include_eq = 0,radigits = 1))
	outvars[7].set("%4.1f      az %5.1f" % (obs.altsun,obs.azsun))
	twilightwarn = twilightwarningcolor(obs.altsun, obs.ztwilight)
	boxes[8].configure(bg = twilightwarn)
	if obs.altsun < 0. and obs.altsun >= -18. :
		outvars[8].set("%5.1f  mag (blue)" % obs.ztwilight)
	elif obs.altsun >= 0. :
		outvars[8].set("Daytime.")
	else : 
		outvars[8].set("No twilight.")

	moonwarn = moonwarningcolor(obs.lunsky,obs.altsun,obs.obj_moon,obs.altmoon,
			obs.altit)
	outvars[9].set(obs.moonphasedescr())
	outvars[10].set(obs.MoonCoords.summarystring(include_eq = 0,radigits = 1))
	outvars[11].set("%4.1f      az %5.1f" % (obs.altmoon,obs.azmoon))
	if obs.altmoon > -1  :
		outvars[12].set("%5.3f" % obs.moonillfrac)
	else :
		outvars[12].set(" Moon is down. ")
	boxes[13].configure(bg = moonwarn)
	if obs.altmoon > -1 and obs.altsun < -12. and obs.altit > 0. :
		outvars[13].set("%5.1f mag." % obs.lunsky)
	elif obs.altmoon <= -1 or obs.altit < 0. :	
		outvars[13].set("---")
	elif obs.altsun >= -12 and obs.altsun < 0.:
		outvars[13].set("(Bright twilight.)")
	else :
		outvars[13].set("(Daylight.)")
	boxes[14].configure(bg = moonwarn)
	outvars[14].set("%5.1f  deg." % obs.obj_moon)
	if obs.barytcor < 0. :
	  outvars[15].set("%14.5f   [%6.1f s]" % (obs.baryjd,obs.barytcor))
	else :
	  outvars[15].set("%14.5f   [+%5.1f s]" % (obs.baryjd,obs.barytcor))
	outvars[16].set("%6.2f  km/s" % obs.baryvcor)
	outvars[17].set(" %s" % obs.constel())
	fillhaform(havars,haboxes)
	fillalmform(almvars)
	fillcooform(coovars)
	if pgqinf('state') != "CLOSED" :
		plotsky('/xwin')
		

# 0 = objname,
# 1 = RA; 2 = dec; 3 = equinox; date = 4, time = 5, 
# Time is: = 6, timestep = 7,
# 8 = obs_name, 9 = longit, 10 = lat, 11 = stdz, 12 = use_dst, 13 = zone_name, 14 = zone_abbrev, 
# 15 = elevsea, 16 = elevhoriz, 17 = siteabbrev


def steptime(variables, outvars, havars, almvars, coovars, planetvars, 
	boxes, haboxes, planetboxes, forward = 1) :
	
#	print "stepping the time ... "
	x = string.split(variables[7].get())
	number = float(x[0])
	mult = 1.
	if len(x) > 1 :
		unit = string.upper(x[1])
		if string.find(unit,'S') == 0 : mult = 1. / 60. 
		if string.find(unit,'M') == 0 : mult = 1. 
		elif string.find(unit,'H') == 0 : mult = 60.
		elif string.find(unit,'D') == 0 : mult = 1440.
		elif string.find(unit,'T') == 0 : mult = 1436.068175587
		elif string.find(unit,'W') == 0 : mult = 10080.
		elif string.find(unit,'L') == 0 : mult = 42524.2 
			# mean month -- this is a "lunation".
	if forward == 1 :
		timeincr = number * mult 
	else :
		timeincr = number * mult * -1.
	obs.incrtime(timeincr)
	if variables[6].get() == 'y' :
		calstr = obs.calstring(style = 1, stdz = obs.stdz, use_dst = 
			obs.use_dst, print_day = 1, daycomma = 0) 
	else :
		calstr = obs.calstring(style = 1, print_day = 1, daycomma = 0)
	[ymd,hms] = ymd_hms_string(calstr)
	variables[4].set(ymd)
	variables[5].set(hms)
	
	circumstances(variables,outvars,havars,almvars,coovars, planetvars,
		boxes, haboxes, planetboxes)

def convert_time(variables, outvars, havars, almvars, coovars, planetvars,
	boxes, haboxes, planetboxes) :
	
	if variables[6].get() == 'y' : # convert local to UT
		calstr = obs.calstring(style = 1, print_day = 1, daycomma = 0)
		variables[6].set('n')
	else :
		calstr = obs.calstring(style = 1, stdz = obs.stdz,
			use_dst = obs.use_dst, print_day = 1, daycomma = 0)
		variables[6].set('y')
	[ymd,hms] = ymd_hms_string(calstr)
	variables[4].set(ymd)
	variables[5].set(hms)

	circumstances(variables,outvars,havars,almvars, coovars, planetvars,
		boxes, haboxes, planetboxes)
	
def set_to_now(variables, outvars, havars, almvars,coovars, planetvars, 
	boxes, haboxes, planetboxes) :

	# print "variables[6].get() = ",variables[6].get()
	obs.setlocal('NOW')
	if variables[6].get() == 'y' :
		calstr = obs.calstring(style = 1, stdz = obs.stdz, \
		 use_dst = obs.use_dst, print_day = 1, daycomma = 0) 
	else :
		calstr = obs.calstring(style = 1, print_day = 1, daycomma = 0) 
	
	[ymd,hms] = ymd_hms_string(calstr)
	variables[4].set(ymd)
	variables[5].set(hms)
	
	circumstances(variables,outvars,havars,almvars,coovars, planetvars,
		boxes, haboxes, planetboxes)

# Globally define two colors to flag inputs - one for site stuff.

#incolor1 = "#d8edc4" # very pale greenish
incolor2 = "#efdee4" # very pale pinkish
#incolor1 = "#edeff4" # near white
#incolor1 = "white"  # this is too much 
incolor1 = "#f5f5ee"  # a somewhat brighter off-white, slight tinge of yellow 
normalentry = "#dbdbdb" # as close as I can tell ... better match than "lightgrey"

def makeinform(root, fields) :

	variables = []
	calstr = obs.calstring(style = 1, stdz = obs.stdz, \
		use_dst = obs.use_dst, print_day = 1, daycomma = 0) 

	[ymd, hms] = ymd_hms_string(calstr)

	row = Frame(root)
	lab = Label(row, text = "Input Variables")
	row.pack(side = TOP)
	lab.pack(side = TOP)

	incolor = incolor1

	# paint in all the usual input variables in one color, then the
	# site variables in another.  
	
	for field in fields :
		row = Frame(root)
		lab = Label(row, width=11, text = field)
		var = StringVar()
		if field == 'siteabbrev' :
			var.set('k')
		elif field == 'Time is:' :
			row.pack(side = TOP, fill = X, expand = YES)
			lab.pack(side = LEFT)
			but = Radiobutton(row,text = "Local", variable = var, value = 'y')
			but.pack(side = RIGHT, expand = YES, fill = X)
			but = Radiobutton(row,text = "UT",variable = var, value = 'n')
			but.pack(side = RIGHT, expand = YES, fill = X)
			var.set('y')
		else :
			if field == "obs_name" : # put in an extra label here ...
				extra = Frame(root)
				extralab = Label(extra, width = 20, height=2, text = "Site Parameters")
				extra.pack(side = TOP, fill = X, expand = YES)
				extralab.pack()
				incolor = incolor2  # AND change the color ... 
			row.pack(side = TOP, expand = YES)
			lab.pack(side = LEFT, anchor = W)
			ent = Entry(row, width=21)
			ent.pack(side=RIGHT, expand = YES, fill = X)
			ent.config(textvariable = var,bg = incolor)
		if field == 'RA' :
			var.set(obs.ra.tripletstring(places = 2, delin = ' ', showsign=0) + 
			 "     hms")
		elif field == 'dec' :
			var.set(obs.dec.tripletstring(places = 1, delin = ' '))
		elif field == 'equinox' :
			var.set("%8.3f" % obs.equinox)
		elif field == 'longit' :
			templong = coord(obs.longit)
			var.set(templong.tripletstring())
		elif field == 'lat' :
			templat = coord(obs.lat)
			var.set(templat.tripletstring())
		elif field == 'stdz' :
			var.set("%5.2f" % obs.stdz)
		elif field == 'use_dst' :
			var.set("%d" % obs.use_dst)
		elif field == 'elevsea' :
			var.set("%4.0f" % obs.elevsea)
		elif field == 'elevhoriz' :
			var.set("%4.0f" % obs.elevhoriz)
		elif field == 'obs_name' :
			var.set(obs.obs_name)
		elif field == 'zone_name' :
			var.set(obs.zone_name)
		elif field == 'zone_abbrev' :
			var.set(obs.zone_abbrev)
		elif field == 'date' :
			var.set(ymd)
		elif field == 'time' :
			var.set(hms)
		elif field == 'timestep' :
			var.set("1   h")
			StepBox = ent
		elif field == 'objname' :
			var.set('(initializes at zenith)')
			ObjBox = ent
		variables.append(var)
	return (variables,StepBox,ObjBox)

def fillhaform(havars, haboxes)  :

	scratch = deepcopy(obs)   # careful!!
	localtimestr = scratch.calstring(stdz = scratch.stdz, \
		use_dst = scratch.use_dst)
	
	x = string.split(localtimestr)
	ymd = x[0] + " " + x[1] + " " + x[2]
	if float(x[3]) >= 12. :
		midnstring = ymd + " 23 59 59.99"
	else :
		midnstring = ymd + " 0 0 0"
	# print "midnstring = ",midnstring,
	jdmid = time_to_jd(midnstring, stdz = scratch.stdz, \
		 use_dst = scratch.use_dst)
	# print "jdmid = ",jdmid

	one_hr = 1 / 24.
	one_sec = 1/86400.

	j = 0
	i = -10   # number of hours away from midnight  
	done = 0
	started = 0
	while i < 18 and j < 18 and done == 0 :
		scratch.jd = jdmid + i * one_hr + one_sec

		scratch.computesky()
		scratch.computesunmoon()

		if scratch.altsun < 8. :
			# print "j = ",j,"ut = ",scratch.calstring()
			for k in range(0,3) : # needs to be re-set if it had been blanked
				haboxes[k][j].configure(bg = normalentry)  
			if j == 0 :
				started = 1
			localdatestring = scratch.calstring(stdz = scratch.stdz,
				use_dst = scratch.use_dst, style = 1, \
				print_day = 1, daycomma = 0, dayabbrev = 1)
			x = string.split(localdatestring)
			localtimestr = x[6] + " " + x[1] \
				+ " " + x[2] + "   " +  x[3] + ":" + x[4]
			havars[0][j].set(localtimestr)
	
			utdatestring = scratch.calstring()
			x = string.split(utdatestring)
			uttimestr = x[3] + ":" + x[4]
			havars[1][j].set(uttimestr)
				
			# print havars[0][j].get(),havars[1][j].get()
	
			scratch.computesky()
			scratch.computesunmoon()

			hawarn = hawarningcolor(scratch.hanow.val,6.)
			moonwarn = moonwarningcolor(scratch.lunsky, scratch.altsun, scratch.obj_moon, \
				scratch.altmoon, scratch.altit)	
			twilightwarn = twilightwarningcolor(scratch.altsun, scratch.ztwilight)
			airmasswarn = airmasswarningcolor(scratch.altit, scratch.airmass)
		
			
			havars[2][j].set(scratch.sidereal.tripletstring(showsign = 0,places = -2, delin = ':'))
			haboxes[3][j].configure(bg = hawarn)
			havars[3][j].set(scratch.hanow.tripletstring(showsign = 1,places = -2, delin = ':'))
			haboxes[4][j].configure(bg = airmasswarn)
			if scratch.altit > 0. :
				if scratch.airmass < 10. :
					havars[4][j].set("%6.3f" % scratch.airmass)
				else :
					havars[4][j].set("> 10.")
			else :
				havars[4][j].set("(down)")
			haboxes[5][j].configure(bg = moonwarn)
			if(scratch.altmoon > -2.) :
				havars[5][j].set("%5.1f" % scratch.altmoon)
			else :
				havars[5][j].set("---")
			haboxes[6][j].configure(bg = twilightwarn)
			if(scratch.altsun >= -18.) :
				havars[6][j].set("%5.1f" % scratch.altsun)
			else :
				havars[6][j].set("---")
			j = j + 1	
		elif started == 1 :
			done = 1
		i = i + 1  
	while j < 18 :
		for k in range(0,7) :
			havars[k][j].set("---")
			haboxes[k][j].configure(bg = "darkgrey")
		j = j + 1

def printhatable(invars,havars)  :

	# Based closely on fillhaform, this version dumps the 
	# output to a file called "skycalc.out"

	outf = open("skycalc.out","a")

	scratch = deepcopy(obs)   # careful!!
	localtimestr = scratch.calstring(stdz = scratch.stdz, \
		use_dst = scratch.use_dst)
	
	x = string.split(localtimestr)
	ymd = x[0] + " " + x[1] + " " + x[2]
	if float(x[3]) >= 12. :
		midnstring = ymd + " 23 59 59.99"
	else :
		midnstring = ymd + " 0 0 0"
	# print "midnstring = ",midnstring,
	jdmid = time_to_jd(midnstring, stdz = scratch.stdz, \
		 use_dst = scratch.use_dst)
	# print "jdmid = ",jdmid

	scratch.jd = jdmid

	one_hr = 1 / 24.
	one_sec = 1/86400.

	outf.write("--- Hourly airmass for %s --- %s ---\n\n" % (invars[0].get(),ymd))
	outf.write("  Input coords: %s\n" % scratch.summarystring())
 	outf.write("Current coords: %s\n\n" % scratch.precess(scratch.julian_epoch()).summarystring())

	outf.write("Local date & time    UT     LST      HA     airm   moonalt  sunalt\n\n")
	j = 0
	i = -10   # number of hours away from midnight  
	done = 0
	started = 0
	while i < 18 and done == 0 :
		scratch.jd = jdmid + i * one_hr + one_sec

		scratch.computesky()
		scratch.computesunmoon()

		if scratch.altsun < 8. :
			for k in range(0,3) : # needs to be re-set if it had been blanked
				haboxes[k][j].configure(bg = normalentry)  
			if j == 0 :
				started = 1
			localtimestr = scratch.calstring(stdz = scratch.stdz, use_dst = scratch.use_dst, style = 2)
			outf.write("%s  " % localtimestr)
	
			utdatestring = scratch.calstring()
			x = string.split(utdatestring)
			uttimestr = x[3] + ":" + x[4]
			outf.write(" %05s " % uttimestr)
				
			scratch.computesky()
			scratch.computesunmoon()

			outf.write(" %06s " % scratch.sidereal.tripletstring(showsign = 0,places = -2, delin = ':'))
			outf.write(" %06s " % scratch.hanow.tripletstring(showsign = 1,places = -2, delin = ':'))
			if scratch.altit > 0. :
				if scratch.airmass < 10. :
					outf.write(" %6.3f " % scratch.airmass)
				else :
					outf.write( "  > 10. ")

			else :
				outf.write(" (down) ")
			if(scratch.altmoon > -2.) :
				outf.write("   %5.1f " % scratch.altmoon)
			else :
				outf.write("     --- ")
			if(scratch.altsun >= -18.) :
				outf.write("  %5.1f " % scratch.altsun)
			else :
				outf.write("    --- ")
			outf.write("\n")
			j = j + 1	
		elif started == 1 :
			done = 1
		i = i + 1  

	outf.write("\n\n")
	outf.close()

def makeplanetform(planetwin) :

	pl_name = [] # make the variables
	pl_ra   = []
	pl_dec  = []
	pl_ha   = []
	pl_airm = []
	pl_prox = []

	pl_name_box = [] # make the box variables
	pl_ra_box   = []
	pl_dec_box  = []
	pl_ha_box   = []
	pl_airm_box = []
	pl_prox_box = []

	plpan = Frame(planetwin)
	plpan.pack(side = LEFT)
	row = Frame(plpan)
	row.pack(side = TOP)
	lab = Label(row,width=11,text = "Name   ")
	lab.pack(side = LEFT,fill=Y)
	lab = Label(row,width=8,text = "RA   ")
	lab.pack(side = LEFT,fill=Y)
	lab = Label(row,width=8,text = "Dec   ")
	lab.pack(side = LEFT,fill=Y)
	lab = Label(row,width=8,text = "HA   ")
	lab.pack(side = LEFT,fill=Y)
	lab = Label(row,width=8,text = "airmass ")
	lab.pack(side = LEFT,fill=Y)
	lab = Label(row,width=8,text = "proximity ")
	lab.pack(side = LEFT,fill=Y)

	for i in range(0,10) :
		if i != 0 and i != 3 :

			row = Frame(plpan)
			row.pack(side = TOP,fill=X,expand=YES)
			name = StringVar()
			ent = Entry(row,width = 9)
			ent.pack(side = LEFT, expand=YES, fill=X)
			ent.config(textvariable = name)
			pl_name = pl_name + [name]
			pl_name_box = pl_name_box + [ent]
			
			ra = StringVar()
			ent = Entry(row,width = 9)
			ent.pack(side = LEFT, expand=YES, fill=X)
			ent.config(textvariable = ra)
			pl_ra = pl_ra + [ra]
			pl_ra_box = pl_ra_box + [ent]
	
			dec = StringVar()
			ent = Entry(row,width = 9)
			ent.pack(side = LEFT, expand=YES, fill=X)
			ent.config(textvariable = dec)
			pl_dec = pl_dec + [dec]
			pl_dec_box = pl_dec_box + [ent]
	
			ha = StringVar()
			ent = Entry(row,width = 9)
			ent.pack(side = LEFT, expand=YES, fill=X)
			ent.config(textvariable = ha)
			pl_ha = pl_ha + [ha]
			pl_ha_box = pl_ha_box + [ent]
	
			airm = StringVar()
			ent = Entry(row,width = 9)
			ent.pack(side = LEFT, expand=YES, fill=X)
			ent.config(textvariable = airm)
			pl_airm = pl_airm + [airm]
			pl_airm_box = pl_airm_box + [ent]

			prox = StringVar()
			ent = Entry(row,width = 9)
			ent.pack(side = LEFT, expand=YES, fill=X)
			ent.config(textvariable = prox)
			pl_prox = pl_prox + [prox]
			pl_prox_box = pl_prox_box + [ent]
	
		else :
			pl_name = pl_name + [None]
			pl_ra = pl_ra + [None]
			pl_dec = pl_dec + [None]
			pl_ha = pl_ha + [None]
			pl_airm = pl_airm + [None]
			pl_prox = pl_prox + [None]

			pl_name_box = pl_name_box + [None]
			pl_ra_box = pl_ra_box + [None]
			pl_dec_box = pl_dec_box + [None]
			pl_ha_box = pl_ha_box + [None]
			pl_airm_box = pl_airm_box + [None]
			pl_prox_box = pl_prox_box + [None]

	row = Frame(plpan)
	row.pack(side=TOP)
	Button(row, text = 'Hide',command = (lambda: planetwin.withdraw())).pack(side = LEFT)

	plvars = [pl_name, pl_ra, pl_dec, pl_ha, pl_airm, pl_prox]
	plboxvars = [pl_name_box, pl_ra_box, pl_dec_box, pl_ha_box, 
			pl_airm_box, pl_prox_box]
	return [plvars,plboxvars]

def fillplform(plvars, plboxvars) :
	
	planets = computeplanets(obs.jd,obs.longit,obs.lat,0)
	
	plobs = deepcopy(obs)  # this gets site and date info ... 

	# print planets
	epnow = obs.julian_epoch()
	objcoo = obs.precess(epnow)
	
	for i in range(1,10) :
		if i != 3 :
			# print i,planets[i]
			plobs.setcelest([planets[i][1],planets[i][2],
				epnow])
			plobs.computesky()
			plvars[0][i].set(planets[i][0])
			plvars[1][i].set(plobs.ra.tripletstring(delin=":",
				places = -1,showsign=0))
			plvars[2][i].set(plobs.dec.tripletstring(delin=":",
				places = -2, showsign = 1))
			plvars[3][i].set(plobs.hanow.tripletstring(delin=":",
				places = -2, showsign = 1))
			if plobs.altit > 0. :
				if plobs.airmass < 10. :
					plvars[4][i].set("%7.2f" % plobs.airmass)
				else : plvars[4][i].set(" > 10.")
			else : plvars[4][i].set("(Down.)")
			prox = subtendang(planets[i][1],planets[i][2],
				obs.CoordsOfDate.ra.val,
				obs.CoordsOfDate.dec.val) * 57.2957795130823
			if prox < 1. :
				for j in range(0,6) :
					plboxvars[j][i].configure(bg = "orange")
			else :
				for j in range(0,6) :
					plboxvars[j][i].configure(bg = normalentry)
			plvars[5][i].set("%6.1f" % prox)

	return(planets)  # don't waste the cpu cycles ... 


def makehaform(hawin) :

	ha_local = []  # make the variables
	ha_ut = []
	ha_lst = []
	ha_ha = []    # ha ha! 
	ha_airm = []
	ha_moonalt = []
	ha_sunalt = []

	ha_local_box = []  # make the variables
	ha_ut_box = []
	ha_lst_box = []
	ha_ha_box = []    # ha ha! 
	ha_airm_box = []
	ha_moonalt_box = []
	ha_sunalt_box = []

	
	hapan = Frame(hawin)
	hapan.pack(side = LEFT)
	row = Frame(hapan)
	row.pack(side = TOP)
	lab = Label(row,width=17,text = " Local")
	lab.pack(side = LEFT)
	lab = Label(row,width=6,text = " UT ")
	lab.pack(side = LEFT)
	lab = Label(row,width=6,text = " LST ")
	lab.pack(side = LEFT)
	lab = Label(row,width=6,text = " HA ")
	lab.pack(side = LEFT)
	lab = Label(row,width=7,text = " Airmass")
	lab.pack(side = LEFT)
	lab = Label(row,width=6,text = " moonalt")
	lab.pack(side = LEFT)
	lab = Label(row,width=6,text = " sunalt")
	lab.pack(side = LEFT)
	
	for i in range(0,18) :
		row = Frame(hapan)
		row.pack(side = TOP, fill = X, expand = YES)

		local = StringVar()
		ent = Entry(row, width = 17)
		ent.pack(side = LEFT, expand = YES, fill = X)
		ent.config(textvariable = local)
		ha_local = ha_local + [local]
		ha_local_box = ha_local_box + [ent]

		ut = StringVar()
		ent = Entry(row, width = 6)
		ent.pack(side = LEFT, expand = YES, fill = X)
		ent.config(textvariable = ut)
		ha_ut = ha_ut + [ut]
		ha_ut_box = ha_ut_box + [ent]

		lst = StringVar()
		ent = Entry(row, width = 6)
		ent.pack(side = LEFT, expand = YES, fill = X)
		ent.config(textvariable = lst)
		ha_lst = ha_lst + [lst]
		ha_lst_box = ha_lst_box + [ent]

		ha = StringVar()
		ent = Entry(row, width = 6)
		ent.pack(side = LEFT, expand = YES, fill = X)
		ent.config(textvariable = ha)
		ha_ha = ha_ha + [ha]
		ha_ha_box = ha_ha_box + [ent]

		airm = StringVar()
		ent = Entry(row, width = 7)
		ent.pack(side = LEFT, expand = YES, fill = X)
		ent.config(textvariable = airm)
		ha_airm = ha_airm + [airm]
		ha_airm_box = ha_airm_box + [ent]

		moonalt = StringVar()
		ent = Entry(row, width = 6)
		ent.pack(side = LEFT, expand = YES, fill = X)
		ent.config(textvariable = moonalt)
		ha_moonalt = ha_moonalt + [moonalt]
		ha_moonalt_box = ha_moonalt_box + [ent]

		sunalt = StringVar()
		ent = Entry(row, width = 6)
		ent.pack(side = LEFT, expand = YES, fill = X)
		ent.config(textvariable = sunalt)
		ha_sunalt = ha_sunalt + [sunalt]
		ha_sunalt_box = ha_sunalt_box + [ent]

	havars = [ha_local,ha_ut,ha_lst,ha_ha,ha_airm,ha_moonalt,ha_sunalt]
		
	row = Frame(hapan)
	row.pack(side = TOP)

	Button(row, text = 'Hide',command = (lambda: hawin.withdraw())).pack(side = LEFT)
	Button(row, text = 'Dump to file "skycalc.out"',command = (lambda i=invars,h=havars : \
			printhatable(i,h))).pack(side = LEFT)

	return [havars, \
		[ha_local_box,ha_ut_box,ha_lst_box,ha_ha_box,ha_airm_box,ha_moonalt_box,ha_sunalt_box]] 

#coofields = ('Current RA:','Current dec:','equinox:',
#  'Proper motion','PM is:','RA (pm only)','Dec (pm only)','equinox:',
#  'Ecliptic latitude','Ecliptic longitude','Galactic latitude',
#  'Galactic longitude') 

def makecooform(coowin,coofields) :
	
	coovars = []
	cooboxes = []
	
	coopan = Frame(coowin)
	coopan.pack(side = LEFT)

	inputfields = ["Proper motion","input epoch","Galactic longitude", \
		"Galactic latitude"]

	for field in coofields :
		row = Frame(coopan)
		lab = Label(row,width=18,text=field)
		var = StringVar()
		row.pack(side = TOP, fill = X, expand = YES)
		if field == "Proper motion" : var.set("0.  0.       [mas/yr]")
		if field == "input epoch" : var.set("2000.")
		if field == "PM is:" : 
			lab.pack(side = LEFT)
			but = Radiobutton(row,text="dX/dt",variable = var,
				value = 'x')
			but.pack(side = LEFT, expand = YES, fill = X)
			but = Radiobutton(row,text= "d(alpha)/dt",variable=var,
				value = 'a')
			but.pack(side = LEFT, expand = YES, fill = X)
			but = Radiobutton(row,text= "mu/theta",variable=var,
				value = 'p')
			but.pack(side = LEFT, expand = YES, fill = X)
			var.set('x')
			# print "var set to", var.get()
			cooboxes = cooboxes + [None]
		else :
			ent = Entry(row, width=21)
			lab.pack(side = LEFT, anchor = W)
			ent.config(textvariable = var)
			try :
				ind = inputfields.index(field)
				ent.config(bg = incolor1)  # globally defined
			except :
				pass
			ent.pack(side = LEFT)
			cooboxes = cooboxes + [ent]

		coovars = coovars + [var]

		
	Button(coopan, text = 'Hide', command=(lambda: coowin.withdraw())).pack(side = TOP)

	return [coovars, cooboxes]

# 0, 1, 2 -> Current RA, dec, and equinox
# 3 -> proper motion (two fields)
# 4 -> 1 = proper motion is dX/dt, 0 = proper motion is dalpha/dt
# 5 -> actual epoch of input coords
# 6, 7, 8 -> PM adjusted RA, and dec, and input equinox repeated
# 9, 10 -> ecliptic latitude and longitude
# 10, 11 -> Galactic latitude and longitude

def fillcooform(coovars) :


	scratch = deepcopy(obs)
	currentep = scratch.julian_epoch()   

	pmoption = coovars[4].get()	
	# print "pmoption = ",pmoption
	inputep = float(coovars[5].get())
	
	delta_ep = currentep - inputep
	cosdelta = math.cos(scratch.dec.radian())
	# print "cosdelta = ",cosdelta
	mas_per_hr = 5.40e7
	mas_per_deg = 3.60e6

	x = string.split(coovars[3].get())
	try :
		pm1 = float(x[0])
		pm2 = float(x[1])
	except :
		print "Cannot parse proper motion, two fields needed."
		pm1 = 0.
		pm2 = 0.

	# print "pm1 pm2 ",pm1,pm2
	
	if (pm1 != 0. or pm2 != 0.) and cosdelta > 0.0001 :
		if pmoption == 'x'  :  # dX/dt, dY/dt
			dra = delta_ep * pm1 / (mas_per_hr * cosdelta)
			scratch.ra.val = scratch.ra.val + dra 
			ddec = delta_ep * pm2 / mas_per_deg
			scratch.dec.val = scratch.dec.val + ddec 
		elif pmoption == 'a' : # d(alpha)/dt, dY/dt
			dra = delta_ep * pm1 / mas_per_hr
			scratch.ra.val = scratch.ra.val + dra
			ddec = delta_ep * pm2 / mas_per_deg
			scratch.dec.val = scratch.dec.val + ddec
		elif pmoption == 'p' :
			theta = pm2 / 57.2957795130823
			dra = delta_ep * pm1 * math.sin(theta) / (mas_per_hr * cosdelta)
			ddec = delta_ep * pm1 * math.cos(theta) / mas_per_deg
			scratch.ra.val = scratch.ra.val + dra
			scratch.dec.val = scratch.dec.val + ddec
	#	print "adjusting dra ddec = ",dra,ddec

	if cosdelta == 0. :
		print "Can't adjust for proper motion, dec = +- 90!"
		
 	outcoo = scratch.precess(scratch.julian_epoch())
	coovars[0].set(outcoo.ra.tripletstring(showsign = 0))
	coovars[1].set(outcoo.dec.tripletstring(showsign = 1,places = 1))
	coovars[2].set("%8.3f" % outcoo.equinox)
	# input equinox, but current epoch ... 
	coovars[6].set(scratch.ra.tripletstring(showsign = 0))
	coovars[7].set(scratch.dec.tripletstring(showsign = 1,places = 1))
	coovars[8].set("%8.3f" % scratch.equinox)
	ecliptcoo = scratch.eclipt()
	galactcoo = scratch.galact()
	coovars[9].set("%6.2f" % ecliptcoo[2])
	coovars[10].set("%6.2f" % ecliptcoo[1])
	coovars[11].set("%6.2f" % galactcoo[1])
	coovars[12].set("%6.2f" % galactcoo[0])
	coovars[13].set("%6.3f   %6.3f" % (scratch.par_dra,scratch.par_ddec))

def makealmform(almwin, almfields) :
	
	almvars = []
	
	almpan = Frame(almwin)
	almpan.pack(side = LEFT)
	
	for field in almfields :
		row = Frame(almpan)
		lab = Label(row,width=12,text=field)
		var = StringVar()
		ent = Entry(row, width=21)
		row.pack(side = TOP, expand = YES)
		lab.pack(side = LEFT, anchor = W)
		ent.config(textvariable = var)
		ent.pack(side = LEFT)
		almvars = almvars + [var]
	
	Button(almpan, text = 'Hide', command=(lambda: almwin.withdraw())).pack(side = TOP)

	return almvars

	
# 0 = sunset, 1 = eve twi, 3 = night center, 4 = morn. twilight, 5 = sunrise,
# 6, 7 = moon rise and/or set in time order.

def fillalmform(almvars) :

	if obs.jdsunset > 10000. :   # sunrise and set do occur
		almvars[0].set(obs.calstring(style = 2, jd_override = obs.jdsunset,
			stdz = obs.stdz, use_dst = obs.use_dst))
		almvars[4].set(obs.calstring(style = 2, jd_override = obs.jdsunrise,
			stdz = obs.stdz, use_dst = obs.use_dst))
		almvars[2].set(obs.calstring(style = 2, jd_override = obs.jdcent,
			stdz = obs.stdz, use_dst = obs.use_dst))
	elif obs.jdsunset > 0 :
		almvars[0].set("Sun up all night")
		almvars[2].set("Sun up all night")
		almvars[4].set("Sun up all night")
	else :
		almvars[0].set("Sun never rises.")
		almvars[2].set("Sun never rises.")
		almvars[4].set("Sun never rises.")
		
	if obs.jdevetwi > 10000. : # twilight does occur 
		almvars[1].set(obs.calstring(style = 2, jd_override = obs.jdevetwi,
			stdz = obs.stdz, use_dst = obs.use_dst))
		almvars[2].set(obs.calstring(style = 2, jd_override = obs.jdcent,
			stdz = obs.stdz, use_dst = obs.use_dst))
		# print obs.calstring(jd_override=obs.jdmorntwi)
		almvars[3].set(obs.calstring(style = 2, jd_override = obs.jdmorntwi,
			stdz = obs.stdz, use_dst = obs.use_dst))
	elif obs.jdevetwi > 0. :
		almvars[1].set("Twilight doesn't end.")
		almvars[3].set("Twilight doesn't begin.")
	else :
		almvars[1].set("No twilight.")
		almvars[3].set("No twilight.")

	moonrisestring = "Rise: " + obs.calstring(style = 2, jd_override = obs.jdmoonrise,
		stdz = obs.stdz, use_dst = obs.use_dst)
	moonsetstring = " Set: " + obs.calstring(style = 2, jd_override = obs.jdmoonset,
		stdz = obs.stdz, use_dst = obs.use_dst)

	if obs.jdmoonrise > 1000000. :
		if obs.jdmoonrise < obs.jdmoonset :
			risevar = 5
			setvar = 6
		else :
			risevar = 6
			setvar = 5
		if abs(obs.jdmoonrise - obs.jdcent) < 0.5 :
			almvars[risevar].set(moonrisestring)
		else :
			almvars[risevar].set("---")
		if abs(obs.jdmoonset - obs.jdcent) < 0.5 :
			almvars[setvar].set(moonsetstring)
		else :
			almvars[setvar].set("---")
	else :
		if abs(obs.jdmoonrise -1000.) < 0.01 :
			moonrisestring = "Moon may stay up?"
		elif abs(obs.jdmoonrise - -1000.) < 0.01 :
			moonrisestring = "Moon may stay down?"
		elif abs(obs.jdmoonrise - -100.) < 0.01 :
			moonrisestring = "Moonrise calcn error"
		if abs(obs.jdmoonset -1000.) < 0.01 :
			moonsetstring = "Moon may stay up?"
		elif abs(obs.jdmoonset - -1000.) < 0.01 :
			moonsetstring = "Moon may stay down?"
		elif abs(obs.jdmoonset - -100.) < 0.01 :
			moonsetstring = "Moonset calcn error"
		almvars[5].set(moonrisestring)
		almvars[6].set(moonsetstring)

def makesiteform(sitewin, sitevar) :

	sitepan = Frame(sitewin)
	sitepan.pack(side = LEFT)
	# root = Frame(win)
	# root.pack()
	row = Frame(sitepan)
	# lab = Label(row,text = "Site menu")
	row.pack(side = TOP)
#	lab = Label(row,text = "(Takes effect on refresh.)")
#	lab.pack(side = TOP)
	# lab.pack(side = TOP)

	for k in obs.obsdir.keys() :
		but = Radiobutton(sitepan,text = obs.obsdir[k][6], variable = sitevar,
					value = k)
		but.pack(side = TOP, anchor = W)
	but = Radiobutton(sitepan,text = "Other (allow user entries)", variable = sitevar,
					value = 'x')	
	but.pack(side = TOP, expand = YES, fill = X)

	Button(sitepan, text = 'Hide',command = (lambda: sitewin.withdraw())).pack(side = TOP)
	sitevar.set('k')

def makeoutform(root, fields) :
	
	variables = []
	entryboxes = []

	calstr = obs.calstring(style = 1, stdz = obs.stdz, use_dst = obs.use_dst) 
	x = string.split(calstr)
	ymd = x[0] + " " + x[1] + " " + x[2]
	hms = x[3] + " " + x[4] + " " + x[5]

	row = Frame(root)
	lab = Label(row, text = "Output Variables")
	row.pack(side = TOP)
	lab.pack(side = TOP)
	
	for field in fields :
		row = Frame(root)
		lab = Label(row, width=12, text = field)
		ent = Entry(row, width=23)
		row.pack(side = TOP, fill = X, expand = YES)
		lab.pack(side = LEFT)
		ent.pack(side=RIGHT, expand = YES, fill = X)
		if field == "jd" :  # signal it's an input ...
			ent.configure(bg = "#c5e5ac")
		var = StringVar()
		ent.config(textvariable = var)
		variables.append(var)
		entryboxes.append(ent)
	return (variables, entryboxes)

# This function is bound to a carriage-return in the JD box, which forces
# the JD to the value you enter.
	
def force_jd(jdindex,variables,outvars,havars,almvars,coovars,planetvars,
		boxes,haboxes,planetboxes) :

	testin = float(outvars[jdindex].get())
	if testin > 2488069. :
		print "Bad JD input, past 2099."
		return()
	elif testin < 2415388. :
		print "Bad JD input, before 1901."
		return()
	else : obs.jd = testin

 	if variables[6].get() == 'y' :
		calstr = obs.calstring(style = 1, stdz = obs.stdz, use_dst = obs.
			use_dst, print_day = 1, daycomma = 0) 
	else :
		calstr = obs.calstring(style = 1, print_day = 1, daycomma = 0)

	[ymd,hms] = ymd_hms_string(calstr)
	variables[4].set(ymd)
	circumstances(variables,outvars,havars,almvars,coovars,planetvars,
		boxes,haboxes,planetboxes) 
	variables[5].set(hms)

# This function sets the coords in the main window to galactic coords
# entered in the coordinate window.  It will be bound to carriage 
# returns in either of those boxes.

def force_galact(variables,outvars,havars,almvars,coovars,planetvars,
		boxes,haboxes,planetboxes) :

	glongin = float(coovars[12].get())
	glatin = float(coovars[11].get())
	equinox = float(variables[3].get())

	[ranew, decnew] = _skysub.gal2radec(glongin,glatin,equinox)
	obs.ra.val = ranew
	obs.dec.val = decnew
	
	variables[1].set(obs.ra.tripletstring(places=2,showsign=0) + "     hms")
	variables[2].set(obs.dec.tripletstring(places=1,showsign=1) + "     dms")

	circumstances(variables,outvars,havars,almvars,coovars,planetvars,
		boxes,haboxes,planetboxes) 


objs2000 = {}  # globally defined, for plotting

class ObjList(ScrolledList) :
	def __init__(self,names,objs,variables,parent) :
		self.lab = Label(parent,text = "Double click to select:")
		self.lab.pack(side = TOP)
		Frame.__init__(self,parent)
		self.parent = parent
		self.pack()
		self.makeWidgets(names)
		self.objs = objs
		self.objnames = names       # keep a list for sorting etc ... 
		self.objnames_orig = names[:]  # keep a copy in order
		self.variables = variables  # need to keep a copy with object ...
		self.pack()
		
		buttonpan = Frame(parent)
		buttonpan.pack(side=LEFT)
		row1 = Frame(buttonpan)
		row1.pack()
		self.but1 = Button(row1, text='Alphabetize', 
   			command=(lambda : self.alphabetical()))
		self.but1.pack(side = LEFT, fill=Y)
		self.but2 = Button(row1, text='List\nby RA', 
   			command=(lambda : self.by_ra()))
		self.but2.pack(side = LEFT)
		row2 = Frame(buttonpan)
		row2.pack()
		self.but3 = Button(row2, text='List by\nProximity', 
   			command=(lambda : self.by_proximity()))
		self.but3.pack(side = LEFT)
		self.but4 = Button(row2, text='Original\norder', 
   			command=(lambda : self.restore_order()))
		self.but4.pack(side = LEFT)
		row3 = Frame(buttonpan)
		row3.pack()
		self.but5 = Button(row3, text='Dismiss\nList', 
   			command=(lambda : self.deleteList()))
		self.but5.pack(side = LEFT)
	def handleList(self,event) :
		index = self.listbox.curselection()[0]
		label = self.listbox.get(index)
		self.variables[0].set(label)
		tempcoo = ra(self.objs[label][0])
		self.variables[1].set(tempcoo.tripletstring(places = 3, showsign=0))
		tempcoo = dec(self.objs[label][1])
		self.variables[2].set(tempcoo.tripletstring(places = 2,showsign=1))
		self.variables[3].set(self.objs[label][2])
		circumstances(self.variables, outvars, havars, almvars, 
		    coovars, planetvars, outboxes, haboxes, planetboxes)
	def deleteList(self) :
		# may be more than one list loaded, so deleted objs2000 
		# selectively ... 
		# print objs2000
		for k in self.objs.keys() :
			# print "about to del ... ",k,
			try :
				del objs2000[k]
				# print "deleted."
			except KeyError :   # if on overlapping list, it's already gone
				 # print "skipped."
				pass
		self.objs.clear()

		self.listbox.destroy()
		self.sb.destroy()
		self.but1.destroy()
		self.but2.destroy()
		self.but3.destroy()
		self.but4.destroy()
		self.but5.destroy()
		self.lab.destroy()
		self.parent.destroy()
	def alphabetical(self) :
		self.objnames.sort()
		self.listbox.delete(0,len(self.objnames))
		pos = 0
		for label in self.objnames :
			self.listbox.insert(pos,label)
			pos = pos + 1
	def restore_order(self) :
		self.objnames = self.objnames_orig[:]
		self.listbox.delete(0,len(self.objnames))
		pos = 0
		for label in self.objnames :
			self.listbox.insert(pos,label)
			pos = pos + 1
	def by_ra(self) :  # doesn't precess, but shouldn't matter much here.
		self.listbox.delete(0,len(self.objnames))
		radict = {} 
		for n in self.objnames :
			ra = self.objs[n][0]
			# print "ra = ",ra
			if radict.has_key(ra) == 0 : radict[ra] = n
			else :
				while radict.has_key(ra) == 1 :
					ra = ra + 0.000001
				radict[ra] = n
		
		pos = 0
		keysort = radict.keys()[:]
		keysort.sort()
		for r in keysort :
			self.listbox.insert(pos,radict[r])
			pos = pos + 1

	def by_proximity(self) :
		self.listbox.delete(0,len(self.objnames))
		proxdict = {}
		for n in self.objnames :
			[rainep, decinp] = _skysub.cooxform(
			  self.objs[n][0],self.objs[n][1],obs.equinox,
			  self.objs[n][2],1,0,0)
			prox = _skysub.subtend(rainep,decinp,obs.ra.val, obs.dec.val)
			if proxdict.has_key(prox) == 0 : proxdict[prox] = n
			else :
			   while proxdict.has_key(prox) == 1:
				prox = prox + 0.0000001
			   proxdict[prox] = n
		pos = 0
		keysort = proxdict.keys()
		keysort.sort()
		for r in keysort :
			self.listbox.insert(pos,proxdict[r])
			pos = pos + 1
			


class Objlistwin(Toplevel) :

	def __init__(self, invars) :
		objfile = askopenfilename()
		Toplevel.__init__(self)
		entries = Frame(self)
		objs = {}
		keylist = []
		for l in open(objfile,'r').readlines() :
			x = string.split(l)
			ra = coord(x[1] + ' ' + x[2] + ' ' + x[3]).val
			dec = coord(x[4] + ' ' + x[5] + ' ' + x[6]).val
			eq = float(x[7])
			# keep a globally-defined copy in equinox 2000
			tempcel = celest([ra,dec,eq])
			tempcel.selfprecess(2000)
			if objs2000.has_key(x[0]) == 0 :  #  avoid overlapping keys ... 
				objs2000[x[0]] = (tempcel.ra.val,tempcel.dec.val,tempcel.equinox)
				objs[x[0]] = (ra,dec,eq)
				keylist = keylist + [x[0]]
			else :
				trialkey = x[0]
				while objs2000.has_key(trialkey) == 1 :
					trialkey = '|' + trialkey + '|'
				objs2000[trialkey] = (tempcel.ra.val,tempcel.dec.val,tempcel.equinox)
				objs[trialkey] = (ra,dec,eq)
				keylist = keylist + [trialkey]
				# print "| ",x[0],"| loaded as |",trialkey,"|"
		objframe = ObjList(keylist, objs, invars , self)
	
def objbyname(variables,outvars,havars,almvars,coovars,planetvars,
		boxes,haboxes,planetboxes) :

	# given an object name typed into the "objname" field, looks to see if it's
	# on the list and then proceeds to load the object and update everything.

	name_in = variables[0].get()
	name_in = string.replace(name_in," ","")
	
	if len(objs2000) == 0 : pass
		# if there's no list open, a CR in the name field does 
		# nothing.  No need to scold the user in that case ...
	elif objs2000.has_key(name_in) :
		obs.ra.val = objs2000[name_in][0]
		variables[1].set(obs.ra.tripletstring(places=2,showsign=0) + "     hms")
		obs.dec.val = objs2000[name_in][1]
		variables[2].set(obs.dec.tripletstring(places=1,showsign=1) + "     dms")
		variables[3].set("%8.3f" % objs2000[name_in][2])
		circumstances(variables,outvars,havars,almvars,coovars,planetvars, 
			boxes,haboxes,planetboxes) 
	else :  # a list is open, but the name is wrong -- scold.
		variables[0].set("%s NOT FOUND!" % name_in)

def airmass_str(airmass, places = 2) :  # stupid little utility to format an airmass
	
	if airmass < 0. :
		return "(down)"
	elif airmass >= 10. :
		return " >10. "
	else :
		if places == 2 : return "%5.2f " % airmass
		if places > 2 : return "%6.3f" % airmass
		if places < 2 : return " %4.1f " % airmass
	
class text_table_win(Toplevel) :

	# transient window for computing predicted eclipse timings.

	def __init__(self, invars) :
		Toplevel.__init__(self)
		self.title('Skycalc: Text Tasks')
		entries = Frame(self)
#		fields = ['HJD eclipse','sigma(ecl)','P [d]','sigma(P)',
#			'start date (UT)','end date (UT)','max sunalt','max airmass',
#			'time step']
		fields = ['start date (UT)','end date (UT)','HJD eclipse','sigma(ecl)',
			'P [d]','sigma(P)', 'max sunalt','max airmass',
			'time step']
		# 0 = start, 1 = end, 2 = T0, 3 = sigT0, 4 = P, 5  = sigP, 
		# 6 = maxsunalt, 7 = maxairmass, 8 = timestep
		self.vars = []
		kount = 2
		for f in fields :
			if kount == 2 or f == fields[:-1] :
				row = Frame(entries) 
				row.pack(side = TOP, expand = YES)
				kount = 0
			lab = Label(row,width=14,text=f) 
			lab.pack(side = LEFT)
			var = StringVar()
			ent = Entry(row,width=21)
			ent.pack(side=LEFT,expand=YES,fill=X)
			ent.config(textvariable = var, bg = incolor1)
			self.vars = self.vars + [var]
			kount = kount + 1
			if f == 'HJD eclipse' :
				var.set('2453000.')
			if f == 'sigma(ecl)' :
				var.set('0.0001')
			if f == 'P [d]' :
				var.set('0.12345')
			if f == 'sigma(P)' :
				var.set('0.00001')
			if f == 'start date (UT)' :
				var.set('2005 Jan 1')
			if f == 'end date (UT)' :
				var.set('2005 Jan 5.')
			if f == 'max sunalt' :
				var.set('-12.')
			if f == 'max airmass' :
				var.set('3.')
			if f == 'time step' :
				var.set('1 h')
		entries.pack()
		buttonpan = Frame(self)
		buttonpan.pack()

		Button(buttonpan,text = "What's\nThis?",
			command = (lambda: self.showhelptext())).pack(side=LEFT,fill=Y)
		Button(buttonpan,text = "Seasonal\n observability",command = 
 			(lambda: self.compute_observability())).pack(side = LEFT)
		Button(buttonpan,text = "Compute\n times",command = 
 			(lambda: self.compute_eclipses())).pack(side = LEFT)
		Button(buttonpan,text = "Compute\n phases",command = 
 			(lambda: self.compute_phases())).pack(side = LEFT)
		Button(buttonpan,text = "Erase\n output",command = 
			(lambda: self.outwin.erasetext())).pack(side=LEFT)
		Button(buttonpan,text = "Dump output\n to 'skycalc.out'",
			command = 
			(lambda: self.outwin.dumptext('skycalc.out'))).pack(side=LEFT)
		Button(buttonpan,text = "Dismiss\n window",command = 
			(lambda: self.destroy())).pack(side = LEFT)
		entries.pack()
		self.outwin = ScrolledText(self)
		
	def compute_phases(self) :

		T0 = float(self.vars[2].get())
		sigT0 = float(self.vars[3].get())
		P = float(self.vars[4].get())
		sigP = float(self.vars[5].get())
		start = instant(self.vars[0].get())
		end = instant(self.vars[1].get())
		maxsunalt = float(self.vars[6].get())
		maxairmass = float(self.vars[7].get())

	        x = string.split(self.vars[8].get())
	        number = float(x[0])
	        mult = 1.
	        if len(x) > 1 :
	                unit = string.upper(x[1])
	                if string.find(unit,'S') == 0 : mult = 1. / 60.
	                if string.find(unit,'M') == 0 : mult = 1.
	                elif string.find(unit,'H') == 0 : mult = 60.
	                elif string.find(unit,'D') == 0 : mult = 1440.
	                elif string.find(unit,'W') == 0 : mult = 10800.
			elif string.find(unit,'Y') == 0 : mult = 525960.
	                        # mean month -- this is a "lunation".

	        timeincr = number * mult
	

		localfl = invars[6].get()   # 'y' or 'Y' for time-is-local

		scratch = deepcopy(obs)

		t = start.jd
		n = 0

		self.outwin.appendline(" ") 
		self.outwin.appendline("**** Phases for %s ****" % (invars[0].get()))
		self.outwin.appendline(" ") 
		self.outwin.appendline("T0 = HJD %16.7f +- %11.7f" % (T0,sigT0))
		self.outwin.appendline(" P = %16.9f +- %11.9f" % (P,sigP))
		self.outwin.appendline(" ") 
		self.outwin.appendline("Coordinates: %s" % (scratch.summarystring()))
		self.outwin.appendline(" ")
		templong = coord(scratch.longit * -15.)  # for output format
		templat = coord(scratch.lat)
		self.outwin.appendline("%s, longit. %s [dms E], lat. %s." \
			% (invars[8].get(),templong.tripletstring(showsign=1),
			   templat.tripletstring(showsign = 1)))
		self.outwin.appendline(" ")

		if localfl == 'y' or localfl == 'Y' :
			timetype = "Local "
		else :
			timetype = "   UT "
		headerline = "---" + timetype +  \
			"Date and time ---  phase del-ph  airm.  HA    moon-[alt]-sun "
		self.outwin.appendline(headerline)
		self.outwin.appendline(" ")
		
		nprint = 0
		maxlines = 500
		last_was_printed = 1 # or too many spaces. 
		while t < end.jd and nprint < maxlines:
			t = start.jd + n * timeincr / 1440. 
			[tcor, vcor] = _skysub.helcor(t,
				scratch.CoordsOfDate.ra.val,
				scratch.CoordsOfDate.dec.val,
				0., 0., 0.)
			thelio = t + tcor / 86400.
			cycles = (thelio - T0) / P
			phase = cycles - math.floor(cycles)
			sig = math.sqrt(sigT0 ** 2 + (cycles * sigP) ** 2)
			dphi = sig / P

			scratch.jd = t
			scratch.computesky()
			scratch.computesunmoon()
			#print "%5.0f %12.3f airm %5.2f alts %8.2f hanow %8.2f" % \
			# (n, tgeo, scratch.airmass, scratch.altsun, scratch.hanow.val)
			if maxairmass > 0. and scratch.altit > 0. and scratch.airmass < maxairmass :  
				airm_print = 1
			elif maxairmass < 0. :  # print all
				airm_print = 1
			else : airm_print = 0
			if scratch.altsun < maxsunalt and airm_print == 1:
				if last_was_printed == 0 :
					self.outwin.appendline(" ")	
				last_was_printed = 1
				hastr = scratch.hanow.tripletstring(showsign = 1, places = -2, delin = ':')
				if localfl == 'y' or localfl == 'Y' :
					calout = scratch.calstring(style = 1, 
						stdz = scratch.stdz, use_dst = scratch.use_dst,							timedelim = ":", print_day = 1,daycomma=1,
						 dayabbrev = 1)
				else :
					calout = scratch.calstring(style = 1, 
						timedelim = ":", print_day = 1,daycomma=1, 
						dayabbrev = 1)
				outline = "%s %6.3f %6.3f " % (calout, phase, dphi)
				if scratch.airmass < 10. and scratch.airmass > 0. :
				   outline = outline + "%5.2f " % scratch.airmass
				elif airmass > 0. :
				   outline = outline + " >10. "
				else : 
				   outline = outline + "down. "
				outline = outline + " %6s  %6.1f %6.1f" % \
					(hastr,scratch.altmoon,scratch.altsun)
				self.outwin.appendline(outline)
				nprint = nprint + 1

			else : last_was_printed = 0

			n = n + 1
			if nprint >= maxlines :
				self.outwin.appendline("Halted after %d lines ...." %
					(maxlines))

	def compute_eclipses(self) :

		T0 = float(self.vars[2].get())
		sigT0 = float(self.vars[3].get())
		P = float(self.vars[4].get())
		sigP = float(self.vars[5].get())
		start = instant(self.vars[0].get())
		end = instant(self.vars[1].get())
		maxsunalt = float(self.vars[6].get())
		maxairmass = float(self.vars[7].get())

		localfl = invars[6].get()   # 'y' or 'Y' for time-is-local

		scratch = deepcopy(obs)

		n = math.floor((start.jd - T0) / P) + 1.
		t = T0 + n * P

		self.outwin.appendline(" ") 
		self.outwin.appendline("**** Ephemeris for %s ****" % (invars[0].get()))
		self.outwin.appendline(" ") 
		self.outwin.appendline("T0 = HJD %16.7f +- %11.7f" % (T0,sigT0))
		self.outwin.appendline(" P = %16.9f +- %11.9f" % (P,sigP))
		self.outwin.appendline(" ") 
		self.outwin.appendline("Coordinates: %s" % (scratch.summarystring()))
		self.outwin.appendline(" ")
		templong = coord(scratch.longit * -15.)  # for output format
		templat = coord(scratch.lat)
		self.outwin.appendline("%s, longit. %s [dms E], lat. %s." \
			% (invars[8].get(),templong.tripletstring(showsign=1),
			   templat.tripletstring(showsign = 1)))
		self.outwin.appendline(" ")

		if localfl == 'y' or localfl == 'Y' :
			timetype = "Local "
		else :
			timetype = "   UT "
		headerline = "    N    ---" + timetype +  \
			"Date and time ---  del-t del-ph  airm.   HA  moon-[alt]-sun "
		self.outwin.appendline(headerline)
		self.outwin.appendline(" ")
		
		nprint = 0
		maxlines = 500
		last_was_printed = 1 # or too many spaces. 
		while t < end.jd and nprint < maxlines:
			t = T0 + n * P
			sig = math.sqrt(sigT0 ** 2 + (n * sigP) ** 2)
			dphi = sig / P
			dtmin = sig * 1440.

			[tcor, vcor] = _skysub.helcor(t,
				scratch.CoordsOfDate.ra.val,
				scratch.CoordsOfDate.dec.val,
				0., 0., 0.)
			tgeo = t - tcor / 86400.  # geocentric
			scratch.jd = tgeo
			scratch.computesky()
			scratch.computesunmoon()
			#print "%5.0f %12.3f airm %5.2f alts %8.2f hanow %8.2f" % \
			# (n, tgeo, scratch.airmass, scratch.altsun, scratch.hanow.val)
			if maxairmass > 0. and scratch.altit > 0. and scratch.airmass < maxairmass :  
				airm_print = 1
			elif maxairmass < 0. :  # print all
				airm_print = 1
			else : airm_print = 0
			if scratch.altsun < maxsunalt and airm_print == 1:
				if last_was_printed == 0 :
					self.outwin.appendline(" ")	
				last_was_printed = 1
				hastr = scratch.hanow.tripletstring(showsign = 1, places = -2, delin = ':')
				if localfl == 'y' or localfl == 'Y' :
					calout = scratch.calstring(style = 1, 
						stdz = scratch.stdz, use_dst = scratch.use_dst,							timedelim = ":", print_day = 1,daycomma=1,
						 dayabbrev = 1)
				else :
					calout = scratch.calstring(style = 1, 
						timedelim = ":", print_day = 1,daycomma=1, 
						dayabbrev = 1)
				outline = "%7.0f  %s %5.0fm %6.3f " % (n, calout, dtmin, dphi)
				if scratch.airmass < 10. and scratch.airmass > 0. :
				   outline = outline + "%5.2f " % scratch.airmass
				elif airmass > 0. :
				   outline = outline + " >10. "
				else : 
				   outline = outline + "down. "
				outline = outline + " %6s  %6.1f %6.1f" % \
					(hastr,scratch.altmoon,scratch.altsun)
				self.outwin.appendline(outline)
				nprint = nprint + 1

			else : last_was_printed = 0

			n = n + 1
			if nprint >= maxlines :
				self.outwin.appendline("Halted after %d lines ...." %
					(maxlines))

	def compute_observability(self) :

		start = instant(self.vars[0].get())
		end = instant(self.vars[1].get())
#		maxsunalt = float(self.vars[6].get())

		scratch = deepcopy(obs)

		self.outwin.appendline(" ") 
		self.outwin.appendline("**** Seasonal Observability for %s ****" % (invars[0].get()))
		self.outwin.appendline(" ") 
		self.outwin.appendline("Coordinates: %s" % (scratch.summarystring()))
		self.outwin.appendline(" ")
		templong = coord(scratch.longit * -15.)  # for output format
		templat = coord(scratch.lat)
		self.outwin.appendline("%s, longit. %s [dms E], lat. %s." \
			% (invars[8].get(),templong.tripletstring(showsign=1),
			   templat.tripletstring(showsign = 1)))
		self.outwin.appendline(" ")
		self.outwin.appendline("--Moon, date--     @eve twi:       @nght ctr:     @morn twi:   nght hrs @airm:")
		self.outwin.appendline("                    HA   airm       HA   airm      HA   airm     <3    <2  <1.5")
		self.outwin.appendline(" ") 

		# get min and max alt for coords of middle of interval
		meanjd = (start.jd + end.jd) / 2.
		scratch.jd = meanjd
		scratch.computesky()
		[min_alt, max_alt] = _skysub.min_max_alt(scratch.lat, 
			scratch.CoordsOfDate.dec.val)
	
		# find first new or full after start.jd
		[lunar_age,lunation] = _skysub.lun_age(start.jd)
		#print "age, lunation for start ",lunar_age,lunation
		nph = 2
		lunation = lunation - 1
		jdlist = 1.
		#print 'start.jd = ',start.jd,' lunation = %d',lunation
		while jdlist < start.jd :
			nph = nph + 2
			if nph == 4 :
				lunation = lunation + 1
				nph = 0

			jdlist = _skysub.flmoon(lunation,nph)
			test = instant(jdlist)
		#	print "lun, nph ",lunation,nph," jdlist ",jdlist," = ",test.calstring()

		# back it up ...

		if nph == 2 : nph = 0
		else :
		   lunation = lunation - 1
		   nph = 2
		
		# now loop through until we're off the end ... 
		while jdlist < end.jd :
			nph = nph + 2
			if nph == 4 :
				lunation = lunation + 1
				nph = 0
				outline = "N: "
			else :
				outline = "F: "
			jdlist = _skysub.flmoon(lunation,nph)
			if jdlist > end.jd : break
		
			scratch.jd = jdlist
#			self.outwin.appendline("lunation %d nph %d - %s" % \
#				(lunation,nph,scratch.calstring(style=2)))


			scratch.jd = jdlist
			scratch.computesky()
			scratch.computesunmoon()

			if scratch.jdevetwi > 1000000. :
				scratch.jd = scratch.jdevetwi
				scratch.computesky()
				evedescr =  "  %6s %6s " % \
			 	 (scratch.hanow.tripletstring(showsign=1,places=-2, delin=":"),
			   	  airmass_str(scratch.airmass,places=1))
			else :  # twilight never ends (or begins, right around pole)
				scratch.jd = scratch.jdmid - 0.1
				if scratch.jdevetwi < 0. :
				    evedescr = " twi.all.nght! "
				else :
				    evedescr = "  no.twilght!  "
			# grab date at eve twilight for output
			outline = outline + scratch.calstring(stdz=scratch.stdz,
				use_dst=scratch.use_dst,style = 3) + " "
			# and stuff the evening description after the date:
			outline = outline + evedescr
	
			scratch.jd = scratch.jdcent
			scratch.computesky()
			hacent = scratch.hanow.val
			#print outline
			#print "  %6s %6s " % \
			# (scratch.hanow.tripletstring(showsign=1,places=-2,delin=":"),
			#   airmass_str(scratch.airmass,places=1))

			outline = outline + "  %6s %6s" % \
			 (scratch.hanow.tripletstring(showsign=1,places=-2,delin=":"),
			    airmass_str(scratch.airmass,places=1))
			
			if scratch.jdmorntwi > 1000000. :
				scratch.jd = scratch.jdmorntwi
				scratch.computesky()
				outline = outline + "  %6s %6s" % \
			 	 (scratch.hanow.tripletstring(showsign=1,places=-2, delin=":"),
			   	  airmass_str(scratch.airmass,places=1))
			else :
				if scratch.jdmorntwi < 0. :
				    outline = outline + "  twi.all.nght! "
				else :
				    outline = outline + "   no.twilght!  "

			# compute jd's at which object passes 3, 2, and 1.5 airm 
			# on either side of transit.

			# jd of transit nearest to midnight.
			jdtrans = scratch.jdcent - hacent / (_skysub.SID_RATE * 24.)

			if min_alt < _skysub.ALT_3 and max_alt > _skysub.ALT_3 :
			# if dec is such that it passes airmass 3:
				dt3 = _skysub.ha_alt(scratch.dec.val,scratch.
					lat,_skysub.ALT_3)/ (_skysub.SID_RATE * 24.)
				jd3_1 = jdtrans - dt3
				jd3_2 = jdtrans + dt3
			else :
				jd3_1 = 0.; jd3_2 = 0.
				if min_alt < _skysub.ALT_3 : dt3 = 0.
				else : dt3 = 12.

			if min_alt < _skysub.ALT_2 and max_alt > _skysub.ALT_2 :
			# if dec is such that it passes airmass 2:
				dt2 = _skysub.ha_alt(scratch.dec.val,scratch.
					lat,_skysub.ALT_2)/ (_skysub.SID_RATE * 24.)
				jd2_1 = jdtrans - dt2
				jd2_2 = jdtrans + dt2
			else :
				jd2_1 = 0.; jd2_2 = 0.
				if min_alt < _skysub.ALT_2 : dt2 = 0.
				else : dt2 = 12.

			if min_alt < _skysub.ALT_15 and max_alt > _skysub.ALT_15 :
			# if dec is such that it passes airmass 1.5:
				dt15 = _skysub.ha_alt(scratch.dec.val,scratch.
					lat,_skysub.ALT_15)/ (_skysub.SID_RATE * 24.)
				jd15_1 = jdtrans - dt15
				jd15_2 = jdtrans + dt15
			else :
				jd15_1 = 0.; jd15_2 = 0.
				if min_alt < _skysub.ALT_15 : dt15 = 0.
				else : dt15 = 12.

			if scratch.jdevetwi > 1000000. :
				if jd2_1 != 0. :
					hrs_2 = _skysub.hrs_up(jd2_1,jd2_2,scratch.jdevetwi,
						   scratch.jdmorntwi)
				elif min_alt > _skysub.ALT_2 :  # always up
					hrs_2 = 24. * (scratch.jdmorntwi - scratch.jdevetwi)
				else : hrs_2 = 0.  # never up.

				if jd3_1 != 0. :
					hrs_3 = _skysub.hrs_up(jd3_1,jd3_2,scratch.jdevetwi,
						   scratch.jdmorntwi)
				elif min_alt > _skysub.ALT_3 :  # always up
					hrs_3 = 24. * (scratch.jdmorntwi - scratch.jdevetwi)
				else : hrs_3 = 0.  # never up.

				if jd15_1 != 0. :
					hrs_15 = _skysub.hrs_up(jd15_1,jd15_2,scratch.jdevetwi,
						   scratch.jdmorntwi)
				elif min_alt > _skysub.ALT_15 :  # always up
					hrs_15 = 24. * (scratch.jdmorntwi - scratch.jdevetwi)
				else : hrs_15 = 0.  # never up.

			elif scratch.jdevetwi > 0. :  # never gets dark
				hrs_2 = 0.; hrs_3 = 0.; hrs_15 = 0.;
			else :  # it never gets light ...
				hrs_2 = 2 * dt2; hrs_3 = 2 * dt3; hrs_15 = 2 * dt15

			outline = outline + "  %4.1f  %4.1f  %4.1f" % (hrs_3,hrs_2,hrs_15)
			
#			self.outwin.appendline("HA airm: eve %5.2f %5.2f  cent %5.2f %5.2f  morn %5.2f %5.2f" % (haeve.val,alteve,hacent.val,altcent,hamorn.val,altmorn))

			self.outwin.appendline(outline)
			
			

	def showhelptext(self) :
		helptext = """
This window is for computations which create tables of text output.
Once you're happy with the output, you can dump the contents 
to a text file "skycalc.out".  The screen is a primitive text
editor, so you can annotate your output directly if you like.

The calculations take the object coordinates and site info
from the main window, and (obviously) use other information from 
the fields on this window.

"Seasonal observability" tabulates circumstances for your object
at each new and full moon between the start and end dates.  Hour angle
and airmass are printed at three times of night: evening (18 degree) 
twilight, night center, and morning twilight.  After that comes 
the number of hours per night in which (a) there is no twilight, 
and (b) the object is less than a given airmass; tabulated
values are for 3, 2, and 1.5 airmasses.  This information is 
useful in planning observing time requests.  Of the information 
entered here, only start and end dates are used.

The "Compute times" option gives observed times of a strictly
periodic phenomeon, e.g. predicted binary star eclipse times.  
All the information in the form on this page is used, except for 
the time step.  The "Compute phases" option gives the phase at 
the interval specified by the time step.

To use these, enter the heliocentric (or more correctly the
BARYcentric) JD (e.g. of an observed eclipse) and its sigma, and 
the period and its sigma.  You can optionally filter output to 
pertain only to that visible from your site, by giving a maximum 
airmass (-1 is code for don't filter) and a maximum sun altitude 
(e.g. +90 doesn't filter, -18 filters to only events after 
twilight).  Times are local or UT depending on how the flag is set 
in the main window (but input ephemerides are always barycentric
julian dates).  The output is in the GEOCENTRIC time system, i.e. 
the time the signal arrives at earth, The period and JD errors 
are propagated to give phase and/or time uncertainties as appropriate. 
Don't neglect the uncertainties -- when they amount to an 
appreciable fraction of a cycle, the ephemeris is basically worthless.

[Note - barycentric and heliocentric times are the same within
a few seconds, because the solar system barycenter stays 
mostly within the body of the sun, which is about 2.3 light 
seconds in radius].
"""

		self.outwin.settext(helptext)

def showhelptext(parentframe = None) :
	helpwin = ScrolledText(parentframe)
	
root = Tk()
root.title("Sky Calculator by John Thorstensen, Dartmouth College")
toppan = Frame(root)
toppan.pack(side = TOP)
bottompan = Frame(root)
bottompan.pack(side = BOTTOM)
leftpan = Frame(toppan)
leftpan.pack(side = LEFT, expand = YES, fill=X, anchor=N)
(invars,StepBox,ObjBox) = makeinform(leftpan,infields)

rightpan = Frame(toppan)
rightpan.pack(side = LEFT, expand = YES, fill = X)
(outvars,outboxes) = makeoutform(rightpan,outfields)

hawin = Toplevel()
hawin.title("Hourly Airmass")
(havars,haboxes) = makehaform(hawin) 
# hawin.withdraw()

almwin = Toplevel()
almwin.title("Nightly Almanac")
almvars = makealmform(almwin,almfields)
almwin.withdraw()

coowin = Toplevel()
coowin.title("Coordinates ...")
[coovars, cooboxes] = makecooform(coowin,coofields)
# fillcooform(coovars)
coowin.withdraw()

planetwin = Toplevel()
planetwin.title("Planets (Low-Precision)")
(planetvars, planetboxes) = makeplanetform(planetwin)
planetwin.withdraw()
# fillplform(planetvars, planetboxes)

# print "calling circumstances ... "
circumstances(invars,outvars,havars,almvars,coovars, planetvars, 
	outboxes, haboxes, planetboxes)
# print "returned, invars[2].get() = ",invars[2].get()

sitewin = Toplevel()
sitewin.title("Site menu")
makesiteform(sitewin,invars[17])

topbuttonpan = Frame(bottompan)
# buttonpan.pack(side=BOTTOM)
topbuttonpan.pack(side=TOP)
Button(topbuttonpan, text = 'Refresh\n output',
   command = (lambda v=invars,o=outvars,h=havars,a=almvars,c=coovars,
      p=planetvars,b=outboxes,hb=haboxes,pb=planetboxes: 
	circumstances(v,o,h,a,c,p,b,hb,pb))).pack(side=LEFT)
Button(topbuttonpan, text = 'Step\n time',
   command = (lambda v=invars,o=outvars,h=havars,a=almvars,c=coovars,
      p=planetvars,b=outboxes,hb=haboxes,pb=planetboxes: 
	steptime(v,o,h,a,c,p,b,hb,pb))).pack(side=LEFT)
Button(topbuttonpan, text = 'Set to\n now',
   command = (lambda v=invars,o=outvars,h=havars,a=almvars,c=coovars,
      p=planetvars,b=outboxes,hb=haboxes,pb=planetboxes: 
	set_to_now(v,o,h,a,c,p,b,hb,pb))).pack(side=LEFT)
Button(topbuttonpan, text = 'UT <->\n local',
   command = (lambda v=invars,o=outvars,h=havars,a=almvars,c=coovars,
     p=planetvars,b=outboxes,hb=haboxes,pb=planetboxes: 
	convert_time(v,o,h,a,c,p,b,hb,pb))).pack(side=LEFT,fill=Y)
#Button(topbuttonpan, text = 'Planets',
#   command = (lambda : planetwin.deiconify()),width=4).pack(side=LEFT,fill=Y)

def win_raise(window) : 
	# takes a pre-existing, possibly iconified window and either
	# de-iconifies it or raises it (the .lift() method) if it's 
	# hidden behind other windows.  This is a nice behavior.
	if window.state() == 'normal' : 
		window.lift()
	else : 
		geotmp = window.geometry()  # it's saved when window is withdrawn
		window.deiconify()          # takes no arguments ... 
		if geotmp != '1x1+0+0' :    # never-popped windows are zero size
			window.geometry(geotmp)     # put it back where it was!

# print "DSwin up, invars[2].get() = ",invars[2].get()

bottombuttonpan = Frame(bottompan)
bottombuttonpan.pack(side = TOP)
Button(topbuttonpan, text = 'Site\n menu',
   command = (lambda w = sitewin : win_raise(w)),width=4).pack(side=LEFT)
Button(bottombuttonpan, text = 'Hourly\n Airmass',
   command = (lambda w = hawin: win_raise(w)),width=6).pack(side=LEFT)
#   command = (lambda : hawin.deiconify()),width=6).pack(side=LEFT)
Button(bottombuttonpan, text = 'Nightly\n Almanac',
   command = (lambda w = almwin: win_raise(w)),width=6).pack(side=LEFT)
Button(bottombuttonpan, text = 'Planets',
   command = (lambda w = planetwin : win_raise(w)),width=4).pack(side=LEFT,fill=Y)
Button(bottombuttonpan, text = 'Alt.\nCoords',
   command = (lambda w = coowin : win_raise(w)),width=5).pack(side=LEFT)
Button(bottombuttonpan, text = 'Plane-\ntarium',
   command = (lambda : plotsky('/xwin',1)),width=4).pack(side=LEFT,fill=Y)
#Button(bottombuttonpan, text = 'Plane-\ntarium',
#   command = (lambda : plotsky('/xwin',1)),width=4,bg='black',
#	fg='white').pack(side=LEFT,fill=Y)

lowerbuttonpan = Frame(bottompan)

lowerbuttonpan.pack(side=TOP)

Button(bottombuttonpan, text = 'Text\nTables',
   command = (lambda v = invars : text_table_win(v)),width=5).pack(side=LEFT)

#objlistwin = Toplevel()
#objlistwin.title("Object list")
#objlistparent = Frame(objlistwin)
#objlistparent.pack()
#objlistwin.withdraw()

# objlistparent = toppan
Button(bottombuttonpan, text='Get object\nlist', 
   command=(lambda v =invars : 
    Objlistwin(v)),width=7).pack(side=LEFT)

quitbutton = Quitter(bottombuttonpan).pack(side=LEFT,fill=Y)

helpwin = Toplevel()
makehelpframe(helpwin,helptext)
helpwin.withdraw()

refwin = Toplevel()
makehelpframe(refwin,referenceman)
refwin.withdraw()

# print "ref and help up, invars[2].get() = ",invars[2].get()
# invars[2].set('gaak!')

Button(topbuttonpan, text = 'Help\nText', command = \
  (lambda w = helpwin : win_raise(w))).pack(side=LEFT)

Button(topbuttonpan, text = 'Reference\nManual', command = \
  (lambda w = refwin : win_raise(w)),width=7).pack(side=LEFT)

root.bind('<Return>',(lambda event,v=invars,o=outvars,h=havars,a=almvars,
  c=coovars,p=planetvars,b=outboxes,hb=haboxes,pb=planetboxes: 
	circumstances(v,o,h,a,c,p,b,hb,pb)))

coowin.bind('<Return>',(lambda event,v=invars,o=outvars,h=havars,a=almvars,
  c=coovars,p=planetvars,b=outboxes,hb=haboxes,pb=planetboxes: 
	circumstances(v,o,h,a,c,p,b,hb,pb)))

outboxes[5].bind('<Return>',(lambda event,v=invars,o=outvars,h=havars,a=almvars,
  c=coovars,p=planetvars,b=outboxes,hb=haboxes,pb=planetboxes: 
	force_jd(5,v,o,h,a,c,p,b,hb,pb)))

cooboxes[11].bind('<Return>',(lambda event,v=invars,o=outvars,h=havars,a=almvars,
  c=coovars,p=planetvars,b=outboxes,hb=haboxes,pb=planetboxes: 
	force_galact(v,o,h,a,c,p,b,hb,pb)))

cooboxes[12].bind('<Return>',(lambda event,v=invars,o=outvars,h=havars,a=almvars,
  c=coovars,p=planetvars,b=outboxes,hb=haboxes,pb=planetboxes: 
	force_galact(v,o,h,a,c,p,b,hb,pb)))

StepBox.bind('<Return>',(lambda event,v=invars,o=outvars,h=havars,a=almvars,
  c=coovars,p=planetvars,b=outboxes,hb=haboxes,pb=planetboxes: 
	steptime(v,o,h,a,c,p,b,hb,pb)))

root.bind('<Right>',(lambda event,v=invars,o=outvars,h=havars,a=almvars,
  c=coovars,p=planetvars,b=outboxes,hb=haboxes,pb=planetboxes: 
	steptime(v,o,h,a,c,p,b,hb,pb)))

root.bind('<Left>',(lambda event,v=invars,o=outvars,h=havars,a=almvars,
  c=coovars,p=planetvars,b=outboxes,hb=haboxes,pb=planetboxes: 
	steptime(v,o,h,a,c,p,b,hb,pb,-1.)))

sitewin.bind('<ButtonRelease>',(lambda event,v=invars,o=outvars,h=havars,a=almvars,
  c=coovars,p=planetvars,b=outboxes,hb=haboxes,pb=planetboxes:
        circumstances(v,o,h,a,c,p,b,hb,pb)))

ObjBox.bind('<Return>',(lambda event,v=invars,o=outvars,h=havars,a=almvars,
  c=coovars,p=planetvars,b=outboxes,hb=haboxes,pb=planetboxes:
        objbyname(v,o,h,a,c,p,b,hb,pb)))

root.mainloop()
