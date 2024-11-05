import gc
from time import sleep_ms
from Models.Api import Api
from Models.RpiPico import RpiPico
from Models.Lightning import Lightning

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

i2c = I2C(0, scl=Pin(21), sda=Pin(20), freq=400000)
address = 0x03 # Dirección del dispositivo i2c
# Escanear el bus I2C en busca de dispositivos
#devices = i2c.scan()


#spi = SPI(0, baudrate=2000000, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
#spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
#address = 5 # CS Pin en el caso de SPI

sleep_ms(500)
sensor = Lightning(i2c=i2c, address=address, pin_irq=22, debug=env.DEBUG,
                   indoor=env.INDOOR)

sleep_ms(200)

# Api
if env.API_UPLOAD:
    api = Api(controller=controller, url=env.API_URL, path=env.API_PATH,
              token=env.API_TOKEN, device_id=env.DEVICE_ID, debug=env.DEBUG)

sleep_ms(3000)


def thread0 ():
    """
    Primer hilo, flujo principal de la aplicación.
    """

    controller.led_on()

    if sensor.check_exist_strike():
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
