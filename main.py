from flask import Flask, request
from oauth2client import client
import requests, json, os, sys

app = Flask(__name__)

@app.route('/', methods = ['POST'])
def main(request):
    
    ## Get the enviornment variables
    url = os.environ['URL']
    encoded_creds = os.environ["ENCODED"]
    audience = os.environ["AUDIENCE"]
    card_image = os.environ["IMAGE"]
    prestage1 = os.environ["PS1"]
    prestage2 = os.environ["PS2"]
    
    ## Define functions
    
    def on_event():
        
        event = request.get_json()
        event_headers = dict(request.headers)
        
        # Verify message is authentic
        CHAT_ISSUER = 'chat@system.gserviceaccount.com'
        PUBLIC_CERT_URL_PREFIX = 'https://www.googleapis.com/service_accounts/v1/metadata/x509/'
        AUDIENCE = audience
        BEARER_TOKEN = event_headers['Authorization'][7:]
        try:
            token = client.verify_id_token(
            BEARER_TOKEN, AUDIENCE, cert_uri=PUBLIC_CERT_URL_PREFIX + CHAT_ISSUER)
            if token['iss'] != CHAT_ISSUER:
                sys.exit('Invalid issuee')
        except:
            sys.exit('Invalid token')
        
        # Handle message
        user = event['message']['sender']['name']
        try:
            event['message']['annotations']
            if event['message']['annotations'][0]['type'] == 'SLASH_COMMAND':
                message = event['message']['argumentText'].split()
                serial = message[0]
                try:
                    id = message[1].lower()
                    if id == 'staff':
                        id = 1
                    elif id == 'student':
                        id = 2
                    else:
                        id = 'Invalid prestage'
                except IndexError:
                    id = 0
                if event['message']['slashCommand']['commandId'] == "1":
                    slash_command = 1
                elif event['message']['slashCommand']['commandId'] == "2":
                    slash_command = 2
                elif event['message']['slashCommand']['commandId'] == "3":
                    slash_command = 3
                elif event['message']['slashCommand']['commandId'] == "4":
                    slash_command = 4
                return serial, id, slash_command, user
            elif event['message']['annotations'][0]['type'] == 'USER_MENTION':
                return "DM", 0, 0, user
        except KeyError:
            return "PM", 0, 0, user
    
    ## Get auth token from Jamf server
    def authorization():
        auth_url = f"{url}/api/auth/tokens"
        auth_headers = { 'Authorization': f'Basic {encoded_creds}'}
        token = requests.request("POST", auth_url, headers=auth_headers)
        token = json.loads(token.text)
        return token["token"]
    
    ## Invalidate token when done
    def invalidate_token(token):
        invalidate_url = f"{url}/api/auth/invalidateToken"
        invalidate_headers = { 'Authorization': f'Bearer {auth_token}'}
        response = requests.request("POST", invalidate_url, headers=invalidate_headers)
        return response
    
    ## Get versionLock by making GET request
    def version_lock(id):
        prestage_add_url = f"{url}/api/v2/computer-prestages/{id}/scope"
        token_headers = { 'Authorization': f'Bearer {auth_token}' }
        version_lock_num = requests.request("GET", prestage_add_url, headers=token_headers)
        version_lock_num = json.loads(version_lock_num.text)
        version_lock_num = version_lock_num["versionLock"]
        return version_lock_num
    
    ## Get and send device details as card
    def get_device_details(serial):
        device_details_url = f"{url}/api/v1/computers-inventory?section=GENERAL&section=HARDWARE&section=OPERATING_SYSTEM&section=STORAGE&page=0&page-size=100&sort=id:asc&filter=hardware.serialNumber=={serial}"
        device_details_headers = {"Authorization": f"Bearer {auth_token}"}
        device_details = requests.request("GET", device_details_url, headers=device_details_headers)
        device_details_info = device_details.json()
        device_asset_tag = device_details_info['results'][0]['general']['assetTag']
        device_last_contact_time = device_details_info['results'][0]['general']['lastContactTime'][:10]
        device_ip = device_details_info['results'][0]['general']['lastReportedIp']
        device_model = device_details_info['results'][0]['hardware']['model']
        device_mac_address = device_details_info['results'][0]['hardware']['macAddress']
        device_processor_type = device_details_info['results'][0]['hardware']['processorType']
        device_total_ram = device_details_info['results'][0]['hardware']['totalRamMegabytes']
        device_total_ram_gb = str(device_total_ram // 1024) + " GB"
        device_os_name = device_details_info['results'][0]['operatingSystem']['name']
        device_os_version = device_details_info['results'][0]['operatingSystem']['version']
        device_os = device_os_name + " " + device_os_version
        device_storage_free = device_details_info['results'][0]['storage']['bootDriveAvailableSpaceMegabytes']
        device_storage_free_gb = str(device_storage_free // 1024) + " GB"
        return json.dumps({
            'cards': [
                {
                    'header': {
                        'title': f'{serial}',
                        'imageUrl': card_image
                    },
                    'sections': [
                        {
                        'widgets': [
                            {
                                'textParagraph': {
                                    'text': f'Asset Tag: {device_asset_tag}<br>Hardware: {device_model}<br>OS Version: {device_os}<br>CPU: {device_processor_type}<br>RAM: {device_total_ram_gb}<br>Storage Available: {device_storage_free_gb}<br>IP Address: {device_ip}<br>Mac Address: {device_mac_address}<br>Last Check-in Date: {device_last_contact_time}'
                                    }
                                }
                            ]
                        }   
                    ]
                }
            ]})
    
    ## Remove device record from Jamf Pro    
    def remove_device(serial):
        id = get_device_details(serial)['results'][0]['id']
        remove_device_url = f"{url}/api/v1/computers-inventory/{id}"
        remove_device_headers = {"Authorization": f"Bearer {auth_token}"}
        remove_device = requests.request("DELETE", remove_device_url, headers=remove_device_headers)
        return remove_device.status_code
    
    ## Remove device from prestage scope   
    def remove_device_scope(serial):
        old_id = 1
        version_lock_num = 1
        status = True
        while status:
            prestage_remove_url = f"{url}/api/v2/computer-prestages/{old_id}/scope/delete-multiple"
            payload = json.dumps({
                "serialNumbers": [
                    serial
                ],
                "versionLock": version_lock_num
            })
            prestage_headers = { "Content-Type": "application/json",
                             "Authorization": f"Bearer {auth_token}"
            }
            remove_scope = requests.request("POST", prestage_remove_url, headers=prestage_headers, data=payload)
            reason = remove_scope.json()
            if 'errors' in reason:
                reason = reason['errors'][0]['code']
            if remove_scope.status_code == 400 and reason == "DEVICE_DOES_NOT_EXIST_ON_TOKEN":
                status = False
                break
            elif remove_scope.status_code == 400 and reason == "ALREADY_SCOPED":
                old_id += 1
            elif remove_scope.status_code == 409:
                version_lock_num = version_lock(old_id)
                remove_scope = requests.request("POST", prestage_remove_url, headers=prestage_headers, data=payload)
            else:
                status = False
        return remove_scope.status_code, reason
    
    ## Add device to prestage enrollment
    def add_device_scope(serial, id) -> None:
        version_lock_num = version_lock(id)
        prestage_add_url = f"{url}/api/v2/computer-prestages/{id}/scope"
        payload = json.dumps({
        "serialNumbers": [
            serial
            ],
            "versionLock": version_lock_num
        })
        prestage_headers = { "Content-Type": "application/json",
                         "Authorization": f"Bearer {auth_token}"
        }
        try:
            add_scope = requests.request("POST", prestage_add_url, headers=prestage_headers, data=payload)
            add_scope.raise_for_status()
            return json.dumps({'text': f'Prestage enrollment for {serial} modifed.'})
        except requests.exceptions.RequestException:
            return json.dumps({'text': f'Sorry, something went wrong. {status}'})
    
    def get_mobile_device_details(serial) -> None:
        mobile_device_url = f'{url}/api//v2/mobile-devices?&sort=id:asc'
        mobile_device_headers = { 'Authorization': f'Bearer {auth_token}'}
        devices = requests.request("GET", mobile_device_url, headers=mobile_device_headers)
        mobile_devices = devices.json()
        for keyval in mobile_devices['results']:
            if serial == keyval['serialNumber']:
                id = keyval['id']
        mobile_device_details_url = f'{url}/api/v2/mobile-devices/{id}/detail'
        device_details = requests.request("GET", mobile_device_details_url, headers=mobile_device_headers)
        device = device_details.json()
        device_asset_tag = device['assetTag']
        if device['type'] == 'ios':
            device_model = device['ios']['model']
            device_os = 'iOS ' + device['osVersion']
            device_storage_total = device['ios']['capacityMb'] // 1024
            device_storage_free = device['ios']['availableMb'] // 1024
            device_mac_address = device['wifiMacAddress']
            device_last_contact_time = device['lastInventoryUpdateTimestamp'][:10]
            device_enrollment_method = device['enrollmentMethod'] 
        return json.dumps({
            'cards': [
                {
                    'header': {
                        'title': f'{serial}',
                        'imageUrl': card_image
                    },
                    'sections': [
                        {
                        'widgets': [
                            {
                                'textParagraph': {
                                    'text': f'Asset Tag: {device_asset_tag}<br>Hardware: {device_model}<br>OS Version: {device_os}<br>Enrollment Method: {device_enrollment_method}<br>Storage Capacity: {device_storage_total} GB<br>Storage Available: {device_storage_free} GB<br>Mac Address: {device_mac_address}<br>Last Check-in Date: {device_last_contact_time}'
                                    }
                                }
                            ]
                        }   
                    ]
                }
            ]})

    ## Function calls
    
    serial, id, slash_command, user = on_event()
    if serial == "DM":
        return json.dumps({'text': f'Hello, <{user}>, please use an available slash command in this space or in a direct message.'})
    elif serial == "PM":
        return json.dumps({'text': f'Hello, <{user}>, please use an available slash command.'})
    else:
        auth_token = authorization()
        if slash_command == 1:
            return get_device_details(serial)
        elif slash_command == 2:
            if type(id) is str:
                return json.dumps({'text': 'Invalid prestage'})
            else:
                status, reason = remove_device_scope(serial)
                if status == 200:
                    return_message = add_device_scope(serial, id)
                    return return_message
                elif reason == "DEVICE_DOES_NOT_EXIST_ON_TOKEN":
                    return json.dumps({'text': 'Invalid serial number'})
                else:
                    return json.dumps({'text': 'Something went wrong'})
        elif slash_command == 3:
            if remove_device(serial) == 200:
                return json.dumps({'text': 'Device successfully removed'})
            else:
                return json.dumps({'text': 'That device does not exist.'})
        elif slash_command == 4:
            return get_mobile_device_details(serial)
        invalidate_token(auth_token)

if __name__ == '__main__':
    app.run(port=8080, debug=True)