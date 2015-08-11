# -*- coding: utf-8 -*-

'''
Created on Jul 15, 2015

@author: gjwang
'''
import logging
import json
import random
import cgi
import os

import tornado.ioloop
import tornado.web
#import tornado.websocket
from tornado import websocket
import constants
from turn_restfull_api import TurnRestfullApi

def generate_random(length):
    word = ''
    for _ in range(length):
        word += random.choice('0123456789')
        
    return word

# HD is on by default for desktop Chrome, but not Android or Firefox (yet)
def get_hd_default(user_agent):
    if 'Android' in user_agent or not 'Chrome' in user_agent:
        return 'false'
    
    return 'true'

# iceServers will be filled in by the TURN HTTP request.
def make_pc_config(ice_transports):
    config = { 'iceServers': [] };
    if ice_transports:
        config['iceTransports'] = ice_transports
    return config

def add_media_track_constraint(track_constraints, constraint_string):
    tokens = constraint_string.split(':')
    mandatory = True
    if len(tokens) == 2:
        # If specified, e.g. mandatory:minHeight=720, set mandatory appropriately.
        mandatory = (tokens[0] == 'mandatory')
    else:
        # Otherwise, default to mandatory, except for goog constraints, which
        # won't work in other browsers.
        mandatory = not tokens[0].startswith('goog')

    tokens = tokens[-1].split('=')
    if len(tokens) == 2:
        if mandatory:
            track_constraints['mandatory'][tokens[0]] = tokens[1]
        else:
            track_constraints['optional'].append({tokens[0]: tokens[1]})
    else:
        logging.error('Ignoring malformed constraint: ' + constraint_string)

def make_media_track_constraints(constraints_string):
    if not constraints_string or constraints_string.lower() == 'true':
        track_constraints = True
    elif constraints_string.lower() == 'false':
        track_constraints = False
    else:
        track_constraints = {'mandatory': {}, 'optional': []}
        for constraint_string in constraints_string.split(','):
            add_media_track_constraint(track_constraints, constraint_string)

    return track_constraints

def make_media_stream_constraints(audio, video, firefox_fake_device):
    stream_constraints = (
      {'audio': make_media_track_constraints(audio),
       'video': make_media_track_constraints(video)})
    if firefox_fake_device:
        stream_constraints['fake'] = True
        
    logging.info('Applying media constraints: ' + str(stream_constraints))
    return stream_constraints

def maybe_add_constraint(constraints, param, constraint):
    if (param.lower() == 'true'):
        constraints['optional'].append({constraint: True})
    elif (param.lower() == 'false'):
        constraints['optional'].append({constraint: False})

    return constraints

def make_pc_constraints(dtls, dscp, ipv6):
    constraints = { 'optional': [] }
    maybe_add_constraint(constraints, dtls, 'DtlsSrtpKeyAgreement')
    maybe_add_constraint(constraints, dscp, 'googDscp')
    maybe_add_constraint(constraints, ipv6, 'googIPv6')

    return constraints

def append_url_arguments(self_request, link):
    arguments = self_request.request.arguments
    
    request = self_request.request
    
    if len(arguments) == 0:
        return link
    
    print link
    
    
    i = 0
    for item in arguments.iteritems():
        split = '&'
        if i == 0:
            split = '?'
        i += 1
        
        print item[0], item[1]
        
        link += (split + cgi.escape(item[0], True) + '=' + cgi.escape(item[1][0], True))

    return link

def get_wss_parameters(request):
    #wss_host_port_pair = request.get('wshpp')
    #wss_tls = request.get('wstls')
    wss_tls = 'false'
    
    wss_host_port_pair = constants.WSS_HOST_PORT_PAIRS[0]

    if wss_tls and wss_tls == 'false':
        wss_url = 'ws://' + wss_host_port_pair + '/ws'
        wss_post_url = 'http://' + wss_host_port_pair + '/wsHttpPost'
    else:
        wss_url = 'wss://' + wss_host_port_pair + '/ws'
        wss_post_url = 'https://' + wss_host_port_pair
    return (wss_url, wss_post_url)

def get_version_info():
    #return ""
    return {"time": "Wed Jun 3 11:08:09 2015 -0700", "branch": "master", "gitHash": "c2179d16ae879f4ece4d2838585966e7c029c9d3"}
    
    #try:
    #    path = os.path.join(os.path.dirname(__file__), 'version_info.json')
    #    f = open(path)
    #    if f is not None:
    #        try:
    #            return json.load(f)
    #        except ValueError as e:
    #            logging.warning('version_info.json cannot be decoded: ' + str(e))
    #except IOError as e:
    #    logging.info('version_info.json cannot be opened: ' + str(e))
    #return None


# For now we have (room_id, client_id) pairs are 'unique' but client_ids are
# not. Uniqueness is not enforced however any bad things may happen if RNG
# generates non-unique numbers. We also have a special loopback client id.
# TODO(tkchin): Generate room/client IDs in a unique way while handling
# loopback scenario correctly.
class Client:
    def __init__(self, clientId, is_initiator):
        self.clientId = clientId
        self.is_initiator = is_initiator
        self.messages = []
        self.webSocketConn = None;
        
    def add_message(self, msg):
        self.messages.append(msg)
        
    def clear_messages(self):
        self.messages = []
        
    def set_initiator(self, initiator):
        self.is_initiator = initiator
        
    def __str__(self):
        return '{%s, %r, %d}' % (self.clientId, self.is_initiator, len(self.messages))

class Room:
    '''
    TODO: must add timeout, delete deprecate client, to prevent mem leak
    '''
    def __init__(self, roomId):
        self.roomId = roomId
        self.clients = {}#clientId: clientObject map
        
    def add_client(self, client):
        self.clients[client.clientId] = client
        
    def remove_client(self, clientId):
        del self.clients[clientId]
        
    def get_occupancy(self):
        return len(self.clients)
    
    def has_client(self, clientId):
        return clientId in self.clients
    
    def get_client(self, clientId):
        return self.clients.get(clientId, None)
    
    
    def get_other_clientId(self, clientId):
        '''
            should return multi clients in the future, for conference
        '''
        for key in self.clients.iterkeys():
            if key != clientId:
                return key
        return None
    
    def get_other_client(self, clientId):
        for key, client in self.clients.iteritems():
            if key is not clientId:
                return client
        return None
    
    def __str__(self):
        return str(self.roomId) +': ' + str(self.clients.keys())

class _RoomManager:
    '''
    TODO: must add timeout, delete deprecate room, to prevent mem leak
    '''
    @classmethod
    def instance(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance
        
    def __init__(self):
        self.rooms = {}

    def addRoom(self, room):
        if room.roomId in self.rooms:
            logging.error("add room failed, roomId=%s already exist" + room.roomId)
        else:
            self.rooms[room.roomId] = room
        
    def removeRoom(self, roomId):
        result = self.rooms.pop(roomId, None)
        if result:
            result = None #destruct the room
            logging.info("success del roomId=%s", roomId)
        else:
            logging.error("remove room failed, roomId=%s is not exist" + roomId)

    def getRoom(self, roomId):
        return self.rooms.get(roomId, None)

    def hasRoom(self, roomId):
        return roomId in self.rooms
    
    def save_message_from_client(self, roomId, clientId, message):
        msg_text = None
        try:
            msg_text = message.encode(encoding='utf-8', errors='strict')
        except Exception as e:
            logging.error('save_message_from_client failed, roomId:' + str(roomId) + 
                          ', clientId:' + str(clientId) + 
                          ', message: ' +  str(message) +
                          ', Exception: ' +  str(e) )
            return {'error': constants.RESPONSE_ERROR, 'saved': False}
            
        error = constants.RESPONSE_ERROR
        saved = False
        
        room = self.rooms.get(roomId, None);
        if room:
            otherClientId = room.get_other_clientId(clientId)

            
            
            if otherClientId:
                wsConn = wsConnManagerInstance.getConnByClientId(roomId, otherClientId)
                if wsConn:
                    logging.info('Forward msg: roomState: ' + str(room) + \
                         ', from clientId:' + str(clientId) + ', to otherClientId: ' + str(otherClientId))
                    
                    #client already connect to the room, forward the msg to the other clients
                    #logging.info('forward msg from: ' + clientId + ', to: ' + otherClientId + ', msg=' + msg_text)
                    #wsConn.write_message(msg_text)
                    return {'error': None, 'saved': False}
            
            client =  room.get_client(clientId)
            if client:
                logging.info('cache msg: roomState: ' + str(room) + \
                         ', clientId: ' + str(clientId) + ' otherClientId: ' + str(otherClientId))
                
                client.add_message(msg_text)
                error = None
                saved = True
            else:
                logging.error('save_message_from_client failed, clientId:' + str(clientId) + ' not exist')
        else:
            logging.error('save_message_from_client failed, roomId:' + str(roomId) + ' not exist')
            
        return {'error': error, 'saved': saved}

    def send_message_to_collider(self, roomId, clientId, message):
        logging.info('send_message_to_collider message to collider for room=' + roomId +
                     ' ,client=' + clientId + ', msg=' + message)
        
        #Forwarding msg to the others of the room
        #TODO: How to deal about loopback?
        
        error = ''
        room = self.getRoom(roomId)
        if room:
            otherClientId = room.get_other_clientId(clientId)
            wsConn = wsConnManagerInstance.getConnByClientId(roomId, otherClientId)
            if wsConn:
                try:
                    wsConn.write_message(message)
                    return True
                except Exception as e:
                    error = str(e)
            else:
                error = 'otherClientId:%s not exist'%otherClientId
        else:
            error = 'roomId:%s not exist'%roomId

        logging.error('Forward msg:%s failed: %s' % (message, error) )
        return False
    
    
    def __str__(self):
        roomState = ''
        for room in self.rooms.itervalues():
            roomState += str(room)
        
        return roomState
        
#roomManagerInstance =_RoomManager.instance()
roomManagerInstance =_RoomManager()
    

def add_client_to_room(request, roomId, clientId, is_loopback):          
    error = None
    is_initiator = False
    messages = []
    
    #TODO: if run in multithread, should consider thread safe
    room = roomManagerInstance.getRoom(roomId)
    if room is None:
        is_initiator = True
        room = Room(roomId)
        roomManagerInstance.addRoom(room)
    
    occupancy = room.get_occupancy()
    if occupancy >= constants.MAX_MEMBERS_IN_ROOM:
        error = constants.RESPONSE_ROOM_FULL

    if room.has_client(clientId):
        error = constants.RESPONSE_DUPLICATE_CLIENT
      
    if error is None:
        if is_initiator:
            if is_loopback:
                room.add_client(constants.LOOPBACK_CLIENT_ID, Client(False))
        else:
            other_client = room.get_other_client(clientId)
            messages = other_client.messages
            other_client.clear_messages()
            
        room.add_client(Client(clientId, is_initiator))
    
    return {'error': error, 'is_initiator': is_initiator,
          'messages': messages, 'room_state': str(room)}

def remove_client_from_room(roomId, clientId):
    room = roomManagerInstance.getRoom(roomId)
    if room and room.has_client(clientId):
        logging.info("before remove clientId=" + str(clientId) + " ,from roomId=" + str(roomId) + ', roomState=' + str(room))

        room.remove_client(clientId)
        
    if room and room.get_occupancy() == 0:
        roomManagerInstance.removeRoom(roomId)
        logging.info('after remove roomid ' + str(roomId) + ', roomManagerInstance State: ' + str(roomManagerInstance))
        
    error = None
    return {'error': error, 'room_state': str(room)}


# Returns appropriate room parameters based on query parameters in the request.
# TODO(tkchin): move query parameter parsing to JS code.
def get_room_parameters(self_request, room_id, client_id, is_initiator):
    error_messages = []
    # Get the base url without arguments.
    base_url = self_request.request.host
    user_agent = self_request.request.headers['User-Agent']
    
    request = self_request

    # HTML or JSON.
    response_type = request.get_argument('t', default='')

    # Which ICE candidates to allow. This is useful for forcing a call to run
    # over TURN, by setting it=relay.
    ice_transports = request.get_argument('it', default='')

    # Which TURN transport= to allow (i.e., only TURN URLs with transport=<tt>
    # will be used). This is useful for forcing a session to use TURN/TCP, by
    # setting it=relay&tt=tcp.
    turn_transports = request.get_argument('tt', default='')
    
    # A HTTP server that will be used to find the right TURN servers to use, as
    # described in http://tools.ietf.org/html/draft-uberti-rtcweb-turn-rest-00.
    turn_base_url = request.get_argument('ts', default = constants.TURN_BASE_URL)

    # Use "audio" and "video" to set the media stream constraints. Defined here:
    # http://goo.gl/V7cZg
    #
    # "true" and "false" are recognized and interpreted as bools, for example:
    #   "?audio=true&video=false" (Start an audio-only call.)
    #   "?audio=false" (Start a video-only call.)
    # If unspecified, the stream constraint defaults to True.
    #
    # To specify media track constraints, pass in a comma-separated list of
    # key/value pairs, separated by a "=". Examples:
    #   "?audio=googEchoCancellation=false,googAutoGainControl=true"
    #   (Disable echo cancellation and enable gain control.)
    #
    #   "?video=minWidth=1280,minHeight=720,googNoiseReduction=true"
    #   (Set the minimum resolution to 1280x720 and enable noise reduction.)
    #
    # Keys starting with "goog" will be added to the "optional" key; all others
    # will be added to the "mandatory" key.
    # To override this default behavior, add a "mandatory" or "optional" prefix
    # to each key, e.g.
    #   "?video=optional:minWidth=1280,optional:minHeight=720,
    #           mandatory:googNoiseReduction=true"
    #   (Try to do 1280x720, but be willing to live with less; enable
    #    noise reduction or die trying.)
    #
    # The audio keys are defined here: talk/app/webrtc/localaudiosource.cc
    # The video keys are defined here: talk/app/webrtc/videosource.cc
    audio = request.get_argument('audio', default = 'true')
    video = request.get_argument('video', default = 'true')

    # Pass firefox_fake_device=1 to pass fake: true in the media constraints,
    # which will make Firefox use its built-in fake device.
    firefox_fake_device = request.get_argument('firefox_fake_device', default = '')

    # The hd parameter is a shorthand to determine whether to open the
    # camera at 720p. If no value is provided, use a platform-specific default.
    # When defaulting to HD, use optional constraints, in case the camera
    # doesn't actually support HD modes.
    hd = request.get_argument('hd', default ='').lower()
    if hd and video:
        message = 'The "hd" parameter has overridden video=' + video
        logging.error(message)
        error_messages.append(message)
        
    if hd == 'true':
        video = 'mandatory:minWidth=1280,mandatory:minHeight=720'
    elif not hd and not video and get_hd_default(user_agent) == 'true':
        video = 'optional:minWidth=1280,optional:minHeight=720'

    if request.get_argument('minre', default='') or request.get_argument('maxre', default=''):
        message = ('The "minre" and "maxre" parameters are no longer supported. '
                  'Use "video" instead.')
        logging.error(message)
        error_messages.append(message)

    # Options for controlling various networking features.
    dtls = request.get_argument('dtls', default='')
    dscp = request.get_argument('dscp', default='')
    ipv6 = request.get_argument('ipv6', default='')

    debug = request.get_argument('debug', default='')
    if debug == 'loopback':
        # Set dtls to false as DTLS does not work for loopback.
        dtls = 'false'
        include_loopback_js = '<script src="/js/loopback.js"></script>'
    else:
        include_loopback_js = ''

    # TODO(tkchin): We want to provide a TURN request url on the initial get,
    # but we don't provide client_id until a join. For now just generate
    # a random id, but we should make this better.
    username = client_id if client_id is not None else generate_random(9)
    if len(turn_base_url) > 0:
        turn_url = constants.TURN_URL_TEMPLATE % \
            (turn_base_url, username, constants.CEOD_KEY)
    else:
        turn_url = ''

    pc_config = make_pc_config(ice_transports)
    pc_constraints = make_pc_constraints(dtls, dscp, ipv6)
    offer_constraints = { 'mandatory': {}, 'optional': [] }
    media_constraints = make_media_stream_constraints(audio, video,
                                                    firefox_fake_device)
    wss_url, wss_post_url = get_wss_parameters(request)

    bypass_join_confirmation = 'BYPASS_JOIN_CONFIRMATION' in os.environ and \
        os.environ['BYPASS_JOIN_CONFIRMATION'] == 'True'

    params = {
        'error_messages': error_messages,
        'is_loopback' : json.dumps(debug == 'loopback'),
        'pc_config': json.dumps(pc_config),
        'pc_constraints': json.dumps(pc_constraints),
        'offer_constraints': json.dumps(offer_constraints),
        'media_constraints': json.dumps(media_constraints),
        'turn_url': turn_url,
        'turn_transports': turn_transports,
        'include_loopback_js' : include_loopback_js,
        'wss_url': wss_url,
        'wss_post_url': wss_post_url,
        'bypass_join_confirmation': json.dumps(bypass_join_confirmation),
        'version_info': json.dumps(get_version_info())
    }

    if room_id is not None:
        room_link = 'http://' + self_request.request.host + '/r/' + room_id
        room_link = append_url_arguments(self_request, room_link)
        params['room_id'] = room_id
        params['room_link'] = room_link
    if client_id is not None:
        params['client_id'] = client_id
    if is_initiator is not None:
        params['is_initiator'] = json.dumps(is_initiator)
    return params    

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        #print 'request = ', self.request
        self.write("Hello, world")


class WebSocketHttpPostHandler(tornado.web.RequestHandler):
    '''
        DELETE /wsHttpPost/roomid/clientid
    '''
    
    def delete(self, *args, **kwargs):
        #tornado.web.RequestHandler.delete(self, *args, **kwargs)


        self.write(json.dumps({
          'result': constants.RESPONSE_ERROR,
          'reason': "Not implemented, Seems we don't need it"
        }))

        

class JoinPage(tornado.web.RequestHandler):
    def write_response(self, result, params, messages):
        # TODO(tkchin): Clean up response format. For simplicity put everything in
        # params for now.
        params['messages'] = messages
        self.write(json.dumps({
          'result': result,
          'params': params
        }))

    def write_room_parameters(self, room_id, client_id, messages, is_initiator):
        params = get_room_parameters(self, room_id, client_id, is_initiator)
        self.write_response('SUCCESS', params, messages)

    def post(self, room_id):
        client_id = generate_random(8)
        is_loopback = self.get_argument('debug', default='') == 'loopback'
        result = add_client_to_room(self.request, room_id, client_id, is_loopback)
        
        if result['error'] is not None:
            logging.error('Error adding client to room: ' + result['error'] + \
              ', room_state=' + result['room_state'])
            self.write_response(result['error'], {}, [])
            return

        self.write_room_parameters(
            room_id, client_id, result['messages'], result['is_initiator'])
        
        logging.info('User ' + client_id + ' joined room ' + room_id)
        logging.info('Room state ' + result['room_state'])
        
        

class LeavePage(tornado.web.RequestHandler):
    '''
    POST  /leave/roomid/userid
    '''
    def post(self, roomId, userId):
        logging.info("leave roomId=%s, clientId=%s"%(roomId, userId))
        result = remove_client_from_room(roomId, userId)
        
        if result['error'] is None:
            logging.info('Room state: ' + result['room_state'])
        
class MessagePage(tornado.web.RequestHandler):    
    def write_response(self, result):
        content = json.dumps({ 'result' : result })
        self.write(content)

    def post(self, room_id, client_id):
        '''
        message body example:
            {  
               "type":"candidate",
               "label":0,
               "id":"audio",
               "candidate":"candidate:684784063 1 udp 2122260223 172.16.243.66 58167 typ host generation 0"
            }
        
        if get message from http request, response the message above
        
        if send message through websocket, must wrap with 'msg'. 
        Example:
            {"msg":"{\"type\":\"candidate\",\"label\":0,\"id\":\"audio\",\"candidate\":\"candidate:684784063 1 udp 2122260223 172.16.243.66 57333 typ host generation 0\"}","error":""}
            
        '''
        messageText = self.request.body
        logging.info('POST roomId=%s, clientId=%s, msg=%s' % (room_id, client_id, messageText))
                
        result = roomManagerInstance.save_message_from_client(room_id, client_id, messageText)

        logging.info('save_msg result' + str(result))
        
        if result['error'] is not None:
            self.write_response(result['error'])
            return
      
        if not result['saved']:
            # Other client joined, forward to collider. Do this outside the lock.
            # Note: this may fail in local dev server due to not having the right
            # certificate file locally for SSL validation.
            # Note: loopback scenario follows this code path.
           
            msgText = json.dumps({'msg': messageText})
          
            result = roomManagerInstance.send_message_to_collider(room_id, client_id, msgText)
            if result:
                self.write_response(constants.RESPONSE_SUCCESS)
            else:
                self.write_response(constants.RESPONSE_ERROR)
        else:
            self.write_response(constants.RESPONSE_SUCCESS)
      
        
class ParamsPage(tornado.web.RequestHandler):
    def get(self):
        # Return room independent room parameters.
        params = get_room_parameters(self, None, None, None)
        self.write(json.dumps(params))
        
class RoomPage(tornado.web.RequestHandler):
    def write_response(self, target_page, params={}):
        #template = jinja_environment.get_template(target_page)
        #content = template.render(params)
        self.write("hello, room Page")

    def get(self, room_id):
        self.post(room_id)

    def post(self, room_id):
        """Renders index.html or full.html."""
        # Check if room is full.
        room = roomManagerInstance.getRoom(room_id)
        
        if room is not None:
            logging.info('Room ' + room_id + ' has state ' + str(room))
            if room.get_occupancy() >= 2:
                logging.info('Room ' + room_id + ' is full')
                self.write_response('full_template.html')
                return
        
        #print self.request
        # 'get_argumentst=', self.get_argument('t')
        #print 'get_argumentsts=', self.get_arguments('t')
        
        #print self.request.arguments
        #print self.request.query_arguments
        
        # Parse out room parameters from request.
        params = get_room_parameters(self, room_id, None, None)
        
        #print params
        
        # room_id/room_link will be included in the returned parameters
        # so the client will launch the requested room.
        self.write_response('index_template.html', params)

       
class WSConnectionManager:
    @classmethod
    def instance(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.clientIdConnMap = {} #{'clientId', 'connection'}
        
    def addConn(self, wsConn, roomId, clientId):
        '''
            clientId should be unique right now, or bad thing will happen! 
        '''
        
        if clientId:
            if clientId in self.clientIdConnMap:
                logging.error('clientId: ' + clientId + 'already added in WSConnectionManagerInstance')
                return
            
            self.clientIdConnMap[clientId] = wsConn
        else:
            logging.error("connection should contain a valid clientId")
    
    def removeConn(self, wsConn):
        clientId = wsConn.clientId
        if clientId and clientId in self.clientIdConnMap:
            del self.clientIdConnMap[clientId]
                    
        #TODO: leave the room?
        

    #maybe one clientId has more than once connection?
    #multi devices login    
    def getConnByClientId(self, roomId, clientId):
        return self.clientIdConnMap.get(clientId, None)
    
    def __str__(self):
        roomId_clientId_Map  = {}
        for conn in self.clientIdConnMap.itervalues():
            if conn.roomId not in roomId_clientId_Map:
                roomId_clientId_Map[conn.roomId] = [conn.clientId]
            else:
                roomId_clientId_Map[conn.roomId].append(conn.clientId)
            
        return str(roomId_clientId_Map)
            
#wsConnManagerInstance = WSConnectionManager.instance()
wsConnManagerInstance = WSConnectionManager()


class DispatchCmd:
    @classmethod
    def instance(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance
            
    def __init__(self):
        self.cmdProcess = {
            'register': 'onRegister',
        }
    
    def dispatch(self, msgJson):
        try:
            cmd = msgJson['cmd']
            onCommand = getattr(self, self.cmdProcess[cmd])
            onCommand(msgJson)
        except Exception as ex:
            logging.error('Process msgJson: ' + str(msgJson) + ' failed, Exception: ' + str(ex))
            
    def onRegister(self, msgJson):
        #{“cmd":"register","roomid":"981405838","clientid":"11402970"}
        pass
          
    def registerCmd(self, cmd):
        pass
    
dispatchCmdInstance = DispatchCmd.instance()



class WebSocketHandler(websocket.WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        self.clientId = None
        self.roomId = None
        
        super(WebSocketHandler, self).__init__(application, request, **kwargs)
        
    
    def check_origin(self, origin):
        return True

    def open(self):
        logging.debug('ws client ip=' + str(self.request.remote_ip) + ' connected, request:' + repr(self.request))

    
    def on_message(self, message):
        '''
            if every message contain the senderId, recvId, should simple a lot server code
        '''
        logging.info('ws on_message: roomId=' + str(self.roomId) + \
                     ' ,clientId=' + str(self.clientId) + ' ,msg=' + str(message))
        #self.write_message(u"Echo: " + message)
        
        msgJson = ''
        try:
            msgJson = json.loads(message)
        except Exception as ex:
            logging.error("load json msg error, Exception: " + str(ex))
            return
        
        
        '''
            msg: msg to register to room, or forward to other clients
        '''
        cmd = []
        try:
            cmd = msgJson['cmd']            
            
            #the same clientId maybe register in difference room?
            if cmd == 'register':
                #{"cmd":"register","roomid":"981405838","clientid":"11402970"}
                roomId = msgJson['roomid']
                clientId =  msgJson['clientid']
                
                if self.clientId is None:
                    self.clientId = clientId
                    self.roomId = roomId
                    pass
                else:
                    logging.error("clientId=" + str(clientId) + " already registered")
                    return

                #use to bind this connection to roomId and clientId
                logging.info('register wsConnManagerInstance.addConn(roomId=%s, clientId:%s)' % (roomId, clientId))
                wsConnManagerInstance.addConn(self, roomId, clientId)

                #TODO: drain the possbile other client's message
                logging.info('register wsConnManagerInstance state: ' + str(wsConnManagerInstance))
                return
            elif cmd == 'send':
                #{"cmd":"send","msg":"{\"type\":\"bye\"}"}
                #Forward msg
                
                
                #sendMsgText = json.dump({"msg": msgText})#{"msg":"{\"type\":\"bye\"}"}                        
                del msgJson['cmd']
                
                msgText =  msgJson['msg'] #{u'type': u'bye'}
                
                msg = json.loads(msgText)
                if  msg['type'] == 'candidate'  or \
                    msg['type'] == 'answer'     or \
                    msg['type'] == 'offer'      or \
                    msg['type'] == 'bye'       :    #{u'type': u'bye'}
                    
                    sendMsgText = json.dumps(msgJson)
                    logging.info('wss send: roomid=' + str(self.roomId)+ ', from=' + str(self.clientId) + ',msg= ' + str(sendMsgText))
                    result = roomManagerInstance.save_message_from_client(self.roomId, self.clientId, sendMsgText)
                    
                    if result['error'] is not None:
                        return
                  
                    if not result['saved']:
                        # Other client joined, forward to collider. Do this outside the lock.
                        # Note: this may fail in local dev server due to not having the right
                        # certificate file locally for SSL validation.
                        # Note: loopback scenario follows this code path.
                        result = roomManagerInstance.send_message_to_collider(self.roomId, self.clientId, sendMsgText)
                        
                else:
                    logging.error("Unknown msg type: " + str(message))
                    #roomManagerInstance.save_message_from_client(self.roomId, self.clientId, sendMsgText)
                
                
                #roomManagerInstance.save_message_from_client(self.roomId, self.clientId, message)
                
                logging.info('send wsConnManagerInstance state: ' + str(wsConnManagerInstance))
                return
            else:
                logging.error('Unknown command:' + str(cmd)) 
            
            return        
            #dispatchCmdInstance.dispatch(msgJson)
        except Exception as ex:
            logging.info('Parse cmd failed, msg:' + str(msgJson) + " Exception: " + str(ex))
            pass
        
        logging.error("ws on_message: Unknown msg:" + str(message) )
        
    def on_close(self):
        logging.info('on_close remote_ip: ' + str(self.request.remote_ip) + ' ,roomId: ' + str(self.roomId) + \
                     ' ,clientId:' + str(self.clientId) + ' closed')
        
        wsConnManagerInstance.removeConn(self)

        logging.info('on_close wsConnManagerInstance state: ' + str(wsConnManagerInstance))
        
        result = remove_client_from_room(self.roomId, self.clientId)
        
        if result['error'] is None:
            logging.info('Room state: ' + result['room_state'])
            

application = tornado.web.Application([
    (r"/", MainHandler),
        
    (r'/ws', WebSocketHandler),
    (r"/wsHttpPost/(\w+)/(\w+)", WebSocketHttpPostHandler), #DELETE /wsHttpPost/roomid/clientid
    
    (r'/join/(\w+)', JoinPage),
    (r'/leave/(\w+)/(\w+)', LeavePage),
    (r'/message/(\w+)/(\w+)', MessagePage),
    (r'/params', ParamsPage),
    (r"/r/(\w+)", RoomPage),
    
    (r"/turn", TurnRestfullApi),
    
    
    (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": "/Users/gjwang/Documents/workspace_py/tornado_ws_test"}),
])


if __name__ == "__main__":
    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    log_FileHandler = logging.handlers.TimedRotatingFileHandler(filename = "log/appRTC.log",
                                                                when = 'D',
                                                                interval = 1,
                                                                backupCount = 7)  
    
    log_FileHandler.setFormatter(formatter)
    log_FileHandler.setLevel(logging.INFO)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(log_FileHandler) 
    
    print 'start listening 8888...'
    logging.info('start listening 8888...')
    
    application.listen(8888)
    tornado.ioloop.IOLoop.current().start()
