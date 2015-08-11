# -*- coding: utf-8 -*-

'''
Created on Jul 20, 2015

@author: gjwang
'''
import json
import time
import hmac
import hashlib

from tornado import web
import constants



def get_ice_services(username, key):
    '''
        https://tools.ietf.org/html/draft-uberti-rtcweb-turn-rest-00
    '''
    time_to_live = 600;
    timestamp = int(time.time()) + time_to_live;
    turn_username = str(timestamp) + ':' + username;
        
    #temporary-password = base64_encode(hmac-sha1(shared-secret, temporary-username))
    hashed = hmac.new(key, turn_username, hashlib.sha1)
    password = hashed.digest().encode("base64").rstrip('\n')

    json_msg =json.dumps({
                          'username':turn_username,
                          'password':password,
                          'ttl':time_to_live,
                          "uris": [
                                "turn:video.roobo.com.cn:3478?transport=udp",
                                "turn:video.roobo.com.cn:3478?transport=tcp",
                                "turn:video.roobo.com.cn:3479?transport=udp",
                                "turn:video.roobo.com.cn:3479?transport=tcp",
                            ]
                         }
                        )
    
    return json_msg

class TurnRestfullApi(web.RequestHandler):
    '''
        Example: POST http://us.roobo.com.cn:3033/turn?username=116997376&key=hi.roobo
        return: iceServices wrap with json, reference to get_ice_services
    '''
    
    def get(self):
        username = self.get_argument("username")
        key = self.get_argument('key')
        
        key_text = None
        try:
            key_text = key.encode(encoding='utf-8', errors='strict')
        except Exception as e:
            return {'error': constants.RESPONSE_ERROR, 'reason': str(e)}
        
        #key_text = constants.CEOD_KEY
        
        reponse_json_msg = get_ice_services(username, key_text)
                
        self.write(reponse_json_msg)

    def post(self):
        self.get()
