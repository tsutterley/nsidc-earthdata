#!/usr/bin/env python
u"""
nsidc_earthdata.py
Written by Tyler Sutterley (09/2017)
ftp-like program for searching NSIDC databases and retrieving data
This is a wrapper function for entering credentials and running the program

https://wiki.earthdata.nasa.gov/display/EL/How+To+Access+Data+With+Python
https://nsidc.org/support/faq/what-options-are-available-bulk-downloading-data-
	https-earthdata-login-enabled
http://www.voidspace.org.uk/python/articles/authentication.shtml#base64

Register with NASA Earthdata Login system:
https://urs.earthdata.nasa.gov

Add NSIDC_DATAPOOL_OPS to NASA Earthdata Applications
https://urs.earthdata.nasa.gov/oauth/authorize?client_id=_JLuwMHxb2xX6NwYTb4dRA

COMMAND LINE OPTIONS:
	help: List the following command line options
	ls: List contents of the remote directory
	cd: Change the remote directory
	lcd: Change the local directory
	mkdir: Create a directory within the local directory
	pwd: Print the current local and remote directory paths
	sync: Sync all files in directory with a local directory
	rsync: Recursively sync all directories with a local directory
	mget: Get all files in directory
	get: Get a single file in a directory
	verbose: Toggle verbose output of program
	exit: Exit program

PYTHON DEPENDENCIES:
	lxml: Pythonic XML and HTML processing library using libxml2/libxslt
		http://lxml.de/
		https://github.com/lxml/lxml

UPDATE HISTORY:
	Updated 09/2017: updated header text
	Written 08/2017
"""
from __future__ import print_function

import getpass
from earthdata import earthdata

#-- PURPOSE: ftp-like program for searching NSIDC databases and retrieving data
def main():
	#-- enter password securely from command-line
	EARTHDATA = 'urs.earthdata.nasa.gov'
	USER = raw_input('Username for {0}: '.format(EARTHDATA))
	PASSWORD = getpass.getpass('Password for {0}@{1}: '.format(USER,EARTHDATA))
	#-- run Earthdata program
	prompt = earthdata(USER,PASSWORD)

#-- run main program
if __name__ == '__main__':
	main()
