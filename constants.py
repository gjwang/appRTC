'''
AppRTC Constants.

This module contains the constants used in AppRTC Python modules.

Created on Jul 16, 2015

@author: gjwang
'''

ROOM_MEMCACHE_EXPIRATION_SEC = 60 * 60 * 24
MEMCACHE_RETRY_LIMIT = 100

LOOPBACK_CLIENT_ID = 'LOOPBACK_CLIENT_ID'

TURN_BASE_URL = 'http://172.16.243.56:8888'
TURN_URL_TEMPLATE = '%s/turn?username=%s&key=%s'
CEOD_KEY = 'hi.roobo'

# Dictionary keys in the collider instance info constant.
WSS_INSTANCE_HOST_KEY = 'host_port_pair'
WSS_INSTANCE_NAME_KEY = 'vm_name'
WSS_INSTANCE_ZONE_KEY = 'zone'
WSS_INSTANCES = [
    {
        WSS_INSTANCE_HOST_KEY: '172.16.243.56:8888',
        WSS_INSTANCE_NAME_KEY: 'wsserver-std',
        WSS_INSTANCE_ZONE_KEY: 'us-central1-a'
    }, 

    #{
    #    WSS_INSTANCE_HOST_KEY: 'apprtc-ws.webrtc.org:443',
    #    WSS_INSTANCE_NAME_KEY: 'wsserver-std',
    #    WSS_INSTANCE_ZONE_KEY: 'us-central1-a'
    #}, 
    #{
    #    WSS_INSTANCE_HOST_KEY: 'apprtc-ws-2.webrtc.org:443',
    #    WSS_INSTANCE_NAME_KEY: 'wsserver-std-2',
    #    WSS_INSTANCE_ZONE_KEY: 'us-central1-f'
    #}
]

WSS_HOST_PORT_PAIRS = [ins[WSS_INSTANCE_HOST_KEY] for ins in WSS_INSTANCES]

# memcache key for the active collider host.
WSS_HOST_ACTIVE_HOST_KEY = 'wss_host_active_host'

# Dictionary keys in the collider probing result.
WSS_HOST_IS_UP_KEY = 'is_up'
WSS_HOST_STATUS_CODE_KEY = 'status_code'
WSS_HOST_ERROR_MESSAGE_KEY = 'error_message'

MAX_MEMBERS_IN_ROOM = 2

RESPONSE_ERROR = 'ERROR'
RESPONSE_ROOM_FULL = 'FULL'
RESPONSE_UNKNOWN_ROOM = 'UNKNOWN_ROOM'
RESPONSE_UNKNOWN_CLIENT = 'UNKNOWN_CLIENT'
RESPONSE_DUPLICATE_CLIENT = 'DUPLICATE_CLIENT'
RESPONSE_SUCCESS = 'SUCCESS'
RESPONSE_INVALID_REQUEST = 'INVALID_REQUEST'


