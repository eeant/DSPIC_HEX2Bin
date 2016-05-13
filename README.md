# DSPIC_HEX2Bin

----------
##如何使用

1. 安装python3
2. 安装numpy库
3. 修改hex2bin.py文件L118 
	将 fname = "F:\\CAN.hex"，修改为待转换的文件名，包含路径
4. 修改hex2bin.py文件L121
	将 boot_address = 0x800 修改为实际bootloader的其实地址。
5. windows平台下可以直接双击hex2bin.bat，即可完成转换，转换后的文件在hex文件对应的路径下。
