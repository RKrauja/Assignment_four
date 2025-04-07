import machine

i2c = machine.I2C(scl=machine.Pin(22), sda=machine.Pin(23))

devices = i2c.scan()

if devices:
    print('I2C devices found:', devices)
else:
    print('No I2C devices found')