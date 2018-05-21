nsidc-earthdata
================

#### ftp-like program for searching NSIDC databases and retrieving NASA Operation IceBridge data  

- [NASA Earthdata Login system](https://urs.earthdata.nasa.gov)  
- [How to Access Data with Python](https://wiki.earthdata.nasa.gov/display/EL/How+To+Access+Data+With+Python)  
- [NSIDC: what download options are available](https://nsidc.org/support/faq/what-options-are-available-bulk-downloading-data-https-earthdata-login-enabled)  

Register with NASA Earthdata Login system and add **NSIDC_DATAPOOL_OPS** to your NASA Earthdata Applications

#### Calling Sequence
```
python nsidc_earthdata.py
Username for urs.earthdata.nasa.gov: <username>
Password for <username>@urs.earthdata.nasa.gov: <password>
Welcome to n5eil01u.ecs.nsidc.org
> help
Documented commands (type help <topic>):
========================================
cd        exit  help  ls    mkdir  rsync  usage  
checksum  get   lcd   mget  pwd    sync   verbose
> help rsync
Recursively sync all directories with a local directory
```

##### Function list:
`usage`: Lists the following command line options  
`ls`: List contents of the remote directory  
`cd`: Change the remote directory  
`lcd`: Change the local directory  
`mkdir`: Create a directory within the local directory  
`pwd`: Print the current local and remote directory paths  
`sync`: Sync all files in directory with a local directory  
`rsync`: Recursively sync all directories with a local directory  
`mget`: Get all files in directory  
`get`: Get a single file in a directory  
`verbose`: Toggle verbose output  
`checksum`: Toggle checksum function  
`exit`: Exit program  

#### Examples
##### Recursively sync two directories
```
> cd ILATM2.002
> rsync 2016.11.17 2016.11.18
```
##### Retrieve everything from a directory
```
> cd ILATM2.002/2016.11.17
> mget
```
##### Retrieve a single file from a directory
```
> cd ILATM2.002/2016.11.17
> get ILATM2_20161117_160929_smooth_nadir3seg_50pt.csv
```

#### Dependencies
[lxml: processing XML and HTML in Python](https://pypi.python.org/pypi/lxml)

#### Download
The program homepage is:   
https://github.com/tsutterley/nsidc-earthdata    
A zip archive of the latest version is available directly at:    
https://github.com/tsutterley/nsidc-earthdata/archive/master.zip  

#### Disclaimer  
This program is not sponsored or maintained by the Universities Space Research Association (USRA), the National Snow and Ice Data Center (NSIDC) or NASA.  It is provided here for your convenience but _with no guarantees whatsoever_.
