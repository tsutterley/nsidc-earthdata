earthdata.py
============

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
```

##### Function list:
 - `usage`: Lists the following command line options
 - `ls`: List contents of the remote directory
 - `cd`: Change the remote directory
 - `lcd`: Change the local directory
 - `mkdir`: Create a directory within the local directory
 - `pwd`: Print the current local and remote directory paths
 - `sync`: Sync all files in directory with a local directory
 - `rsync`: Recursively sync all directories with a local directory
 - `mget`: Get all files in directory
 - `get`: Get a single file in a directory
 - `verbose`: Toggle verbose output
 - `checksum`: Toggle checksum function
 - `exit`: Exit program

#### Examples
##### Getting help for a function
```
> help rsync
Recursively sync all directories with a local directory
```
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
