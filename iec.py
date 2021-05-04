#!/usr/bin/env python3

import sys

IDLE = 0
SENDER_READY = 1
RX_READY = 2
ACTIVE = 3
WAIT_FOR_RX_ACK = 4
EOI_ACK = 5

active_count = 0
buffer = 0

state = IDLE
clk = 1
data = 0
atn = 0
eoi_counter = 0
byte_counter = 0
last_byte = False

def recv_byte():
    print("Got byte {:02x}".format(buffer))
    if atn == 1:
        if buffer == 0x3f:
            print("UNLISTEN")
        elif buffer == 0x5f:
            print("UNTALK")
        elif buffer & 0xf0 == 0xe0:
            print("CLOSE {}".format(buffer & 0xf))
        elif buffer & 0xf0 == 0xf0:
            print("OPEN {}".format(buffer & 0xf))
        elif (buffer >> 5) & 7 == 0x1:
            print("LISTEN {}".format(buffer & 0x1f))
        elif (buffer >> 5) & 7 == 0x2:
            print("TALK {}".format(buffer & 0x1f))
        elif (buffer >> 5) & 7 == 0x3:
            print("SECOND {}".format(buffer & 0x1f))

for l in sys.stdin.readlines():
    if not l:
        break
    l = l.strip()
    if not l:
        continue

    if "DD00 store" in l:
        #print(l)
        if "ATN" in l:
            if atn == 0:
                print("ATTN")
                state = SENDER_READY
            atn = 1
        else:
            if atn == 1:
                byte_counter = 0
                print("END OF ATTENTION")
                state = IDLE
            atn = 0

    if "DD00 read" in l or "1800 read" in l:
        #print(l)

        last_clk = clk
        last_data = data

        # VICE logging already inverts the DATA/CLK inputs
        if "CLK IN" in l:
            clk = 1
        else:
            clk = 0

        if "DATA IN" in l:
            data = 1
        else:
            data = 0

        if last_clk == 0 and clk == 1:
            if state == ACTIVE:
                active_count += 1
                if active_count == 8:
                    recv_byte()
                    byte_counter += 1
                    state = WAIT_FOR_RX_ACK
                    active_count = 0
                    buffer = 0
                else:
                    buffer >>= 1

            if state == RX_READY and data == 0:
                state = ACTIVE
                active_count = 0
                buffer = 0
        elif last_clk == 1 and clk == 0:
            if state == IDLE:
                state = SENDER_READY
            elif state == ACTIVE:
                if data == 0:
                    buffer |= 1 << 7

        if last_data == 1 and data == 0:
            if state == SENDER_READY and clk == 0:
                state = RX_READY
                eoi_counter = 0
        elif last_data == 0 and data == 1:
            if state == EOI_ACK:
                state = ACTIVE

        if state == WAIT_FOR_RX_ACK and data == 1:
            if last_byte:
                byte_counter = 0
            state = IDLE

        if state == RX_READY and data == 0 and clk == 0:
            eoi_counter += 1
            if eoi_counter >= 30:
                print("LAST BYTE")
                last_byte = True
                state = EOI_ACK

    #print("atn {} state {} active_count {} buffer {:02x}".format(atn, state, active_count, buffer))
    #print("clk {} data {} atn {} state {} active_count {}".format(clk, data, atn, state, active_count))
