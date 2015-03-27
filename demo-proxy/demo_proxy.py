#!/usr/bin/python

# Copyright (C) 2015 PSNC
# Lukasz Ogrodowczyk (PSNC) <lukaszog_at_man.poznan.pl>

import os, paramiko, time, sys, threading, socket, datetime
from flask import Flask,jsonify, render_template, request
import requests

uv_streamer = [
    {'name':'streamer1', 'command':'/home/felix/UltraGrid/ultragrid/bin/uv --playback POT_PRZYRODA_20Mbps -P 2222 192.168.1.200','hostIP':'127.0.0.1','username':'felix','password':'pcss'},
    {'name':'streamer2', 'command':'/home/felix/UltraGrid/ultragrid/bin/uv --playback POT_PRZYRODA_20Mbps -P 4444 192.168.2.200','hostIP':'127.0.0.1','username':'felix','password':'pcss'},
    {'name':'streamer3', 'command':'/home/felix/UltraGrid/ultragrid/bin/uv --playback POT_PRZYRODA_20Mbps -P 6666 192.168.3.200','hostIP':'127.0.0.1','username':'felix','password':'pcss'},
    {'name':'streamer4', 'command':'/home/felix/UltraGrid/ultragrid/bin/uv --playback POT_PRZYRODA_20Mbps -P 8888 192.168.4.200','hostIP':'127.0.0.1','username':'felix','password':'pcss'}]

uv_player = {
    'hostIP':'10.0.0.2',
    'username':'player',
    'password':'pcss',
    'command_p1':'DISPLAY=:0.1 /home/player/ultragrid/bin/uv -d sdl -P 2222',
    'command_p2':'DISPLAY=:0.2 /home/player/ultragrid/bin/uv -d sdl -P 4444',
    'command_p3':'DISPLAY=:0.3 /home/player/ultragrid/bin/uv -d sdl -P 6666',
    'command_p4':'DISPLAY=:0.4 /home/player/ultragrid/bin/uv -d sdl -P 8888',
    'command_ifstat':'ifstat -i eth1 -b',
    'command_ping':'ping 10.0.0.10'}
    
ryu_controller_config = {
    'hostIP':'10.134.0.236',
    'username':'felix',
    'password':'pcss',
    'command_ryu':'PYTHONPATH=/home/felix/ryu /home/felix/ryu/bin/ryu-manager --verbose /home/felix/ryu/ryu/app/ofctl_rest.py'}    
       
app = Flask(__name__)

#---------------------------------------------------------#
class RyuController(threading.Thread):
    def __init__(self, ryuparam):
        threading.Thread.__init__(self)
        self.connected=False
        self.ryuparam=ryuparam
        
    def run(self):
        self.connect()
        while 1:
            while self.connected: 
                try:
                    self.getFlows()
                except:
                    None
                time.sleep(1)
            print "Ryu is dead? :("       
            time.sleep(1)
            
    def connect(self):       
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.ryuparam['hostIP'], timeout=60, username=self.ryuparam['username'], password=self.ryuparam['password'])
            print "Connection with Ryu controller established"
        except:  
            return
        try:    
            self.channel = self.ssh.get_transport().open_session()
            self.channel.get_pty()
            self.channel.exec_command(self.ryuparam['command_ryu'])    
            print "SSH channel created with Ryu"
        except:  
            return
        self.connected = True
     
    def isConnected(self):
        return self.connected   

    def getFlows(self):
        response = requests.get('http://10.134.0.236:8080/stats/flow/9354246419888',
                         auth=(self.ryuparam['username'], self.ryuparam['password']))  
        print response.json()
        
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
            self.ssh.connect(self.uvparam['hostIP'], timeout=60, username=self.uvparam['username'], password=self.uvparam['password'])
            print "Connection with player %s established"%(self.uvparam['name'])
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
                except:
                    None
                
                # --- channel_p2 (UltraGrid) ---
                try:
                    trace = self.channel_p2.recv(4096)
                    if ('[SDL]' in trace)and('FPS' in trace):
                        self.params['player2']['fps']=float(((trace.split('=')[1]).split('FPS')[0]).strip())
                    if ('packets expected' in trace)and('%' in trace):
                        self.params['player2']['loss']=100-float((((trace.split('(')[1]).split(')')[0]).split('%')[0]).strip())
                except:
                    None                
                
                # --- channel_p3 (UltraGrid) ---
                try:
                    trace = self.channel_p3.recv(4096)
                    if ('[SDL]' in trace)and('FPS' in trace):
                        self.params['player3']['fps']=float(((trace.split('=')[1]).split('FPS')[0]).strip())
                    if ('packets expected' in trace)and('%' in trace):
                        self.params['player3']['loss']=100-float((((trace.split('(')[1]).split(')')[0]).split('%')[0]).strip())
                except:
                    None
                    
                # --- channel_p4 (UltraGrid) ---
                try:
                    trace = self.channel_p4.recv(4096)
                    if ('[SDL]' in trace)and('FPS' in trace):
                        self.params['player4']['fps']=float(((trace.split('=')[1]).split('FPS')[0]).strip())
                    if ('packets expected' in trace)and('%' in trace):
                        self.params['player4']['loss']=100-float((((trace.split('(')[1]).split(')')[0]).split('%')[0]).strip())
                except:
                    None
                    
                time.sleep(1) 

            print "No connection to the Player? :("      
            time.sleep(1)
            
    def connect(self):       
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
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
@app.route("/")
def hello():
    return render_template('index.html')

@app.route("/startryucontroller")
def startryucontroller():  
    if not ryu_controller.isAlive():
        ryu_controller.start()
    else:
        ryu_controller.connect()
    return "Ok"
    
@app.route("/startplayers")
def startplayers():  
    if not player.isAlive():
        player.start()
    else:
        player.connect()
    return "Ok"
    
@app.route("/stopplayers")
def stopplayers():
    if player.isAlive():
        player.stop()       
    return "Ok"
  
@app.route('/playerstatus')
def playerstatus():
    status="Unknown"
    try:
        if player.isAlive():
            if player.isConnected():
                status="alive: connected"
            else:
                status="alive: not connected"
        else:
            status="not alive"
        return jsonify(player=status)
    except:
        return jsonify(result="error")  
  
@app.route("/startstreamer/<nr>")
def startstreamer(nr):    
    streamer = streamer_list[int(nr)]
    if not streamer.isAlive():
        streamer.start()
    else:
        streamer.connect()   
    return "Ok"  

@app.route("/playerparams/<resource>")
def playerparams(resource):    
    try: 
        if resource == 'media':
            return jsonify(fps1=player.getFPS('player1'),loss1=player.getLoss('player1'),
            fps2=player.getFPS('player2'),loss2=player.getLoss('player2'),
            fps3=player.getFPS('player3'),loss3=player.getLoss('player3'),
            fps4=player.getFPS('player4'),loss4=player.getLoss('player4'))
        if resource == 'network':
            return jsonify(band=player.getBand(),rtt=player.getRTT())
    except:
        return jsonify(result="error")       
    return "Ok"
   
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

                
        import os, signal
        os._exit(1)        
        pid = os.getpid()
        os.kill(pid, signal.SIGTERM)
       
    # We never get here.
    raise RuntimeError, "not reached"
#---------------------------------------------------------#  