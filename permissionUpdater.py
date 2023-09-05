import warnings
import dotenv
import requests
import os
import csv
from tqdm import tqdm

class PermissionUpdater:
    
    def __init__(self, envfile=None):
        try:
            if envfile:
                dotenv.load_dotenv(envfile)
                self.env = envfile
            else:
                self.env = '.env'
                dotenv.load_dotenv()
            self.url = f"{os.getenv('url').rstrip('/')}/"
            self.tenant = os.getenv('tenant')
            self.token = os.getenv('token')
            userPermissionsFile = os.getenv('user_permissions_file')
            userIdColumnIndex = int(os.getenv('user_id_column_index'))
            userIdRowIndex = int(os.getenv('user_id_row_index'))
            self.results = os.getenv('permsResultsFileName')
        except ValueError as env_error:
            raise env_error('Information missing from .env file. Required values: url, tenant, token')
        
        self.headers = {"Content-Type": "application/json",
                    "x-okapi-tenant": self.tenant,
                    "x-okapi-token": self.token,
                    "Accept": "application/json"}

        try:
            if self._test_token() == -1:
                self._retrieve_token(os.getenv('user'), os.getenv('password'))
        except PermissionError as perm:
            raise perm

        try:
            with open(userPermissionsFile, 'r') as file:
                userPermissionsReader = csv.reader(file, delimiter=',')
                # Prepares the user Permissions dictionary
                userPermissionsContents = []
                for i, row in enumerate(userPermissionsReader):
                    if i >= userIdRowIndex:
                        userPermissionsContents.append(row)
        except FileNotFoundError as missingPermissionsFile:
            raise missingPermissionsFile
        permissions = []
        permissionDict = {}
        self.userPermissions = {}
        for row in userPermissionsContents:
            for permission in row[userIdColumnIndex+1:]:
                if permission not in permissions and permission != '':
                    permissions.append(permission)
        print("Looking Up Permission UUIDs...")
        for permission in tqdm(permissions):
            permissionDict[permission] = self._permission_lookup(permission)
        print("Permission UUIDs Retrieved!")
        for row in userPermissionsContents:
            self.userPermissions[row[userIdColumnIndex]] = []
            for permission in row[userIdColumnIndex+1:]:
                if permission != '':
                    self.userPermissions[row[userIdColumnIndex]].append(permissionDict[permission])

    def _test_token(self):
        connection_url = self.url + "users?query=limit=0"
        try:
            test = requests.get(connection_url, headers=self.headers)
        except:
            return -1
        if test.status_code == 401:
            warnings.warn('Invalid Token')
            return -1
        else:
            return 0
    
    def _retrieve_token(self, user, password):
        headers = {'Content-Type': 'application/json',
                   'x-okapi-tenant': self.tenant}
        payload = f'{{\"username\": \"{user}\", \"password\": \"{password}\"}}'
        print(payload)
        connection_url = self.url + "authn/login"
        login = requests.post(connection_url, headers=headers, data=payload, timeout=10)
        if login.status_code != 201:
            raise RuntimeError(f'Invalid Token and login credentials, auth/login response status: {login.status_code}')
        else:
            self._set_token(login.headers['x-okapi-token'])
            return 0
    
    def _set_token(self, token):
        try:
            os.environ['token'] = token
            dotenv.set_key(self.env, 'token', token, os.environ['token'])
            self.token = token
        except PermissionError:
            return -1

    def _permission_lookup(self, permission_name):
        permSetURL = f'{self.url}perms/permissions?query=displayName=={permission_name} OR permissionName=={permission_name}'
        request = requests.get(permSetURL, headers=self.headers)
        if request.status_code != 200:
            raise ValueError(f'Permission {permission_name} not found, response code: {request.status_code}, url: {permSetURL}, headers: {self.headers}')
        response = request.json()
        if len(response['permissions']) == 0:
            raise ValueError(f'Permission {permission_name} not found')
        perm_id = response['permissions'][0]['permissionName']
        
        return perm_id

    def _perm_user_lookup(self, user_id):
        permUserURL = self.url + 'perms/users?query=userId=' + user_id
        request = requests.get(permUserURL, headers=self.headers)
        response = request.json()
        if len(response['permissionUsers']) == 0:
            warnings.warn(f'User with id: {user_id} not found')
            return
        perm_user_id = response['permissionUsers'][0]['id']
        return perm_user_id

    def _permission_put(self, user_id, perm_user_id, permission_list):
        permissionURL = f'{self.url}perms/users/{perm_user_id}?indexField=userId'
        payload = str({
            'id': perm_user_id,
            'userId': user_id,
            'permissions': permission_list
        }).replace('\'','\"')
        request = requests.put(permissionURL, data=str(payload), headers = self.headers)
        return [user_id, request.status_code, str(permission_list), str(permissionURL), str(payload), str(self.headers)]
    
    def _save_results(self, resultsList):
        with open(self.results, 'w') as output:
            for result in resultsList:
                output.write(str(result)+'\n')

    def get_user_permissions_table(self):
        return str(self.userPermissions)
    
    def put_user_permissions(self):
        resultsList = []
        print("Applying Permissions in FOLIO...")
        for user in tqdm(self.userPermissions.keys()):
            user_id = user
            perm_user_id = self._perm_user_lookup(user_id=user_id)
            if perm_user_id:
                permissions = self.userPermissions[user]
                resultsList.append(self._permission_put(user_id=user_id, perm_user_id=perm_user_id, permission_list=permissions))
            else:
                resultsList.append(f'No Service Point User found for {user_id}')
        print("Requests complete, see results file for response statuses")
        self._save_results(resultsList=resultsList)
        return resultsList
              

if __name__ == '__main__':
    updater = PermissionUpdater()
    updater.put_user_permissions()
    