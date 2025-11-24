import logging
import dotenv
import requests
import os
import csv
from tqdm import tqdm
from datetime import datetime


class RolesUpdater:
    
    def __init__(self, envfile=None):
        logging.info("Initializing Permission Updater...")
        logging.info("Reading .env configuration file...")
        if envfile:
            dotenv.load_dotenv(envfile)
            self.env = envfile
        else:
            self.env = '.env'
            dotenv.load_dotenv()
        if os.getenv('url') and os.getenv('tenant') and os.getenv('perms_file') and os.getenv('user_id_column_index') and os.getenv('user') and os.getenv('password'):
            self.url = f"{os.getenv('url').rstrip('/')}/"
            self.tenant = os.getenv('tenant')
            self.userFile = os.getenv('perms_file')
            self.userIdColumnIndex = int(os.getenv('user_id_column_index'))
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
            with open(self.userFile, 'r') as file:
                userPermissionsReader = csv.reader(file, delimiter='\t')
                # Prepares the user Permissions dictionary
                userPermissionsContents = []
                for i, row in enumerate(userPermissionsReader):
                    if i >= 1 and row[self.userIdColumnIndex]!= '':
                        userPermissionsContents.append(row)
        except Exception as e:
            logging.critical(f"Data file, \"{self.userFile}\" not found or was formatted incorrectly")
            raise e
        permissions = []
        permissionDict = {}
        self.userPermissions = {}
        self.userInfo = {}
        for row in tqdm(userPermissionsContents, desc = "Parsing data file and looking up permission ids"):
            self.userInfo[row[self.userIdColumnIndex]] = []
            self.userPermissions[row[self.userIdColumnIndex]] = []
            for i, column in enumerate(row):
                if i<self.userIdColumnIndex:
                    self.userInfo[row[self.userIdColumnIndex]].append(column)
                if i>self.userIdColumnIndex and column != '':
                    if column not in permissions:
                        permissions.append(column)
                        permissionDict[column] = self._permission_id_lookup(column)
                    self.userPermissions[row[self.userIdColumnIndex]].append(permissionDict[column])
        logging.info("Data file parsed successfully")
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

    def _permission_id_lookup(self, permission_name):
        permSetURL = f'{self.url}roles?query=name=="{permission_name}"'
        request = self.session.get(permSetURL)
        if request.status_code != 200:
            logging.critical(f'Permission {permission_name} not found, response code: {request.status_code}, url: {permSetURL}, headers: {self.session.headers}')
            raise ValueError
        response = request.json()
        if len(response['roles']) == 0:
            logging.critical(f'Permission {permission_name} not found')
            raise ValueError
        perm_id = response['roles'][0]['id']
        return perm_id
    
    def _permission_name_lookup(self, permission_id):
        permSetURL = f'{self.url}roles/{permission_id}'
        request = self.session.get(permSetURL)
        if request.status_code != 200:
            logging.critical(f'Permission with ID {permission_id} not found, response code: {request.status_code}, url: {permSetURL}, headers: {self.session.headers}')
            raise ValueError
        response = request.json()
        perm_name = response['name']
        return perm_name

    def _get_current_perms(self, user_id):
        permLookupURL = f'{self.url}roles/users/{user_id}'
        request = self.session.get(permLookupURL)
        if request.status_code >= 400:
            logging.warning(f'User with id: {user_id} not found')
            return []
        response = request.json()
        user_perms = []
        for role in response['userRoles']:
            user_perms.append(role['roleId'])
        return user_perms

    def _perm_comparison(self, user_id):
        existing_perms = self._get_current_perms(user_id=user_id)
        if sorted(self.userPermissions[user_id]) == sorted(existing_perms):
            logging.info(f"Permissions for User with id {user_id} required no changes")
            return False, ''
        else:
            return True

    def _create_keycloak_user(self, user_id):
        """
        Used when a user record does not have an associated keycloak user record. 
        Takes a User record UUID, creates a new keycloak user in FOLIO
        """
        logging.info(f"Retrieving User Record with id: {user_id}")
        userGetURL = f'{self.url}users/{user_id}'
        userRequest = self.session.get(userGetURL)
        userRecord = str(userRequest.json()).replace("'",'"').replace("True", "true").replace("False","false")
        logging.info(f"User record retrieved")
    
        logging.info(f"Creating keycloak user record for user with id: {user_id}...")
        keycloakUserURL = f'{self.url}users-keycloak/users'
        keycloakRequest = self.session.post(keycloakUserURL, data=userRecord)
        if keycloakRequest.status_code != 201:
            logging.critical(f'Keycloak User creation for user with id: {user_id} failed: {keycloakRequest.text}')
            raise RuntimeError
        else:
            logging.info(f"Keycloak user record created for user with id: {user_id}")
            return True

    def _permission_put(self, user_id, permission_list):
        permissionURL = f'{self.url}roles/users/{user_id}'
        payload = str({
            'userId': user_id,
            'roleIds': permission_list
        }).replace('\'','\"')
        logging.info(f"Updating user with id: {user_id} assigning the following permissions: {permission_list}")
        request = self.session.put(permissionURL, data=str(payload))
        if request.status_code == 200:
            logging.info(f"Permissions updated for user with id: {user_id}")
        if request.status_code == 404:
            response = request.json()
            if response["errors"][0]["type"] == "EntityNotFoundException":
                logging.warning(f"Keycloak user could not be found for user with Id: {user_id}")
                # Moved to other function
                if self._create_keycloak_user(user_id):
                    return self._permission_put(user_id, permission_list)
        else:
            logging.info(request.text)
        return [user_id, request.status_code, str(permission_list), str(permissionURL), str(payload), str(self.session.headers)]

    def get_user_permissions_table(self):
        return str(self.userPermissions)
    
    def rebuild_permissions_csv(self):
        logging.info("Rebuilding Permissions csv file to match data in FOLIO...")
        currentUserPermissions = {}
        unique_perms = []
        
        # Retrieves Current Permissions for each user
        logging.info("Retrieving Current user permissions...")
        for user_id in tqdm(self.userPermissions.keys(), desc="Retrieving Current user permissions"):
            user_perms = self._get_current_perms(user_id)
            currentUserPermissions[user_id] = user_perms
            unique_perms = list(set(unique_perms) | set(user_perms))
        logging.info("Current Permissions retrieved!")

        logging.info("Looking up permission names...")
        permissionDict = {}
        for permission in tqdm(unique_perms, desc="Looking up permission names"):
            permissionDict[permission] = self._permission_name_lookup(permission)
        self.userPermissions = currentUserPermissions
        logging.info("Permission names retrieved.")

        logging.info("Updating csv file...")
        # Updates Data File with current permissions
        with open(self.userFile, 'w', encoding="utf-8") as file:
            data_headers = 'User Data\t'*self.userIdColumnIndex
            perms_headers = '\t '.join(permissionDict.values())
            headers = f"{data_headers}User Id\t {perms_headers}\n"
            file.write(headers)
            for user_id in tqdm(currentUserPermissions.keys(), desc = "Updating csv file"):
                user_line = ""
                for data in self.userInfo[user_id]:
                    user_line += f"{data}\t"

                user_line += f"{user_id}\t"

                for permission in permissionDict.keys():
                    if permission in currentUserPermissions[user_id]:
                        user_line += f"{permissionDict[permission]}\t"
                    else:
                        user_line += f"\t"
                user_line += '\n'
                for permission in permissionDict.keys():
                    user_line.replace(permission, permissionDict[permission])
                file.write(user_line)
        logging.info("File updated")
        logging.info("Rebuild Complete")
        return(0)

    def apply_user_permissions(self):
        logging.info("Applying Permissions in FOLIO...")
        for user_id in tqdm(self.userPermissions.keys(), desc= "Applying permissions in FOLIO"):
            updated = self._perm_comparison(user_id=user_id)
            if updated:
                permissions = self.userPermissions[user_id]
                self._permission_put(user_id=user_id, permission_list=permissions)
        logging.info("All permissions applied in FOLIO")
        return 0
              

if __name__ == '__main__':
    start_time = datetime.now()
    logFile = f'Logs/{start_time.year}-{start_time.month}-{start_time.day}--{start_time.hour}-{start_time.minute}-{start_time.second}.log'
    logging.basicConfig(filename=logFile, encoding='utf-8', level=logging.DEBUG,
                    format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logging.info("Beginning Log")
    updater = RolesUpdater("rolesTest.env")
    updater.apply_user_permissions()