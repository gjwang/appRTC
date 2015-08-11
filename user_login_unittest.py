# -*- coding: utf-8 -*-

'''
Created on Jul 28, 2015

@author: gjwang
'''

import unittest
import json

from websocket import create_connection


WS_URL = "ws://127.0.0.1:8090/ws"

USER01_LOGIN_TEXT = {'type':'login', 'userid':'gjwang01', 'pwd':'123456'}
USER02_LOGIN_TEXT = {'type':'login', 'userid':'gjwang02', 'pwd':'123456'}

USER01_TO_USER02_MSG = {'type':'msg', 'from':'gjwang01', 'to':'gjwang02', 'body':'hi, buddy'}
USER02_TO_USER01_MSG = {'type':'msg', 'from':'gjwang02', 'to':'gjwang01', 'body':'hi, buddy'}

USER01_LOGOUT_TEXT = {'type':'logout', 'userid':'gjwang01'}
USER02_LOGOUT_TEXT = {'type':'logout', 'userid':'gjwang02'}


class TestStringMethods(unittest.TestCase):
    
    def __init__(self, methodName='runTest'):
        self.ws = None
        super(TestStringMethods, self).__init__(methodName)
    
    def setUp(self):
        #self.ws = create_connection(WS_URL)
        
        #print "Sending 'Hello, World'..."
        #self.ws.send("Hello, World")
        #print "Sent"
        #print "Reeiving..."
        #result = self.ws.recv()
        #print "Received '%s'" % result
        #self.ws.close()
        pass      
    
    def test_login(self):
        ws = create_connection(WS_URL)
        ws.send(json.dumps(USER01_LOGIN_TEXT))
        
        login_resp_text = ws.recv()
        login_resp_json = json.loads(login_resp_text)
        self.assertEqual(login_resp_json['ack'], 'ok')
        ws.close()
    
    def test_non_login(self):
        ws = create_connection(WS_URL)
        ws.send(json.dumps(USER01_TO_USER02_MSG))
        
        resp_text = ws.recv()
        resp_json = json.loads(resp_text)
        #print resp_json
        self.assertEqual(resp_json['ack'], 'error', resp_json['reason'])
        ws.close()
            

    def test_login_and_send_msg(self):
        
        ws = create_connection(WS_URL)
        ws.send(json.dumps(USER01_LOGIN_TEXT))
        
        login_resp_text = ws.recv()
        login_resp_json = json.loads(login_resp_text)
        self.assertEqual(login_resp_json['ack'], 'ok')
        
        ws.send(json.dumps(USER01_TO_USER02_MSG));
        ack = ws.recv() #{"ack": "error", "reason": "userid=gjwang02 is not login"}
        ack_json = json.loads(ack)
        self.assertEqual(ack_json['ack'], 'error')
        

        ws2 = create_connection(WS_URL)
        ws2.send(json.dumps(USER02_LOGIN_TEXT))
        login_resp_text = ws2.recv()    #{u'ack': u'ok'} login success
        login_resp_json = json.loads(login_resp_text)
        self.assertEqual(login_resp_json['ack'], 'ok')
        
        
        #### test user2 send msg to user1
        ws2.send(json.dumps(USER02_TO_USER01_MSG));
        ack = ws2.recv() #{u'ack': u'ok'}
        ack_json = json.loads(ack)
        self.assertEqual(ack_json['ack'], 'ok')
        
        msg_from_user2 = ws.recv()
        self.assertDictEqual(json.loads(msg_from_user2), USER02_TO_USER01_MSG)
        
        
        
        ####test user1 send msg to user2
        ws.send(json.dumps(USER01_TO_USER02_MSG));
        ack = ws.recv() #{u'ack': u'ok'}
        ack_json = json.loads(ack)
        self.assertEqual(ack_json['ack'], 'ok')
        
        msg_from_user1 = ws2.recv()
        self.assertDictEqual(json.loads(msg_from_user1), USER01_TO_USER02_MSG)

        
        
        ws.close()
        ws2.close()
    
    def test_logout(self):
        ''''
        1, test user01 still can or can not send msg after logout, 
        2, test if user02 can or can not send msg to user01 after user01 logout
        '''
        ws = create_connection(WS_URL)
        ws.send(json.dumps(USER01_LOGIN_TEXT))
        
        login_resp_text = ws.recv()
        login_resp_json = json.loads(login_resp_text)
        self.assertEqual(login_resp_json['ack'], 'ok')
        
        #test logout ack msg
        ws.send(json.dumps(USER01_LOGOUT_TEXT)) 
        logout_resp_text = ws.recv()
        logout_resp_json = json.loads(logout_resp_text)
        self.assertEqual(logout_resp_json['ack'], 'ok')
        
        #test if it can send msg or not after success
        ws.send(json.dumps(USER01_TO_USER02_MSG))
        ack_msg = ws.recv() 
        ack_json = json.loads(ack_msg)
        self.assertEqual(ack_json['ack'], 'error')


        #test if other user can send msg or not after success
        ws2 = create_connection(WS_URL)
        ws2.send(json.dumps(USER02_LOGIN_TEXT))
        
        ws.send(json.dumps(USER01_TO_USER02_MSG))
        resp_text = ws.recv()
        resp_json = json.loads(resp_text)
        self.assertEqual(resp_json['ack'], 'error')
        
        
        ws.close()
        ws2.close()
                
    def tearDown(self):
        if self.ws:
            self.ws.close()
        self.ws = None
        pass
    

if __name__ == '__main__':
    unittest.main()
