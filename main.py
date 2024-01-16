"""
Copyright (C) 2022-2024  Amelia Sutton
This software is distributed under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version. See the file "[COPYING](COPYING)" for more details.
"""
from servicePointUpdater import ServicePointUpdater
from permissionUpdater import PermissionUpdater
from datetime import datetime
import logging
if __name__ == '__main__':
    start_time = datetime.now()
    logFile = f'Logs/{start_time.year}-{start_time.month}-{start_time.day}--{start_time.hour}-{start_time.minute}-{start_time.second}.log'
    logging.basicConfig(filename=logFile, encoding='utf-8', level=logging.DEBUG,
                    format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logging.info("Beginning Log")
    #permsUpdater = PermissionUpdater("UM Staff.env")
    #permsUpdater.put_user_permissions()
    #servicePointUpdater = ServicePointUpdater("UM Staff.env")
    #servicePointUpdater.put_user_service_points()
    
    permsUpdater = PermissionUpdater("Test.env")
    permsUpdater.put_user_permissions()
    servicePointUpdater = ServicePointUpdater("Test.env")
    servicePointUpdater.put_user_service_points()