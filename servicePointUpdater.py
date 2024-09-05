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
        if os.getenv('url') and os.getenv('tenant') and os.getenv('sp_file') and os.getenv('user_id_column_index') and os.getenv('user') and os.getenv('password'): 
            self.url = f"{os.getenv('url').rstrip('/')}/"
            self.tenant = os.getenv('tenant')
            self.userFile = os.getenv('sp_file')
            self.userIdColumnIndex = int(os.getenv('user_id_column_index'))
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
            with open(self.userFile, 'r') as file:
                userServicePointReader = csv.reader(file, delimiter='\t')
                # Prepares the user Service Points dictionary
                userServicePointsContents = []
                for i, row in enumerate(userServicePointReader):
                    if i >= 1 and row[self.userIdColumnIndex] != '':
                        userServicePointsContents.append(row)
        except Exception as e:
            logging.critical(f"Data file, \"{self.userFile}\" not found or was formatted incorrectly")
            raise e
        servicePoints = []
        servicePointDict = {}
        self.userServicePoints = {}
        self.userInfo = {}
        for row in tqdm(userServicePointsContents, desc = "Parsing data file and looking up service point ids"):
            self.userInfo[row[self.userIdColumnIndex]] = []
            self.userServicePoints[row[self.userIdColumnIndex]] = []
            for i, column in enumerate(row):
                if i<self.userIdColumnIndex:
                    self.userInfo[row[self.userIdColumnIndex]].append(column)
                elif i>self.userIdColumnIndex and column != '':
                    if column not in servicePoints:
                        servicePoints.append(column)
                        servicePointDict[column] = self._service_point_id_lookup(column)
                    self.userServicePoints[row[self.userIdColumnIndex]].append(servicePointDict[column])
        logging.info("Data file parsed successfully")

        for row in userServicePointsContents:
            self.userServicePoints[row[self.userIdColumnIndex]] = []
            for servicePoint in row[self.userIdColumnIndex+1:]:
                if servicePoint != '':
                    self.userServicePoints[row[self.userIdColumnIndex]].append(servicePointDict[servicePoint])
        logging.info("Service Point Updater Initialized!")
    
    def _retrieve_token(self, user, password):
        """Requests a new authentication token, returns 0 on success."""
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

        
    def _service_point_id_lookup(self, service_point_name):
        """Looks up a service point by name or code, returns the UUID for the Service Point."""    
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

    def _service_point_name_lookup(self, service_point_id):
        """Takes a service point UUID and returns the service point's code"""
        spURL = f'{self.url}service-points/{service_point_id}'
        request = self.session.get(spURL)
        if request.status_code != 200:
            logging.critical(f'Service Point with ID {service_point_id} not found, response code: {request.status_code}, url: {spURL}, headers: {self.session.headers}')
            raise ValueError
        response = request.json()
        service_point_name = response['code']
        return service_point_name


    def _create_service_point_user(self, user_id):
        """
        Used when a user record does not have an associated service point user record. 
        Takes a User record UUID, creates a new service point user in FOLIO, then returns the new record's UUID
        """
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

    def _get_current_sps(self, user_id):
        sp_user_URL = self.url + 'service-points-users?query=userId=' + user_id
        request = self.session.get(sp_user_URL)
        response = request.json()
        if (response['totalRecords']) == 0:
            logging.warning(f'Service Point User record for user with id: {user_id} not found.')
            return self._create_service_point_user(user_id), '' , []
        sp_user_id = response['servicePointsUsers'][0]['id']
        current_service_points = response['servicePointsUsers'][0]['servicePointsIds']
        try:
            current_default_sp = response['servicePointsUsers'][0]['defaultServicePointId']
        except:
            logging.warning(f'User with id: {user_id} has no existing detault service point')
            current_default_sp = ''
        return sp_user_id, current_default_sp, current_service_points

    def _service_point_user_comparison(self, user_id):
        sp_user_id, current_default_sp, current_service_points = self._get_current_sps(user_id)
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

    def rebuild_service_points_csv(self):
        logging.info("Rebuilding Service Points csv file to match data in FOLIO...")
        currentUserSPs = {}
        unique_sps = []
        
        # Retrieves Current Service Points for each user
        logging.info("Retrieving Current user Service Points...")
        for user_id in tqdm(self.userServicePoints.keys(), desc="Retrieving Current user service points"):
            sp_user_id, current_default_sp, current_service_points = self._get_current_sps(user_id)
            currentUserSPs[user_id] = [current_default_sp, current_service_points]
            unique_sps = list(set(unique_sps) | set(current_service_points))
        logging.info("Current Service Points retrieved!")

        logging.info("Looking up Service Points names...")
        servicePointDict = {}
        for sp in tqdm(unique_sps, desc="Looking up Service Points names"):
            servicePointDict[sp] = self._service_point_name_lookup(sp)
        self.userServicePoints = currentUserSPs
        logging.info("Service Point codes retrieved.")

        logging.info("Updating csv file...")
        # Updates Data File with current service points
        with open(self.userFile, 'w', encoding="utf-8") as file:
            data_headers = 'User Data\t'*self.userIdColumnIndex
            sp_headers = 'Default Service Point\t'+'Service Point\t'*(len(unique_sps)-1)
            headers = f"{data_headers}User Id\t {sp_headers}\n"
            file.write(headers)
            for user_id in tqdm(currentUserSPs.keys(), desc = "Updating csv file"):
                user_line = ""
                for data in self.userInfo[user_id]:
                    user_line += f"{data}\t"

                user_line += f"{user_id}\t"
                if currentUserSPs[user_id][0] != '':
                    user_line += f"{servicePointDict[currentUserSPs[user_id][0]]}\t"
                else:
                    user_line += "\t"
                for servicePoint in servicePointDict.keys():
                    if servicePoint in currentUserSPs[user_id][1] and servicePoint != currentUserSPs[user_id][0]:
                        user_line += f"{servicePointDict[servicePoint]}\t"
                    else:
                        user_line += f"\t"
                user_line += '\n'
                for servicePoint in servicePointDict.keys():
                    user_line.replace(servicePoint, servicePointDict[servicePoint])
                file.write(user_line)
        logging.info("File updated")
        logging.info("Rebuild Complete")
        return(0)


    def apply_user_service_points(self):
        logging.info("Applying Service Points in FOLIO...")
        for user in tqdm(self.userServicePoints.keys(), desc="Applying Service Points in FOLIO"):
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
    updater.rebuild_service_points_csv()
    #updater.apply_user_service_points()

