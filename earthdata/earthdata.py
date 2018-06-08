#!/usr/bin/env python
u"""
earthdata.py
Written by Tyler Sutterley (06/2018)
ftp-like program for searching NSIDC databases and retrieving data

COMMAND LINE OPTIONS:
	usage: List the following command line options
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
	checksum: Toggle checksum function within program
	exit: Exit program

PYTHON DEPENDENCIES:
	lxml: Pythonic XML and HTML processing library using libxml2/libxslt
		http://lxml.de/
		https://github.com/lxml/lxml
	future: Compatibility layer between Python 2 and Python 3
		(http://python-future.org/)

UPDATE HISTORY:
	Updated 06/2018: using python3 compatible octal, input and urllib
	Updated 05/2018: using python cmd module (line-oriented command interpreter)
	Updated 11/2017: added checksum comparison function for CRC32
	Updated 10/2017: added checksum comparison function for MD5 and CKSUM
	Updated 09/2017: added option verbose to toggle verbose output. cd to root
	Updated 08/2017: modules and variables shared within a python class
		earthdata class is entirely self-contained.  Added credential check
	Written 08/2017
"""
from __future__ import print_function

import sys
import cmd
import os
import re
import shutil
import base64
import getpass
import hashlib
import builtins
import lxml.etree
import posixpath
import calendar, time
if sys.version_info[0] == 2:
	from cookielib import CookieJar
	import urllib2
else:
	from http.cookiejar import CookieJar
	import urllib.request as urllib2

#-- PURPOSE: creates Earthdata class containing the main functions and variables
class earthdata(cmd.Cmd):
	def __init__(self, parent=None):
		#-- call constructor of parent class
		cmd.Cmd.__init__(self)
		#-- NSIDC host for Pre-Icebridge and IceBridge data
		self.host = 'n5eil01u.ecs.nsidc.org'
		self.prompt = '> '
		self.intro = 'Welcome to {0}'.format(self.host)
		self.goodbye = 'Goodbye!'
		#-- remote https server for IceBridge Data (can cd to ../PRE_OIB)
		self.remote_directory = posixpath.join(self.host,"ICEBRIDGE")
		self.local_directory = os.getcwd()
		#-- verbosity settings
		self.verbose = True
		#-- run checksums for all downloaded data files
		self.checksums = False
		#-- permissions mode of the local directories and files (in octal)
		self.mode = 0o775
		#-- compile HTML and xml parsers for lxml
		self.htmlparser = lxml.etree.HTMLParser()
		self.xmlparser = lxml.etree.XMLParser()
		#-- enter credentials with password entered securely from the command-line
		self.get_credentials()
		#-- create https opener for NASA Earthdata using supplied credentials
		self.https_opener()
		self.check_credentials()

	#-- PURPOSE: get the username and password for NASA Earthdata login
	def get_credentials(self):
		self.user = builtins.input('Username for {0}: '.format(self.host))
		self.password = getpass.getpass('Password for {0}@{1}: '.format(self.user,self.host))

	#-- PURPOSE: "login" to NASA Earthdata with supplied credentials
	def https_opener(self):
		#-- https://docs.python.org/3/howto/urllib2.html#id5
		#-- create a password manager
		password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
		#-- Add the username and password for NASA Earthdata Login system
		password_mgr.add_password(None,'https://urs.earthdata.nasa.gov',self.user,self.password)
		#-- Encode username/password for request authorization headers
		base64_string = base64.b64encode('{0}:{1}'.format(self.user,self.password))
		#-- Create cookie jar for storing cookies. This is used to store and return
		#-- the session cookie given to use by the data server (otherwise will just
		#-- keep sending us back to Earthdata Login to authenticate).
		cookie_jar = CookieJar()
		#-- create "opener" (OpenerDirector instance)
		opener = urllib2.build_opener(
			urllib2.HTTPBasicAuthHandler(password_mgr),
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
			remote_path = posixpath.join('https://',self.remote_directory)
			request = urllib2.Request(url=remote_path)
			response = urllib2.urlopen(request, timeout=20)
		except urllib2.HTTPError:
			print('AUTHENTICATION ERROR: check your NASA Earthdata credentials')
			sys.exit()

	#-- PURPOSE: help module that lists the commands for the program
	def do_usage(self, *kwargs):
		"""Help module that lists all commands for the program"""
		print('\nHelp: {0}'.format(os.path.basename(sys.argv[0])))
		print(' ls\t\tList contents of the remote directory')
		print(' cd\t\tChange the remote directory')
		print(' lcd\t\tChange the local directory')
		print(' mkdir\t\tCreate a directory within the local directory')
		print(' pwd\t\tPrint the current local and remote directory paths')
		print(' sync\t\tSync all files in directory with a local directory')
		print(' rsync\t\tRecursively sync all directories with a local directory')
		print(' mget\t\tGet all files in directory')
		print(' get\t\tGet a single file in a directory')
		print(' verbose\tToggle verbose output of program')
		print(' checksum\tToggle checksum function within program')
		print(' exit\t\tExit program\n')

	#-- PURPOSE: list everything in directory
	def do_ls(self, args):
		"""List contents of the remote directory"""
		#-- print either:
		#-- 1) everything within the directories of each argument passed
		#-- 2) everything within the current directory
		if args:
			#-- for each argument
			for a in args.split():
				#-- print contents from remote subdirectories
				RD = posixpath.normpath(posixpath.join(self.remote_directory,a))
				remote_path = posixpath.join('https://',RD)
				req = urllib2.Request(url=remote_path)
				try:
					response = urllib2.urlopen(req, timeout=20)
				except urllib2.URLError:
					#-- print an error if invalid
					print('ERROR: {0} not a valid path'.format(remote_path))
				else:
					#-- parse response for subdirectories (find column names)
					tree = lxml.etree.parse(response,self.htmlparser)
					colnames = tree.xpath('//td[@class="indexcolname"]//a/@href')
					print('\n'.join([w for w in colnames]))
		else:
			#-- print contents from remote directory
			remote_path = posixpath.join('https://',self.remote_directory)
			req = urllib2.Request(url=remote_path)
			#-- read and parse request for subdirectories (find column names)
			tree=lxml.etree.parse(urllib2.urlopen(req,timeout=20),self.htmlparser)
			colnames = tree.xpath('//td[@class="indexcolname"]//a/@href')
			print('\n'.join([w for w in colnames]))
		#-- close the request
		req = None

	#-- PURPOSE: change the remote directory
	def do_cd(self, args):
		"""Change the remote directory to a new path"""
		if args:
			#-- change to parent directory or to the argument passed
			RD=posixpath.normpath(posixpath.join(self.remote_directory,args))
		else:
			RD=posixpath.join(self.host,"ICEBRIDGE")
		#-- attempt to connect to new remote directory
		remote_path = posixpath.join('https://',RD)
		try:
			urllib2.urlopen(remote_path,timeout=20)
		except urllib2.URLError:
			#-- print an error if invalid
			print('ERROR: {0} not a valid path'.format(remote_path))
		else:
			#-- set the new remote directory and print prompt
			self.remote_directory = RD
			#-- print that command was success if verbose output
			if self.verbose:
				print('Directory changed to\n\t{0}\n'.format(remote_path))

	#-- PURPOSE: change the local directory and make sure it exists
	def do_lcd(self, args):
		"""Change the local directory to a new path"""
		self.local_directory = os.path.normpath(os.path.join(self.local_directory,
			os.path.expanduser(args)))
		#-- create new local directory if it did not presently exist
		if not os.path.exists(self.local_directory):
			os.makedirs(self.local_directory,self.mode)
		#-- print that command was success if verbose output
		if self.verbose:
			print('Local directory changed to\n\t{0}\n'.format(self.local_directory))

	#-- PURPOSE: create a set of directories within the local directory
	def do_mkdir(self, args):
		"""Create a directory within the local directory"""
		#-- for each input argument: create the subdirectory
		for d in args.split():
			local_path = os.path.join(self.local_directory,d)
			os.makedirs(local_path,self.mode) if not os.path.exists(local_path) else None

	#-- PURPOSE: print the current local and remote directory paths
	def do_pwd(self,*kwargs):
		"""Print the current local and remote directory paths"""
		d=(posixpath.join('https://',self.remote_directory),self.local_directory)
		print('Remote directory:\t{0}\nLocal directory:\t{1}\n'.format(*d))

	#-- PURPOSE: sync files in a remote directory to a local directory
	def do_sync(self, args):
		"""Sync all files in directory with a local directory"""
		#-- local and remote directories
		local_dir = self.local_directory
		remote_dir = self.remote_directory
		#-- make sure local directory exists
		os.makedirs(local_dir,self.mode) if not os.path.exists(local_dir) else None
		#-- submit request
		req = urllib2.Request(url=posixpath.join('https://',remote_dir))
		#-- read and parse request for remote files (columns and dates)
		tree = lxml.etree.parse(urllib2.urlopen(req,timeout=20),self.htmlparser)
		colnames = tree.xpath('//td[@class="indexcolname"]/a/text()')
		collastmod = tree.xpath('//td[@class="indexcollastmod"]/text()')
		#-- regular expression pattern
		R1 = '(' + '|'.join(args.split()) + ')' if args else "^(?!Parent)"
		remote_file_lines = [i for i,f in enumerate(colnames) if re.match(R1,f)]
		#-- compile regular expression operator for extracting modification date
		date_regex_pattern = '(\d+)\-(\d+)\-(\d+)\s(\d+)\:(\d+)'
		R2 = re.compile(date_regex_pattern, re.VERBOSE)
		#-- sync each data file
		for i in remote_file_lines:
			#-- remote and local versions of the file
			self.remote_file = posixpath.join('https://',remote_dir,colnames[i])
			self.local_file = os.path.join(local_dir,colnames[i])
			#-- create regular expression pattern for finding xml files
			if self.checksums:
				fileBasename,fileExtension = os.path.splitext(colnames[i])
				regex_pattern = '{0}(.*?).xml$'.format(fileBasename)
				xml, = [f for f in colnames if re.match(regex_pattern,f)]
				self.remote_xml = posixpath.join('https://',remote_dir,xml)
			#-- get last modified date and convert into unix time
			Y,M,D,H,MN = [int(v) for v in R2.findall(collastmod[i]).pop()]
			self.remote_mtime = calendar.timegm((Y,M,D,H,MN,0))
			#-- sync files with server (clobber set to False: will NOT overwrite)
			self.http_pull_file(False)
		#-- close request
		req = None

	#-- PURPOSE: recursively sync a remote directory to a local directory
	def do_rsync(self, args):
		"""Recursively sync all directories with a local directory"""
		#-- submit request
		req=urllib2.Request(url=posixpath.join('https://',self.remote_directory))
		#-- read and parse request for remote files (columns and dates)
		tree = lxml.etree.parse(urllib2.urlopen(req,timeout=20),self.htmlparser)
		#-- regular expression pattern
		R1 = '(' + '|'.join(args.split()) + ')' if args else "^(?!Parent)"
		colnames = tree.xpath('//td[@class="indexcolname"]/a/text()')
		subdirectories = [sd for sd in colnames if re.match(R1,sd)]
		#-- compile regular expression operator for extracting modification date
		date_regex_pattern = '(\d+)\-(\d+)\-(\d+)\s(\d+)\:(\d+)'
		R2 = re.compile(date_regex_pattern, re.VERBOSE)
		for sd in subdirectories:
			#-- local and remote directories
			local_dir = os.path.join(self.local_directory,sd)
			remote_dir = posixpath.join('https://',self.remote_directory,sd)
			#-- make sure local directory exists
			os.makedirs(local_dir,self.mode) if not os.path.exists(local_dir) else None
			#-- submit request
			req = urllib2.Request(url=remote_dir)
			#-- read and parse request for remote files (columns and dates)
			tree=lxml.etree.parse(urllib2.urlopen(req,timeout=20),self.htmlparser)
			colnames = tree.xpath('//td[@class="indexcolname"]/a/text()')
			collastmod = tree.xpath('//td[@class="indexcollastmod"]/text()')
			remote_file_lines = [i for i,f in enumerate(colnames) if
				re.match("^(?!Parent)",f)]
			#-- sync each data file
			for i in remote_file_lines:
				#-- remote and local versions of the file
				self.remote_file = posixpath.join(remote_dir,colnames[i])
				self.local_file = os.path.join(local_dir,colnames[i])
				#-- create regular expression pattern for finding xml files
				if self.checksums:
					fileBasename,fileExtension = os.path.splitext(colnames[i])
					regex_pattern = '{0}(.*?).xml$'.format(fileBasename)
					xml, = [f for f in colnames if re.match(regex_pattern,f)]
					self.remote_xml = posixpath.join('https://',remote_dir,xml)
				#-- get last modified date and convert into unix time
				Y,M,D,H,MN = [int(v) for v in R2.findall(collastmod[i]).pop()]
				self.remote_mtime = calendar.timegm((Y,M,D,H,MN,0))
				#-- sync files with server (clobber set to False: will NOT overwrite)
				self.http_pull_file(False)
		#-- close request
		req = None

	#-- PURPOSE: get files in a remote directory to a local directory
	def do_mget(self, args):
		"""Get all files in directory"""
		#-- local and remote directories
		local_dir = self.local_directory
		remote_dir = self.remote_directory
		#-- make sure local directory exists
		os.makedirs(local_dir,self.mode) if not os.path.exists(local_dir) else None
		#-- submit request
		req = urllib2.Request(url=posixpath.join('https://',remote_dir))
		#-- read and parse request for remote files (columns and dates)
		tree = lxml.etree.parse(urllib2.urlopen(req,timeout=20),self.htmlparser)
		colnames = tree.xpath('//td[@class="indexcolname"]/a/text()')
		collastmod = tree.xpath('//td[@class="indexcollastmod"]/text()')
		#-- regular expression pattern
		regex_pattern = '(' + '|'.join(args.split()) + ')' if args else "^(?!Parent)"
		remote_file_lines = [i for i,f in enumerate(colnames) if
			re.match(regex_pattern,f)]
		#-- compile regular expression operator for extracting modification date
		date_regex_pattern = '(\d+)\-(\d+)\-(\d+)\s(\d+)\:(\d+)'
		R2 = re.compile(date_regex_pattern, re.VERBOSE)
		#-- get each data file
		for i in remote_file_lines:
			#-- remote and local versions of the file
			self.remote_file = posixpath.join('https://',remote_dir,colnames[i])
			self.local_file = os.path.join(local_dir,colnames[i])
			#-- create regular expression pattern for finding xml files
			if self.checksums:
				fileBasename,fileExtension = os.path.splitext(colnames[i])
				regex_pattern = '{0}(.*?).xml$'.format(fileBasename)
				xml, = [f for f in colnames if re.match(regex_pattern,f)]
				self.remote_xml = posixpath.join('https://',remote_dir,xml)
			#-- get last modified date and convert into unix time
			Y,M,D,H,MN = [int(v) for v in R2.findall(collastmod[i]).pop()]
			self.remote_mtime = calendar.timegm((Y,M,D,H,MN,0))
			#-- get files from server (clobber set to True: will overwrite)
			self.http_pull_file(True)
		#-- close request
		req = None

	#-- PURPOSE: get a single file in a remote directory to a local directory
	def do_get(self, args):
		"""Get a single file in a directory"""
		#-- local and remote directories
		local_dir = self.local_directory
		remote_dir = self.remote_directory
		#-- make sure local directory exists
		os.makedirs(local_dir,self.mode) if not os.path.exists(local_dir) else None
		#-- submit request
		req = urllib2.Request(url=posixpath.join('https://',remote_dir))
		#-- read and parse request for remote files (columns and dates)
		tree = lxml.etree.parse(urllib2.urlopen(req,timeout=20),self.htmlparser)
		colnames = tree.xpath('//td[@class="indexcolname"]/a/text()')
		collastmod = tree.xpath('//td[@class="indexcollastmod"]/text()')
		regex_pattern = '{0}$'.format(args)
		i, = [i for i,f in enumerate(colnames) if re.match(regex_pattern,f)]
		#-- remote and local versions of the file
		self.remote_file = posixpath.join('https://',remote_dir,colnames[i])
		self.local_file = os.path.join(local_dir,colnames[i])
		#-- create regular expression pattern for finding xml files
		if self.checksums:
			fileBasename,fileExtension = os.path.splitext(args)
			regex_pattern = '{0}(.*?).xml$'.format(fileBasename)
			xml, = [f for f in colnames if re.match(regex_pattern,f)]
			self.remote_xml = posixpath.join('https://',remote_dir,xml)
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
			#-- run compare checksum program for data files (and not .xml files)
			self.compare_checksum() if self.checksums else None
			#-- close request
			request = None

	#-- PURPOSE: compare the checksum in the remote xml file with the local hash
	def compare_checksum(self, *kwargs):
		#-- read and parse remote xml file
		req = urllib2.Request(self.remote_xml)
		tree = lxml.etree.parse(urllib2.urlopen(req,timeout=20),self.xmlparser)
		filename, = tree.xpath('//DataFileContainer/DistributedFileName/text()')
		#-- if the DistributedFileName matches the synced filename
		if (os.path.basename(self.local_file) == filename):
			#-- extract checksum and checksum type of the remote file
			checksum_type, = tree.xpath('//DataFileContainer/ChecksumType/text()')
			remote_hash, = tree.xpath('//DataFileContainer/Checksum/text()')
			#-- calculate checksum of local file
			local_hash = self.get_checksum(checksum_type)
			#-- compare local and remote checksums to validate data transfer
			if (local_hash != remote_hash):
				if self.verbose:
					print('Remote checksum: {0}'.format(remote_hash))
					print('Local checksum: {0}' .format(local_hash))
				raise Exception('Checksum verification failed')
			elif (local_hash == remote_hash) and self.verbose:
				print('{0} checksum match: {1}'.format(checksum_type,local_hash))

	#-- PURPOSE: generate checksum hash from a local file for a checksum type
	#-- supplied hashes within NSIDC *.xml files can currently be MD5 and CKSUM
	#-- https://nsidc.org/data/icebridge/provider_info.html
	def get_checksum(self, checksum_type):
		#-- read the input file to get file information
		fd = os.open(self.local_file, os.O_RDONLY)
		n = os.fstat(fd).st_size
		#-- open the filename in binary read mode
		file_buffer = os.fdopen(fd, 'rb').read()
		#-- generate checksum hash for a given type
		if (checksum_type == 'MD5'):
			return hashlib.md5(file_buffer).hexdigest()
		elif (checksum_type == 'CKSUM'):
			crc32_table = []
			for b in range(0,256):
				vv = b<<24
				for i in range(7,-1,-1):
				    vv = (vv<<1)^0x04c11db7 if (vv & 0x80000000) else (vv<<1)
				crc32_table.append(vv & 0xffffffff)
			#-- calculate CKSUM hash with both file length and file buffer
			i = c = s = 0
			for c in file_buffer:
			    s = ((s << 8) & 0xffffffff)^crc32_table[(s >> 24)^ord(c)]
			while n:
			    c = n & 0xff
			    n = n >> 8
			    s = ((s << 8) & 0xffffffff)^crc32_table[(s >> 24)^c]
			return str((~s) & 0xffffffff)
		elif (checksum_type == 'CRC32'):
			crc32_table = []
			for b in range(256):
				vv = b
				for i in range(8):
				    vv = (vv>>1)^0xedb88320 if (vv & 1) else (vv>>1)
				crc32_table.append(vv & 0xffffffff)
			s = 0xffffffff
			for c in file_buffer:
			    s = crc32_table[(ord(c) ^ s) & 0xff] ^ (s >> 8)
			return str((~s) & 0xffffffff)

	#-- PURPOSE: set the verbosity level of the program
	def do_verbose(self, *kwargs):
		"""Toggle verbose output of program"""
		self.verbose ^= True

	#-- PURPOSE: toggle the checksum function within the program
	def do_checksum(self, *kwargs):
		"""Toggle checksum function within program"""
		self.checksums ^= True

	#-- PURPOSE: exit the while loop to end the program
	def do_exit(self, *kwargs):
		"""Exit program"""
		return True

#-- run main program
if __name__ == '__main__':
	#-- run Earthdata program
	#-- ftp-like program for searching NSIDC databases and retrieving data
	prompt = earthdata()
	#-- print introductory message
	#-- run program until exit or keyboard interrupt
	prompt.cmdloop(prompt.intro)
	#-- print goodbye message
	print(prompt.goodbye)
