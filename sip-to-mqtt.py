##
# Logging
##
import logging
logging.basicConfig(level=logging.INFO)
mylogger = logging.getLogger('sip-to-mqtt')
mylogger.setLevel(logging.INFO)

import json
import pprint
import os
import socket
import time
from datetime import datetime

import paho.mqtt.client as mqtt
from rtclite.app.sip.client import *
from rtclite import multitask

##
# MQTT
##
def on_mqtt_connect(client, userdata, flags, rc):
    global mylogger, service_status

    mylogger.debug("on_mqtt_connect: connected with result code: %s", str(rc))

    mylogger.debug("on_mqtt_connect: Reporting online")
    service_status['ts'] = int(time.mktime(datetime.now().timetuple()))
    client.publish(MQTT_STATUS_TOPIC, json.dumps(service_status))


def on_mqtt_message(client, userdata, msg):
    global mylogger

    mylogger.debug("on_mqtt_message: Received MQTT message:")
    mylogger.debug("%s: %s", msg.topic, str(msg.payload))


def updateMQTTStatusTask():
    global mylogger, mqttClient, service_status, sip_connected

    mylogger.debug("updateMQTTStatusTask: running...")

    while True:
        yield multitask.sleep(MQTT_STATUS_INTERVAL)
        mylogger.debug("updateMQTTStatusTask: pushing MQTT status")
        service_status['ts'] = int(time.mktime(datetime.now().timetuple()))
        mqttClient.publish(MQTT_STATUS_TOPIC, json.dumps(service_status))

##
# SIP
##
def sipSetupTask():
    global mylogger, myself, sip_connected

    mylogger.debug("sipSetupTask: running...")

    if sip_connected == False:
        SIP_INFO = '"sip-to-mqtt" <sip:'+SIP_USER+'@'+SIP_HOST+'>'
        mylogger.debug("sipSetupTask: Connecting as %s", SIP_INFO)
        result, reason = (yield myself.bind(SIP_INFO, username=SIP_USER, password=SIP_PASS, interval=3600, refresh=True, update=True))
        if result == 'failed':
            mylogger.critical('sipSetupTask: bind failed %s', reason)
        else:
            sip_connected = True


def sipLoopTask():
    global mqttClient, mylogger, myself, sip_connected

    mylogger.debug("sipLoopTask: running...")
    
    cmd, arg = (yield myself.recv())
    if cmd == 'connect':				  # incoming connect request
        mylogger.info("sipLoopTask: Incoming call from: %s", arg[0])
        mqttClient.publish(MQTT_RING_TOPIC, json.dumps({"msg":arg[0]}))
    else:
        mylogger.error('sipLoopTask: unknown/unhandled cmd: %s', cmd)
        mylogger.error('sipLoopTask: args: %s', arg)


##
# Main
##
if __name__ == "__main__":
    SIP_HOST = os.environ.get('SIP_HOST', 'sip1.example.com')
    SIP_USER = os.environ.get('SIP_USER', 'test')
    SIP_PASS = os.environ.get('SIP_PASS', 'test')
    MQTT_HOST = os.environ.get('MQTT_HOST', 'test.mosquitto.org')
    MQTT_PORT = int(os.environ.get('MQTT_PORT', 1883))
    MQTT_RING_TOPIC = os.environ.get('MQTT_RING_TOPIC', '/test/events/sip-to-mqtt/ring')
    MQTT_STATUS_TOPIC = os.environ.get('MQTT_STATUS_TOPIC', '/test/status/services/sip-to-mqtt')
    MQTT_STATUS_INTERVAL = int(os.environ.get('MQTT_STATUS_INTERVAL', 60))

    service_status = {"status": "online", "ts": 0}

    mqttClient = mqtt.Client()
    mqttClient.on_connect = on_mqtt_connect
    mqttClient.on_message = on_mqtt_message

    mylogger.debug("Connecting MQTT...")
    mqttClient.connect(MQTT_HOST, MQTT_PORT, 15)
    mqttClient.loop_start()

    mylogger.info("Setting up SIP sock...")
    sip_connected = False
    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 5060))
    myself = User(sock).start()

    multitask.add(sipSetupTask())
    multitask.add(sipLoopTask())
    multitask.add(updateMQTTStatusTask())

    mylogger.info("Entering loop...")
    while True:
        mylogger.debug("Entering loop...")
        multitask.run()
