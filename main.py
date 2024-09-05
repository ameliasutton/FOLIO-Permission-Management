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

    logpath = "Logs"

    logFile = f'{logpath}/{start_time.year}-{start_time.month}-{start_time.day}--{start_time.hour}-{start_time.minute}-{start_time.second}.log'
    logging.basicConfig(filename=logFile, encoding='utf-8', level=logging.DEBUG,
                    format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logging.info("Beginning Log")
    
    env = input("Which .env file should be used?\n")

    if env.lower() == "staff":
        permsUpdater = PermissionUpdater("UM Staff.env")
        servicePointUpdater = ServicePointUpdater("UM Staff.env")
    elif env.lower() == "students":
        permsUpdater = PermissionUpdater("UM Student.env")
        servicePointUpdater = ServicePointUpdater("UM Student.env")
    elif env.lower() == "test":
        permsUpdater = PermissionUpdater("Test.env")
        servicePointUpdater = ServicePointUpdater("Test.env")
    else:
        permsUpdater = PermissionUpdater(env)
        servicePointUpdater = ServicePointUpdater(env)

    action = input("What would you like to do? (Refresh/Apply)\n")

    if action.lower() == "refresh":
        permsUpdater.rebuild_permissions_csv()
        servicePointUpdater.rebuild_service_points_csv()
    elif action.lower() == "apply":
        permsUpdater.apply_user_permissions()
        servicePointUpdater.apply_user_service_points()

