#!/usr/bin/env python

from distutils.core import setup,Extension

setup(name="skycalc",
	version="6.3",
	description="GUI skycalc programs",
	url="http://www.dartmouth.edu",
	author = "John Thorstensen",
	author_email = "John.Thorstensen@dartmouth.edu",
	scripts = ['skycalcgui.py','skycalcdisp.py'],
	py_modules=['cooclasses'],
	ext_modules=[Extension("_skysub",["_skysub.c","skysub_wrap.c"])],
	data_files=[('.',['skysub.h']),
                    ('share/skycalc',['brightest.dat'])])
