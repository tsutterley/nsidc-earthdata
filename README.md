nsidc-earthdata
================

#### ftp-like program for searching NSIDC databases and retrieving NASA Operation IceBridge data  

- [NASA Earthdata Login system](https://urs.earthdata.nasa.gov)  
- [How to Access Data with Python](https://wiki.earthdata.nasa.gov/display/EL/How+To+Access+Data+With+Python)  
- [NSIDC: what options are available](https://nsidc.org/support/faq/what-options-are-available-bulk-downloading-data-https-earthdata-login-enabled)  

Register with NASA Earthdata Login system and add **NSIDC_DATAPOOL_OPS** to your NASA Earthdata Applications

#### Calling Sequence
```
python nsidc_earthdata.py
Username for urs.earthdata.nasa.gov: <username>
Password for <username>@urs.earthdata.nasa.gov: <password>
Welcome to n5eil01u.ecs.nsidc.org
> help
```

##### Function list:
`help`: Lists the following command line options  
`ls`: List contents of the remote directory  
`cd`: Change the remote directory  
`lcd`: Change the local directory  
`mkdir`: Create a directory within the local directory  
`pwd`: Print the current local and remote directory paths  
`sync`: Sync all files in directory with a local directory  
`rsync`: Recursively sync all directories with a local directory  
`mget`: Get all files in directory  
`get`: Get a single file in a directory  
`exit`: Exit program  

#### Dependencies
[lxml: processing XML and HTML in Python](https://pypi.python.org/pypi/lxml)

#### Download
The program homepage is:   
https://github.com/tsutterley/nsidc-earthdata    
A zip archive of the latest version is available directly at:    
https://github.com/tsutterley/nsidc-earthdata/archive/master.zip  

#### Disclaimer  
This program is not sponsored or maintained by the Universities Space Research Association (USRA), the National Snow and Ice Data Center (NSIDC) or NASA.  It is provided here for your convenience but _with no guarantees whatsoever_.
