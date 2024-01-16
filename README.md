# FOLIO Permissions and Service Point Management
Copyright (C) 2022-2024  Amelia Sutton

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
* Create .env config file in the following format:
>url = <br />
tenant = <br />
user = <br />
password=<br />
user_file=<br />
user_id_row_index = <br />
user_id_column_index = <br />
user_permission_column_index = <br />
user_service_point_column_index = <br />

* Create a .csv file with the name listed in the user_file in the .env file formatted as follows:
  
    * The file should be comma deliniated
    * Columns 0 through user_id_column_index can contain any data of your choice.
    * Rows 0 through user_id_row_column_index can contain any data of your choice
    * The Column at user_id_column_index should contain the uuids for the user records to be updated
    * The columns between user_id_column_index up to but not including user_

* Place .csv data file in the program's directory.
* Create a subfolder in the program's directory called "Logs"
* Open cmd and navigate to the program's directory and run main.py


## Contributors


* Amelia Sutton

    
## Known Issues
  
## Planned Features
* Updating Acquisitions Unit assignment
* Updating eHoldings Group assignment