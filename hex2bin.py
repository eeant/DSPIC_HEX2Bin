import numpy as np
import time
import io
import argparse
import sys
import os

def parse_hex(hex_file,memory):
    '''
    	Parses a hex file (provided as a list of strings) and copies its contents to a memory object.
    '''
    ext_address = 0
    for line in hex_file:
        #parse format
        byte_count = int(line[1:3],base=16)
        address = int(line[3:7],base=16)
        record_type = int(line[7:9],base=16)
        if(record_type==1):
            print ("EOF record")
        elif(record_type==4):
            print ("Extended address")
            ext_address = int(line[9:13],base=16)<<16
        elif(record_type==0):
            address = (ext_address+address)/2
            #for i in xrange(bytecount)
            #print( "data: %d bytes at address %d \t %.5x"%(byte_count,address,address))
            #instruction "==4bytes 00xxxxxx" per iteration 
            for i in range(int(byte_count/4)):
                cur_address = int(address+i*2)#addresses increase in steps of two
                opcode_little_endian = line[9+i*8:9+(i+1)*8]
                opcode = opcode_little_endian[6:8]+opcode_little_endian[4:6]+opcode_little_endian[2:4]+opcode_little_endian[0:2]
                opcode_num = int(opcode,base=16)
                print ("address: %.6x opcode: %.6x"%(cur_address,opcode_num))
                memory.write(cur_address,(0,(opcode_num>>16)&0xFF,(opcode_num>>8)&0xFF,opcode_num&0xFF))

def load_hex_file(file_name):
    '''
    	Opens a hex file and loads its contents into a list.
    '''
    f = open(file_name,'rb')
    hex_file = [l for l in f]
    f.close()
    return hex_file

class pic_memory(object):
    def __init__(self,num_pages=171):
        self.data = np.zeros((num_pages*1024,4),dtype=np.uint8) #just one big continuous chunk of memory. Note that addresses increase in steps of two
        self.data[::] = 0xFFFF
        self.tags = np.zeros(num_pages,dtype=np.uint8) #0 = empty, 1 = dirty program memory       
    def write(self, address, data):#data is assumed to be in the format phantombyte(0) 23..16 15..8 7..0
        '''
        	Stores an instruction in the memory object.
        	Data is supposed to be a list/array of 4 uint8s (bytes). The first is a phantom byte (0).
        '''
        address=int(address) #just to make sure
        mem_address = address>>1 #addresses increase in steps of two
        page_address = mem_address>>10
        self.tags[page_address] = 1#mark as dirty
        self.data[mem_address] = data

    def data_to_transmit(self):
        '''
        	Creates a list of dirty pages to transmit to the microcontroller.
        	Returns a numpy uint8 array (N by 1024 by 3, no phantom byte uint8) and a numpy array of page addresses (uint).
        '''
        N = np.sum(self.tags==1)
        pic_mem = np.zeros((N,1024,3),dtype=np.uint8)
        pic_mem_addr = np.where(self.tags==1)[0]<<11 #multiply addresses by 2048 (1024 instructions in steps of two)
        for i, idx in enumerate(pic_mem_addr):
            pic_mem[i] = self.data[idx>>1:(idx>>1)+1024,1:]
        return pic_mem, pic_mem_addr

    def set_boot_address(self,address=0x800):
        '''
        	Changes the goto instruction that is executed when the uC boots up.
        	Address should be an unsigned int.
        '''
        self.write(0x0,(0x00,0x04,(address>>8)&0xFF,address&0xFE)) #0x0004 is a GOTO instruction (http://ww1.microchip.com/downloads/en/DeviceDoc/70157C.pdf page 196)
        self.write(0x2,(0x00,0x00,0x00,(address>>16)&0x7F))


def write_uC_code_memory(memory,fname):
    '''
    	Writes the microcontroller program memory (non-zero) to a file.
    	The resulting file can be programmed using the CANOpen bootloader.
    '''
    #write header
    #byte 0		uint8		magic byte (0x00 = program memory)
    #byte 1-2	uint16		number of lines in file
    #byte 3-6	uint32		device id
    #byte 7-N			page to program (lines)
    #				byte 0		uint8	magic byte (0x00 = write page to uC memory)
    #				byte 1-2	uint16	number of instructions on page 
    #				byte 3-5	uint24	page address	
    #				byte 6-8,9-11...uint24	instructions to program		
    #read device id
    with io.FileIO(fname,'w') as stream:
        #stream.write(bytearray([0x00])) #magic byte

        pic_mem, pic_mem_addr = memory.data_to_transmit()
        #stream.write(bytearray([pic_mem.shape[0]>>8,pic_mem.shape[0]&0xFF])) #number of lines

        #stream.write(bytearray([dev_id>>24,(dev_id>>16)&0xFF,(dev_id>>8)&0xFF,(dev_id)&0xFF])) #dev id

        #program memory lines
        for i, idx in enumerate(pic_mem_addr):
            print( "writing program page %d/%d: \t %.6x\tnum. instr. %d"%(i,pic_mem_addr.shape[0],idx,pic_mem.shape[1]))
            #stream.write(bytearray([0x00]))
            #stream.write(bytearray([0x04,0x00]))#1024 instructions per page
            #stream.write(bytearray([idx&0xFF,(idx>>8)&0xFF,(idx>>16)&0xFF])) #page address little endian
            #send page data
            for j in range(pic_mem.shape[1]):
                stream.write(bytearray([pic_mem[i,j,2]])) #little endian
                stream.write(bytearray([pic_mem[i,j,1]]))
                stream.write(bytearray([pic_mem[i,j,0]]))	


fname = "F:\\CAN.hex"
modify_boot_address = True
hex_file = load_hex_file(fname)
boot_address = 0x800
memory = pic_memory()
parse_hex(hex_file,memory)
if(modify_boot_address):
    print ("Modifying boot address")
    memory.set_boot_address(boot_address)	

output=os.path.splitext(fname)[0]+".bin"
print("Writing program memory to file (%s)"%output) 
write_uC_code_memory(memory,output)