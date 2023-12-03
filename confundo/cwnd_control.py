# -*- Mode: python; py-indent-offset: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# Copyright 2019 Alex Afanasyev

from .common import *

class CwndControl:
    '''Implementation of TCP Tahoe congestion control'''

    def __init__(self):
        self.cwnd = 1.0 * MTU
        self.ss_thresh = INIT_SSTHRESH

    def on_ack(self, ackedDataLen):
        # Slow start
        if self.cwnd < self.ss_thresh:
            self.cwnd += 412
        # Congestion avoidance
        elif self.cwnd >= self.ss_thresh:
            self.cwnd += (412 * 412) / self.cwnd

    def on_timeout(self):
        # Timeout handling
        self.ss_thresh = self.cwnd / 2
        self.cwnd = 412  # Set to the initial value
        # Retransmit data after the last acknowledged byte (not implemented here)

    def __str__(self):
        return f"cwnd:{self.cwnd} ss_thresh:{self.ss_thresh}"