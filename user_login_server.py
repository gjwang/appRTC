# -*- coding: utf-8 -*-

'''
Use for keeping client long-live connection, to call to each other
After connection success:
Step1, login (must)
Step2, send message 
Step3, recv message

Created on Jul 28, 2015

@author: gjwang
'''
import logging
import json
import time

import tornado.ioloop
import tornado.web
from tornado import websocket
from tornado.options import define, options

import constants

RESPONSE_ACK = 'ack'
RESPONSE_SUCCESS = 'ok'
RESPONSE_ERROR = 'error'
RESPONSE_ERROR_REASON = 'reason'

RESPONSE_OK_TEMPLATE = {RESPONSE_ACK: RESPONSE_SUCCESS}
RESPONSE_ERROR_TEMPLATE = {RESPONSE_ACK: RESPONSE_ERROR, RESPONSE_ERROR_REASON:''}


class User:
    STATUS_LOGOUT = 'logout'
    STATUS_ONLINE = 'online'
    STATUS_OFFLINE = 'offline'
    
    def __init__(self, userid, password, connection):
        #assert(userid != None)
        
        self.userid = userid
        self.password = password
        self.loginTime = None;
        self.logoutTime = None;
        
        self.messages = []
        self.webSocketConn = connection;
        self.status = User.STATUS_LOGOUT
        
    def addMessage(self, msg):
        self.messages.append(msg)
        
    def clearMessages(self):
        self.messages = []
        
    def getStatus(self):
        return self.status
    
    def getConnection(self):
        return self.webSocketConn
    
    def setStatus(self, status):
        if status == User.STATUS_ONLINE:
            self.loginTime = int(time.time())
        elif status == User.STATUS_LOGOUT:
            self.logoutTime = int(time.time())
        elif status == User.STATUS_OFFLINE:
            self.setConnection(None)
            self.logoutTime = int(time.time())
        else:
            logging.info("User set unknown Status")
            return
        
        self.status = status
    
    def setConnection(self, connection):    
        self.webSocketConn = connection
        
    def __str__(self):
        return '{userid=%s, connStatus=%s, msg_count= %d}' % \
               (self.userid, self.getStatus(), len(self.messages))



class UserManager:
    @classmethod
    def instance(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.useridMap = {} #{'userid':'user'}
        
    def addUser(self, userid, password, connection):
        '''
        try to add a user to the userManagerInstance, 
        if the user not exist, make a new user
        if the user already existed, replace the user's connection    
        '''
        
        user = self.useridMap.get(userid, None)
        if user is not None:
            user.setConnection(connection)
            user.setStatus(User.STATUS_ONLINE)
            result = {'ack':'ok'}
        elif userid is not None:
            user = User(userid, password, connection)
            user.setStatus(User.STATUS_ONLINE)
            self.useridMap[userid] = user            
            result = {'ack':'ok'}
        else:
            logging.error("userid is None")
            result = {'ack':'error',
                      'reason': "userid is None"}

        return result
        
    def removeUser(self, userid, password):
        user = self.useridMap.pop(userid, None)
        if user is not None:
            #TODO: may need close the connection
            pass
        
        logging.info('UserManager removeUser userid=' + str(userid))
        
        return user
  
    def getUser(self, userid):
        return self.useridMap.get(userid, None)
    
    def __str__(self):
        usersStatus  = []
        for user in self.useridMap.itervalues():
            usersStatus.append(str(user))
            
        return str(usersStatus)
            
#userManagerInstance = UserManager.instance()
userManagerInstance = UserManager()

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        #print 'request = ', self.request
        self.write("Hello, world")

class DispatchMessage:
    @classmethod
    def instance(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance
            
    def __init__(self):
        self.msgProcess = {
            'login' : 'onLogin',
            'msg'   : 'onMessage',
            'logout': 'onLogout',
        }
    
    def dispatch(self, connection, msg):   
        #TODO: maybe we should encode msg to utf-8
        msgJson = None
        try:
            msgJson = json.loads(msg)
            msgType = msgJson['type']
            processMessage = getattr(self, self.msgProcess[msgType])
            result = processMessage(connection, msgJson)
            if result is not None:
                connection.write_message(json.dumps(result))
            return
        except Exception as ex:
            resp_msg = json.dumps({"ack":"error",
                                   "reason":'Process msgJson: ' + str(msgJson) + ' failed, Exception: ' + str(ex)});
                                   
            logging.error( resp_msg )
            #TODO: return json format msg
            return connection.write_message(resp_msg)
            
    def onLogin(self, connection, msgJson):
        #{'type':'login', 'userid':'', 'pwd':''}
        userid = msgJson['userid']
        password = msgJson['pwd']
        
        result = {'ack':'error',
                  'reason': "unknown"}
        
        if validateUser(userid, password):
            connection.userid = userid;
            connection.password = password

            result = userManagerInstance.addUser(userid, password, connection)
        return result    
        
                  
    def onMessage(self, connection, msgJson):
        #{'type':'msg', 'from':'', 'to':'', 'body':''}
        
        logging.info('onMessage: ' + str(msgJson))
        
        fromUserid = msgJson['from']
        toUserid = msgJson['to']
        #msgBody = msgJson['body']
        
        #assert(fromUserid != None)
        #assert(toUserid != None)
        #assert(msgBody != None)
        
        response_msg = {RESPONSE_ACK: RESPONSE_ERROR, RESPONSE_ERROR_REASON:'unkown'}
        
        result = checkUserLogin(fromUserid) 
        if result['error'] is not None:
            #TODO: close the connection
            logging.error(str(result))
            response_msg = {RESPONSE_ACK: RESPONSE_ERROR, RESPONSE_ERROR_REASON: result['error']}
            return response_msg
        
        
        #TODO: we should cache the msg for the toUserid for a while, in case toUser is frequency online/offline
        result = checkUserLogin(toUserid)
        if result['error'] is not None:
            #TODO: close the connection
            logging.error(str(result))
            response_msg = {RESPONSE_ACK: RESPONSE_ERROR, RESPONSE_ERROR_REASON: result['error']}
            return response_msg
        
        #Forward msg to toUserid
        toUser = userManagerInstance.getUser(toUserid)
        toUser.getConnection().write_message(json.dumps(msgJson))
        
        response_msg = {RESPONSE_ACK: RESPONSE_SUCCESS}
        return response_msg
        
        
    def onLogout(self, connection, msgJson):
        logging.info('onLogout: ' + str(msgJson))
        
        userid = msgJson['userid']
        
        user = userManagerInstance.getUser(userid)
        user.setStatus(User.STATUS_LOGOUT);

        #TODO: do we need to remove user from userManagerInstance
                
        return {RESPONSE_ACK: RESPONSE_SUCCESS}
        
def checkUserLogin(userid):
    user = userManagerInstance.getUser(userid)
    
    if user is None:
        return {'error':"userid=" + userid + " is not login"}        
    
    if user.getStatus() == 'offline':
        #should not happen
        return {'error':"userid=" + userid + " offline"}
    
    if user.getStatus() == 'logout':
        #should not happen
        return {'error':"userid=" + userid + " logout"}
    
    return {'error': None}

 
def validateUser(userid, password):
    #TODO: we should validate the user, but we don't have the account info now
    return  True

#dispatchMsgInstance = DispatchMessage.instance()
dispatchMsgInstance = DispatchMessage() #just for eclipse understand the code better    

class WebSocketHandler(websocket.WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        #TODO: maybe we should not bind a connection to a userid,
        #because one connection maybe reuse for many purpose in the future
        
        self.userid = None
        self.password = None
        
        super(WebSocketHandler, self).__init__(application, request, **kwargs)
        
    
    def check_origin(self, origin):
        return True

    def open(self):
        logging.info('ws client ip=' + str(self.request.remote_ip) + ' connected')

    
    def on_message(self, message):
        '''
            
        '''
        
        logging.info('ws on_message: userid=' + str(self.userid) + ' ,msg=' + str(message))
        #self.write_message(u"Echo: " + message)
        
        try:
            dispatchMsgInstance.dispatch(self, message)
        except Exception as ex:    
            resp_msg = json.dumps({"ack":"error",
                                   "reason":"Process msg: " + str(message) + ", Exception: " + str(ex)});
                                   
            logging.error( resp_msg )
            #TODO: return json format msg
            return self.write_message(resp_msg)
        
    def on_close(self):
        logging.info('on_close remote_ip: ' + str(self.request.remote_ip) + 
                     ' ,userid: ' + str(self.userid) +' closed')

        #TODO: we may not have self.userid in the future, or have a list of users
        user = userManagerInstance.getUser(self.userid)
        if user is not None:
            user.setStatus(User.STATUS_OFFLINE)
             
        userManagerInstance.removeUser(self.userid, self.password)
        
        logging.info('on_close userManagerInstance Status: ' + str(userManagerInstance))

application = tornado.web.Application([
    (r"/", MainHandler),        
    (r'/ws', WebSocketHandler),
])

def main():
    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    log_FileHandler = logging.handlers.TimedRotatingFileHandler(filename = "log/user_login_server.log",
                                                                when = 'D',
                                                                interval = 1,
                                                                backupCount = 7)  
    
    log_FileHandler.setFormatter(formatter)
    log_FileHandler.setLevel(logging.INFO)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(log_FileHandler) 

    define("port", default="8090", help="user keep-alive server port")

    
    print 'start listening ' + options.port + ' ...'
    logging.info('start listening ' + options.port + ' ...')
    
    application.listen(options.port)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
    