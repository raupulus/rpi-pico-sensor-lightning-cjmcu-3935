import gc
import random
from time import sleep_ms
from Models.Api import Api
from Models.RpiPico import RpiPico
from Models.Lightning import Lightning
from Models.SSD1306 import SSD1306_I2C as SSD1306


# Importo variables de entorno
import env
from machine import I2C, Pin

# Habilito recolector de basura
gc.enable()

sleep_ms(1000)

# Rpi Pico Model
controller = RpiPico(ssid=env.AP_NAME, password=env.AP_PASS, debug=env.DEBUG,
                     alternatives_ap=env.ALTERNATIVES_AP,
                     hostname="Lightning")

sleep_ms(20)
controller.led_on()
sleep_ms(20)

i2c = I2C(0, scl=Pin(9), sda=Pin(8), freq=400000)
address = 0x03 # Dirección del dispositivo i2c para AS3935

# Configuro los GPIO para los tres LEDs que simulan flashes
led1 = Pin(13, Pin.OUT)
led2 = Pin(14, Pin.OUT)
led3 = Pin(15, Pin.OUT)
leds = [led1, led2, led3]

led1.high()
led2.high()
led3.high()

# Inicializando pantalla OLED
DISPLAY_ENABLED = env.DISPLAY_ENABLED

if DISPLAY_ENABLED:
    oled_width = 128
    oled_height = 64
    oled_address = 0x3c
    oled = SSD1306(oled_width, oled_height, i2c, addr=oled_address)

    oled.text('Esperando Eventos', 0, 0)

    oled.show()



sleep_ms(500)
sensor = Lightning(i2c=i2c, address=address, pin_irq=22, debug=env.DEBUG,
                   indoor=env.INDOOR)

sleep_ms(200)

# Api
if env.API_UPLOAD:
    api = Api(controller=controller, url=env.API_URL, path=env.API_PATH,
              token=env.API_TOKEN, device_id=env.DEVICE_ID, debug=env.DEBUG)

sleep_ms(3000)

led1.low()
led2.low()
led3.low()

def simulate_random_lightning ():
    """Función para simular flashes de relámpagos de forma aleatoria con 3 LEDs"""
    # Generar un número aleatorio de flashes entre 10 y 25
    total_flashes = random.randint(10, 25)

    for _ in range(total_flashes):
        # Elegir un LED aleatorio
        led = random.choice(leds)

        # Duración del flash (entre 150 y 350 ms)
        delay = int(
            random.uniform(0.15, 0.35) * 1000)  # Convertir a milisegundos

        # Encender y apagar el LED
        led.on()
        sleep_ms(delay)
        led.off()

        # Pausa antes del siguiente flash (entre 50 y 100 ms)
        pause = int(
            random.uniform(0.05, 0.1) * 1000)  # Convertir a milisegundos
        sleep_ms(pause)


simulate_random_lightning()

def thread0 ():
    """
    Primer hilo, flujo principal de la aplicación.
    """

    controller.led_on()

    if sensor.check_exist_strike():

        simulate_random_lightning()

        if DISPLAY_ENABLED:
            last_strike = sensor.lightnings[0]

            print(last_strike)

            oled.fill(0)
            oled.text('Hay ' + str(len(sensor.lightnings)) + ' rayos', 0, 0)
            oled.text('Distance: ' + str(last_strike.get('distance')) + 'km', 0, 10)
            oled.text('Energy: ' + str(last_strike.get('energy')) + 'J', 0, 20)
            oled.text('Noise: ' + str(last_strike.get('noise_floor')), 0, 30)
            oled.text('Type: ' + str(last_strike.get('type')), 0, 40)

            oled.show()

        if env.DEBUG:
            print('Se han detectado rayos, se guardan en la API')
            print(sensor.lightnings)

        if env.API_UPLOAD:
            # Subir datos a la api
            if api.save_lightnings(sensor.lightnings):
                sensor.clear_datas()

        else:
            sensor.clear_datas()

    controller.led_off()


while True:
    try:
        thread0()
    except Exception as e:
        if env.DEBUG:
            print('Error: ', e)
            print('Memoria antes de liberar: ', gc.mem_free())

        gc.collect()

        if env.DEBUG:
            print("Memoria después de liberar:", gc.mem_free())
    finally:
        sleep_ms(10000)
