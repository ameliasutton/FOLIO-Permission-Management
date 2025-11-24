# FOLIO Permissions and Service Point Management
Copyright (C) 2022-2025  Amelia Sutton

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  

See the file "[COPYING](COPYING)" for more details.


## Introduction
A script to update the service points and permissions assigned to users in FOLIO

## Requirements
* Python 3.x
* dotenv
* tqdm

## Usage Instructions
### Configuration
Create .env config file in the following format:
>url = <br />
tenant = <br />
user = <br />
password=<br />
perms_file=<br />
sp_file=<br />
user_id_column_index = <br />

### Create Data Files
#### Create a .csv file with the name listed in the perms_file in the .env file formatted as follows:

* The file should be comma deliniated
* Row 0 should contain column headers
* Columns 0 through user_id_column_index can contain any data of your choice.
* The Column at user_id_column_index should contain the uuids for the user records to be updated
* Columns after the user_id_column_index will be populated with permissions data when you refresh the files

#### Create a .csv file with the name listed in the sp_file in the .env file formatted as follows:

* The file should be comma deliniated
* Row 0 should contain column headers
* Columns 0 through user_id_column_index can contain any data of your choice.
* The Column at user_id_column_index should contain the uuids for the user records to be updated

### Refresh Data Files

* Place .csv data file in the program's directory.
* Create a subfolder in the program's directory called "Logs"
* Open cmd and navigate to the program's directory and run main.py (or "rolesMain.py" for Eureka environments)
* When prompted enter the name of your .env file
* When prompted enter "refresh"
  * The script will update the Permissions and Service Points .csv files with the users' current permissions

### Apply Permissions and Service Points 
* Make any changes to user permissions and service points in their respective files
  * Permissions either the displayName or permissionName should be used in the permissions file 
  * Service points codes should be used in the service points file
  * You can add as many additional columns as you need to the right of the user_id_column_index column
  * The first column of service point codes will be set as the user's default service point
* Open cmd and navigate to the program's directory and run "main.py" (or "rolesMain.py" for Eureka environments)
* When prompted enter the name of your .env file
* When prompted enter "apply"
  * The script will update the Permissions and Service points for the users in FOLIO


## Contributors


* Amelia Sutton

    
## Known Issues
  
## Planned Features
* Updating Acquisitions Unit assignment
* Updating eHoldings Group assignment