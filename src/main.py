#from machine import Pin, SPI
import gc
from time import sleep_ms
from Models.Api import Api
from Models.RpiPico import RpiPico
from Models.Lightning import Lightning

# Importo variables de entorno
import env

# Habilito recolector de basura
gc.enable()

# Rpi Pico Model
controller = RpiPico(ssid=env.AP_NAME, password=env.AP_PASS, debug=env.DEBUG,
                     alternatives_ap=env.ALTERNATIVES_AP,
                     hostname="Lightning Sensor")

sleep_ms(20)

sensor = Lightning(sda=20, scl=21, pin_irq=22, debug=False, indoor=True)


sleep_ms(3000)

exit()

# Api
api = Api(controller=controller, url=env.API_URL, path=env.API_PATH,
          token=env.API_TOKEN, device_id=env.DEVICE_ID, debug=env.DEBUG)

sleep_ms(3000)


def thread0 ():
    """
    Primer hilo, flujo principal de la aplicación.
    """

    if env.DEBUG:
        print('Inicia hilo principal (thread0)')


while True:
    try:
        thread0()
    except Exception as e:
        if env.DEBUG:
            print('Error: ', e)
    finally:
        if env.DEBUG:
            print('Memoria antes de liberar: ', gc.mem_free())

        gc.collect()

        if env.DEBUG:
            print("Memoria después de liberar:", gc.mem_free())

        sleep_ms(5000)
