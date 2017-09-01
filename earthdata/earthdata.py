#!/usr/bin/env python
u"""
earthdata.py
Written by Tyler Sutterley (09/2017)
ftp-like program for searching NSIDC databases and retrieving data

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
	quiet: Turn off verbose output
	exit: Exit program

PYTHON DEPENDENCIES:
	lxml: Pythonic XML and HTML processing library using libxml2/libxslt
		http://lxml.de/
		https://github.com/lxml/lxml

UPDATE HISTORY:
	Updated 09/2017: added option quiet to turn off verbose output. cd to root
	Written 08/2017
"""
from __future__ import print_function

import sys
import os
import re
import shutil
import lxml.etree
import posixpath
import urllib2, cookielib
import calendar, time

#-- PURPOSE: creates Earthdata class containing the main functions and variables
class earthdata(object):
	def __init__(self, USER, PASSWORD, parent=None):
		#-- NSIDC host for Pre-Icebridge and IceBridge data
		self.host = 'n5eil01u.ecs.nsidc.org'
		self.prompt = '> '
		self.intro = 'Welcome to {0}'.format(self.host)
		self.goodbye = 'Goodbye!'
		#-- remote https server for IceBridge Data (can cd to ../PRE_OIB)
		self.remote_directory = posixpath.join(self.host,"ICEBRIDGE")
		self.local_directory = os.getcwd()
		#-- flag to keep while loop running
		self.run = True
		#-- verbosity settings
		self.verbose = True
		#-- permissions mode of the local directories and files (in octal)
		self.mode = 0775
		#-- compile HTML parser for lxml
		self.parser = lxml.etree.HTMLParser()
		#-- python dictionary with valid functions
		functions = {}
		functions['help'] = self.usage
		functions['ls'] = self.list_directory
		functions['cd'] = self.change_remote_directory
		functions['lcd'] = self.change_local_directory
		functions['mkdir'] = self.make_local_directories
		functions['pwd'] = self.print_directory_paths
		functions['sync'] = self.sync_directory
		functions['rsync'] = self.rsync_directories
		functions['mget'] = self.mget_files
		functions['get'] = self.get_file
		functions['quiet'] = self.set_verbosity
		functions['exit'] = self.exit_program
		#-- create https opener for NASA Earthdata using supplied credentials
		self.https_opener(USER,PASSWORD)
		self.check_credentials()
		#-- print introductory message
		print(self.intro)
		#-- run program until exit or keyboard interrupt
		try:
			while self.run:
				tokens = raw_input(self.prompt).split()
				command = tokens[0]
				if command in functions.keys():
					functions[command](tokens[1:])
				else:
					print('ERROR: invalid command <{0}>'.format(command))
					self.usage()
		except KeyboardInterrupt:
		    pass
		#-- print goodbye message
		print(self.goodbye)

	#-- PURPOSE: "login" to NASA Earthdata with supplied credentials
	def https_opener(self,USER,PASS):
		#-- https://docs.python.org/2/howto/urllib2.html#id6
		#-- create a password manager
		password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
		#-- Add the username and password for NASA Earthdata Login system
		password_mgr.add_password(None,'https://urs.earthdata.nasa.gov',USER,PASS)
		#-- Encode username/password for request authorization headers
		base64_string = urllib2.base64.b64encode('{0}:{1}'.format(USER,PASS))
		#-- Create cookie jar for storing cookies. This is used to store and return
		#-- the session cookie given to use by the data server (otherwise will just
		#-- keep sending us back to Earthdata Login to authenticate).
		cookie_jar = cookielib.CookieJar()
		#-- create "opener" (OpenerDirector instance)
		opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(password_mgr),
		    #urllib2.HTTPHandler(debuglevel=1),  # Uncomment these two lines to see
		    #urllib2.HTTPSHandler(debuglevel=1), # details of the requests/responses
			urllib2.HTTPCookieProcessor(cookie_jar))
		#-- add Authorization header to opener
		opener.addheaders = [("Authorization", "Basic {0}".format(base64_string))]
		#-- Now all calls to urllib2.urlopen will use the opener.
		urllib2.install_opener(opener)
		#-- All calls to urllib2.urlopen will now use handler
		#-- Make sure not to include the protocol in with the URL, or
		#-- HTTPPasswordMgrWithDefaultRealm will be confused.

	#-- PURPOSE: check that entered NASA Earthdata credentials are valid
	def check_credentials(self):
		try:
			remote_path = ('https://',self.remote_directory)
			request = urllib2.Request(url='{0}{1}'.format(*remote_path))
			response = urllib2.urlopen(request, timeout=20)
		except urllib2.HTTPError:
			print('AUTHENTICATION ERROR: check your NASA Earthdata credentials')
			sys.exit()

	#-- PURPOSE: help module that lists the commands for the program
	def usage(self, *kwargs):
		print('\nHelp: {0}'.format(os.path.basename(sys.argv[0])))
		print(' ls\tList contents of the remote directory')
		print(' cd\tChange the remote directory')
		print(' lcd\tChange the local directory')
		print(' mkdir\tCreate a directory within the local directory')
		print(' pwd\tPrint the current local and remote directory paths')
		print(' sync\tSync all files in directory with a local directory')
		print(' rsync\tRecursively sync all directories with a local directory')
		print(' mget\tGet all files in directory')
		print(' get\tGet a single file in a directory')
		print(' quiet\tTurn off verbose output')
		print(' exit\tExit program\n')

	#-- PURPOSE: list everything in directory
	def list_directory(self, args):
		#-- print either:
		#-- 1) everything within the directories of each argument passed
		#-- 2) everything within the current directory
		if args:
			#-- for each argument
			for a in args:
				#-- print contents from remote subdirectories
				RD = posixpath.normpath(posixpath.join(self.remote_directory,a))
				req = urllib2.Request(url='{0}{1}'.format('https://',RD))
				try:
					response = urllib2.urlopen(req, timeout=20)
				except urllib2.URLError:
					#-- print an error if invalid
					print('ERROR: {0}{1} not a valid path'.format('https://',RD))
				else:
					#-- parse response for subdirectories (find column names)
					tree = lxml.etree.parse(response,self.parser)
					colnames = tree.xpath('//td[@class="indexcolname"]//a/@href')
					print('\n'.join([w for w in colnames]))
		else:
			#-- print contents from remote directory
			remote_path = ('https://',self.remote_directory)
			req = urllib2.Request(url='{0}{1}'.format(*remote_path))
			#-- read and parse request for subdirectories (find column names)
			tree = lxml.etree.parse(urllib2.urlopen(req,timeout=20),self.parser)
			colnames = tree.xpath('//td[@class="indexcolname"]//a/@href')
			print('\n'.join([w for w in colnames]))
		#-- close the request
		req = None

	#-- PURPOSE: change the remote directory
	def change_remote_directory(self, args):
		if args:
			#-- change to parent directory or to the argument passed
			RD=posixpath.normpath(posixpath.join(self.remote_directory,args[0]))
		else:
			RD=posixpath.join(self.host,"ICEBRIDGE")
		#-- attempt to connect to new remote directory
		try:
			urllib2.urlopen('https://{0}'.format(RD),timeout=20)
		except urllib2.URLError:
			#-- print an error if invalid
			print('ERROR: {0}{1} not a valid path'.format('https://',RD))
		else:
			#-- set the new remote directory and print prompt
			self.remote_directory = RD
			#-- print that command was success if verbose output
			if self.verbose:
				print('Directory changed to\n\t{0}{1}\n'.format('https://',RD))

	#-- PURPOSE: change the local directory and make sure it exists
	def change_local_directory(self, args):
		self.local_directory = os.path.normpath(os.path.join(self.local_directory,
			os.path.expanduser(args[0])))
		#-- create new local directory if it did not presently exist
		if not os.path.exists(self.local_directory):
			os.makedirs(self.local_directory,self.mode)
		#-- print that command was success if verbose output
		if self.verbose:
			print('Local directory changed to\n\t{0}\n'.format(self.local_directory))

	#-- PURPOSE: create a set of directories within the local directory
	def make_local_directories(self, args):
		#-- for each input argument: create the subdirectory
		for d in args:
			LD = os.path.join(self.local_directory,d)
			os.makedirs(LD,self.mode) if not os.path.exists(LD) else None

	#-- PURPOSE: print the current local and remote directory paths
	def print_directory_paths(self,*kwargs):
		print('Remote directory:\t{0}{1}'.format('https://',self.remote_directory))
		print('Local directory:\t{0}\n'.format(self.local_directory))

	#-- PURPOSE: sync files in a remote directory to a local directory
	def sync_directory(self, args):
		#-- local and remote directories
		local_dir = self.local_directory
		remote_dir = self.remote_directory
		#-- make sure local directory exists
		os.makedirs(local_dir,self.mode) if not os.path.exists(local_dir) else None
		#-- submit request
		req = urllib2.Request(url='{0}{1}'.format('https://',remote_dir))
		#-- read and parse request for remote files (columns and dates)
		tree = lxml.etree.parse(urllib2.urlopen(req, timeout=20), self.parser)
		colnames = tree.xpath('//td[@class="indexcolname"]/a/text()')
		collastmod = tree.xpath('//td[@class="indexcollastmod"]/text()')
		#-- regular expression pattern
		R1 = '(' + '|'.join(args) + ')' if args else "^(?!Parent)"
		remote_file_lines = [i for i,f in enumerate(colnames) if re.match(R1,f)]
		#-- compile regular expression operator for extracting modification date
		date_regex_pattern = '(\d+)\-(\d+)\-(\d+)\s(\d+)\:(\d+)'
		R2 = re.compile(date_regex_pattern, re.VERBOSE)
		#-- sync each data file
		for i in remote_file_lines:
			#-- remote and local versions of the file
			self.remote_file='{0}{1}/{2}'.format('https://',remote_dir,colnames[i])
			self.local_file = os.path.join(local_dir,colnames[i])
			#-- get last modified date and convert into unix time
			Y,M,D,H,MN = [int(v) for v in R2.findall(collastmod[i]).pop()]
			self.remote_mtime = calendar.timegm((Y,M,D,H,MN,0))
			#-- sync files with server (clobber set to False: will NOT overwrite)
			self.http_pull_file(False)
		#-- close request
		req = None

	#-- PURPOSE: recursively sync a remote directory to a local directory
	def rsync_directories(self, args):
		#-- submit request
		req=urllib2.Request(url='{0}{1}'.format('https://',self.remote_directory))
		#-- read and parse request for remote files (columns and dates)
		tree = lxml.etree.parse(urllib2.urlopen(req, timeout=20), self.parser)
		#-- regular expression pattern
		R1 = '(' + '|'.join(args) + ')' if args else "^(?!Parent)"
		colnames = tree.xpath('//td[@class="indexcolname"]/a/text()')
		subdirectories = [sd for sd in colnames if re.match(R1,sd)]
		#-- compile regular expression operator for extracting modification date
		date_regex_pattern = '(\d+)\-(\d+)\-(\d+)\s(\d+)\:(\d+)'
		R2 = re.compile(date_regex_pattern, re.VERBOSE)
		for sd in subdirectories:
			#-- local and remote directories
			local_dir = os.path.join(self.local_directory,sd)
			remote_dir = '{0}{1}/{2}'.format('https://',self.remote_directory,sd)
			#-- make sure local directory exists
			os.makedirs(local_dir,self.mode) if not os.path.exists(local_dir) else None
			#-- submit request
			req = urllib2.Request(url=remote_dir)
			#-- read and parse request for remote files (columns and dates)
			tree = lxml.etree.parse(urllib2.urlopen(req,timeout=20),self.parser)
			colnames = tree.xpath('//td[@class="indexcolname"]/a/text()')
			collastmod = tree.xpath('//td[@class="indexcollastmod"]/text()')
			remote_file_lines = [i for i,f in enumerate(colnames) if
				re.match("^(?!Parent)",f)]
			#-- sync each data file
			for i in remote_file_lines:
				#-- remote and local versions of the file
				self.remote_file='{0}/{1}'.format(remote_dir,colnames[i])
				self.local_file = os.path.join(local_dir,colnames[i])
				#-- get last modified date and convert into unix time
				Y,M,D,H,MN = [int(v) for v in R2.findall(collastmod[i]).pop()]
				self.remote_mtime = calendar.timegm((Y,M,D,H,MN,0))
				#-- sync files with server (clobber set to False: will NOT overwrite)
				self.http_pull_file(False)
		#-- close request
		req = None

	#-- PURPOSE: get files in a remote directory to a local directory
	def mget_files(self, args):
		#-- local and remote directories
		local_dir = self.local_directory
		remote_dir = self.remote_directory
		#-- make sure local directory exists
		os.makedirs(local_dir,self.mode) if not os.path.exists(local_dir) else None
		#-- submit request
		req = urllib2.Request(url='{0}{1}'.format('https://',remote_dir))
		#-- read and parse request for remote files (columns and dates)
		tree = lxml.etree.parse(urllib2.urlopen(req, timeout=20), self.parser)
		colnames = tree.xpath('//td[@class="indexcolname"]/a/text()')
		collastmod = tree.xpath('//td[@class="indexcollastmod"]/text()')
		#-- regular expression pattern
		regex_pattern = '(' + '|'.join(args) + ')' if args else "^(?!Parent)"
		remote_file_lines = [i for i,f in enumerate(colnames) if
			re.match(regex_pattern,f)]
		#-- compile regular expression operator for extracting modification date
		date_regex_pattern = '(\d+)\-(\d+)\-(\d+)\s(\d+)\:(\d+)'
		R2 = re.compile(date_regex_pattern, re.VERBOSE)
		#-- get each data file
		for i in remote_file_lines:
			#-- remote and local versions of the file
			self.remote_file='{0}{1}/{2}'.format('https://',remote_dir,colnames[i])
			self.local_file = os.path.join(local_dir,colnames[i])
			#-- get last modified date and convert into unix time
			Y,M,D,H,MN = [int(v) for v in R2.findall(collastmod[i]).pop()]
			self.remote_mtime = calendar.timegm((Y,M,D,H,MN,0))
			#-- get files from server (clobber set to True: will overwrite)
			self.http_pull_file(True)
		#-- close request
		req = None

	#-- PURPOSE: get a single file in a remote directory to a local directory
	def get_file(self, args):
		#-- local and remote directories
		local_dir = self.local_directory
		remote_dir = self.remote_directory
		#-- make sure local directory exists
		os.makedirs(local_dir,self.mode) if not os.path.exists(local_dir) else None
		#-- submit request
		req = urllib2.Request(url='{0}{1}'.format('https://',remote_dir))
		#-- read and parse request for remote files (columns and dates)
		tree = lxml.etree.parse(urllib2.urlopen(req, timeout=20), self.parser)
		colnames = tree.xpath('//td[@class="indexcolname"]/a/text()')
		collastmod = tree.xpath('//td[@class="indexcollastmod"]/text()')
		regex_pattern = '{0}$'.format(args[0])
		i, = [i for i,f in enumerate(colnames) if re.match(regex_pattern,f)]
		#-- remote and local versions of the file
		self.remote_file = '{0}{1}/{2}'.format('https://',remote_dir,colnames[i])
		self.local_file = os.path.join(local_dir,colnames[i])
		#-- compile regular expression operator for extracting modification date
		date_regex_pattern = '(\d+)\-(\d+)\-(\d+)\s(\d+)\:(\d+)'
		R2 = re.compile(date_regex_pattern, re.VERBOSE)
		#-- get last modified date and convert into unix time
		Y,M,D,H,MN = [int(v) for v in R2.findall(collastmod[i]).pop()]
		self.remote_mtime = calendar.timegm((Y,M,D,H,MN,0))
		#-- get file from server (clobber set to True: will overwrite)
		self.http_pull_file(True)
		#-- close request
		req = None

	#-- PURPOSE: pull file from a remote host checking if file exists locally
	#-- and if the remote file is newer than the local file
	def http_pull_file(self, CLOBBER):
		#-- if file exists in file system: check if remote file is newer
		TEST = False
		OVERWRITE = ' (clobber)'
		#-- check if local version of file exists
		if os.access(self.local_file, os.F_OK):
			#-- check last modification time of local file
			local_mtime = os.stat(self.local_file).st_mtime
			#-- if remote file is newer: overwrite the local file
			if (self.remote_mtime > local_mtime):
				TEST = True
				OVERWRITE = ' (overwrite)'
		else:
			TEST = True
			OVERWRITE = ' (new)'
		#-- if file does not exist locally, is to be overwritten, or CLOBBER is set
		if TEST or CLOBBER:
			#-- Printing files transferred if verbose output
			if self.verbose:
				print('{0} --> '.format(self.remote_file))
				print('\t{0}{1}\n'.format(self.local_file,OVERWRITE))
			#-- Create and submit request. There are a wide range of exceptions
			#-- that can be thrown here, including HTTPError and URLError.
			request = urllib2.Request(self.remote_file)
			response = urllib2.urlopen(request, timeout=20)
			#-- chunked transfer encoding size
			CHUNK = 16 * 1024
			#-- copy contents to local file using chunked transfer encoding
			#-- transfer should work properly with ascii and binary data formats
			with open(self.local_file, 'wb') as f:
				shutil.copyfileobj(response, f, CHUNK)
			#-- keep remote modification time of file and local access time
			os.utime(self.local_file, (os.stat(self.local_file).st_atime,
				self.remote_mtime))
			os.chmod(self.local_file, self.mode)
			#-- close request
			request = None

	#-- PURPOSE: set the verbosity level of the program
	def set_verbosity(self, *kwargs):
		self.verbose = False

	#-- PURPOSE: exit the while loop to end the program
	def exit_program(self, *kwargs):
		self.run = False
