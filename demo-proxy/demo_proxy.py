#!/usr/bin/python

# Copyright (C) 2015 PSNC
# Lukasz Ogrodowczyk (PSNC) <lukaszog_at_man.poznan.pl>

import os, paramiko, time, sys, threading, socket, datetime
from flask import Flask,jsonify, render_template, request, make_response, current_app
import requests, json
from datetime import timedelta
from functools import update_wrapper
from cherrypy import wsgiserver

STREAM_BAND = '20Mbps'
#STREAM_BAND = '200Mbps'

SUCCESS_CODE = "ok"
SUCCESS_CODE_PATH_ESTABLISHED = "Path established"
SUCCESS_CODE_PATH_RELEASED = "Path released"
SUCCESS_CODE_STREAM_STARTED = "Stream started"
SUCCESS_CODE_STREAM_STOPED = "Stream stopped"
SUCCESS_CODE_BAND_SET = "Band set"
  

ERROR_CODE = "Error"
ERROR_CODE_ADD_FLOW_FAIL = "Error: add flow_mod fail"
ERROR_CODE_DEL_FLOW_FAIL = "Error: del flow_mod fail"
ERROR_WRONG_PATH_NR = "Error: wrong path number"
ERROR_CODE_OF_CTRL_NOT_CONNECTED = "Error: Ryu ctrl not connected!"
ERROR_CODE_RL_NOT_CONNECTED = "Error: RL not connected!"
ERROR_CODE_BAND_NOT_SET = "Error: Band not set"

player_IP = {
    1:'150.254.185.246',
    2:'150.254.185.246',
    3:'150.254.185.246',
    4:'150.254.185.246'
}
'''
    1:'150.254.173.135',
    2:'150.254.173.135',
    3:'150.254.173.135',
    4:'150.254.173.135'
'''

player_IP_list = [player_IP[1],player_IP[2],player_IP[3],player_IP[4]]

DPID_lists = {
        "AIST":  [0x0000000000000001],
        "KDDI":  [0x000000255ce64f07],
        "PSNC":  [0x000054e032cca4c0,0x00000881f488f5b0],
        "iMinds":[0x000000259065bc62], #0x0000089e016164dd],
        "i2cat": [0x0010000000000001,0x0010000000000002,0x0010000000000003],
        "tests": [0x777,0x888,0x999]}

uv_streamer = [
    {'name':'streamer1', 'command':'/home/okazaki/ultragrid/bin/uv --playback /home/okazaki/Videos/POT_PRZYRODA_'+STREAM_BAND+' -P 2222 '+player_IP[1],'hostIP':'163.220.30.135','username':'lukaszog','password':''},
    {'name':'streamer2', 'command':'/home/okazaki/ultragrid/bin/uv --playback /home/okazaki/Videos/TEARS_OF_STEEL_'+STREAM_BAND+' -P 4444 '+player_IP[2],'hostIP':'163.220.30.135','username':'lukaszog','password':''},
    {'name':'streamer3', 'command':'/home/okazaki/ultragrid/bin/uv --playback /home/okazaki/Videos/POZNAN_'+STREAM_BAND+' -P 6666 '+player_IP[3],'hostIP':'163.220.30.135','username':'lukaszog','password':''},
    {'name':'streamer4', 'command':'/home/okazaki/ultragrid/bin/uv --playback /home/okazaki/Videos/BBB_'+STREAM_BAND+' -P 8888 '+player_IP[4],'hostIP':'163.220.30.135','username':'lukaszog','password':''}]

uv_player = {
    'hostIP':'150.254.185.246',
    'username':'player',
    'password':'!Pcss 4.12',
    'command_p1':'DISPLAY=:0.1 /home/player/ultragrid/bin/uv -d sdl -P 2222',
    'command_p2':'DISPLAY=:0.2 /home/player/ultragrid/bin/uv -d sdl -P 4444',
    'command_p3':'DISPLAY=:0.3 /home/player/ultragrid/bin/uv -d sdl -P 6666',
    'command_p4':'DISPLAY=:0.4 /home/player/ultragrid/bin/uv -d sdl -P 8888',
    'command_ifstat':'ifstat -i eth0 -b',
    'command_ping':'ping 163.220.30.135'}
    
ryu_controller_config = {
    'hostIP':'127.0.0.1',
    'username':'felix',
    'password':'',
    'command_ryu':'PYTHONPATH=/home/felix/felix-demo-tools/ryu /home/felix/felix-demo-tools/ryu/bin/ryu-manager --verbose /home/felix/felix-demo-tools/ryu/ryu/app/ofctl_rest.py',
    'openflow_path':{
        1:[
            # Demo C - 180Mbps
            # --- AIST
            {'dpid':DPID_lists['AIST'][0],'in_port':'4', 'out_port':'6', 'ip_dst':player_IP_list},
            # --- KDDI
            {'dpid':DPID_lists['KDDI'][0],'in_port':'1', 'out_port':'2', 'ip_dst':player_IP_list},
            # --- PSNC   
            {'dpid':DPID_lists['PSNC'][0],'in_port':'21','out_port':'1', 'ip_dst':player_IP_list},
            {'dpid':DPID_lists['PSNC'][1],'in_port':'1', 'out_port':'7', 'ip_dst':player_IP_list},
            
            #i2cat - temp
            {'dpid':DPID_lists['i2cat'][0],'in_port':'3', 'out_port':'6', 'ip_dst':player_IP_list},
            {'dpid':DPID_lists['i2cat'][1],'in_port':'1', 'out_port':'3', 'ip_dst':player_IP_list},
            {'dpid':DPID_lists['i2cat'][2],'in_port':'1', 'out_port':'2', 'ip_dst':player_IP_list},
            #iMinds - temp
            {'dpid':DPID_lists['iMinds'][0],'in_port':'21', 'out_port':'1', 'ip_dst':player_IP_list},
            
            # --- Tests
            # - PSNC test slice
            {'dpid':0x00000881f488f5b0, 'in_port':'28', 'ip_dst':player_IP_list, 'out_port':'29'},
            # - Mininet
            {'dpid':0x777, 'in_port':'1', 'ip_dst':player_IP_list, 'out_port':'2'},            
            {'dpid':0x777, 'in_port':'2', 'ip_dst':player_IP_list, 'out_port':'1'}
        ],
        2:[
            # Demo C - 200Mbps
            # --- AIST
            # --- KDDI
            # --- PSNC
            # --- iMinds
            # --- i2cat
        ],
        3:[
            # --- Tests   
            {'dpid':0x888, 'in_port':'1', 'ip_dst':player_IP_list, 'out_port':'7'}
        ],
        4:[
            # --- Tests   
            {'dpid':0x777, 'in_port':'1', 'ip_dst':player_IP_list, 'out_port':'7'}
        ]
        
    },
    'of_sw_list' : [ 
        DPID_lists['AIST'][0],
        DPID_lists['KDDI'][0],
        DPID_lists['PSNC'][0],
        DPID_lists['PSNC'][1],
        DPID_lists['iMinds'][0],
        DPID_lists['i2cat'][0],
        DPID_lists['i2cat'][1],
        DPID_lists['i2cat'][2],
        DPID_lists['tests'][0],
        DPID_lists['tests'][1],
        DPID_lists['tests'][2]      
    ]
}    

rate_limiter_config = {
    'hostIP':'163.220.30.135',
    'username':'lukaszog',
    'password':''
}    
app = Flask(__name__)   
#---------------------------------------------------------#
def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator
#---------------------------------------------------------#
class RyuController(threading.Thread):
    def __init__(self, ryuparam):
        threading.Thread.__init__(self)
        self.connected=False
        self.ryuparam=ryuparam
        self.of_flows={}
        self.last_path_number=None
        self.active = True
        
    def run(self):
        self.connect()
        while self.active:
            while self.connected: 
                '''
                try:
                    trace = self.channel.recv(4096)
                    try:
                        print trace
                    except:
                        continue
                except:
                    continue  
                '''    
                time.sleep(1)
            print "Ryu is dead? :("       
            time.sleep(1)
            
    def connect(self):       
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.ryuparam['password'] == '':
                ki = paramiko.RSAKey.from_private_key_file('/home/felix/.ssh/id_rsa')
                print "Trying to connect with Ryu controller ...."
                self.ssh.connect(self.ryuparam['hostIP'], timeout=60, username=self.ryuparam['username'], pkey=ki)
                print "Connection with Ryu controller established"
            
            else:
                print "Trying to connect with Ryu controller..."
                self.ssh.connect(self.ryuparam['hostIP'], timeout=60, username=self.ryuparam['username'], password=self.ryuparam['password'])
                print "Connection with Ryu controller established"
        except:  
            return
        try:    
            self.channel = self.ssh.get_transport().open_session()
            self.channel.get_pty()
            self.channel.exec_command(self.ryuparam['command_ryu'])  
            #self.channel.setblocking(0)            
            print "SSH channel created with Ryu"
        except:  
            return
        self.connected = True
        return "TEST CONNECT - RYU"
    
    def listofConnectedOFSw(self):
        response = requests.get('http://localhost:8080/stats/switches')  
        return response.json()

    def setPath(self, path_number):
        if path_number in self.ryuparam['openflow_path']:
            for flow in self.ryuparam['openflow_path'][path_number]:
                for dst_ip in flow['ip_dst']:
                    return_code = self.addFlow(flow['dpid'],flow['in_port'],dst_ip,flow['out_port'])
                    if return_code != SUCCESS_CODE:
                        return return_code
            self.last_path_number=path_number
            return SUCCESS_CODE_PATH_ESTABLISHED
        return ERROR_WRONG_PATH_NR
        
    def delPath(self, path_number):
        if path_number in self.ryuparam['openflow_path']:
            for flow in self.ryuparam['openflow_path'][path_number]:
                for dst_ip in flow['ip_dst']:
                    return_code = self.delFlow(flow['dpid'],flow['in_port'],dst_ip,flow['out_port'])
                    if return_code != SUCCESS_CODE:
                        return return_code                    
            self.last_path_number=None
            return SUCCESS_CODE_PATH_RELEASED
        return ERROR_WRONG_PATH_NR
            
    def isConnected(self):
        return self.connected   

    def getLastPathNumber(self):
        return self.last_path_number
        
    def getFlows(self):
        flows = {}
        for of_sw in self.ryuparam['of_sw_list']:
            response = requests.get('http://localhost:8080/stats/flow/'+str(of_sw))
            
            if response.status_code == 404:
                flows[str(hex(of_sw))]={}
            else:
                flows[str(hex(of_sw))]=response.json()           
        return flows
        
    def addFlow(self, dpid, in_port, ip_dst, out_port):
        eth_type_list = [0x800, 0x806]
        for eth_type in eth_type_list:
            payload = {
                "dpid":dpid,
                "cookie":1,
                "cookie_mask":1,
                "table_id":0,
                "idle_timeout":0,
                "hard_timeout":0,
                #"idle_timeout":60,
                #"hard_timeout":60,
                "priority":1,
                "flags":1,
                "match":{
                    "in_port":in_port,
                    "dl_type": eth_type,
                    "nw_dst": ip_dst
                },
                "actions":[
                    {
                        "type":"OUTPUT",
                        "port":out_port
                    }
                ]
            }
            response = requests.post('http://10.134.0.236:8080/stats/flowentry/add',
                            data=json.dumps(payload))  
            if response.status_code==200:     
                print "Flow added"
            else:
                return ERROR_CODE_ADD_FLOW_FAIL+" DPID: %s"%(hex(dpid))
        return SUCCESS_CODE
    
    def delFlow(self, dpid, in_port, ip_dst, out_port):
        eth_type_list = [0x800, 0x806]
        for eth_type in eth_type_list:
            payload = {
                "dpid":dpid,
                "cookie":1,
                "cookie_mask":1,
                "table_id":0,
                "idle_timeout":0,
                "hard_timeout":0,                
                #"idle_timeout":60,
                #"hard_timeout":60,
                "priority":1,
                "flags":1,
                "match":{
                    "in_port":in_port,
                    "dl_type": eth_type,
                    "nw_dst": ip_dst
                },
                "actions":[
                    {
                        "type":"OUTPUT",
                        "port":out_port
                    }
                ]
            }
            response = requests.post('http://10.134.0.236:8080/stats/flowentry/delete',
                            data=json.dumps(payload))  
            if response.status_code==200:      
                print "Flow deleted"
            else:
                return ERROR_CODE_DEL_FLOW_FAIL+" DPID: %s"%(hex(dpid))
        return SUCCESS_CODE                
    
    def getMaxPathID(self):
        max_path_nr = 0
        for path_number in self.ryuparam['openflow_path']:
            if path_number>max_path_nr:
                 max_path_nr = path_number
        #print "################### %s"%(max_path_nr)
        return max_path_nr
    
    def stop(self):        
        if self.connected:
            print "Ryu Controller stopping"
            self.ssh.close()  
            self.channel.close()
            self.active = False 
            self.connected = False
            print "Ryu Controller stopped"
#---------------------------------------------------------#

ryu_controller = RyuController(ryu_controller_config)

#---------------------------------------------------------#
class UGstreamer(threading.Thread):
    def __init__(self, uvparam):
        threading.Thread.__init__(self)
        self.connected=False
        self.active = True
        self.uvparam=uvparam
        
    def run(self):
        self.connect()
        while self.active:
            while self.connected:
                #print "Streamer %s connected :)\n"%(self.uvparam['name'])   
                time.sleep(1)
            print "Waiting for connection with streamer: %s..."%(self.uvparam['name'])            
            time.sleep(1)
            
    def connect(self):       
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if self.uvparam['password'] == '':
                ki = paramiko.RSAKey.from_private_key_file('/home/felix/.ssh/id_rsa')
                print "Trying to connect with streamer %s ...."%(self.uvparam['name'])
                self.ssh.connect(self.uvparam['hostIP'], timeout=60, username=self.uvparam['username'], pkey=ki)
                print "Connection with streamer %s established"%(self.uvparam['name'])
            else:
                print "Trying to connect with streamer %s ...."%(self.uvparam['name'])
                self.ssh.connect(self.uvparam['hostIP'], timeout=60, username=self.uvparam['username'], password=self.uvparam['password'])           
                print "Connection with streamer %s established"%(self.uvparam['name'])
        except:  
            print "Error: sth wrong during connection with the streamer"
            return
        try:    
            self.channel = self.ssh.get_transport().open_session()
            self.channel.get_pty()
            self.channel.exec_command(self.uvparam['command'])    
            print "SSH channel created with %s"%(self.uvparam['name'])
        except:  
            print "Error: sth wrong during command execution into streamer"
            return
        self.connected = True
     
    def isConnected(self):
        return self.connected          
        
    def stop(self):        
        if self.connected:
            print "Streamer %s stopping"%self.uvparam['name']
            self.ssh.close()  
            self.channel.close() 
            #self.active = False
            self.connected=False
            print "Streamer stopped"
#---------------------------------------------------------#
streamer1 = UGstreamer(uv_streamer[0])         
streamer2 = UGstreamer(uv_streamer[1]) 
streamer3 = UGstreamer(uv_streamer[2]) 
streamer4 = UGstreamer(uv_streamer[3]) 

streamer_list=[streamer1,streamer2,streamer3,streamer4]
#---------------------------------------------------------#
class UGplayer(threading.Thread):
    def __init__(self, uvparam):
        threading.Thread.__init__(self)
        self.connected=False
        self.active = True
        self.uvparam=uvparam
        self.params ={
            'network':{'band':None,'rtt':None},
            'player1':{'fps':None,'loss':None},
            'player2':{'fps':None,'loss':None},
            'player3':{'fps':None,'loss':None},
            'player4':{'fps':None,'loss':None}
        }
        self.livestreaming_cntr_on = 5
        self.livestreaming_cntr = [0,0,0,0]
        
    def run(self):
        self.connect()
        while self.active:
            while self.connected:

            # --- channel_ping (ping player->streamer) ---
                try:
                    trace = self.channel_ping.recv(4096)
                    try:
                        self.params['network']['rtt']=(trace.split('time=')[1]).split(' ')[0]
                    except ValueError:
                        continue
                except:
                    continue  
                    
            # --- channel_ifstat (ifstat) ---
                try:
                    trace = self.channel_ifstat.recv(4096)
                    try:
                        self.params['network']['band']=float("{0:.2f}".format(float(trace.split()[0])/1024))
                    except ValueError:
                        continue
                except:
                    continue                
                
                # --- channel_p1 (UltraGrid) ---
                try:
                    trace = self.channel_p1.recv(4096)
                    if ('[SDL]' in trace)and('FPS' in trace):
                        self.params['player1']['fps']=round(float(((trace.split('=')[1]).split('FPS')[0]).strip()),0)
                    if ('packets expected' in trace)and('%' in trace):
                        self.params['player1']['loss']=round(100-float((((trace.split('(')[1]).split(')')[0]).split('%')[0]).strip()),0)
                    
                    if (('[SDL]' in trace)or('FPS' in trace)or('packets expected' in trace)or('%' in trace))and(self.livestreaming_cntr[0] <= self.livestreaming_cntr_on):
                        self.livestreaming_cntr[0] = self.livestreaming_cntr_on 

                except:
                    if self.livestreaming_cntr[0] > 0:                        
                        self.livestreaming_cntr[0]=self.livestreaming_cntr[0]-1
                
                # --- channel_p2 (UltraGrid) ---
                try:
                    trace = self.channel_p2.recv(4096)
                    if ('[SDL]' in trace)and('FPS' in trace):
                        self.params['player2']['fps']=round(float(((trace.split('=')[1]).split('FPS')[0]).strip()),0)
                    if ('packets expected' in trace)and('%' in trace):
                        self.params['player2']['loss']=round(100-float((((trace.split('(')[1]).split(')')[0]).split('%')[0]).strip()),0)
                        
                    if (('[SDL]' in trace)or('FPS' in trace)or('packets expected' in trace)or('%' in trace))and(self.livestreaming_cntr[1] <= self.livestreaming_cntr_on):
                        self.livestreaming_cntr[1] = self.livestreaming_cntr_on 
                except:
                    if self.livestreaming_cntr[1] > 0:                        
                        self.livestreaming_cntr[1]=self.livestreaming_cntr[1]-1              
                
                # --- channel_p3 (UltraGrid) ---
                try:
                    trace = self.channel_p3.recv(4096)
                    if ('[SDL]' in trace)and('FPS' in trace):
                        self.params['player3']['fps']=round(float(((trace.split('=')[1]).split('FPS')[0]).strip()),0)
                    if ('packets expected' in trace)and('%' in trace):
                        self.params['player3']['loss']=round(100-float((((trace.split('(')[1]).split(')')[0]).split('%')[0]).strip()),0)
                   
                    if (('[SDL]' in trace)or('FPS' in trace)or('packets expected' in trace)or('%' in trace))and(self.livestreaming_cntr[2] <= self.livestreaming_cntr_on):
                        self.livestreaming_cntr[2] = self.livestreaming_cntr_on                         
                except:
                    if self.livestreaming_cntr[2] > 0:                        
                        self.livestreaming_cntr[2]=self.livestreaming_cntr[2]-1
                    
                # --- channel_p4 (UltraGrid) ---
                try:
                    trace = self.channel_p4.recv(4096)
                    if ('[SDL]' in trace)and('FPS' in trace):
                        self.params['player4']['fps']=round(float(((trace.split('=')[1]).split('FPS')[0]).strip()),0)
                    if ('packets expected' in trace)and('%' in trace):
                        self.params['player4']['loss']=round(100-float((((trace.split('(')[1]).split(')')[0]).split('%')[0]).strip()),0)
                    
                    if (('[SDL]' in trace)or('FPS' in trace)or('packets expected' in trace)or('%' in trace))and(self.livestreaming_cntr[3] <= self.livestreaming_cntr_on):
                        self.livestreaming_cntr[3] = self.livestreaming_cntr_on 
                except:
                    if self.livestreaming_cntr[3] > 0:                        
                        self.livestreaming_cntr[3]=self.livestreaming_cntr[3]-1
                    
                time.sleep(1) 

            print "No connection to the Player? :("      
            
            time.sleep(1)
            
    def connect(self):       

        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())        
            if self.uvparam['password'] == '':
                ki = paramiko.RSAKey.from_private_key_file('/home/felix/.ssh/id_rsa')
                print "Trying to connect with player %s ...."%(self.uvparam['hostIP'])
                self.ssh.connect(self.uvparam['hostIP'], timeout=60, username=self.uvparam['username'], pkey=ki)
                print "Connection with player %s established"%(self.uvparam['hostIP'])            
            else:
                print "Trying to connect with Player: %s ...."%(self.uvparam['hostIP'])
                self.ssh.connect(self.uvparam['hostIP'], timeout=60, username=self.uvparam['username'], password=self.uvparam['password'])
                print "Connection with Player %s established"%(self.uvparam['hostIP'])
        except:  
            return
        
        try:    

            self.channel_p1 = self.ssh.get_transport().open_session()
            self.channel_p1.get_pty()
            self.channel_p1.exec_command(self.uvparam['command_p1'])  
            self.channel_p1.setblocking(0)
            
            self.channel_p2 = self.ssh.get_transport().open_session()
            self.channel_p2.get_pty()
            self.channel_p2.exec_command(self.uvparam['command_p2'])  
            self.channel_p2.setblocking(0)

            self.channel_p3 = self.ssh.get_transport().open_session()
            self.channel_p3.get_pty()
            self.channel_p3.exec_command(self.uvparam['command_p3'])  
            self.channel_p3.setblocking(0)

            self.channel_p4 = self.ssh.get_transport().open_session()
            self.channel_p4.get_pty()
            self.channel_p4.exec_command(self.uvparam['command_p4'])  
            self.channel_p4.setblocking(0)
            
            self.channel_ifstat = self.ssh.get_transport().open_session()
            self.channel_ifstat.get_pty()
            self.channel_ifstat.exec_command(self.uvparam['command_ifstat'])  
            self.channel_ifstat.setblocking(0)

            self.channel_ping = self.ssh.get_transport().open_session()
            self.channel_ping.get_pty()
            self.channel_ping.exec_command(self.uvparam['command_ping'])  
            self.channel_ping.setblocking(0)
            
            print "SSH channels created!"
        except:  
            return
        
        self.connected = True
     
    def isConnected(self):
        return self.connected
                    
    def isLifeStreamingOn(self,number):
        #print "Map of on-line streaming cntr: %s"%(self.livestreaming_cntr)
        if self.connected:
            if self.livestreaming_cntr[number] > 0:
                return True
            else:
                return False
        else:
            return False
                
    def getFPS(self,player):
        return self.params[player]['fps']
    
    def getLoss(self,player):
        return self.params[player]['loss']

    def getBand(self):
        return self.params['network']['band']
    
    def getRTT(self):
        return self.params['network']['rtt']
                
    def stop(self):        
        if self.connected:
            print "Player %s stopping"%self.uvparam['hostIP']
            self.ssh.close()  
            self.channel_p1.close() 
            self.channel_p2.close() 
            self.channel_p3.close() 
            self.channel_p4.close() 
            self.channel_ifstat.close()
            self.connected=False
            self.active = False
            print "Player stopped"
#---------------------------------------------------------# 

player = UGplayer(uv_player) 
players_list=['player1','player2','player3','player4']

#---------------------------------------------------------#
class RateLimiter(threading.Thread):
    def __init__(self, ratelimiterparam):
        threading.Thread.__init__(self)
        self.ratelimiterparam=ratelimiterparam
        self.connected=False
        self.active=True
        
    def run(self):
        self.connect()
        while self.active:
            while self.connected: 
                '''
                try:
                    trace = self.channel.recv(4096)
                    print trace
                except:
                    None
                '''          
                time.sleep(1)
            print "RL is dead? :("  
            rate_limiter.connect()            
            time.sleep(1)
            
    def connect(self):       
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.ratelimiterparam['password'] == '':
                ki = paramiko.RSAKey.from_private_key_file('/home/felix/.ssh/id_rsa')
                print "Trying to connect with RL ...."
                self.ssh.connect(self.ratelimiterparam['hostIP'], timeout=60, username=self.ratelimiterparam['username'], pkey=ki)
                print "Connection with RL established"
            
            else:
                print "Trying to connect with RL..."
                self.ssh.connect(self.ratelimiterparam['hostIP'], timeout=60, username=self.ratelimiterparam['username'], password=self.ratelimiterparam['password'])
                print "Connection with RL established"
        except:  
            return
        try:    
            self.channel = self.ssh.get_transport().open_session()
            self.channel.get_pty()  
            print "SSH channel created with RL"                        
            self.channel.setblocking(0)
            
        except:  
            return
        self.connected = True
     
    def isConnected(self):
        return self.connected   
        
    def getConfofRL(self): 
        r = requests.get("http://163.220.30.135:8000/flows/", auth=('lukaszog','poznanpl')) 
        if r.json() == []:
            return {"RL Service status": "not created"}
        else:
            return r.json()[0]

    def setBand(self, band):
        #check if session exist:
        r = requests.get("http://163.220.30.135:8000/flows/", auth=('lukaszog','poznanpl')) 
        if r.json() == []:
            print "RL Session not created"
            try:                
                payload = {'bandwidth':str(band)+'mbit', 'destinations':'["'+player_IP[1]+'","'+player_IP[2]+'","'+player_IP[3]+'","'+player_IP[4]+'"]'}
                header = {'content-type': 'application/json'}
                r = requests.post("http://163.220.30.135:8000/flows/", data=json.dumps(payload), headers=header, auth=('lukaszog','poznanpl'))            
                print "Status:%s | Response:%s"%(r.status_code, r.text)   

                if r.status_code==200: 
                    return SUCCESS_CODE_BAND_SET
                else:
                    return ERROR_CODE_BAND_NOT_SET                
            except:
                print "Sth wrong: RL"
                return ERROR_CODE_BAND_NOT_SET 
        else:
            session_id = r.json()[0]["id"]
            print "RL session exists - id=%s"%(session_id)
            try:
                payload = {'bandwidth':str(band)+'mbit', 'destinations':'["'+player_IP[1]+'","'+player_IP[2]+'","'+player_IP[3]+'","'+player_IP[4]+'"]'}
                print payload
                header = {'content-type': 'application/json'}
                r = requests.put("http://163.220.30.135:8000/flows/"+str(session_id)+"/", data=json.dumps(payload), headers=header, auth=('lukaszog','poznanpl'))            
                print "Status:%s | Response:%s"%(r.status_code, r.text)  

                if r.status_code==200: 
                    return SUCCESS_CODE_BAND_SET
                else:
                    return ERROR_CODE_BAND_NOT_SET                  
            except:
                print "Sth wrong: RL"
                return ERROR_CODE_BAND_NOT_SET 
                
    def delRLsession(self):
        try:
            r = requests.get("http://163.220.30.135:8000/flows/", auth=('lukaszog','poznanpl')) 
            if r.json() != []:
                session_id = r.json()[0]["id"]
                header = {'content-type': 'application/json'}
                r = requests.delete("http://163.220.30.135:8000/flows/"+str(session_id)+"/", headers=header, auth=('lukaszog','poznanpl'))
                print "Status:%s | Response:%s"%(r.status_code, r.text)             
        except:
            print "Sth wrong with RL"
            
    def stop(self):        
        if self.connected:
            print "RL stopping"
            self.ssh.close()  
            self.channel.close() 
            self.connected=False
            self.active=False
            print "RL stopped"
#---------------------------------------------------------#

rate_limiter = RateLimiter(rate_limiter_config)

#---------------------------------------------------------#
class HQmon(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.active = True
        self.on = False
        self.delay_time=[0,0,0,0]
        self.delay_after_network_change = 0
        self.lowQcounter = 0 
        
        self.delay_time_treshold = 10                 # min time movie is play at the beginning before app measure params
        self.delay_after_network_change_treshold = 10 # min time after network rearrangements before monitoring again
        self.FPS_treshold = 21                        
        self.loss_treshold = 1
        self.lowQcounter_treshold = 1                 # how long LowQ exists
        
        self.path_installed = None      
        
    def run(self):
        
        while self.active:        
            while self.on:

                #check OF network (which path installed) :
                if ryu_controller.isAlive():
                    self.path_installed = ryu_controller.getLastPathNumber()
                        
                if player.isConnected():
                     
                    # change in OF network should not be trigger too fast
                    # wait delay_after_network_change_treshold before next change
                    if self.delay_after_network_change < self.delay_after_network_change_treshold:
                        self.delay_after_network_change = self.delay_after_network_change+1
        
                    # Stream should be visualized at least delay_time_treshold      
                    # because of unstable monitoring results at the beginning 
                    for i in range(4):
                        if player.isLifeStreamingOn(i)==True:
                            if self.delay_time[i]<self.delay_time_treshold:
                                self.delay_time[i] = self.delay_time[i] + 1       
                  
                    # app check if low quality remains at least lowQcounter_treshold
                    if (((self.delay_time[0]==self.delay_time_treshold)and((player.isLifeStreamingOn(0))and((player.getFPS('player1')<self.FPS_treshold)or(player.getLoss('player1')>self.loss_treshold))))or
                        ((self.delay_time[1]==self.delay_time_treshold)and((player.isLifeStreamingOn(1))and((player.getFPS('player2')<self.FPS_treshold)or(player.getLoss('player2')>self.loss_treshold))))or
                        ((self.delay_time[2]==self.delay_time_treshold)and((player.isLifeStreamingOn(2))and((player.getFPS('player3')<self.FPS_treshold)or(player.getLoss('player3')>self.loss_treshold))))or
                        ((self.delay_time[3]==self.delay_time_treshold)and((player.isLifeStreamingOn(3))and((player.getFPS('player4')<self.FPS_treshold)or(player.getLoss('player4')>self.loss_treshold))))):
                        if self.lowQcounter<self.lowQcounter_treshold:
                            self.lowQcounter = self.lowQcounter + 1
                    else:
                        self.lowQcounter = 0
                                            
                    # in case of lowQ -> network rearrangements
                    # but min delay_after_network_change_treshold after previus change
                    if ((self.delay_after_network_change==self.delay_after_network_change_treshold)and(self.lowQcounter == self.lowQcounter_treshold)):
                        self.delay_after_network_change = 0
                        self.lowQcounter = 0
                        print "\n----------- OF path should be changed -------------"
                        if ryu_controller.isAlive():
                            if (self.path_installed==None):
                                ryu_controller.setPath(1)

                            elif(ryu_controller.getMaxPathID()>int(self.path_installed)):
                                #del old path:
                                ryu_controller.delPath(int(self.path_installed))
                                #set up new path:
                                ryu_controller.setPath(int(self.path_installed)+1)
                                
                            else:
                                print "No better OF path available"
                    
                time.sleep(1)
            
            time.sleep(1)
            
    def enableHQmon(self):
        self.on = True 
         
    def disableHQmon(self):
        self.delay_time=[0,0,0,0]
        self.delay_after_network_change = 0
        self.lowQcounter = 0
        self.on = False
        
    def getStatus(self):
        return {"status":self.on, "of_path":self.path_installed}
            
    def stop(self):        
        print "HQmon stopping"
        self.on=False
        self.active = False
        print "HQmon stopped"
#---------------------------------------------------------#
net_app = HQmon()
#---------------------------------------------------------#
class FlaskAPP(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.active = True
        
        self.d = wsgiserver.WSGIPathInfoDispatcher({'/': app})
        self.server = wsgiserver.CherryPyWSGIServer(('0.0.0.0', 5000), self.d)

    def run(self):
        # run flask service:
        print "Starting flask service"
        #app.run("0.0.0.0")
        
        self.server.start()

        while self.active:        
            time.sleep(1)
                        
    def stop(self):        
        print "Flask stopping"
        self.active = False
        self.server.stop()
        print "Flask stopped"
#---------------------------------------------------------#
flask_app = FlaskAPP()
flask_app.start()
#---------------------------------------------------------#
#--- Admin Panel -----------------------------------------#      
@app.route("/demo_proxy_admin_panel")
def hello():
    return render_template('index.html')

# --- OpenFlow Controller - Ryu ---------------------------
@app.route("/startryucontroller")
@crossdomain(origin='*')
def startryucontroller():  
    if not ryu_controller.isAlive():
        ryu_controller.start()
    else:
        ryu_controller.connect()
    return jsonify(status="OF CTRL started")
    
@app.route("/getryustatus")
def getryustatus():  
    return jsonify(status=ryu_controller.isConnected())
    
@app.route("/setpath/<nr>")
@crossdomain(origin='*')
def setpath(nr):    
    if ryu_controller.isAlive():
        return jsonify(status=ryu_controller.setPath(int(nr))) 
    else:
        return jsonify(status=ERROR_CODE_OF_CTRL_NOT_CONNECTED)

@app.route("/delpath/<nr>")
@crossdomain(origin='*')
def delpath(nr):    
    if ryu_controller.isAlive():
        return jsonify(status=ryu_controller.delPath(int(nr))) 
    else:
        return jsonify(status=ERROR_CODE_OF_CTRL_NOT_CONNECTED)        
    
@app.route("/getflows")
def getflows():    
    if ryu_controller.isAlive():
        flows = ryu_controller.getFlows()
        return jsonify(**flows)
    return "Ok"
  
@app.route("/getlistofsw")
def getlistofsw():    
    if ryu_controller.isAlive():
        of_sw_list = ryu_controller.listofConnectedOFSw()
        of_sw_hex_list = []
        for sw in of_sw_list:
            of_sw_hex_list.append(hex(sw))
        return jsonify(status=of_sw_hex_list)
    else: 
        return jsonify(status=ERROR_CODE_OF_CTRL_NOT_CONNECTED) 

@app.route("/getpathnumber")
@crossdomain(origin='*')
def getpathnumber():
    if ryu_controller.isAlive():
        return jsonify(status=ryu_controller.getLastPathNumber())
    else: 
        return jsonify(status=ERROR_CODE_OF_CTRL_NOT_CONNECTED) 
    
# --- RL: --------------------------------------------
@app.route("/setband/<band>")
@crossdomain(origin='*')
def setband(band):    
    if rate_limiter.isAlive():
        return jsonify(status=rate_limiter.setBand(int(band)))
    else:
        return jsonify(status=ERROR_CODE_RL_NOT_CONNECTED)    

@app.route("/getrlstatus")
@crossdomain(origin='*')
def getrlustatus():  
    return jsonify(result=rate_limiter.isConnected())
    
@app.route("/getconfigurationofratelimiter")
@crossdomain(origin='*')
def getconfigurationofratelimiter():  
    if rate_limiter.isAlive():     
        rl_status = rate_limiter.getConfofRL()
        return jsonify(**rl_status)
    return "Ok" 

@app.route("/deleterlsession")
@crossdomain(origin='*')
def deleterlsession():    
    if rate_limiter.isAlive():
        rate_limiter.delRLsession()
    return "Ok"  
        
# --- Players: ------------------------------------------   
@app.route("/startplayers")
@crossdomain(origin='*')
def startplayers():  
    '''
    Should be call once 
    - to enable channel to UG-player
    - to run four UG players
    - to receive media params (FPS and frames losses)
    - to receive network params (bandwidth on the interface and RTT to AIST)
    '''
    if not player.isAlive():
        player.start()
    else:
        player.connect()    
    return jsonify(status="UG players started")
    
@app.route("/stopplayers")
def stopplayers():
    '''
    To stop UG-player
    '''
    if player.isAlive():
        player.stop()       
    return "Ok"
  
@app.route('/playerstatus')
@crossdomain(origin='*')
def playerstatus():
    '''
    To check if channel with UG-player is established
    '''
    return jsonify(isconnected=player.isConnected(), 
        islive_1=player.isLifeStreamingOn(0),
        islive_2=player.isLifeStreamingOn(1),
        islive_3=player.isLifeStreamingOn(2),
        islive_4=player.isLifeStreamingOn(3))    

@app.route("/playerparams/<resource>")
@crossdomain(origin='*')
def playerparams(resource):    
    try: 
        if resource == 'media':

            islive_list = [player.isLifeStreamingOn(0),
                player.isLifeStreamingOn(1),
                player.isLifeStreamingOn(2),
                player.isLifeStreamingOn(3)]
        
            fps_list = [0,0,0,0]
            loss_list = [0,0,0,0]
            
            index=0
            for item in islive_list:
                if item:
                    fps_list[index] = player.getFPS(str(players_list[index]))
                    loss_list[index] = player.getLoss(str(players_list[index]))
                index = index+1
                
            return jsonify(fps1=fps_list[0],loss1=loss_list[0],
                fps2=fps_list[1],loss2=loss_list[1],
                fps3=fps_list[2],loss3=loss_list[2],
                fps4=fps_list[3],loss4=loss_list[3])
         
        if resource == 'network':
            if player.isConnected():
                return jsonify(band=player.getBand(),rtt=player.getRTT())
            else:
                return jsonify(band=0,rtt=0)
    except:
        return jsonify(result="error")       
    return "Ok"
        
# --- UG - streamer -----------------------------------
@app.route("/startstreamer/<nr>")
@crossdomain(origin='*')
def startstreamer(nr):    
    streamer = streamer_list[int(nr)]
    if not streamer.isAlive():
        streamer.start()
    else:
        streamer.connect()   
    return jsonify(status=SUCCESS_CODE_STREAM_STARTED) 

@app.route("/stopstreamer/<nr>")
@crossdomain(origin='*')
def stopstreamer(nr):    
    streamer = streamer_list[int(nr)]
    if streamer.isAlive():
        streamer.stop()
    return jsonify(status=SUCCESS_CODE_STREAM_STOPED)   

@app.route("/streamerstatus")
@crossdomain(origin='*')
def streamerstatus():    
    status = []
    for streamer in streamer_list:
        status.append(streamer.isConnected())
    return jsonify(result=status)  
    
#---- Network application (HQmon)------------------------- 
@app.route("/networkapplication/<action>")
@crossdomain(origin='*')
def networkapplication(action):    
    if net_app.isAlive():
        if action=="HQmonOn":            
            net_app.enableHQmon()
        else:
            net_app.disableHQmon()         
    return jsonify(result="HQmon started")  

@app.route("/HQmonstatus")
def HQmonstatus():    
    if net_app.isAlive():
        status = net_app.getStatus()
        return jsonify(**status)     
    
#---------------------------------------------------------# 
if __name__ == "__main__":
    
    net_app.start()
    rate_limiter.start()
    
    #may break by ctrl+c    
    try:
                    
        # Wait forever, so we can receive KeyboardInterrupt.
        while True:
            time.sleep(1)
                 
    except (KeyboardInterrupt, SystemExit):
        print "FELIX : ^C received"
            
        if player.isAlive():
            player.stop()  

        for streamer in streamer_list:
            if streamer.isAlive():
                streamer.stop()                  

        if ryu_controller.isAlive():
            ryu_controller.stop()  

        if rate_limiter.isAlive():
            rate_limiter.stop()
        
        if net_app.isAlive():
            net_app.stop()            
        
        if flask_app.isAlive():
            flask_app.stop()  
        
        import os, signal
        os._exit(1)        
        pid = os.getpid()
        os.kill(pid, signal.SIGTERM)
       
    # We never get here.
    raise RuntimeError, "not reached"
#---------------------------------------------------------#  