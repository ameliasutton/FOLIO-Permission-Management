

# FOLIO Permissions and Service Point Management

A script to update the service points and permissions assigned to users in FOLIO
## Requirements


* Python 3.x
* dotenv

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

* Place Student and Staff data files in the program's directory.



## Contributors


* Amelia Sutton


## Version History

* 0.1
    * Initial Release
    
## Known Issues
* 
## Planned Features
*