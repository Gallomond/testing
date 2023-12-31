# -*- Mode: python; py-indent-offset: 4; indent-tabs-mode: nil; coding: utf-8; -*-

from enum import Enum
import socket
import sys
import time

from .common import *
from .packet import Packet
from .cwnd_control import CwndControl
from .util import *

class State(Enum):
    INVALID = 0
    SYN = 1
    OPEN = 3
    LISTEN = 4
    FIN = 10
    FIN_WAIT = 11
    CLOSED = 20
    ERROR = 21

# class TimeoutError:
#     pass

MAX_SEQ_NUM = 50000
class Socket:
    '''Incomplete socket abstraction for Confundo protocol'''

    def __init__(self, connId=0, inSeq=None, synReceived=False, sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM), noClose=False):
        self.sock = sock
        self.connId = connId
        self.sock.settimeout(0.5)
        self.timeout = 10

        self.base = 50000
        self.seqNum = self.base

        self.inSeq = inSeq

        self.lastAckTime = time.time() # last time ACK was sent / activity timer
        self.cc = CwndControl()
        self.outBuffer = b""
        self.inBuffer = b""
        self.state = State.INVALID
        self.nDupAcks = 0

        self.synReceived = synReceived
        self.finReceived = False

        self.remote = None
        self.noClose = noClose
        
        self.cwnd = 412
        self.ssthresh = 12000
        self.dupAckThreshold = 3

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if self.state == State.OPEN:
            self.close()
        if self.noClose:
            return
        self.sock.close()

    def connect(self, endpoint):
        remote = socket.getaddrinfo(endpoint[0], endpoint[1], family=socket.AF_INET, type=socket.SOCK_DGRAM)
        (family, type, proto, canonname, sockaddr) = remote[0]

        return self._connect(sockaddr)

    def bind(self, endpoint):
        if self.state != State.INVALID:
            raise RuntimeError()

        remote = socket.getaddrinfo(endpoint[0], endpoint[1], family=socket.AF_INET, type=socket.SOCK_DGRAM)
        (family, type, proto, canonname, sockaddr) = remote[0]

        self.sock.bind(sockaddr)
        self.state = State.LISTEN

    def listen(self, queue):
        if self.state != State.LISTEN:
            raise RuntimeError("Cannot listen")
        pass

    def accept(self):
        if self.state != State.LISTEN:
            raise RuntimeError("Cannot accept")

        hadNewConnId = True
        while True:
            # just wait forever until a new connection arrives

            if hadNewConnId:
                self.connId += 1 # use it for counting incoming connections, no other uses really
                hadNewConnId = False
            pkt = self._recv()
            if pkt and pkt.isSyn:
                hadNewConnId = True
                ### UPDATE CORRECTLY HERE
                clientSock = Socket(connId = self.connId, synReceived=True, sock=self.sock, inSeq=0, noClose=True)
                # at this point, syn was received, ack for syn was sent, now need to send our SYN and wait for ACK
                clientSock._connect(self.lastFromAddr)
                return clientSock

    def settimeout(self, timeout):
        self.timeout = timeout

    def _send(self, packet):
        '''"Private" method to send packet out'''

        if self.remote:
            self.sock.sendto(packet.encode(), self.remote)
        else:
            self.sock.sendto(packet.encode(), self.lastFromAddr)
        print(format_line("SEND", packet, -1, -1))

    def _recv(self):
        '''"Private" method to receive incoming packets'''

        try:
            (inPacket, self.lastFromAddr) = self.sock.recvfrom(50000)
        except socket.error as e:
            return None

        ### TODO dispatch based on fromAddr... and it can only be done from the "parent" socket

        inPkt = Packet().decode(inPacket)
        #print(format_line("RECV", inPkt, -1, -1))
        print(f'RECV {inPkt.seqNum} {inPkt.ackNum} {inPkt.connId} {self.cc.cwnd} {self.cc.ss_thresh} {"ACK" if inPkt.isAck else ""} {"SYN" if inPkt.isSyn else ""} {"FIN" if inPkt.isFin else ""}')

        outPkt = None
        if inPkt.isSyn:
            ### UPDATE CORRECTLY HERE
            self.inSeq = 0
            if inPkt.connId != 0:
                self.connId = inPkt.connId
            self.synReceived = True

            outPkt = Packet(seqNum=self.seqNum, ackNum=self.inSeq, connId=self.connId, isAck=True)

        elif inPkt.isFin:
            if self.inSeq == inPkt.seqNum: # all previous packets has been received, so safe to advance
                ### UPDATE CORRECTLY HERE
                self.inSeq += 1
                self.finReceived = True
            else:
                # don't advance, which means we will send a duplicate ACK
                pass

            outPkt = Packet(seqNum=self.seqNum, ackNum=self.inSeq, connId=self.connId, isAck=True)

        elif len(inPkt.payload) > 0:
            if not self.synReceived:
                raise RuntimeError("Receiving data before SYN received")

            if self.finReceived:
                raise RuntimeError("Received data after getting FIN (incoming connection closed)")

            if self.inSeq == inPkt.seqNum: # all previous packets has been received, so safe to advance
                ### UPDATE CORRECTLY HERE
                self.inSeq += len(inPkt.payload)
                self.inBuffer += inPkt.payload
            else:
                # don't advance, which means we will send a duplicate ACK
                pass

            outPkt = Packet(seqNum=self.seqNum, ackNum=self.inSeq, connId=self.connId, isAck=True)

        if outPkt:
            self._send(outPkt)

        return inPkt

    def _connect(self, remote):
        self.remote = remote

        if self.state != State.INVALID:
            raise RuntimeError("Trying to connect, but socket is already opened")

        self.sendSynPacket()
        self.state = State.SYN

        self.expectSynAck()

    def close(self):
        if self.state != State.OPEN:
            raise RuntimeError("Trying to send FIN, but socket is not in OPEN state")

        self.sendFinPacket()
        self.state = State.FIN

        self.expectFinAck()

    def sendSynPacket(self):
        synPkt = Packet(seqNum=self.seqNum, connId=self.connId, isSyn=True)
        ### UPDATE CORRECTLY HERE
        self.seqNum = 5000
        if self.seqNum >= MAX_SEQ_NUM:
            self.seqNum = 0
        self._send(synPkt)

    def expectSynAck(self):
        ### MAY NEED FIXES IN THIS METHOD
        startTime = time.time()
        while True:
            pkt = self._recv()
            if pkt and pkt.isAck and pkt.ackNum == self.seqNum:
                self.base = self.seqNum
                self.state = State.OPEN
                
                # Send the final ACK packet in response to SYN-ACK
                ack_packet = Packet(seqNum=self.seqNum, ackNum=pkt.seqNum + 1, connId=self.connId, isAck=True)
                self._send(ack_packet)
            
                break
            if time.time() - startTime > GLOBAL_TIMEOUT:
                self.state = State.ERROR
                raise RuntimeError("timeout")

    def sendFinPacket(self):
        synPkt = Packet(seqNum=self.seqNum, connId=self.connId, isFin=True)
        ### UPDATE CORRECTLY HERE
        self.seqNum += 1
        if self.seqNum >= MAX_SEQ_NUM:
            self.seqNum = 0
        self._send(synPkt)

    def expectFinAck(self):
        ### MAY NEED FIXES IN THIS METHOD
        startTime = time.time()
        while True:
            pkt = self._recv()
            if pkt and pkt.isAck and pkt.ackNum == self.seqNum:
                self.base = self.seqNum
                self.state = State.CLOSED
                break
            if time.time() - startTime > GLOBAL_TIMEOUT:
                return

    def recv(self, maxSize):
        startTime = time.time()
        while len(self.inBuffer) == 0:
            self._recv()
            if self.finReceived:
                return None
            if time.time() - startTime > GLOBAL_TIMEOUT:
                self.state = State.ERROR
                raise RuntimeError("timeout")

        if len(self.inBuffer) > 0:
            actualResponseSize = min(len(self.inBuffer), maxSize)
            response = self.inBuffer[:actualResponseSize]
            self.inBuffer = self.inBuffer[actualResponseSize:]

            return response

    def send(self, data):
        '''
        This is one of the methods that require fixes.  Besides the marked place where you need
        to figure out proper updates (to make basic transfer work), this method is the place
        where you should initate congestion control operations.   You can either directly update cwnd, ssthresh,
        and anything else you need or use CwndControl class, up to you.  There isn't any skeleton code for the
        congestion control operations.  You would need to update things here and in `format_msg` calls
        in this file to properly print values.
        '''
    
        if self.remote:
            self.sock.sendto(pkt.encode(), self.remote)
        else:
            self.sock.sendto(pkt.encode(), self.lastFromAddr)
        
        if self.state != State.OPEN:
            raise RuntimeError("Trying to send FIN, but socket is not in OPEN state")

        self.outBuffer += data

        startTime = time.time()
        while len(self.outBuffer) > 0:  #and MTU >= len(self.outBuffer):
            toSend = self.outBuffer[:MTU]
            pkt = Packet(seqNum=self.base, connId=self.connId, payload=toSend)
            ### UPDATE CORRECTLY HERE
            self.seqNum += len(toSend)
            self._send(pkt)

            pkt = self._recv()  # if within RTO we didn't receive packets, things will be retransmitted
            if pkt and pkt.isAck:
                ### UPDATE CORRECTLY HERE
                advanceAmount = max(pkt.ackNum - self.base, 0)
                if advanceAmount == 0:
                    self.nDupAcks += 1
                else:
                    self.nDupAcks = 0
               
                endIndex = min(len(self.outBuffer), advanceAmount)
                self.outBuffer = self.outBuffer[endIndex:]
                ### UPDATE CORRECTLY HERE
                self.base = pkt.ackNum

            elif pkt and pkt.isDup:
                self.nDupAcks += 1
                if self.nDupAcks == self.dupAckThreshold:
                    # Fast retransmit
                    self.ssthresh = max(self.cwnd / 2, 2)
                    self.cwnd = self.ssthresh + 3
                    # Fast retransmit, so advance by 3 segments
                    advanceAmount = len(toSend) * 3
                    self.nDupAcks = 0
                    self.outBuffer = self.outBuffer[advanceAmount:]
                    # Update base for the next sequence number
                    self.base = self.seqNum  

            if time.time() - startTime > GLOBAL_TIMEOUT:
                self.state = State.ERROR
                raise RuntimeError("Timeout")

        print(f'SEND {pkt.seqNum} {pkt.ackNum} {pkt.connId} {self.cc.cwnd} {self.cc.ss_thresh} {"ACK" if pkt.isAck else ""} {"SYN" if pkt.isSyn else ""} {"FIN" if pkt.isFin else ""} {"DUP" if pkt.isDup else ""}')
        return len(data)