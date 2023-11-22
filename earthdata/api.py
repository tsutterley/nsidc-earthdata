#!/usr/bin/env python
u"""
api.py
Written by Tyler Sutterley (11/2023)
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
        https://lxml.de/
        https://github.com/lxml/lxml
    future: Compatibility layer between Python 2 and Python 3
        (http://python-future.org/)

UPDATE HISTORY:
    Updated 11/2023: using pathlib for path operations
        updated ssl context to prevent deprecation errors
    Updated 08/2021: NSIDC no longer requires authentication headers
    Updated 05/2021: added option for connection timeout (in seconds)
    Updated 04/2021: default credentials from environmental variables
    Updated 03/2021: added sha1 checksum
    Updated 09/2020: add manual retries to enter NASA Earthdata credentials
    Updated 05/2020: will check for netrc file before asking for authentication
    Updated 09/2019: added ssl context to urlopen headers
    Updated 06/2019: use strptime to extract last modified time of remote files
    Updated 12/2018: decode authorization header for python3 compatibility
    Updated 11/2018: encode base64 strings for python3 compatibility
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
import ssl
import netrc
import shutil
import base64
import getpass
import hashlib
import pathlib
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

# PURPOSE: creates Earthdata class containing the main functions and variables
class api(cmd.Cmd):

    def __init__(self, parent=None):
        # call constructor of parent class
        cmd.Cmd.__init__(self)
        # NASA Earthdata Login system
        self.urs = 'urs.earthdata.nasa.gov'
        # NSIDC opener arguments
        self.context = self._create_ssl_context_no_verify()
        self.password_manager = True
        self.get_ca_certs = False,
        self.redirect = False
        self.authorization_header = False
        # NSIDC host for Pre-Icebridge and IceBridge data
        self.host = 'n5eil01u.ecs.nsidc.org'
        self.prompt = '> '
        self.intro = f'Welcome to {self.host}'
        self.goodbye = 'Goodbye!'
        # credentials from environmental variables
        self.user = os.environ.get('EARTHDATA_USERNAME')
        self.password = os.environ.get('EARTHDATA_PASSWORD')
        # default netrc file for credentials
        self.netrc = pathlib.Path.home().joinpath('.netrc')
        # remote https server for IceBridge Data (can cd to ../PRE_OIB)
        self.remote_directory = posixpath.join(self.host, "ICEBRIDGE")
        self.local_directory = pathlib.Path.cwd()
        # default timeout in seconds for blocking operations
        self.timeout = 20
        # time format
        self.timeformat = r'%Y-%m-%d %H:%M'
        # default number of retries for retrieving files and supplying credentials
        self.retries = 5
        # verbosity settings
        self.verbose = True
        # run checksums for all downloaded data files
        self.checksums = False
        # chunked transfer encoding size
        self.chunk = 16 * 1024
        # permissions mode of the local directories and files (in octal)
        self.mode = 0o775
        # compile HTML and xml parsers for lxml
        self.htmlparser = lxml.etree.HTMLParser()
        self.xmlparser = lxml.etree.XMLParser()
        # enter credentials with password entered securely
        # from the command-line or from .netrc file
        if not self.user or not self.password:
            self._get_credentials()
        # create https opener for NASA Earthdata using supplied credentials
        # attempt to login with supplied credentials up to number of retries
        assert self.retries >= 1
        for _ in range(self.retries):
            self._https_opener()
            if self._check_credentials():
                break
            self._manual_credentials()
        else:
            print('Authentication Error: Check your NASA Earthdata credentials')
            sys.exit()

    # default ssl context
    def _create_default_ssl_context(self) -> ssl.SSLContext:
        """Creates the default SSL context
        """
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._set_ssl_context_options(context)
        context.options |= ssl.OP_NO_COMPRESSION
        return context

    def _create_ssl_context_no_verify(self) -> ssl.SSLContext:
        """Creates an SSL context for unverified connections
        """
        context = self._create_default_ssl_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    def _set_ssl_context_options(self, context: ssl.SSLContext) -> None:
        """Sets the default options for the SSL context
        """
        if sys.version_info >= (3, 10) or ssl.OPENSSL_VERSION_INFO >= (1, 1, 0, 7):
            context.minimum_version = ssl.TLSVersion.TLSv1_2
        else:
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            context.options |= ssl.OP_NO_TLSv1
            context.options |= ssl.OP_NO_TLSv1_1

    # PURPOSE: get the username and password for NASA Earthdata login
    def _get_credentials(self):
        # try using netrc authentication before manual entry of credentials
        try:
            self.user,_,self.password = netrc.netrc(self.netrc).authenticators(self.urs)
        except (FileNotFoundError, TypeError):
            self.manual_credentials()

    # PURPOSE: manually enter credentials
    def _manual_credentials(self):
        self.user = builtins.input(f'Username for {self.urs}: ')
        self.password = getpass.getpass(f'Password for {self.user}@{self.urs}: ')

    # PURPOSE: "login" to NASA Earthdata with supplied credentials
    def _https_opener(self):
        # https://docs.python.org/3/howto/urllib2.html#id5
        handler = []
        # create a password manager
        if self.password_manager:
            password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            # Add the username and password for NASA Earthdata Login system
            password_mgr.add_password(None, self.urs, self.user, self.password)
            handler.append(urllib2.HTTPBasicAuthHandler(password_mgr))
        # Create cookie jar for storing cookies. This is used to store and return
        # the session cookie given to use by the data server (otherwise will just
        # keep sending us back to Earthdata Login to authenticate).
        cookie_jar = CookieJar()
        handler.append(urllib2.HTTPCookieProcessor(cookie_jar))
        # SSL context handler
        if self.get_ca_certs:
            self.context.get_ca_certs()
        handler.append(urllib2.HTTPSHandler(context=self.context))
        # redirect handler
        if self.redirect:
            handler.append(urllib2.HTTPRedirectHandler())
        # create "opener" (OpenerDirector instance)
        self.opener = urllib2.build_opener(*handler)
        # Encode username/password for request authorization headers
        # add Authorization header to opener
        if self.authorization_header:
            b64 = base64.b64encode(f'{self.user}:{self.password}'.encode())
            self.opener.addheaders = [("Authorization", f"Basic {b64.decode()}")]
        # Now all calls to urllib2.urlopen use our opener.
        urllib2.install_opener(self.opener)
        # All calls to urllib2.urlopen will now use handler
        # Make sure not to include the protocol in with the URL, or
        # HTTPPasswordMgrWithDefaultRealm will be confused.

    # PURPOSE: check that entered NASA Earthdata credentials are valid
    def _check_credentials(self):
        try:
            remote_path = posixpath.join('https://',self.remote_directory)
            request = urllib2.Request(url=remote_path)
            response = urllib2.urlopen(request, timeout=self.timeout)
        except urllib2.HTTPError:
            print('Authentication Error: Retry your NASA Earthdata credentials')
        else:
            return True

    # PURPOSE: help module that lists the commands for the program
    def do_usage(self, *kwargs):
        """Help module that lists all commands for the program"""
        print(f'\nHelp: {pathlib.Path(sys.argv[0]).name}')
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
        print(' timeout\tSet timeout in seconds for blocking operations')
        print(' retry\tSet number of retry attempts for retrieving files')
        print(' checksum\tToggle checksum function within program')
        print(' exit\t\tExit program\n')

    # PURPOSE: list everything in directory
    def do_ls(self, args):
        """List contents of the remote directory"""
        # print either:
        # 1) everything within the directories of each argument passed
        # 2) everything within the current directory
        if args:
            # for each argument
            for a in args.split():
                # print contents from remote subdirectories
                RD = posixpath.normpath(posixpath.join(self.remote_directory,a))
                remote_path = posixpath.join('https://',RD)
                request = urllib2.Request(url=remote_path)
                try:
                    response = urllib2.urlopen(request, timeout=self.timeout)
                except urllib2.URLError:
                    # print an error if invalid
                    print(f'ERROR: {remote_path} not a valid path')
                else:
                    # parse response for subdirectories (find column names)
                    tree = lxml.etree.parse(response, self.htmlparser)
                    colnames = tree.xpath(r'//td[@class="indexcolname"]//a/@href')
                    print('\n'.join([w for w in colnames]))
        else:
            # print contents from remote directory
            remote_path = posixpath.join('https://',self.remote_directory)
            request = urllib2.Request(url=remote_path)
            response = urllib2.urlopen(request, timeout=self.timeout)
            # read and parse request for subdirectories (find column names)
            tree = lxml.etree.parse(response, self.htmlparser)
            colnames = tree.xpath(r'//td[@class="indexcolname"]//a/@href')
            print('\n'.join([w for w in colnames]))
        # close the request
        request = None

    # PURPOSE: change the remote directory
    def do_cd(self, args):
        """Change the remote directory to a new path"""
        if args:
            # change to parent directory or to the argument passed
            RD = posixpath.normpath(posixpath.join(self.remote_directory,args))
        else:
            RD = posixpath.join(self.host,"ICEBRIDGE")
        # attempt to connect to new remote directory
        remote_path = posixpath.join('https://',RD)
        try:
            urllib2.urlopen(remote_path, timeout=self.timeout)
        except urllib2.URLError:
            # print an error if invalid
            print(f'ERROR: {remote_path} not a valid path')
        else:
            # set the new remote directory and print prompt
            self.remote_directory = RD
            # print that command was success if verbose output
            if self.verbose:
                print(f'Directory changed to\n\t{remote_path}\n')

    # PURPOSE: change the local directory and make sure it exists
    def do_lcd(self, args):
        """Change the local directory to a new path"""
        self.local_directory = self.local_directory.joinpath(
            pathlib.Path(args).expanduser()).absolute()
        # create new local directory if it did not presently exist
        self.local_directory.mkdir(mode=self.mode, parents=True, exist_ok=True)
        # print that command was success if verbose output
        if self.verbose:
            print('Local directory changed to\n\t{0}\n'.format(self.local_directory))

    # PURPOSE: create a set of directories within the local directory
    def do_mkdir(self, args):
        """Create a directory within the local directory"""
        # for each input argument: create the subdirectory
        for d in args.split():
            local_path = self.local_directory.joinpath(d)
            local_path.mkdir(mode=self.mode, parents=True, exist_ok=True)

    # PURPOSE: print the current local and remote directory paths
    def do_pwd(self,*kwargs):
        """Print the current local and remote directory paths"""
        local_dir = self.local_directory
        remote_dir = posixpath.join('https://',self.remote_directory)
        print(f'Remote directory:\t{remote_dir}')
        print(f'Local directory:\t{local_dir}\n')

    # PURPOSE: sync files in a remote directory to a local directory
    def do_sync(self, args):
        """Sync all files in directory with a local directory"""
        # local and remote directories
        local_dir = self.local_directory
        remote_dir = posixpath.join('https://', self.remote_directory)
        # make sure local directory exists
        local_dir.mkdir(mode=self.mode, parents=True, exist_ok=True)
        # submit request
        request = urllib2.Request(url=remote_dir)
        response = urllib2.urlopen(request, timeout=self.timeout)
        # read and parse request for remote files (columns and dates)
        tree = lxml.etree.parse(response, self.htmlparser)
        colnames = tree.xpath(r'//td[@class="indexcolname"]/a/text()')
        collastmod = tree.xpath(r'//td[@class="indexcollastmod"]/text()')
        # regular expression pattern
        R1 = r'(' + r'|'.join(args.split()) + r')' if args else r"^(?!Parent)"
        remote_file_lines = [i for i,f in enumerate(colnames) if re.match(R1,f)]
        # sync each data file
        for i in remote_file_lines:
            # remote and local versions of the file
            self.remote_file = posixpath.join(remote_dir, colnames[i])
            self.local_file = local_dir.joinpath(colnames[i])
            # create regular expression pattern for finding xml files
            if self.checksums:
                regex_pattern = rf'{self.local_file.stem}(.*?).xml$'
                xml, = [f for f in colnames if re.match(regex_pattern,f)]
                self.remote_xml = posixpath.join(remote_dir, xml)
            # get last modified date and convert into unix time
            lastmodtime = time.strptime(collastmod[i].rstrip(), self.timeformat)
            self.remote_mtime = calendar.timegm(lastmodtime)
            # sync files with server (clobber set to False: will NOT overwrite)
            self.http_pull_file(False)
        # close request
        request = None

    # PURPOSE: recursively sync a remote directory to a local directory
    def do_rsync(self, args):
        """Recursively sync all directories with a local directory"""
        # local and remote directories
        local_dir = self.local_directory
        remote_dir = posixpath.join('https://', self.remote_directory)
        # make sure local directory exists
        local_dir.mkdir(mode=self.mode, parents=True, exist_ok=True)
        # submit request
        request = urllib2.Request(url=remote_dir)
        response = urllib2.urlopen(request, timeout=self.timeout)
        # read and parse request for remote files (columns and dates)
        tree = lxml.etree.parse(response, self.htmlparser)
        # regular expression pattern
        R1 = r'(' + r'|'.join(args.split()) + r')' if args else r"^(?!Parent)"
        colnames = tree.xpath(r'//td[@class="indexcolname"]/a/text()')
        subdirectories = [sd for sd in colnames if re.match(R1,sd)]
        for sd in subdirectories:
            # local and remote directories
            local_dir = self.local_directory.joinpath(sd)
            remote_dir = posixpath.join('https://', self.remote_directory, sd)
            # make sure local directory exists
            local_dir.mkdir(mode=self.mode, parents=True, exist_ok=True)
            # submit request
            request = urllib2.Request(url=remote_dir)
            response = urllib2.urlopen(request, timeout=self.timeout)
            # read and parse request for remote files (columns and dates)
            tree = lxml.etree.parse(response, self.htmlparser)
            colnames = tree.xpath(r'//td[@class="indexcolname"]/a/text()')
            collastmod = tree.xpath(r'//td[@class="indexcollastmod"]/text()')
            remote_file_lines = [i for i,f in enumerate(colnames) if
                re.match(r"^(?!Parent)",f)]
            # sync each data file
            for i in remote_file_lines:
                # remote and local versions of the file
                self.remote_file = posixpath.join(remote_dir, colnames[i])
                self.local_file = local_dir.joinpath(colnames[i])
                # create regular expression pattern for finding xml files
                if self.checksums:
                    regex_pattern = rf'{self.local_file.stem}(.*?).xml$'
                    xml, = [f for f in colnames if re.match(regex_pattern,f)]
                    self.remote_xml = posixpath.join(remote_dir, xml)
                # get last modified date and convert into unix time
                lastmodtime = time.strptime(collastmod[i].rstrip(), self.timeformat)
                self.remote_mtime = calendar.timegm(lastmodtime)
                # sync files with server (clobber set to False: will NOT overwrite)
                self.http_pull_file(False)
        # close request
        request = None

    # PURPOSE: get files in a remote directory to a local directory
    def do_mget(self, args):
        """Get all files in directory"""
        # local and remote directories
        local_dir = self.local_directory
        remote_dir = posixpath.join('https://', self.remote_directory)
        # make sure local directory exists
        local_dir.mkdir(mode=self.mode, parents=True, exist_ok=True)
        # submit request
        request = urllib2.Request(url=remote_dir)
        response = urllib2.urlopen(request, timeout=self.timeout)
        # read and parse request for remote files (columns and dates)
        tree = lxml.etree.parse(response, self.htmlparser)
        colnames = tree.xpath(r'//td[@class="indexcolname"]/a/text()')
        collastmod = tree.xpath(r'//td[@class="indexcollastmod"]/text()')
        # regular expression pattern
        regex_pattern = r'(' + r'|'.join(args.split()) + r')' if args else r"^(?!Parent)"
        remote_file_lines = [i for i,f in enumerate(colnames) if
            re.match(regex_pattern,f)]
        # get each data file
        for i in remote_file_lines:
            # remote and local versions of the file
            self.remote_file = posixpath.join(remote_dir, colnames[i])
            self.local_file = local_dir.joinpath(colnames[i])
            # create regular expression pattern for finding xml files
            if self.checksums:
                regex_pattern = rf'{self.local_file.stem}(.*?).xml$'
                xml, = [f for f in colnames if re.match(regex_pattern,f)]
                self.remote_xml = posixpath.join(remote_dir, xml)
            # get last modified date and convert into unix time
            lastmodtime = time.strptime(collastmod[i].rstrip(), self.timeformat)
            self.remote_mtime = calendar.timegm(lastmodtime)
            # get files from server (clobber set to True: will overwrite)
            self.http_pull_file(True)
        # close request
        request = None

    # PURPOSE: get a single file in a remote directory to a local directory
    def do_get(self, args):
        """Get a single file in a directory"""
        # local and remote directories
        local_dir = self.local_directory
        remote_dir = posixpath.join('https://', self.remote_directory)
        # make sure local directory exists
        local_dir.mkdir(mode=self.mode, parents=True, exist_ok=True)
        # submit request
        request = urllib2.Request(url=remote_dir)
        response = urllib2.urlopen(request, timeout=self.timeout)
        # read and parse request for remote files (columns and dates)
        tree = lxml.etree.parse(response, self.htmlparser)
        colnames = tree.xpath(r'//td[@class="indexcolname"]/a/text()')
        collastmod = tree.xpath(r'//td[@class="indexcollastmod"]/text()')
        regex_pattern = f'{args}$'
        i, = [i for i,f in enumerate(colnames) if re.match(regex_pattern,f)]
        # remote and local versions of the file
        self.remote_file = posixpath.join(remote_dir, colnames[i])
        self.local_file = local_dir.joinpath(colnames[i])
        # create regular expression pattern for finding xml files
        if self.checksums:
            regex_pattern = rf'{self.local_file.stem}(.*?).xml$'
            xml, = [f for f in colnames if re.match(regex_pattern,f)]
            self.remote_xml = posixpath.join(remote_dir, xml)
        # get last modified date and convert into unix time
        lastmodtime = time.strptime(collastmod[i].rstrip(), self.timeformat)
        self.remote_mtime = calendar.timegm(lastmodtime)
        # get file from server (clobber set to True: will overwrite)
        self.http_pull_file(True)
        # close request
        request = None

    # PURPOSE: pull file from a remote host checking if file exists locally
    # and if the remote file is newer than the local file
    def http_pull_file(self, CLOBBER):
        # if file exists in file system: check if remote file is newer
        TEST = False
        OVERWRITE = ' (clobber)'
        # check if local version of file exists
        if self.local_file.exist():
            # check last modification time of local file
            local_mtime = self.local_file.stat().st_mtime
            # if remote file is newer: overwrite the local file
            if (self.even(self.remote_mtime) > self.even(local_mtime)):
                TEST = True
                OVERWRITE = ' (overwrite)'
        else:
            TEST = True
            OVERWRITE = ' (new)'
        # if file does not exist locally, is to be overwritten, or CLOBBER is set
        if TEST or CLOBBER:
            # Printing files transferred if verbose output
            if self.verbose:
                print(f'{self.remote_file} --> ')
                print(f'\t{self.local_file}{OVERWRITE}\n')
            # attempt to download up to the number of retries
            retry_counter = 0
            while (retry_counter < self.retries):
                # attempt to retrieve file from https server
                try:
                    # Create and submit request. There are a wide range of exceptions
                    # that can be thrown here, including HTTPError and URLError.
                    request = urllib2.Request(self.remote_file)
                    response = urllib2.urlopen(request, timeout=self.timeout)
                    # copy contents to local file using chunked transfer encoding
                    # transfer should work properly with ascii and binary data formats
                    with open(self.local_file, 'wb') as f:
                        shutil.copyfileobj(response, f, self.chunk)
                except:
                    pass
                else:
                    break
                # add to retry counter
                retry_counter += 1
            # check if maximum number of retries were reached
            if (retry_counter == self.retries):
                raise TimeoutError('Maximum number of retries reached')
            # keep remote modification time of file and local access time
            os.utime(self.local_file, (self.local_file.stat().st_atime,
                self.remote_mtime))
            self.local_file.chmod(mode=self.mode)
            # run compare checksum program for data files (and not .xml files)
            self.compare_checksum() if self.checksums else None
            # close request
            request = None

    # PURPOSE: compare the checksum in the remote xml file with the local hash
    def compare_checksum(self, *kwargs):
        # read and parse remote xml file
        request = urllib2.Request(self.remote_xml)
        response = urllib2.urlopen(request, timeout=self.timeout)
        tree = lxml.etree.parse(response, self.xmlparser)
        filename, = tree.xpath(r'//DataFileContainer/DistributedFileName/text()')
        # if the DistributedFileName matches the synced filename
        if (self.local_file.name == filename):
            # extract checksum and checksum type of the remote file
            checksum_type, = tree.xpath(r'//DataFileContainer/ChecksumType/text()')
            remote_hash, = tree.xpath(r'//DataFileContainer/Checksum/text()')
            # calculate checksum of local file
            local_hash = self.get_checksum(checksum_type)
            # compare local and remote checksums to validate data transfer
            if (local_hash != remote_hash):
                if self.verbose:
                    print(f'Remote checksum: {remote_hash}')
                    print(f'Local checksum: {local_hash}')
                raise Exception('Checksum verification failed')
            elif (local_hash == remote_hash) and self.verbose:
                print(f'{checksum_type} checksum match: {local_hash}')
        # close request
        request = None

    # PURPOSE: generate checksum hash from a local file for a checksum type
    # supplied hashes within NSIDC *.xml files can currently be MD5 and CKSUM
    # https://nsidc.org/data/icebridge/provider_info.html
    def get_checksum(self, checksum_type):
        # get file information
        n = self.local_file.stat().st_size
        # open the filename in binary read mode
        with self.local_file.open(mode='xb') as fd:
            file_buffer = fd.read()
        # generate checksum hash for a given type
        if (checksum_type == 'MD5'):
            return hashlib.md5(file_buffer).hexdigest()
        elif (checksum_type == 'sha1'):
            return hashlib.sha1(file_buffer).hexdigest()
        elif (checksum_type == 'CKSUM'):
            crc32_table = []
            for b in range(0,256):
                vv = b<<24
                for i in range(7,-1,-1):
                    vv = (vv<<1)^0x04c11db7 if (vv & 0x80000000) else (vv<<1)
                crc32_table.append(vv & 0xffffffff)
            # calculate CKSUM hash with both file length and file buffer
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

    def even(self, value: float):
        """
        Rounds a number to an even number less than or equal to original

        Parameters
        ----------
        value: float
            number to be rounded
        """
        return 2*int(value//2)

    # PURPOSE: set the verbosity level of the program
    def do_verbose(self, *kwargs):
        """Toggle verbose output of program"""
        self.verbose ^= True

    # PURPOSE: set the timeout in seconds for blocking operations
    def do_timeout(self, timeout):
        """Set the timeout in seconds for blocking operations"""
        self.timeout = int(timeout)

    # PURPOSE: set the number of retry attempts for retrieving files
    def do_retry(self, retry):
        """Set the number of retry attempts for retrieving files"""
        self.retries = int(retry)

    # PURPOSE: toggle the checksum function within the program
    def do_checksum(self, *kwargs):
        """Toggle checksum function within program"""
        self.checksums ^= True

    # PURPOSE: exit the while loop to end the program
    def do_exit(self, *kwargs):
        """Exit program"""
        return True

# run main program
if __name__ == '__main__':
    # run Earthdata program
    # ftp-like program for searching NSIDC databases and retrieving data
    prompt = earthdata()
    # print introductory message
    # run program until exit or keyboard interrupt
    prompt.cmdloop(prompt.intro)
    # print goodbye message
    print(prompt.goodbye)
