## A very simple makefile for skycalc and skycalendar
## To change installation directory from default, edit INSTALLDIR
## Otherwise, just type "make" and "make install", followed by
## "make clean" to destroy local copies.  In c-shell, "rehash" to
## activate.

skycalc : skycalc.c skycalendar.c
	cc skycalc.c -o skycalc -lm
	cc skycalendar.c -o skycalendar -lm


.PHONY : clean

clean : 
	-rm skycalc
	-rm skycalendar

.PHONY : install

INSTALLDIR = /usr/local/bin

install : skycalc skycalendar
	cp skycalc $(INSTALLDIR)
	cp skycalendar $(INSTALLDIR)

