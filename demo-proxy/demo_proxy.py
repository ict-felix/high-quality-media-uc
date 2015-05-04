#!/usr/bin/python

# Copyright (C) 2015 PSNC
# Lukasz Ogrodowczyk (PSNC) <lukaszog_at_man.poznan.pl>

import os, paramiko, time, sys, threading, socket, datetime
from flask import Flask,jsonify, render_template, request
import requests, json

player_IP = {
    1:'150.254.173.135',
    2:'150.254.173.135',
    3:'150.254.173.135',
    4:'150.254.173.135'
}

uv_streamer = [
    {'name':'streamer1', 'command':'/home/okazaki/ultragrid/bin/uv --playback /home/okazaki/Videos/POT_PRZYRODA_200Mbps -P 2222 '+player_IP[1],'hostIP':'163.220.30.135','username':'lukaszog','password':''},
    {'name':'streamer2', 'command':'/home/okazaki/ultragrid/bin/uv --playback /home/okazaki/Videos/TEARS_OF_STEEL_200Mbps -P 4444 '+player_IP[2],'hostIP':'163.220.30.135','username':'lukaszog','password':''},
    {'name':'streamer3', 'command':'/home/okazaki/ultragrid/bin/uv --playback /home/okazaki/Videos/POT_PRZYRODA_200Mbps -P 6666 '+player_IP[3],'hostIP':'163.220.30.135','username':'lukaszog','password':''},
    {'name':'streamer4', 'command':'/home/okazaki/ultragrid/bin/uv --playback /home/okazaki/Videos/POT_PRZYRODA_200Mbps -P 8888 '+player_IP[4],'hostIP':'163.220.30.135','username':'lukaszog','password':''}]
#    {'name':'streamer2', 'command':'/home/felix/UltraGrid/ultragrid/bin/uv --playback POT_PRZYRODA_20Mbps -P 4444 192.168.2.200','hostIP':'127.0.0.1','username':'felix','password':'pcss'},
#    {'name':'streamer3', 'command':'/home/felix/UltraGrid/ultragrid/bin/uv --playback POT_PRZYRODA_20Mbps -P 6666 192.168.3.200','hostIP':'127.0.0.1','username':'felix','password':'pcss'},
#    {'name':'streamer4', 'command':'/home/felix/UltraGrid/ultragrid/bin/uv --playback POT_PRZYRODA_20Mbps -P 8888 192.168.4.200','hostIP':'127.0.0.1','username':'felix','password':'pcss'}]

uv_player = {
    'hostIP':'150.254.173.135',
    'username':'player',
    'password':'',
    'command_p1':'DISPLAY=:0.1 /home/player/ultragrid/bin/uv -d sdl -P 2222',
    'command_p2':'DISPLAY=:0.2 /home/player/ultragrid/bin/uv -d sdl -P 4444',
    'command_p3':'DISPLAY=:0.3 /home/player/ultragrid/bin/uv -d sdl -P 6666',
    'command_p4':'DISPLAY=:0.4 /home/player/ultragrid/bin/uv -d sdl -P 8888',
    'command_ifstat':'ifstat -i eth0 -b',
    'command_ping':'ping 163.220.30.135'}
    
ryu_controller_config = {
    'hostIP':'127.0.0.1',
    'username':'felix',
    'password':'!Pcss 4.12',
    'command_ryu':'PYTHONPATH=/home/felix/felix-demo-tools/ryu /home/felix/felix-demo-tools/ryu/bin/ryu-manager --verbose /home/felix/felix-demo-tools/ryu/ryu/app/ofctl_rest.py',
    'openflow_path':{
        1:[
            # --- AIST
            # --- KDDI
            # --- PSNC
            {'dpid':0x00000881f488f5b0, 'in_port':'28', 'ip_dst':'1.2.3.4', 'out_port':'29'},
            {'dpid':0x00000881f488f5b0, 'in_port':'28', 'ip_dst':'10.10.10.10', 'out_port':'29'},
            # --- PSNC (Mininet test):
            {'dpid':0x0000000000000001, 'in_port':'1', 'ip_dst':'7.7.7.7', 'out_port':'2'}
            
            
            # --- iMinds
            # --- i2cat            
        ],
        2:[
            # --- AIST
            # --- KDDI
            # --- PSNC
            
            # --- PSNC (Mininet test):
            {'dpid':0x0000000000000001, 'in_port':'1', 'ip_dst':'8.8.8.8', 'out_port':'2'}            
            
            # --- iMinds
            # --- i2cat
        ]
    },
    'of_sw_list' : [
        # PSNC
        0x00000881f488f5b0, 0x0000000000000001]
    
}    

rate_limiter_config = {
    'hostIP':'163.220.30.135',
    'username':'lukaszog',
    'password':'',
    'service_session_list':[
        {'bandwidth': '200mbit', 'destination': '1.1.1.1', 'id':''},
        {'bandwidth': '400mbit', 'destination': '2.2.2.2', 'id':''},
        {'bandwidth': '600mbit', 'destination': '3.3.3.3', 'id':''},
        {'bandwidth': '800mbit', 'destination': '4.4.4.4', 'id':''}
    ]
}    
    
app = Flask(__name__)

#---------------------------------------------------------#
class RyuController(threading.Thread):
    def __init__(self, ryuparam):
        threading.Thread.__init__(self)
        self.connected=False
        self.ryuparam=ryuparam
        self.of_flows={}
    def run(self):
        self.connect()
        while 1:
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
                self.addFlow(flow['dpid'],flow['in_port'],flow['ip_dst'],flow['out_port'])

    def delPath(self, path_number):
        if path_number in self.ryuparam['openflow_path']:
            for flow in self.ryuparam['openflow_path'][path_number]:
                self.delFlow(flow['dpid'],flow['in_port'],flow['ip_dst'],flow['out_port'])
                
    def isConnected(self):
        return self.connected   

    def getFlows(self):
        flows = {}
        for of_sw in self.ryuparam['of_sw_list']:
            response = requests.get('http://localhost:8080/stats/flow/'+str(of_sw))
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
                "idle_timeout":60,
                "hard_timeout":60,
                "priority":3,
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
    
    def delFlow(self, dpid, in_port, ip_dst, out_port):
        eth_type_list = [0x800, 0x806]
        for eth_type in eth_type_list:
            payload = {
                "dpid":dpid,
                "cookie":1,
                "cookie_mask":1,
                "table_id":0,
                "idle_timeout":60,
                "hard_timeout":60,
                "priority":3,
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
                
    def stop(self):        
        if self.connected:
            print "Ryu Controller stopping"
            self.ssh.close()  
            self.channel.close() 
            self.connected=False
            print "Ryu Controller stopped"
#---------------------------------------------------------#

ryu_controller = RyuController(ryu_controller_config)

#---------------------------------------------------------#
class UGstreamer(threading.Thread):
    def __init__(self, uvparam):
        threading.Thread.__init__(self)
        self.connected=False
        self.uvparam=uvparam
        
    def run(self):
        self.connect()
        while 1:
            while self.connected:
                #print "Streamer %s connected :)\n"%(self.uvparam['name'])   
                time.sleep(1)
            print "Streamer %s is dead? :(\n"%(self.uvparam['name'])            
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
            return
        try:    
            self.channel = self.ssh.get_transport().open_session()
            self.channel.get_pty()
            self.channel.exec_command(self.uvparam['command'])    
            print "SSH channel created with %s"%(self.uvparam['name'])
        except:  
            return
        self.connected = True
     
    def isConnected(self):
        return self.connected          
        
    def stop(self):        
        if self.connected:
            print "Streamer %s stopping"%self.uvparam['name']
            self.ssh.close()  
            self.channel.close() 
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
        while 1:
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
                        self.params['player1']['fps']=float(((trace.split('=')[1]).split('FPS')[0]).strip())
                    if ('packets expected' in trace)and('%' in trace):
                        self.params['player1']['loss']=100-float((((trace.split('(')[1]).split(')')[0]).split('%')[0]).strip())
                    
                    if (('[SDL]' in trace)or('FPS' in trace)or('packets expected' in trace)or('%' in trace))and(self.livestreaming_cntr[0] <= self.livestreaming_cntr_on):
                        self.livestreaming_cntr[0] = self.livestreaming_cntr_on 

                except:
                    if self.livestreaming_cntr[0] > 0:                        
                        self.livestreaming_cntr[0]=self.livestreaming_cntr[0]-1
                
                # --- channel_p2 (UltraGrid) ---
                try:
                    trace = self.channel_p2.recv(4096)
                    if ('[SDL]' in trace)and('FPS' in trace):
                        self.params['player2']['fps']=float(((trace.split('=')[1]).split('FPS')[0]).strip())
                    if ('packets expected' in trace)and('%' in trace):
                        self.params['player2']['loss']=100-float((((trace.split('(')[1]).split(')')[0]).split('%')[0]).strip())
                        
                    if (('[SDL]' in trace)or('FPS' in trace)or('packets expected' in trace)or('%' in trace))and(self.livestreaming_cntr[1] <= self.livestreaming_cntr_on):
                        self.livestreaming_cntr[1] = self.livestreaming_cntr_on 
                except:
                    if self.livestreaming_cntr[1] > 0:                        
                        self.livestreaming_cntr[1]=self.livestreaming_cntr[1]-1              
                
                # --- channel_p3 (UltraGrid) ---
                try:
                    trace = self.channel_p3.recv(4096)
                    if ('[SDL]' in trace)and('FPS' in trace):
                        self.params['player3']['fps']=float(((trace.split('=')[1]).split('FPS')[0]).strip())
                    if ('packets expected' in trace)and('%' in trace):
                        self.params['player3']['loss']=100-float((((trace.split('(')[1]).split(')')[0]).split('%')[0]).strip())
                   
                    if (('[SDL]' in trace)or('FPS' in trace)or('packets expected' in trace)or('%' in trace))and(self.livestreaming_cntr[2] <= self.livestreaming_cntr_on):
                        self.livestreaming_cntr[2] = self.livestreaming_cntr_on                         
                except:
                    if self.livestreaming_cntr[2] > 0:                        
                        self.livestreaming_cntr[2]=self.livestreaming_cntr[2]-1
                    
                # --- channel_p4 (UltraGrid) ---
                try:
                    trace = self.channel_p4.recv(4096)
                    if ('[SDL]' in trace)and('FPS' in trace):
                        self.params['player4']['fps']=float(((trace.split('=')[1]).split('FPS')[0]).strip())
                    if ('packets expected' in trace)and('%' in trace):
                        self.params['player4']['loss']=100-float((((trace.split('(')[1]).split(')')[0]).split('%')[0]).strip())
                    
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
        print "Map of on-line streaming cntr: %s"%(self.livestreaming_cntr)
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
        
    def run(self):
        self.connect()
        while 1:
            while self.connected: 
                try:
                    trace = self.channel.recv(4096)
                    print trace
                except:
                    None
                          
                time.sleep(1)
            print "RL is dead? :("       
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
        
    def createServiceSessions(self):
        print "Rate Limiter: Creation of service session..."
        for service_session in self.ratelimiterparam['service_session_list']:
            payload = {'bandwidth':service_session['bandwidth'], 'destination':service_session['destination']}
            print payload
            r = requests.post("http://163.220.30.135:8000/flows/", data=payload, auth=('lukaszog','poznanpl'))            
            print "Status:%s | Response:%s"%(r.status_code, r.json())       
            if r.status_code == 201:
                service_session['id'] = "%s"%r.json()['id']

    def getStatusofRL(self): 
        r = requests.get("http://163.220.30.135:8000/flows/", auth=('lukaszog','poznanpl')) 
        return r.json()[0]
            
    def getServiceSession(self,number):
        print "Rate Limiter: getting Service Session..."
        r = requests.get("http://163.220.30.135:8000/flows/%s/"%(number), auth=('lukaszog','poznanpl'))
        print "Status:%s | Response:%s"%(r.status_code, r.json())        

    def deleteAllServiceSessions(self):     
        print "Rate Limiter: Delete ALL service session..."
        for service_session in self.ratelimiterparam['service_session_list']:
            if service_session['id'] != '': 
                self.deleteServiceSession(int(service_session['id']))
        
    def deleteServiceSession(self,number):
        print "Rate Limiter: deleting ServiceSession..."
        r = requests.delete("http://163.220.30.135:8000/flows/%s/"%(number), auth=('lukaszog','poznanpl'))
        print "Status:%s | Response:%s"%(r.status_code, r.json())     
        
    def stop(self):        
        if self.connected:
            print "RL stopping"
            self.ssh.close()  
            self.channel.close() 
            self.connected=False
            print "RL stopped"
#---------------------------------------------------------#

rate_limiter = RateLimiter(rate_limiter_config)

#--- Admin Panel -----------------------------------------#      
@app.route("/demo_proxy_admin_panel")
def hello():
    return render_template('index.html')

# --- OpenFlow Controller - Ryu ---------------------------
@app.route("/startryucontroller")
def startryucontroller():  
    if not ryu_controller.isAlive():
        ryu_controller.start()
    else:
        ryu_controller.connect()
    return "Ok"
    
@app.route("/getryustatus")
def getryustatus():  
    return jsonify(result=ryu_controller.isConnected())
    
@app.route("/setpath/<nr>")
def setpath(nr):    
    if ryu_controller.isAlive():
        ryu_controller.setPath(int(nr))
    return "Ok"  

@app.route("/delpath/<nr>")
def delpath(nr):    
    if ryu_controller.isAlive():
        ryu_controller.delPath(int(nr))
    return "Ok"  
    
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
        return jsonify(connected_OF_SW=of_sw_hex_list)
    return "Ok"  

# --- RL: --------------------------------------------
@app.route("/startratelimiter")
def startratelimiter():  
    if not rate_limiter.isAlive():
        rate_limiter.start()
    else:
        rate_limiter.connect()
    return "Ok" 
    
@app.route("/setband/<band>")
def setband(band):    
    if rate_limiter.isAlive():
        rate_limiter.setBand(int(band))
    return "Ok"  
    
@app.route("/createrlservicesessions")
def createrlservicesessions():  
    if rate_limiter.isAlive():
        rate_limiter.createServiceSessions()
    return "Ok"     

@app.route("/deleteallrlservicesessions")
def deleteallrlservicesessions():  
    if rate_limiter.isAlive():
        rate_limiter.deleteAllServiceSessions()
    return "Ok"         
    
@app.route("/getstatusofratelimiter")
def getstatusofratelimiter():  
    if rate_limiter.isAlive():     
        rl_status = rate_limiter.getStatusofRL()
        return jsonify(**rl_status)
    return "Ok" 

# --- Players: ------------------------------------------   
@app.route("/startplayers")
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
    return "Ok"
    
@app.route("/stopplayers")
def stopplayers():
    '''
    To stop UG-player
    '''
    if player.isAlive():
        player.stop()       
    return "Ok"
  
@app.route('/playerstatus')
def playerstatus():
    '''
    To check if channel with UG-player is established
    '''
    return jsonify(isconnected=player.isConnected(), islive_1=player.isLifeStreamingOn(0),islive_2=player.isLifeStreamingOn(1),islive_3=player.isLifeStreamingOn(2),islive_4=player.isLifeStreamingOn(3))

@app.route("/playerparams/<resource>")
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
def startstreamer(nr):    
    streamer = streamer_list[int(nr)]
    if not streamer.isAlive():
        streamer.start()
    else:
        streamer.connect()   
    return "Ok"  

@app.route("/stopstreamer/<nr>")
def stopstreamer(nr):    
    streamer = streamer_list[int(nr)]
    if streamer.isAlive():
        streamer.stop()
    return "Ok"    

@app.route("/streamerstatus")
def streamerstatus():    
    status = []
    for streamer in streamer_list:
        status.append(streamer.isConnected())
    return jsonify(result=status)  
#---------------------------------------------------------#  
if __name__ == "__main__":
    
    print "Starting flask service"
    app.run("0.0.0.0")
 
    #may break by ctrl+c    
    try:
                   
        # Wait forever, so we can receive KeyboardInterrupt.
        while True:
            time.sleep(1)
                 
    except (KeyboardInterrupt, SystemExit):
        print "^C received"
      
        if player.isAlive():
            player.stop()  

        for streamer in streamer_list:
            if streamer.isAlive():
                streamer.stop()                  

        if ryu_controller.isAlive():
            ryu_controller.stop()  

        if rate_limiter.isAlive():
            rate_limiter.stop()
              
        import os, signal
        os._exit(1)        
        pid = os.getpid()
        os.kill(pid, signal.SIGTERM)
       
    # We never get here.
    raise RuntimeError, "not reached"
#---------------------------------------------------------#  