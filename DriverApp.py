#!/usr/bin/python
"""""
@File:           DriverApp.py
@Description:    Driver Application to collect information about the
                 Routers Network Architecture
@Authors:        Arunkumar Bagavathi, Chetan Borse
@EMail:          abagavat@uncc.edu, chetanborse2106@gmail.com
@Created_on:     04/23/2017
@License         GNU General Public License
@python_version: 3.5.2
===============================================================================
"""

import os
import argparse

from DistanceVector.driver import Driver
from DistanceVector.driver import DriverStartError,RouterStartError
from DistanceVector.driver import InvalidNetworkError
from DistanceVector.driver import InvalidConfigurationError
from DistanceVector.driver import FileNotExistError,RouterNotExistError
from DistanceVector.driver import SocketError

def DriverApp(**args):
    # Arguments
    www = args["www"]
    filename = args["filename"]
    driver_ip = args["driver_ip"]
    driver_port = args["driver_port"]

    ddd = args["ddd"]

    try:
        driver = Driver(filename,driver_ip,driver_port,www)

        driver.start()
        driver.validateNetwork(ddd)
        driver.startRouters()
        driver.monitor()

    except KeyboardInterrupt as e:
        print("Keyboard Interruption detected...Stopping the simulation...")
        driver.terminateAll()
    except DriverStartError as e:
        print("Unexpected Exception in starting the driver!")
    except RouterStartError as e:
        print("Unexpected Exception in starting a router")
        print(e)
    except RouterNotExistError as e:
        print("Invalid Router Name")
        print(e)
    except InvalidNetworkError as e:
        print("Unexpected Exception in the given network. Please give proper network!")
    except InvalidConfigurationError as e:
        print(e)
    except SocketError as e:
        print("Unexpected exception in the socket")
        print(e)
    except FileNotExistError as e:
        print("Unexpected exception in Router network file!!")
        print(e)
    except Exception as e:
        print("Unexpected Exception!")
        print(e)


if __name__ == "__main__":
    # Argument parser
    parser = argparse.ArgumentParser(description='Distance Vector Routing Protocol Driver Program',
                                     prog='python \
                                           DriverApp.py \
                                           -f <filename> \
                                           -x <driver_ip> \
                                           -y <driver_port> \
                                           -i <ddd> \
                                           -d <www>')

    parser.add_argument("-f", "--filename", type=str, default="RouterNetwork.txt",
                        help="Routers Network Architecture, default: RouterNetwork.txt")
    parser.add_argument("-x", "--driver_ip", type=str, default="127.0.0.1",
                        help="Driver's IP, default: 127.0.0.1")
    parser.add_argument("-y", "--driver_port", type=int, default=8080,
                        help="Driver's Port, default: 8080")
    parser.add_argument("-d", "--www", type=str, default=os.path.join(os.getcwd(), "NetworkConf"),
                        help="Source folder for network configuration, default: /<Current Working Directory>/NetworkConf")
    parser.add_argument("-i", "--ddd", type=str, default=os.path.join(os.getcwd(), "InputDistances"),
                        help="Source folder for distance values between nodes, default: /<Current Working Directory>/InputDistances")

    # Read user inputs
    args = vars(parser.parse_args())

    # Run Client Application
    DriverApp(**args)
