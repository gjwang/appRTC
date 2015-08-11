'''
Created on Aug 4, 2015

@author: gjwang
'''

import random
import json
import time

from websocket import create_connection

WS_URL = "ws://172.16.243.43:8090/ws"

USER01_LOGIN_TEXT = {'type':'login', 'userid':'gjwang01', 'pwd':'123456'}
USER02_LOGIN_TEXT = {'type':'login', 'userid':'gjwang02', 'pwd':'123456'}

USER01_TO_USER02_MSG = {'type':'msg', 'from':'gjwang01', 'to':'gjwang02', 'body':'hi, buddy'}

def generate_random(length):
    word = ''
    for _ in range(length):
        word += random.choice('0111111')
        
    return word

user_map_01 = {}
user_map_02 = {}

class User():
    def __init__(self, userid):
        self.userid = userid
        self.ws = None
        
    def login(self, ws_url):
        self.ws = create_connection(ws_url)
        
        user_login_text = {'type':'login', 'userid': self.userid, 'pwd':'123456'}
        self.ws.send(json.dumps(user_login_text))
    
        login_resp_text = self.ws.recv()
        login_resp_json = json.loads(login_resp_text)
        print self.userid, login_resp_json 
        
    def send_msg(self, msg):
        self.ws.send(json.dumps(msg))

    def recv_msg(self):
        resp_text = self.ws.recv()
        return resp_text

def gererate_users(start, user_count, user_map):
    for uid in xrange(start, start + user_count, 1):        
        userid = 'user_' + str(uid)
        
        user = User(userid)
        user.login(WS_URL)
        
        user_map[userid] = user
        
        #time.sleep(0.001)

def send_msg(user_from, user_to, msg):
    _msg = {'type':'msg', 'from':user_from.userid, 'to':user_to.userid, 'body':msg}
    
    
    user_from.send_msg(_msg)

    user_from.recv_msg()
    #print user_from.userid + ' send ok'
    
    user_to.recv_msg()
    print user_from.userid + ' send to: ' + user_to.userid + ', ok'

def send_msg_in_loop(userMap01, userMap02):
    while True:
        for user_from in userMap01.itervalues():
            for user_to in userMap02.itervalues():
                idx = int(random.choice('0111111'))
                send_msg(user_from, user_to, msg_list[idx])
                time.sleep(0.01)



sdp_msg = {
   "sdp":"v=0\r\no=- 7127555276685957110 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=group:BUNDLE audio video\r\na=msid-semantic: WMS CYEtVIrazRdMb3uJbpaWUEzwnAFUcIyACXME\r\nm=audio 9 RTP/SAVPF 111 103 104 9 0 8 126\r\nc=IN IP4 0.0.0.0\r\na=rtcp:9 IN IP4 0.0.0.0\r\na=ice-ufrag:6Y0zpShhDfGVYN57\r\na=ice-pwd:e7lEkuz0Axmzzq/Xf7R1zxh9\r\na=fingerprint:sha-256 82:3F:7B:DE:42:B9:69:5C:8B:A8:78:AD:E5:49:15:80:0D:F1:16:90:01:C6:52:8A:A6:76:CA:56:59:80:89:23\r\na=setup:actpass\r\na=mid:audio\r\na=extmap:1 urn:ietf:params:rtp-hdrext:ssrc-audio-level\r\na=extmap:3 http://www.webrtc.org/experiments/rtp-hdrext/abs-send-time\r\na=sendrecv\r\na=rtcp-mux\r\na=rtpmap:111 opus/48000/2\r\na=fmtp:111 minptime=10; useinbandfec=1\r\na=rtpmap:103 ISAC/16000\r\na=rtpmap:104 ISAC/32000\r\na=rtpmap:9 G722/8000\r\na=rtpmap:0 PCMU/8000\r\na=rtpmap:8 PCMA/8000\r\na=rtpmap:126 telephone-event/8000\r\na=maxptime:60\r\na=ssrc:390441228 cname:A1fYLg8V3TKweH2J\r\na=ssrc:390441228 msid:CYEtVIrazRdMb3uJbpaWUEzwnAFUcIyACXME ac49e0d7-5e24-4131-b75a-5e0e19756305\r\na=ssrc:390441228 mslabel:CYEtVIrazRdMb3uJbpaWUEzwnAFUcIyACXME\r\na=ssrc:390441228 label:ac49e0d7-5e24-4131-b75a-5e0e19756305\r\nm=video 9 RTP/SAVPF 111 100 116 117 96\r\nc=IN IP4 0.0.0.0\r\na=rtcp:9 IN IP4 0.0.0.0\r\na=ice-ufrag:6Y0zpShhDfGVYN57\r\na=ice-pwd:e7lEkuz0Axmzzq/Xf7R1zxh9\r\na=fingerprint:sha-256 82:3F:7B:DE:42:B9:69:5C:8B:A8:78:AD:E5:49:15:80:0D:F1:16:90:01:C6:52:8A:A6:76:CA:56:59:80:89:23\r\na=setup:actpass\r\na=mid:video\r\na=extmap:2 urn:ietf:params:rtp-hdrext:toffset\r\na=extmap:3 http://www.webrtc.org/experiments/rtp-hdrext/abs-send-time\r\na=extmap:4 urn:3gpp:video-orientation\r\na=sendrecv\r\na=rtcp-mux\r\na=rtpmap:100 VP8/90000\r\na=rtcp-fb:100 ccm fir\r\na=rtcp-fb:100 nack\r\na=rtcp-fb:100 nack pli\r\na=rtcp-fb:100 goog-remb\r\na=rtpmap:116 red/90000\r\na=rtpmap:117 ulpfec/90000\r\na=rtpmap:96 rtx/90000\r\na=fmtp:96 apt=100\r\na=ssrc-group:FID 3146449481 1781259502\r\na=ssrc:3146449481 cname:A1fYLg8V3TKweH2J\r\na=ssrc:3146449481 msid:CYEtVIrazRdMb3uJbpaWUEzwnAFUcIyACXME 6351c509-0491-483e-a50f-104f87debad6\r\na=ssrc:3146449481 mslabel:CYEtVIrazRdMb3uJbpaWUEzwnAFUcIyACXME\r\na=ssrc:3146449481 label:6351c509-0491-483e-a50f-104f87debad6\r\na=ssrc:1781259502 cname:A1fYLg8V3TKweH2J\r\na=ssrc:1781259502 msid:CYEtVIrazRdMb3uJbpaWUEzwnAFUcIyACXME 6351c509-0491-483e-a50f-104f87debad6\r\na=ssrc:1781259502 mslabel:CYEtVIrazRdMb3uJbpaWUEzwnAFUcIyACXME\r\na=ssrc:1781259502 label:6351c509-0491-483e-a50f-104f87debad6\r\n",
   "type":"offer"
}    

candidate_msg = {
   "type":"candidate",
   "label":0,
   "id":"audio",
   "candidate":"candidate:684784063 1 udp 2122260223 172.16.243.66 59728 typ host generation 0"
}

msg_list = (sdp_msg, candidate_msg)



if __name__ == '__main__':
    gererate_users(0, 30000, user_map_01)
    gererate_users(500000, 34000, user_map_02)

    #gererate_users(600000, 3000, user_map_01)
    #gererate_users(700000, 1000, user_map_02)

    #gererate_users(800000, 3000, user_map_01)
    #gererate_users(900000, 1000, user_map_02)

    send_msg_in_loop(user_map_01, user_map_02)
    
    time.sleep(60)
    
    pass
