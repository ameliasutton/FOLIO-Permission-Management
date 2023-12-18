import logging
import dotenv
import requests
import os
import csv
from tqdm import tqdm
from datetime import datetime


class PermissionUpdater:
    
    def __init__(self, envfile=None):
        logging.info("Initializing Permission Updater...")
        logging.info("Reading .env configuration file...")
        if envfile:
            dotenv.load_dotenv(envfile)
            self.env = envfile
        else:
            self.env = '.env'
            dotenv.load_dotenv()
        if os.getenv('url') and os.getenv('tenant') and os.getenv('user_file') and os.getenv('user_id_column_index') and os.getenv('user_service_point_column_index') and os.getenv('user_id_row_index') and os.getenv('user_id_row_index') and os.getenv('user') and os.getenv('password') and os.getenv('user_permission_column_index'):
            self.url = f"{os.getenv('url').rstrip('/')}/"
            self.tenant = os.getenv('tenant')
            userFile = os.getenv('user_file')
            userIdColumnIndex = int(os.getenv('user_id_column_index'))
            userIdRowIndex = int(os.getenv('user_id_row_index'))
            userServicePointColumnIndex = int(os.getenv('user_service_point_column_index'))
            userPermissionColumnIndex = int(os.getenv('user_permission_column_index'))
        else:
            logging.critical(f".env file, \"{self.env}\"  not found or one or more required fields missing from .env")
            exit(".env file missing or required field(s) missing from .env")
        logging.info(".env file read successfully!")
        logging.info("Retrieving API token...")
        try:
            self.session = requests.session()
            self._retrieve_token(os.getenv('user'), os.getenv('password'))
            self.session.headers.update({"Content-Type": "application/json",
                    "x-okapi-tenant": self.tenant,
                    "Accept": "application/json"})
        except PermissionError as perm:
            logging.critical("Token retrieval failed.")
            raise perm
        logging.info("API token retrieved!")
    
        logging.info("Parsing Data file...")
        try:
            with open(userFile, 'r') as file:
                userPermissionsReader = csv.reader(file, delimiter=',')
                # Prepares the user Permissions dictionary
                userPermissionsContents = []
                for i, row in enumerate(userPermissionsReader):
                    if i >= userIdRowIndex and row[userIdColumnIndex]!= '':
                        userPermissionsContents.append(row)
        except Exception as e:
            logging.critical(f"Data file, \"{userFile}\" not found or was formatted incorrectly")
            raise e
        permissions = []
        permissionDict = {}
        self.userPermissions = {}
        for row in userPermissionsContents:
            for permission in row[userPermissionColumnIndex:userServicePointColumnIndex]:
                if permission not in permissions and permission != '':
                    permissions.append(permission)
        logging.info("Data file parsed successfully")
        logging.info("Looking Up Permission UUIDs...")
        for permission in tqdm(permissions):
            permissionDict[permission] = self._permission_lookup(permission)
        logging.info("Permission UUIDs Retrieved!")
        for row in userPermissionsContents:
            self.userPermissions[row[userIdColumnIndex]] = []
            for permission in row[userPermissionColumnIndex:userServicePointColumnIndex]:
                if permission != '':
                    self.userPermissions[row[userIdColumnIndex]].append(permissionDict[permission])
        logging.info("Permission Updater Initialized")

    def _retrieve_token(self, user, password):
        headers = {'Content-Type': 'application/json',
                   'x-okapi-tenant': self.tenant}
        payload = f'{{\"username\": \"{user}\", \"password\": \"{password}\"}}'
        connection_url = self.url + "authn/login-with-expiry"
        login = self.session.post(connection_url, headers=headers, data=payload, timeout=10)
        if login.status_code != 201:
            logging.critical(f'Invalid Token and login credentials, auth/login response status: {login.status_code}')
            exit(f'Invalid Token and login credentials, auth/login response status: {login.status_code}')
        else:
            return 0

    def _permission_lookup(self, permission_name):
        permSetURL = f'{self.url}perms/permissions?query=displayName=={permission_name} OR permissionName=={permission_name}'
        request = self.session.get(permSetURL)
        if request.status_code != 200:
            logging.critical(f'Permission {permission_name} not found, response code: {request.status_code}, url: {permSetURL}, headers: {self.session.headers}')
            raise ValueError
        response = request.json()
        if len(response['permissions']) == 0:
            logging.critical(f'Permission {permission_name} not found')
            raise ValueError
        perm_id = response['permissions'][0]['permissionName']
        return perm_id

    def _perm_comparison(self, user_id):
        permUserURL = f'{self.url}perms/users/{user_id}?full=true&indexField=userId'
        request = self.session.get(permUserURL)
        if request.status_code >= 400:
            logging.warning(f'User with id: {user_id} not found')
            return False, ''
        response = request.json()
        perm_user_id = response['id']
        existing_perms = response['permissions']
        if sorted(self.userPermissions[user_id]) == sorted(existing_perms):
            logging.info(f"Permissions for User with id {user_id} required no changes")
            return False, ''
        else:
            return True, perm_user_id

    def _permission_put(self, user_id, perm_user_id , permission_list):
        permissionURL = f'{self.url}perms/users/{perm_user_id}'
        payload = str({
            'id' : perm_user_id,
            'userId': user_id,
            'permissions': permission_list
        }).replace('\'','\"')
        logging.info(f"Updating user with id: {user_id} assigning the following permissions: {permission_list}")
        request = self.session.put(permissionURL, data=str(payload))
        if request.status_code == 200:
            logging.info(f"Permissions updated for user with id: {user_id}")
        else:
            logging.info(request.text)
        return [user_id, request.status_code, str(permission_list), str(permissionURL), str(payload), str(self.session.headers)]

    def get_user_permissions_table(self):
        return str(self.userPermissions)
    
    def put_user_permissions(self):
        print("Applying Permissions in FOLIO...")
        for user_id in tqdm(self.userPermissions.keys()):
            updated, perm_user_id = self._perm_comparison(user_id=user_id)
            if updated:
                permissions = self.userPermissions[user_id]
                self._permission_put(user_id=user_id, perm_user_id=perm_user_id, permission_list=permissions)
        logging.info("All permissions applied in FOLIO")
        return 0
              

if __name__ == '__main__':
    start_time = datetime.now()
    logFile = f'Logs/{start_time.year}-{start_time.month}-{start_time.day}--{start_time.hour}-{start_time.minute}-{start_time.second}.log'
    logging.basicConfig(filename=logFile, encoding='utf-8', level=logging.DEBUG,
                    format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logging.info("Beginning Log")
    updater = PermissionUpdater("Test.env")
    updater.put_user_permissions()
    