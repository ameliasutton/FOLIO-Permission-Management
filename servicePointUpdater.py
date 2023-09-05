import warnings
import dotenv
import requests
import os
import csv
from tqdm import tqdm

class ServicePointUpdater:
    
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
            userServicePointFile = os.getenv('user_service_points_file')
            userIdColumnIndex = int(os.getenv('user_id_column_index'))
            userIdRowIndex = int(os.getenv('user_id_row_index'))
            self.results = os.getenv('servicePointsResultsFileName')
        except ValueError as env_error:
            raise env_error('Information missing from .env file. Required values: url, tenant, token')
        
        self.headers = {"Content-Type": "application/json",
                    "x-okapi-tenant": self.tenant,
                    "x-okapi-token": self.token}

        try:
            if self._test_token() == -1:
                self._retrieve_token(os.getenv('user'), os.getenv('password'))
        except PermissionError as perm:
            raise perm

        try:
            with open(userServicePointFile, 'r') as file:
                userPermissionsReader = csv.reader(file, delimiter=',')
                # Prepares the user Service Points dictionary
                userServicePointsContents = []
                for i, row in enumerate(userPermissionsReader):
                    if i >= userIdRowIndex:
                        userServicePointsContents.append(row)
        except FileNotFoundError as missingServicePointsFile:
            raise missingServicePointsFile
        servicePoints = []
        servicePointDict = {}
        self.userServicePoints = {}
        for row in userServicePointsContents:
            for permission in row[userIdColumnIndex+1:]:
                if permission not in servicePoints and permission != '':
                    servicePoints.append(permission)
        print("Looking Up Service Point UUIDs...")
        for permission in tqdm(servicePoints):
            servicePointDict[permission] = self._service_point_lookup(permission)
        print("Service Point UUIDs Retrieved!")
        for row in userServicePointsContents:
            self.userServicePoints[row[userIdColumnIndex]] = []
            for permission in row[userIdColumnIndex+1:]:
                if permission != '':
                    self.userServicePoints[row[userIdColumnIndex]].append(servicePointDict[permission])

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

    def _service_point_lookup(self, service_point_name):
        sp_URL = f'{self.url}service-points?query=name=={service_point_name} OR code=={service_point_name}'
        request = requests.get(sp_URL, headers=self.headers)
        if request.status_code != 200:
            raise ValueError(f'Service Point {service_point_name} not found, response code: {request.status_code}, url: {sp_URL}, headers: {self.headers}')
        response = request.json()
        if len(response['servicepoints']) == 0:
            raise ValueError(f'Service Point {service_point_name} not found')
        sp_id = response['servicepoints'][0]['id']
        
        return sp_id

    def _service_point_user_lookup(self, user_id):
        sp_user_URL = self.url + 'service-points-users?query=userId=' + user_id
        request = requests.get(sp_user_URL, headers=self.headers)
        response = request.json()
        if len(response['servicePointsUsers']) == 0:
            warnings.warn(f'User with id: {user_id} not found')
            return
        sp_user_id = response['servicePointsUsers'][0]['id']
        return sp_user_id

    def _service_point_put(self, user_id, sp_user_id, service_point_list):
        sp_URL = f'{self.url}service-points-users/{sp_user_id}'
        if len(service_point_list) != 0:
            payload = str({
                'userId': user_id,
                'servicePointsIds': service_point_list,
                'defaultServicePointId': service_point_list[0],
                'id': sp_user_id
            }).replace('\'','\"')
        else:
            payload = str({
            'id': sp_user_id,
            'userId': user_id,
            'servicePointsIds': service_point_list,
            'defaultServicePointId': 'null'
        }).replace('\'','\"').replace('\"null\"', 'null')
        request = requests.put(sp_URL, data=str(payload), headers = self.headers)
        return [user_id, request.status_code, str(service_point_list), str(sp_URL), str(payload), str(self.headers)]
    
    def _save_results(self, resultsList):
        with open(self.results, 'w') as output:
            for result in resultsList:
                output.write(str(result)+'\n')

    def get_user_service_points_table(self):
        return str(self.userServicePoints)
    
    def put_user_service_points(self):
        resultsList = []
        print("Applying Service Points in FOLIO...")
        for user in tqdm(self.userServicePoints.keys()):
            user_id = user
            perm_user_id = self._service_point_user_lookup(user_id=user_id)
            if perm_user_id:
                permissions = self.userServicePoints[user]
                resultsList.append(self._service_point_put(user_id=user_id, sp_user_id=perm_user_id, service_point_list=permissions))
        print("Requests complete, see results file for response statuses")
        self._save_results(resultsList=resultsList)
        return resultsList
              

if __name__ == '__main__':
    updater = ServicePointUpdater()
    updater.put_user_service_points()
    