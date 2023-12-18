import dotenv
import requests
import os
import csv
from tqdm import tqdm
from datetime import datetime
import logging

class ServicePointUpdater:
    
    def __init__(self, envfile=None):
        logging.info("Initializing Service Point Updater...")
        logging.info("Reading .env configuration file...")
        if envfile:
            dotenv.load_dotenv(envfile)
            self.env = envfile
        else:
            self.env = '.env'
            dotenv.load_dotenv()
        if os.getenv('url') and os.getenv('tenant') and os.getenv('user_file') and os.getenv('user_id_column_index') and os.getenv('user_service_point_column_index') and os.getenv('user_id_row_index') and os.getenv('user_id_row_index') and os.getenv('user') and os.getenv('password'): 
            self.url = f"{os.getenv('url').rstrip('/')}/"
            self.tenant = os.getenv('tenant')
            userFile = os.getenv('user_file')
            userIdColumnIndex = int(os.getenv('user_id_column_index'))
            userServicePointColumnIndex = int(os.getenv('user_service_point_column_index'))
            userIdRowIndex = int(os.getenv('user_id_row_index'))
        else:
            logging.critical(f".env file, \"{self.env}\"  not found or one or more required fields missing from .env")
            exit(".env file missing or required field(s) missing from .env")
        logging.info(".env file read successfully!")
        logging.info("Starting Requester Session...")
        try:
            self.session = requests.Session()
            self._retrieve_token(os.getenv('user'), os.getenv('password'))
            self.session.headers.update({"Content-Type": "application/json",
            "x-okapi-tenant": self.tenant})
        except PermissionError as perm:
            logging.critical("Token retrieval failed.")
            raise perm
        logging.info("Requester Session Initialized!")

        logging.info("Parsing Data file...")
        try:
            with open(userFile, 'r') as file:
                userServicePointReader = csv.reader(file, delimiter=',')
                # Prepares the user Service Points dictionary
                userServicePointsContents = []
                for i, row in enumerate(userServicePointReader):
                    if i >= userIdRowIndex and row[userIdColumnIndex] != '':
                        userServicePointsContents.append(row)
        except Exception as e:
            logging.critical(f"Data file, \"{userFile}\" not found or was formatted incorrectly")
            raise e
        servicePoints = []
        servicePointDict = {}
        self.userServicePoints = {}
        for row in userServicePointsContents:
            for servicePoint in row[userServicePointColumnIndex:]:
                if servicePoint not in servicePoints and servicePoint != '':
                    servicePoints.append(servicePoint)
        logging.info("Data file parsed successfully")
        logging.info("Looking up UUIDs for required service points...")
        for servicePoint in tqdm(servicePoints):
            servicePointDict[servicePoint] = self._service_point_lookup(servicePoint)
        logging.info("Service Point UUIDs Retrieved!")
        for row in userServicePointsContents:
            self.userServicePoints[row[userIdColumnIndex]] = []
            for servicePoint in row[userServicePointColumnIndex:]:
                if servicePoint != '':
                    self.userServicePoints[row[userIdColumnIndex]].append(servicePointDict[servicePoint])
        logging.info("Service Point Updater Initialized!")
    
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

    def _service_point_lookup(self, service_point_name):
        sp_URL = f'{self.url}service-points?query=name=={service_point_name} OR code=={service_point_name}'
        request = self.session.get(sp_URL)
        if request.status_code != 200:
            logging.critical(f'Service Point {service_point_name} not found, response code: {request.status_code}, url: {sp_URL}, headers: {self.session.headers}')
            raise ValueError
        response = request.json()
        if len(response['servicepoints']) == 0:
            logging.critical(f'Service Point {service_point_name} not found')
            raise ValueError
        sp_id = response['servicepoints'][0]['id']
        return sp_id

    def _create_service_point_user(self, user_id):
        logging.info(f"Creating service point user record for user with id: {user_id}...")
        sp_user_creation_URL = self.url + 'service-points-users'
        payload = {"userId": user_id, "servicePointsIds": []}
        request = self.session.post(sp_user_creation_URL, data = str(payload).replace("'",'"'))
        if request.status_code != 201:
            logging.critical(f'Service Point User creation for user with id: {user_id} failed, status code: {request.status_code}')
            raise RuntimeError
        else:
            response = request.json()
            logging.info(f"Service point user record created for user with id: {user_id}")
            return response['id']

    def _service_point_user_comparison(self, user_id):
        sp_user_URL = self.url + 'service-points-users?query=userId=' + user_id
        request = self.session.get(sp_user_URL)
        response = request.json()
        if (response['totalRecords']) == 0:
            logging.warning(f'Service Point User record for user with id: {user_id} not found.')
            return True, self._create_service_point_user(user_id)
        sp_user_id = response['servicePointsUsers'][0]['id']
        current_service_points = response['servicePointsUsers'][0]['servicePointsIds']
        try:
            current_default_sp = response['servicePointsUsers'][0]['defaultServicePointId']
        except:
            logging.warning(f'User with id: {user_id} has no existing detault service point')
            current_default_sp = ''
        if set(self.userServicePoints[user_id]) == set(current_service_points) and len(self.userServicePoints[user_id])==len(current_default_sp) and len(self.userServicePoints[user_id]) == 0:
            return False, ''
        elif set(self.userServicePoints[user_id]) == set(current_service_points) and self.userServicePoints[user_id][0] == current_default_sp:
            return False, ''
        else:
            return True, sp_user_id
        

    def _service_point_put(self, user_id, sp_user_id, service_point_list):
        sp_URL = f'{self.url}service-points-users/{sp_user_id}'
        if len(service_point_list) != 0:
            payload = str({
                'userId': user_id,
                'servicePointsIds': service_point_list,
                'defaultServicePointId': service_point_list[0],
                'id': sp_user_id
            }).replace('\'','\"')
            logging.info(f"Updating user with id: {user_id} and service point user id: {sp_user_id} assigning the following default service point: {service_point_list[0]} and the following service points: {service_point_list}")
        else:
            payload = str({
            'id': sp_user_id,
            'userId': user_id,
            'servicePointsIds': service_point_list,
            'defaultServicePointId': 'null'
            }).replace('\'','\"').replace('\"null\"', 'null')
            logging.info(f"Updating user with id: {user_id} and service point user id: {sp_user_id} removing all service point assignments")
        request = self.session.put(sp_URL, data=str(payload))
        if request.status_code == 204:
            logging.info(f"Service points updated for user with id: {user_id}")
        return [user_id, request.status_code, str(service_point_list), str(sp_URL), str(payload), str(self.session.headers)]

    def put_user_service_points(self):
        logging.info("Applying Service Points in FOLIO...")
        for user in tqdm(self.userServicePoints.keys()):
            user_id = user
            update, sp_user_id = self._service_point_user_comparison(user_id=user_id)
            if update:
                self._service_point_put(user_id, sp_user_id, self.userServicePoints[user])
            else:
                logging.info(f"Service Points for User with id {user_id} required no changes")
        logging.info("All service points applied in FOLIO.")
        return 0
              

if __name__ == '__main__':
    start_time = datetime.now()
    logFile = f'Logs/{start_time.year}-{start_time.month}-{start_time.day}--{start_time.hour}-{start_time.minute}-{start_time.second}.log'
    logging.basicConfig(filename=logFile, encoding='utf-8', level=logging.DEBUG,
                    format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logging.info("Beginning Log")
    updater = ServicePointUpdater("Test.env")
    updater.put_user_service_points()

