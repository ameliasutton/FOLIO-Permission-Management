from servicePointUpdater import ServicePointUpdater
from permissionUpdater import PermissionUpdater

if __name__ == '__main__':
    permsUpdater = PermissionUpdater()
    permsUpdater.put_user_permissions()
    servicePointUpdater = ServicePointUpdater()
    servicePointUpdater.put_user_service_points()