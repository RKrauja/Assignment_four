import machine
import network
import socket

ap = network.WLAN(network.AP_IF)  # Create a WLAN object and assign it to a variable
ap.active(True)  # Activate the access point
ap.config(essid='Shawarma 24')  # Set the network name
ap.config(authmode=3, password='LielsDibens')  # Set the authentication mode and password

pins = [machine.Pin(i, machine.Pin.IN) for i in (12, 22, 23, 34)]

temp_sensor = machine.I2C(scl=machine.Pin(22), sda=machine.Pin(23))
button = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_UP)

potentiometer = machine.ADC(machine.Pin(34))
potentiometer.atten(machine.ADC.ATTN_11DB)

address = 24
temp_reg = 5

# Define an HTML template for displaying the pin values as a table tag
html = """<!DOCTYPE html>
<html>
    <head> <title>ESP32 Pins</title> </head>
    <body> <h1>ESP32 Pins</h1>
        <table border="1"> <tr><th>Pin</th><th>Value</th></tr> %s </table>
    </body>
</html>
"""

# Get the address information of the server
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

s = socket.socket()  # Create new socket
s.bind(addr)  # Bind the socket to the address
s.listen(1)  # Listen for incoming connections, specifying the maximum number of queued connections

print('listening on', addr)


def temp_c(data):
    value = data[0] << 8 | data[1]
    temp = (value & 0xFFF) / 16.0
    if value & 0x1000:
        temp -= 256.0
    return temp


def read_temp():
    data = temp_sensor.readfrom_mem(address, temp_reg, 2)
    current_temp = temp_c(data)
    print("Current Temperature: {:.2f}°C".format(current_temp))
    return current_temp

def read_pot():
    return potentiometer.read_uv()



while True:
    cl, addr = s.accept()  # Accept a connection
    print('client connected from', addr)
    cl_file = cl.makefile('rwb',
                          0)  # Create a file-like (behaves further just like a file) object with permission to read and write, as well as a buffer size of 0
    while True:
        temperature = read_temp()
        line = cl_file.readline()  # Read a line from the client request
        pot_input = read_pot()
        print(f"Current line: {line}")
        if not line or line == b'\r\n':  # Check if the line is empty or contains only a newline
            break  # If true break the inner loop
    # Create a list with html tags of table rows containing pins and their values
    rows = ['<tr><td>%s</td><td>%d</td></tr>' % (str(p), p.value()) for p in pins]
    rows.append('<tr><td>%s</td><td>%d</td></tr>' % ('Temperature', temperature))
    rows.append('<tr><td>%s</td><td>%d</td></tr>' % ('Potentiometer', pot_input))
    response = html % '\n'.join(rows)  # Format the HTML template with the new rows
    cl.send(response)  # Send the response to the client
    cl.close()  # Close the connection
