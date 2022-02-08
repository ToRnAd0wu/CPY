import time
import busio
import board
import neopixel
import displayio
import microcontroller
import adafruit_adt7410
import adafruit_touchscreen
from analogio import AnalogIn
import adafruit_minimqtt as MQTT
from digitalio import DigitalInOut
from adafruit_button import Button
from adafruit_pyportal import PyPortal
from adafruit_io.adafruit_io import IO_MQTT
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket

#import fromAdafruitIO
#import weathercode
### WiFi ###

# ------------- Inputs and Outputs Setup ------------- #
try:  # attempt to init. the temperature sensor
    i2c_bus = busio.I2C(board.SCL, board.SDA)
    adt = adafruit_adt7410.ADT7410(i2c_bus, address=0x48)
    adt.high_resolution = True
except ValueError:
    # Did not find ADT7410. Probably running on Titano or Pynt
    adt = None

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]
location = secrets.get("timezone", None)

TIME_URL = "https://io.adafruit.com/api/v2/%s/integrations/time/strftime?x-aio-key=%s" % (aio_username, aio_key)
TIME_URL += "&fmt=%25Y-%25m-%25d+%25H%3A%25M%3A%25S.%25L+%25j+%25u+%25z+%25Z"

# init. the light sensor
light_sensor = AnalogIn(board.LIGHT)

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=1)
WHITE = 0xffffff
RED = 0xff0000
ORANGE = 0xFFA500
YELLOW = 0xffff00
GREEN = 0x00ff00
BLUE = 0x0000ff
PURPLE = 0xff00ff
PINK = 0xee82ee
BLACK = 0x000000

# ---------- Sound Effects ------------- #
soundDemo = '/sounds/sound.wav'
soundBeep = '/sounds/beep.wav'
soundTab = '/sounds/tab.wav'
soundButton = '/sounds/hellothere.wav'

# ------------- Other Helper Functions------------- #
# Helper for cycling through a number set of 1 to x.
def numberUP(num, max_val):
    num += 1
    if num <= max_val:
        return num
    else:
        return 1

# ------------- Screen Setup ------------- #
temp_value = "x"
humi_value = "x"
pyportal = PyPortal()
display = board.DISPLAY
display.rotation = 0

pyportal.network.connect()

# Define callback functions which will be called when certain events happen.
# pylint: disable=unused-argument
def connected(client):
    # Connected function will be called when the client is connected to Adafruit IO.
    # This is a good place to subscribe to feed changes.  The client parameter
    # passed to this function is the Adafruit IO MQTT client so you can make
    # calls against it easily.
    print("Connected to Adafruit IO!  Listening for DemoFeed changes...")


def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0}, the value is {1}".format(topic, granted_qos))


def unsubscribe(client, userdata, topic, pid):
    # This method is called when the client unsubscribes from a feed.
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))


# pylint: disable=unused-argument
def disconnected(client):
    # Disconnected function will be called when the client disconnects.
    print("Disconnected from Adafruit IO!")


# pylint: disable=unused-argument
def on_message(client, feed_id, payload):
    # Message function will be called when a subscribed feed has a new value.
    # The feed_id parameter identifies the feed, and the payload parameter has
    # the new value.
    print("Feed {0} received new value: {1}".format(feed_id, payload))


def on_temperature_msg(client, topic, message):
    # Method called whenever user/feeds/temperature has a new value
    print("Temperature level: {} °C".format(message))
    global temp_value
    temp_value = message

def on_humidity_msg(client, topic, message):
    # Method called whenever user/feeds/humidity has a new value
    print("Humidity level: {} %".format(message))
    global humi_value
    humi_value = message

# Connect to WiFi
print("Connecting to WiFi...")
#wifi.connect()
print("Connected!")

# Initialize MQTT interface with the esp interface
MQTT.set_socket(socket, pyportal.network._wifi.esp)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=secrets["aio_username"],
    password=secrets["aio_key"],
)

# Initialize an Adafruit IO MQTT Client
io = IO_MQTT(mqtt_client)

io.on_connect = connected
io.on_disconnect = disconnected
io.on_subscribe = subscribe
io.on_unsubscribe = unsubscribe
io.on_message = on_message

# Connect to Adafruit IO
print("Connecting to Adafruit IO...")
io.connect()

# Set up a message handler for the temperature feed
io.add_feed_callback("temperature", on_temperature_msg)

# Subscribe to all messages on the temperature feed
io.subscribe("temperature")

# Set up a message handler for the humidity feed
io.add_feed_callback("humidity", on_humidity_msg)

# Subscribe to all messages on the humidity feed
io.subscribe("humidity")

#-------------------------------------------------------------------#

# Backlight function
# Value between 0 and 1 where 0 is OFF, 0.5 is 50% and 1 is 100% brightness.
def set_backlight(val):
    val = max(0, min(1.0, val))
    board.DISPLAY.auto_brightness = False
    board.DISPLAY.brightness = val

# Set the Backlight
set_backlight(0.3)

# Touchscreen setup
# ------Rotate 0:
screen_width = 320
screen_height = 240
ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000),
                                                   (5800, 57000)),
                                      size=(screen_width, screen_height))


# ------------- Display Groups ------------- #
splash = displayio.Group(max_size=15)  # The Main Display Group
view1 = displayio.Group(max_size=15)  # Group for View 1 objects
view2 = displayio.Group(max_size=15)  # Group for View 2 objects
view3 = displayio.Group(max_size=15)  # Group for View 3 objects

def hideLayer(hide_target):
    try:
        splash.remove(hide_target)
    except ValueError:
        pass

def showLayer(show_target):
    try:
        time.sleep(0.1)
        splash.append(show_target)
    except ValueError:
        pass

# ------------- Setup for Images ------------- #

# Display an image until the loop starts
pyportal.set_background('/images/loading.bmp')


bg_group = displayio.Group(max_size=1)
splash.append(bg_group)


# This will handel switching Images and Icons
def set_image(group, filename):
    """Set the image file for a given goup for display.
    This is most useful for Icons or image slideshows.
        :param group: The chosen group
        :param filename: The filename of the chosen image
    """
    print("Set image to ", filename)
    if group:
        group.pop()

    if not filename:
        return  # we're done, no icon desired

    image_file = open(filename, "rb")
    image = displayio.OnDiskBitmap(image_file)
    try:
        image_sprite = displayio.TileGrid(image, pixel_shader=displayio.ColorConverter())
    except TypeError:
        image_sprite = displayio.TileGrid(image, pixel_shader=displayio.ColorConverter(),
                                          position=(0, 0))
    group.append(image_sprite)

set_image(bg_group, "/images/BGview1.bmp")

# ---------- Text Boxes ------------- #
# Set the font and preload letters
font = bitmap_font.load_font("/fonts/Helvetica-Bold-16.bdf")
font.load_glyphs(b'abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890- ()')

# Default Label styling:
TABS_X = 5
TABS_Y = 50

# Text Label Objects
feed1_label = Label(font, text="Text Wondow 1", color=0xFFA500, max_glyphs=200)
feed1_label.x = TABS_X
feed1_label.y = TABS_Y
view1.append(feed1_label)

feed2_label = Label(font, text="Text Wondow 2", color=0x03669C, max_glyphs=200)
feed2_label.x = TABS_X
feed2_label.y = TABS_Y
view2.append(feed2_label)

sensors_label = Label(font, text="Data View", color=0x000000, max_glyphs=200)
sensors_label.x = TABS_X
sensors_label.y = TABS_Y
view3.append(sensors_label)

sensor_data = Label(font, text="Data View", color=0x000000, max_glyphs=100)
sensor_data.x = TABS_X
sensor_data.y = 130
view3.append(sensor_data)

adafruit_data = Label(font, text="Data View", color=0xFFA500, max_glyphs=200)
adafruit_data.x = TABS_X
adafruit_data.y = 130
view1.append(adafruit_data)

text_hight = Label(font, text="M", color=0x03AD31, max_glyphs=10)

# return a reformatted string with word wrapping using PyPortal.wrap_nicely
def text_box(target, top, string, max_chars):
    text = pyportal.wrap_nicely(string, max_chars)
    new_text = ""
    test = ""
    for w in text:
        new_text += '\n'+w
        test += 'M\n'
    text_hight.text = test  # Odd things happen without this
    glyph_box = text_hight.bounding_box
    target.text = ""  # Odd things happen without this
    target.y = int(glyph_box[3]/2)+top
    target.text = new_text

# ---------- Display Buttons ------------- #
# Default button styling:
BUTTON_HEIGHT = 40
BUTTON_WIDTH = 80

# We want three buttons across the top of the screen
TAPS_HEIGHT = 40
TAPS_WIDTH = int(screen_width/3)
TAPS_Y = 0

VIEW2BUTTON_HEIGHT = 40
VIEW2BUTTON_WIDTH = int(screen_width/2)
VIEW2BUTTON_Y = int(screen_height-VIEW2BUTTON_HEIGHT)

# This group will make it easy for us to read a button press later.
buttons = []

# Main User Interface Buttons
button_view1 = Button(x=0, y=0,
                      width=TAPS_WIDTH, height=TAPS_HEIGHT,
                      label="1", label_font=font, label_color=0xFFA500,
                      fill_color=0x5c5b5c, outline_color=0x767676,
                      selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                      selected_label=0x525252)
buttons.append(button_view1)  # adding this button to the buttons group

button_view2 = Button(x=TAPS_WIDTH, y=0,
                      width=TAPS_WIDTH, height=TAPS_HEIGHT,
                      label="2", label_font=font, label_color=0x03669C,
                      fill_color=0x5c5b5c, outline_color=0x767676,
                      selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                      selected_label=0x525252)
buttons.append(button_view2)  # adding this button to the buttons group

button_view3 = Button(x=TAPS_WIDTH*2, y=0,
                      width=TAPS_WIDTH, height=TAPS_HEIGHT,
                      label="3", label_font=font, label_color=0x000000,
                      fill_color=0x5c5b5c, outline_color=0x767676,
                      selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                      selected_label=0x525252)
buttons.append(button_view3)  # adding this button to the buttons group

# Add all of the main buttons to the splash Group
for b in buttons:
    splash.append(b)

button_sound = Button(x=0, y=VIEW2BUTTON_Y,
                       width=VIEW2BUTTON_WIDTH, height=VIEW2BUTTON_HEIGHT,
                       label="Sound", label_font=font, label_color=0x03669C,
                       fill_color=0x5c5b5c, outline_color=0x767676,
                       selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                       selected_label=0x525252)
buttons.append(button_sound)  # adding this button to the buttons group
view2.append(button_sound) # adding this button to view 2

button_light = Button(x=VIEW2BUTTON_WIDTH, y=VIEW2BUTTON_Y,
                       width=VIEW2BUTTON_WIDTH, height=VIEW2BUTTON_HEIGHT,
                       label="Color", label_font=font, label_color=0x03669C,
                       fill_color=0x5c5b5c, outline_color=0x767676,
                       selected_fill=0x1a1a1a, selected_outline=0x2e2e2e,
                       selected_label=0x525252)
buttons.append(button_light)  # adding this button to the buttons group
view2.append(button_light) # adding this button to view 2

#pylint: disable=global-statement
def switch_view(what_view):
    global view_live
    if what_view == 1:
        hideLayer(view2)
        hideLayer(view3)
        button_view1.selected = False
        button_view2.selected = True
        button_view3.selected = True
        showLayer(view1)
        view_live = 1
        print("View1 On")
    elif what_view == 2:
        # global icon
        hideLayer(view1)
        hideLayer(view3)
        button_view1.selected = True
        button_view2.selected = False
        button_view3.selected = True
        showLayer(view2)
        view_live = 2
        print("View2 On")
    else:
        hideLayer(view1)
        hideLayer(view2)
        button_view1.selected = True
        button_view2.selected = True
        button_view3.selected = False
        showLayer(view3)
        view_live = 3
        print("View3 On")
#pylint: enable=global-statement

# Set veriables and startup states
button_view1.selected = False
button_view2.selected = True
button_view3.selected = True
showLayer(view1)
hideLayer(view2)
hideLayer(view3)

view_live = 1
button_mode = 1
switch_state = 0

# Update out Labels with display text.
text_box(feed1_label, TABS_Y,
         'Values from Adafruit IO', 30)

text_box(feed2_label, TABS_Y, 'Funny Buttons', 30)

text_box(sensors_label, TABS_Y,
         "Sensor Data", 30)

board.DISPLAY.show(splash)
# ------------- Code Loop ------------- #
while True:

    touch = ts.touch_point
    light = light_sensor.value

    if adt:  # Only if we have the temperature sensor
        tempC = adt.temperature
    else:  # No temperature sensor
        tempC = microcontroller.cpu.temperature

    tempF = tempC * 1.8 + 32
    sensor_data.text = 'Touch: {}\nLight: {}\nTemp: {:.0f}°C'.format(touch, light, tempC)

    adafruit_data.text = "Temperature: {}°C\nHumidity: {}%".format(
        temp_value, humi_value
    )
    # ------------- Handle Button Press Detection  ------------- #
    if touch:  # Only do this if the screen is touched
        # loop with buttons using enumerate() to number each button group as i
        for i, b in enumerate(buttons):
            if b.contains(touch):  # Test each button to see if it was pressed
                print('button%d pressed' % i)
                if i == 0 and view_live != 1:  # only if view1 is visable
                    pyportal.play_file(soundTab)
                    switch_view(1)
                    set_image(bg_group, "/images/BGview1.bmp")
                    while ts.touch_point:
                        pass
                if i == 1 and view_live != 2:  # only if view2 is visable
                    pyportal.play_file(soundTab)
                    switch_view(2)
                    set_image(bg_group, "/images/BGview2.bmp")
                    while ts.touch_point:
                        pass
                if i == 2 and view_live != 3:  # only if view3 is visable
                    pyportal.play_file(soundTab)
                    switch_view(3)
                    set_image(bg_group, "/images/BGview3.bmp")
                    while ts.touch_point:
                        pass
                if i == 3 and view_live == 2:
                    pyportal.play_file(soundButton)
                    b.selected = True
                    # for debounce
                    while ts.touch_point:
                        pass
                    b.selected = False
                if i == 4 and view_live == 2:
                    pyportal.play_file(soundBeep)
                    # Momentary button type
                    b.selected = True
                    button_mode = numberUP(button_mode, 7)
                    if button_mode == 1:
                        pixel.fill(RED)
                    elif button_mode == 2:
                        pixel.fill(ORANGE)
                    elif button_mode == 3:
                        pixel.fill(YELLOW)
                    elif button_mode == 4:
                        pixel.fill(GREEN)
                    elif button_mode == 5:
                        pixel.fill(BLUE)
                    elif button_mode == 6:
                        pixel.fill(PURPLE)
                    elif button_mode == 7:
                        pixel.fill(PINK)
                    switch_state = 1
                    # for debounce
                    while ts.touch_point:
                        pass
                    b.selected = False
    io.loop()