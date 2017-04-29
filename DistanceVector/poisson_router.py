#!/usr/bin/python
"""""
@File:           poisson_router.py
@Description:    Router Application to execute Distance Vector Routing Protocol with Poisson Reverse feature
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
import sys
import select
import struct
import time

from threading import Thread
from copy import deepcopy


# Set logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s SENDER [%(levelname)s] %(message)s',)
log = logging.getLogger()


class RouterStartError(Exception):
    pass

class SocketError(Exception):
    pass

class Router(object):
    """
    Router program to execute the algorithm
    """

    def __init__(self,routerName,routerIP,routerPort,routerInfoFilePath,routerNeighbors,routerIDs):
        self.routerInfoFile = routerInfoFilePath
        self.routerIP = routerIP
        self.routerPort = int(routerPort)
        self.routerName = routerName
        # self.routerNeighbors = routerNeighbors
        # self.ids = routerIDs

        self.listenerFlag = False
        self.neighborDetails = {}
        self.routerIDs = {}
        self.poisonnedData = {}

        self.neighborDistances = {}
        self.routerDistances = []

        self.parseNeighbors(routerNeighbors)
        self.parseRouterIDs(routerIDs)
        self.fillRoutingTable()

        self.routerID = self.routerIDs[self.routerName]


    # Parsing the router neighbor details such as IP and Port
    def parseNeighbors(self,routerNeighbors):
        neighbors = routerNeighbors.split("<NEIGHBOR>")
        for i in range(len(neighbors) - 1):
            details = neighbors[i].split("<VAL>")
            self.neighborDetails[details[0]] = (details[1], int(details[2]))

    # Parsing router IDs
    def parseRouterIDs(self,ids):
        routers = ids.split("<VAL>")
        routerNames = routers[0].split("<ROUTER>")
        routerid = routers[1].split("<ID>")

        for id in routerid:
            self.routerIDs[routerNames[int(id)]] = int(id)

    # Initilizing the routing table with largest integer
    def fillRoutingTable(self):
        for i in range(len(self.routerIDs)):
            row = []
            for j in range(len(self.routerIDs)):
                if i == j:
                    row.append(0)
                else:
                    row.append(sys.maxsize)

            self.routerDistances.append(row)

    def open(self):
        """
        Create UDP socket for communication with the client.
        """
        log.info("Creating UDP socket at %s:%d for router '%s' to start the algorithm",
                 self.routerIP, self.routerPort,self.routerName)

        try:
            self.routerSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.routerSocket.bind((self.routerIP, self.routerPort))
            self.routerSocket.setblocking(0) # Setting a socket to non-blocking mode

            log.info("Router '%s' successfully running at IP Address:%s and in Port: %d ", self.routerName, self.routerIP, self.routerPort)
        except Exception as e:
            log.error("Could not create UDP socket for router '%s'",self.routerName)
            log.debug(e)
            raise RouterStartError("Creating UDP socket in %s:%d for router '%s' failed!"
                              % (self.routerIP, self.routerPort, self.routerName))

    # Function to start the router
    def execute(self):
        packetReceiver = PacketReceiver(self.routerName,self.neighborDetails,self.routerSocket,self)
        packetReceiver.start()

        # packetReceiver.join()

    # Function for the router to start sending some packet
    def sendPacket(self,receiverIP,receiverPort,data,datatype):
        packetSender =PacketSender(receiverIP,receiverPort,data,self.routerName,self.routerSocket,datatype)
        packetSender.start()

        # packetSender.join()

    def forceStop(self,driverIP,driverPort):
        self.sendPacket(driverIP,driverPort,"STOP_SIMULATION",0)
        log.info("Closing the connection in 2s....")
        time.sleep(2.0 - ((time.time() - starttime) % 2.0))
        self.closeConnection()

    # Function to close terminate the connection
    def closeConnection(self):
        self.routerSocket.close()

    def setListenerFlag(self,flag):
        self.listenerFlag = flag

    def getListenerFlag(self):
        return self.listenerFlag

    def calculateDistance(self,count):
        print()
        print("Output number %d" %count)

        oldVector = deepcopy(self.routerDistances[self.routerID])

        # Reading neighbor distances from the given file path and updating the routing table
        with open(self.routerInfoFile) as f:
            fileLines = f.readlines()

            for i in range(1, len(fileLines)):
                neighbors = fileLines[i].split()
                self.poisonnedData[neighbors[0]] = []
                self.neighborDistances[self.routerIDs[neighbors[0]]] = int(neighbors[1])
                self.routerDistances[self.routerID][self.routerIDs[neighbors[0]]] = int(neighbors[1])

        # Filling remaining distances as maximum value
        nonNeighborIDs = set(self.routerIDs.values()) - set(self.neighborDistances.keys())
        # print("Non neighbors of router %s : ")
        for id in nonNeighborIDs:
            if id != self.routerID:
                self.routerDistances[self.routerID][id] = sys.maxsize

        totalRouters = len(self.routerIDs)

        routerIDKeys = list(self.routerIDs.keys())
        routerIDValues = list(self.routerIDs.values())

        # 'i'  is the destination
        for i in range(totalRouters):
            destinationRouterName = routerIDKeys[routerIDValues.index(i)]
            minimumDist = sys.maxsize
            nextHopRouterName = ""

            # 'j' is the intermediate hop
            for j in range(totalRouters):
                distance = self.routerDistances[self.routerID][j] + self.routerDistances[j][i]

                if distance < minimumDist:
                    minimumDist = distance

                    if self.routerID == j:
                        nextHopRouterName = routerIDKeys[routerIDValues.index(i)]
                    else:
                        nextHopRouterName = routerIDKeys[routerIDValues.index(j)]

            if minimumDist == sys.maxsize:
                nextHopRouterName = ""

            print("Shortest Path '%s'-'%s': The next hop is '%s' and the cost is %s" %(self.routerName,destinationRouterName,nextHopRouterName,str(minimumDist)))

            # Determining at which position in the data to be set to infinity for a particular neighbor
            if destinationRouterName != nextHopRouterName:
                if nextHopRouterName in self.poisonnedData:
                    self.poisonnedData[nextHopRouterName].append(self.routerIDs[destinationRouterName])

            self.routerDistances[self.routerID][i] = minimumDist

        print()

        newVector = self.routerDistances[self.routerID]

        if count > 1 and set(oldVector) == set(newVector):
            print("Converged!!!")
        else:
            self.sendUpdate()

    # Initializing packet sending to other routers
    def sendUpdate(self):
        # data = ','.join(map(str,self.routerDistances[self.routerIDs[self.routerName]]))

        log.info("Temporarily stopping the router to listen incoming data")
        self.setListenerFlag(False)

        for neighbor in self.neighborDetails:
            toSend = deepcopy(self.routerDistances[self.routerIDs[self.routerName]])

            # Setting infinity to particular location
            if neighbor in self.poisonnedData:
                for poisson in self.poisonnedData[neighbor]:
                    toSend[poisson] = sys.maxsize

            data = ','.join(map(str,toSend))

            details = self.neighborDetails[neighbor]
            neighborIP = details[0]
            neighborPort = int(details[1])

            log.info("Sending %s to %s",data,neighbor)
            self.sendPacket(neighborIP,neighborPort,data,1)

        log.info("Starting the router to listen incoming data again!")
        self.setListenerFlag(True)

# Thread running to receive packets when they reach this router
class PacketReceiver(Thread):
    def __init__(self,routerName,neighborDetails,routerSocket,router):
        Thread.__init__(self)
        self.routerName = routerName
        self.neighborDetails = neighborDetails
        self.routerSocket = routerSocket
        self.router = router

    def run(self):
        """
        Start monitoring packet receipt.
        """
        log.info("Router '%s' is active now!", self.routerName)

        while True:

            if self.router.getListenerFlag() == True:
                # Listen for incoming requests from other routers indefinitely
                ready = select.select([self.routerSocket], [], [])

                # Receive packet
                try:
                    receivedPacket,senderAddress = self.routerSocket.recvfrom(512)
                except Exception as e:
                    log.error("Could not receive UDP packet!")
                    log.debug(e)
                    raise SocketError("Receiving UDP packet failed!")

                # Finding who sent the message
                for details in self.router.neighborDetails:
                    neighborIPPort = self.router.neighborDetails[details]

                    if neighborIPPort[0] == senderAddress[0] and neighborIPPort[1] == int(senderAddress[1]):
                        log.info("New Message from the router '%s'", details)
                        self.senderRouterName = details
                        break

                # Parse header fields and payload data from the received packet
                data, datatype = self.parse(receivedPacket)

                if datatype == 0:
                    self.routerSocket.close()
                if datatype == 1:
                    intData = [int(x) for x in data.split(',')]

                    log.info("Updating the routing table")
                    self.router.routerDistances[self.router.routerIDs[self.senderRouterName]] = intData

    # Parsing the received packet
    def parse(self, packet):
        datatype = struct.unpack('=I', packet[0:4])[0]
        data = packet[4:]
        data = data.decode('utf-8')

        return data, datatype


# Thread running to send packets to other routers or to Driver
class PacketSender(Thread):
    # packetSender =PacketSender(receiverIP,receiverPort,data,self.routerName,self.routerSocket,datatype)
    def __init__(self,receiverIP,receiverPort,data,routerName,routerSocket,datatype):
        Thread.__init__(self)
        self.receiverIP = receiverIP
        self.receiverPort = receiverPort
        self.data = data
        self.routerName = routerName
        self.routerSocket = routerSocket
        self.datatype = datatype

    def run(self):
        log.info("Transferring packet to the recipient")
        raw_packet = self.makePacket(self.datatype,self.data.encode('utf-8'))
        self.udt_send(raw_packet)

    def makePacket(self,datatype,data):
        packedDatatype = struct.pack("=I",datatype)
        rawPacket = packedDatatype + data
        return rawPacket

    def udt_send(self, packet):
        """
        Unreliable data transfer using UDP protocol.
        """
        try:
            self.routerSocket.sendto(packet, (self.receiverIP, self.receiverPort))
            log.info("Packet to %s:%d sent successfully!!!",self.receiverIP,self.receiverPort)

        except Exception as e:
            log.error("[%s] could not send UDP packet!", self.routerName)
            log.debug(e)
            raise SocketError("Sending UDP packet to %s:%d failed!"
                              % (self.receiverIP, self.receiverPort))


if __name__ == "__main__":
    driverIP = sys.argv[6]
    driverPort = int(sys.argv[7])

    router = Router(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[8])

    try:
        router.open()
        router.execute()

        starttime = time.time()
        i=0
        while True:
            i = i+1
            router.calculateDistance(i)
            time.sleep(15.0 - ((time.time() - starttime) % 15.0))

    except KeyboardInterrupt as e:
        log.info("Keyboard interruption detected")
        router.forceStop(driverIP,driverPort)
    except RouterStartError as e:
        print("Unexpected Error in starting the router!")
    except SocketError as e:
        print("Unexpected Exception in the socket")
        print(e)
    except Exception as e:
        print(e)


