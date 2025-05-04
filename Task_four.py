import machine
import network
import socket
import json

ap = network.WLAN(network.AP_IF)  # Create a WLAN object and assign it to a variable
ap.active(True)  # Activate the access point
ap.config(essid='Shawarma 24')  # Set the network name
ap.config(authmode=3, password='LielsDibens')  # Set the authentication mode and password

#pins = [machine.Pin(i, machine.Pin.IN) for i in (12, 22, 23, 34)]
pin_numbers = (12, 22, 23, 34)
sensor_names = ['button', 'temp_sensor', 'potentiometer']
pins = {pin_num: machine.Pin(pin_num, machine.Pin.IN) for pin_num in pin_numbers}

temp_sensor = machine.I2C(scl=machine.Pin(22), sda=machine.Pin(23))
button = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_UP)

potentiometer = machine.ADC(machine.Pin(34))
potentiometer.atten(machine.ADC.ATTN_11DB)

address = 24
temp_reg = 5

def generate_html(pins, temperature, pot_input):
    # This will create the table rows
    rows = ['<tr><td>%s</td><td>%d</td></tr>' % (str(pin_num), pins[pin_num].value()) for pin_num in pins]
    rows.append('<tr><td>Temperature</td><td>%.2f°C</td></tr>' % temperature)
    rows.append('<tr><td>Potentiometer</td><td>%d µV</td></tr>' % pot_input)
    
    # Define an HTML template for displaying the pin values as a table tag
    html = """<!DOCTYPE html>
    <html>
        <head> <title>ESP32 Pins</title> </head>
        <body> <h1>ESP32 Pins</h1>
            <table border="1"> <tr><th>Pin</th><th>Value</th></tr> %s </table>
        </body>
    </html>
    """

    return html % '\n'.join(rows) 

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

def handle_pin(cl, pin_id):
    if pin_id in pins:
        pin = pins[pin_id]
        response = {
            "value": pin.value()
        }
    else:
        response = {"error": f"Pin {pin_id} not found."}

    json_data = json.dumps(response)
    cl.send('HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n')
    cl.send(json_data)

def load_all_pins():
    response = {
        "pins": pins
    }
    json_data = json.dumps(response)
    cl.send('HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n')
    cl.send(json_data)

while True:
    cl, addr = s.accept()  # Accept a connection
    print('client connected from', addr)
    cl_file = cl.makefile('rwb',0)  # Create a file-like (behaves further just like a file) object with permission to read and write, as well as a buffer size of 0
    handled = False

    while True:
        temperature = read_temp()
        line = cl_file.readline()  # Read a line from the client request
        pot_input = read_pot()
        print(f"Current line: {line}")

        if not line or line == b'\r\n':  # Check if the line is empty or contains only a newline
                break  # If true break the inner loop
        
        if 'GET /pins/' in line:
                request_line = line.decode().split(' ')[1]  # Get the URL path, like /pins/12
                pin_str = request_line.split('/')[2] #12
                print(pin_str)
                try:
                    pin_id = int(pin_str)
                    if '/sethigh' in line:
                         machine.Pin(pin_id, machine.Pin.OUT).value(1)
                    elif '/setlow' in line:
                         machine.Pin(pin_id, machine.Pin.OUT).value(0)
                    handle_pin(cl, pin_id)
                except:
                     print("Couldn't read pin id, rerouting back to all pins")
                     load_all_pins()
                handled = True

        elif 'GET /pins' in line:
            load_all_pins()
            handled = True

        elif 'GET /sensors' in line:
                response = {
                    "sensors": sensor_names 
                }
                json_data = json.dumps(response)
                cl.send('HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n')
                cl.send(json_data)
                handled = True


        elif 'GET /sensor/' in line:
            request_line = line.decode().split(' ')[1]  # Get the URL path, like /sensor/button
            sensor_str = request_line.split('/')[2] # temp_sensor
            
            if sensor_str == 'temp_sensor':
                temp = read_temp()
                response = {
                    "Value": temp 
                }
                json_data = json.dumps(response)
                cl.send('HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n')
                cl.send(json_data)
                handled = True

            elif sensor_str == 'potentiometer':
                pot = read_pot()
                response = {
                    "Value": pot 
                }
                json_data = json.dumps(response)
                cl.send('HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n')
                cl.send(json_data)
                handled = True

            elif sensor_str == 'button':
                pin_id = 12
                handle_pin(cl, pin_id)
                handled = True
            
            else:
                cl.send('HTTP/1.1 404 Not Found\r\n\r\nSensor not found')    
                handled = True

    if not handled:
        # Only generate and send HTML if no JSON was already sent
        response = generate_html(pins, temperature, pot_input)
        cl.send('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
        cl.send(response)

    cl.close()