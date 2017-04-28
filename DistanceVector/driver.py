#!/usr/bin/python
"""""
@File:           driver.py
@Description:    This is the Driver running in the Distance Vector Routing
                 Protocol. This starts all nodes in their corresponding ip and ports
@Authors:        Arunkumar Bagavathi, Chetan Borse
@EMail:          abagavat@uncc.edu, chetanborse2106@gmail.com
@Created_on:     04/23/2017
@License         GNU General Public License
@python_version: 3.5.2
===============================================================================
"""

import os
import logging
import socket
import select
import struct

from sys import executable
from subprocess import Popen,CREATE_NEW_CONSOLE
from threading import Thread

from DistanceVector.router import Router

# Set logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s SENDER [%(levelname)s] %(message)s',)
log = logging.getLogger()


class DriverStartError(Exception):
    pass

class RouterStartError(Exception):
    pass

class FileNotExistError(Exception):
    pass

class RouterNotExistError(Exception):
    pass

class InvalidNetworkError(Exception):
    pass

class InvalidConfigurationError(Exception):
    pass

class SocketError(Exception):
    pass


class Driver(object):
    """
    Driver program to validate user's Routers setup and Configuration
    """

    def __init__(self,
                 filename="RouterNetwork.txt",
                 driverIP="127.0.0.1",
                 driverPort=8080,
                 www=os.path.join(os.getcwd(), "NetworkConf")):
        self.driverIP = driverIP
        self.driverPort = driverPort
        self.www = www
        self.filename = os.path.join(self.www,filename)

        self.routerInfoFilePath = {}
        self.routers={}
        self.routerIP={}
        self.routerPort={}


    def start(self):
        """
        Start the driver at specified/default IP and Port
        """
        log.info("Starting the Driver at IP Address:%s and in Port: %d ", self.driverIP,self.driverPort)

        try:
            self.routerSocket = socket.socket(socket.AF_INET,
                                              socket.SOCK_DGRAM)
            self.routerSocket.bind((self.driverIP, self.driverPort))
            self.routerSocket.setblocking(0)

            log.info("Driver successfully running at IP Address:%s and in Port: %d ", self.driverIP, self.driverPort)
        except Exception as e:
            log.error("Could not create UDP socket for driver")
            log.debug(e)
            raise DriverStartError("Driver instantiation failed at IP: %s in Port:%d"
                              % (self.driverIP, self.driverPort))


    def validateNetwork(self,distancesDirectory):
        # If file does not exist, terminate the program
        if not os.path.exists(self.filename):
            raise FileNotExistError("File does not exist!\nFilename: %s"
                                    % self.filename)
        else:
            with open(self.filename) as f:
                networkSetup = f.readlines()

                networkSetup = [line.strip() for line in networkSetup]

                log.info("Validating user's details about the routers from %s",self.filename)

                for router in range(len(networkSetup)):
                    routerInfo = networkSetup[router].split(',')
                    routerFilePath = os.path.join(distancesDirectory,routerInfo[0] + ".dat")

                    if not os.path.exists(routerFilePath):
                        raise RouterNotExistError("Router information of Router-'%s' does not exist in %s"
                                                  % (routerInfo[0], distancesDirectory))

                    # Checking if the given file contains IP address and Port number
                    elif len(routerInfo) == 3:
                        if routerInfo[1] in self.routerIP and routerInfo[2] in self.routerPort:
                            raise RouterStartError("Router %s can not be started in IP: %s at Port: %s! Because another router is running at the same address"
                                                          % (routerInfo[0], routerInfo[1],routerInfo[2]))
                        else:
                            self.routerIP[routerInfo[0]] = routerInfo[1]
                            self.routerPort[routerInfo[0]] = int(routerInfo[2])

                    # Assigning default values to IP and Port addresses
                    else:
                        log.info("IP or Port address of router '%s' are not specified. Assigning own IP and Port addresses...",routerInfo[0])

                        self.routerIP[routerInfo[0]] = "127.0.0.1"
                        if len(self.routerPort) == 0:
                            self.routerPort[routerInfo[0]] = self.routerPort + 1

                        else:
                            self.routerPort[routerInfo[0]] = self.routerPort[list(self.routerPort.keys())[-1]] + 1
                        log.info(
                            "IP Address: '%s' and Port: '%s' have been assigned to the router '%s'",
                            self.routerIP[routerInfo[0]],self.routerPort[routerInfo[0]],routerInfo[0])

                    self.routerInfoFilePath[routerInfo[0]] = routerFilePath
                    self.routers[routerInfo[0]] = str(router)

    # Starting all routers
    def startRouters(self):
        log.info("User details about the routers are valid")
        log.info("Starting routers at their specified address")

        routerDetails = "<ROUTER>".join(self.routers.keys())
        routerDetails = routerDetails + "<VAL>" + "<ID>".join(self.routers.values())

        for router in range(len(self.routers)):
            routerNeighbors = ""

            routerName = list(self.routers.keys())[router]
            routerIP = self.routerIP[routerName]
            routerPort = self.routerPort[routerName]
            routerInfoFilePath = self.routerInfoFilePath[routerName]

            with open(str(self.routerInfoFilePath[routerName])) as f:
                fileLines = f.readlines()

                for i in range(1,len(fileLines)):
                    neighborName = fileLines[i].split()[0]
                    neighborName = neighborName + "<VAL>" + self.routerIP[neighborName] + "<VAL>" + str(self.routerPort[neighborName])

                    routerNeighbors = routerNeighbors + neighborName + "<NEIGHBOR>"

            Popen([executable, 'DistanceVector/router.py', routerName,routerIP,str(routerPort),routerInfoFilePath,routerNeighbors,self.driverIP,str(self.driverPort),routerDetails], creationflags=CREATE_NEW_CONSOLE)

    # Function to initiate the thread
    def monitor(self):
        listen = MonitorRequests(self,self.routerSocket)
        listen.start()

    # Function to find router name from the given address
    def findRouterName(self, address):
        ip = address[0]
        port = address[1]

        for routerName,routerPort in self.routerPort.items():
            if routerPort == port:
                for routerName2,routerIP in self.routerIP.items():
                    if routerIP == ip:
                        return routerName
                        break
                    else:
                        continue


    # Function to close all running scripts
    def terminateAll(self):
        """
        CODE TO TERMINATE ALL THREADS AND DRIVER!
        """
        self.routerSocket.close()

# Thread to monitor shut down request from routers
class MonitorRequests(Thread):
    def __init__(self,driver,routerSocket):
        Thread.__init__(self)
        self.driver = driver
        self.routerSocket = routerSocket

    def run(self):
        """
        Start monitoring packet receipt.
        """
        log.info("Started to monitor requests from routers")

        while True:
            # Listen for incoming requests from routers infinitely
            ready = select.select([self.routerSocket], [], [])

            # Receive packet
            try:
                receivedPacket, senderAddress = self.routerSocket.recvfrom(2048)
            except Exception as e:
                log.error("Could not receive UDP packet!")
                log.debug(e)
                raise SocketError("Receiving UDP packet failed!")

            # Finding who sent the message
            whoSent = self.driver.findRouterName(senderAddress)
            log.info("New Message from the router '%s'",whoSent)

            # Parse header fields and payload data from the received packet
            data,datatype = self.parse(receivedPacket)

            if datatype == 0:
                self.routerSocket.close()
                # self.driver.terminateAll()


    def parse(self,packet):
        datatype = struct.unpack('=I', packet[0:4])[0]
        data = packet[4:]
        data = data.decode('utf-8')

        return data,datatype