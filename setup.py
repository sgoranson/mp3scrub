#!/usr/bin/env python

from distutils.core import setup
try:
    import py2exe
except:
    'print no py2exe...but not needed for linux'

from glob import glob

setup(name='mp3scrub',
      version='1.1.6',
      data_files=[('.', glob(r'dlls\*.*'))],
      description='mp3 smart tag cleaner',
      author='Steve Goranson',
      author_email='stephen.goranson@gmail.com',
      url='http://1024.us/code',
      py_modules=['main'],
      packages=['mp3scrub', 'mp3scrub.util', 'mp3scrub.gui', 'mp3scrub.netquery'],
      windows = [{'script': 'main.py', 'icon_resources': [(1, 'mondrian.ico')]}], 
     )
