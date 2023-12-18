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
    
    permsUpdater = PermissionUpdater("UM Student.env")
    permsUpdater.put_user_permissions()
    servicePointUpdater = ServicePointUpdater("UM Student.env")
    servicePointUpdater.put_user_service_points()