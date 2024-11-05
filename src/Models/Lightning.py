#!/usr/bin/python3
# -*- encoding: utf-8 -*-

# @author     Raúl Caro Pastorino
# @email      public@raupulus.dev
# @web        https://raupulus.dev
# @gitlab     https://gitlab.com/raupulus
# @github     https://github.com/raupulus
# @twitter    https://twitter.com/raupulus
# @telegram   https://t.me/raupulus_diffusion

# Create Date: 2024
# Dependencies:
#
# Revision 0.01 - File Created

# @copyright  Copyright © 2024 Raúl Caro Pastorino
# @license    https://wwww.gnu.org/licenses/gpl.txt

# Copyright (C) 2024  Raúl Caro Pastorino
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

# # Descripción
# Modelo que implementa las clases básicas para el detector de rayo CJMCU-3935
# usando el chip AS3935 por i2c en raspberry pi pico w con micropython.


from machine import Pin, I2C, SPI
import utime
from time import sleep_ms
from Models.SensorCJMCUAS3935_3 import SensorCJMCUAS3935


class Lightning:
    sensor = None
    lightnings = []

    def __init__(self, i2c=None, spi=None, address=None, pin_irq=26,
                 debug=False, indoor=True):
        # Marco el modo debug para el modelo.
        self.DEBUG = debug

        # Instancio el sensor como atributo de este modelo.
        #self.sensor = SensorCJMCUAS3935(spi=spi, address=address, debug=True)
        self.sensor = SensorCJMCUAS3935(i2c=i2c, address=address, debug=True)



        # Sensor model 2
        #self.sensor.full_calibration(12)
        #self.sensor.set_indoors(indoor)



        # Sensor model 3
        self.sensor.powerUp()
        self.sensor.setIndoors()
        #self.sensor.setOutdoors()
        self.sensor.disturberEn()
        #self.sensor.disturberDis()
        self.sensor.setIrqOutputSource(0)
        sleep_ms(500)
        # Antenna tuning capcitance (must be integer multiple of 8, 8 - 120 pf)
        self.sensor.setTuningCaps(120)
        # Connect the IRQ and GND pin to the oscilloscope.
        # uncomment the following sentences to fine tune the antenna for better performance.
        # This will dispaly the antenna's resonance frequency/16 on IRQ pin (The resonance frequency will be divided by 16 on this pin)
        # Tuning AS3935_CAPACITANCE to make the frequency within 500/16 kHz plus 3.5% to 500/16 kHz minus 3.5%
        #
        # self.sensor.setLcoFdiv(0)
        # self.sensor.setIrqOutputSource(3)

        # Set the noise level,use a default value greater than 7
        self.sensor.set_noise_floor(2)
        # noiseLv = self.sensor.get_noise_floor()

        # used to modify WDTH,alues should only be between 0x00 and 0x0F (0 and 7)
        self.sensor.setWatchdogThreshold(2)
        # wtdgThreshold = sensor.getWatchdogThreshold()

        # used to modify SREJ (spike rejection),values should only be between 0x00 and 0x0F (0 and 7)
        self.sensor.setSpikeRejection(2)
        # spikeRejection = sensor.getSpikeRejection()






        # Configuro el pin de interrupción cuando se detecta eventos
        pin = Pin(pin_irq, Pin.IN, Pin.PULL_UP)

        # Inicio Callback para en cada detección registrar rayo
        pin.irq(trigger=Pin.IRQ_FALLING, handler=self.handle_interrupt)

        if self.DEBUG:
            print('Inicializado sensor de rayos y esperando detectar campos electromagnéticos para procesarlos.')

    def handle_interrupt(self, channel):
        """
        Función que se ejecuta cuando detecta un rayo para registrarlo
        en el array de objetos con los datos registrados.
        :return:
        """
        sleep_ms(30)
        sensor = self.sensor

        # Momento actual en formato timestamp respecto a inicio del microcontrolador.
        now = utime.time()

        reason = sensor.get_interrupt_src()

        if reason == 1:
            if self.DEBUG:
                print('El nivel de ruido es demasiado alto → Ajustando')

                print('--------------------------')
                print('El nivel de ruido es demasiado alto → Calibrando')
                print('Timestamp: ' + str(now))
                print('--------------------------')
        elif reason == 2:
            if self.DEBUG:
                print('--------------------------')
                print('Se ha detectado una perturbación → Enmascarándola')
                print('Timestamp: ' + str(now))
                print('--------------------------')
        elif reason == 3:
            # En este punto, parece una detección correcta y la guardo.
            self.lightnings.append({
                "noise_floor": self.get_noise_floor(),
                "distance": self.get_distance(),
                "type": self.get_type(),
                "energy": self.get_energy(),
                "timestamp_read": utime.time(),
            })

            if self.DEBUG:
                distance = sensor.get_distance()

                print('--------------------------')
                print('¡Se ha detectado un posible RAYO!')
                print('Timestamp: ' + str(now))
                print("Está a " + str(distance) + "km de distancia.")
                print("------------------------")
                print("All Data:")
                print('Distance:' + str(distance))
                print('Interrupt: 3')
                print('Energy:' + str(self.sensor.get_energy()))
                print('Ruido:' + str(self.sensor.get_noise_floor()))
                #print('In Indoor:' + str(self.sensor.get_indoors()))
                #print('Mask Disturber:' + str(self.sensor.get_mask_disturber()))
                print('--------------------------')
        else:
            if self.DEBUG:
                print(
                    'Se ha detectado algo no controlado aún, ¿Has provocado el irq?')

        """
        if reason == 0x01:
            # TODO: Implementar? Ver más exactamente que ha ocurrido?
            sensor.raise_noise_floor()

            if self.DEBUG:
                print('El nivel de ruido es demasiado alto → Ajustando')

                print('--------------------------')
                print('El nivel de ruido es demasiado alto → Calibrando')
                print('Timestamp: ' + str(now))
                print('--------------------------')

        elif reason == 0x04:
            sensor.set_mask_disturber(True)

            if self.DEBUG:
                print('--------------------------')
                print('Se ha detectado una perturbación → Enmascarándola')
                print('Timestamp: ' + str(now))
                print('--------------------------')

        elif reason == 0x08:
            # En este punto, parece una detección correcta y la guardo.
            self.lightnings.append({
                "noise_floor": self.get_noise_floor(),
                "distance": self.get_distance(),
                "type": self.get_type(),
                "energy": self.get_energy(),
                "timestamp_read": utime.time(),
            })

            if self.DEBUG:
                distance = sensor.get_distance()

                print('--------------------------')
                print('¡Se ha detectado un posible RAYO!')
                print('Timestamp: ' + str(now))
                print("Está a " + str(distance) + "km de distancia.")
                print("------------------------")
                print("All Data:")
                print('Distance:' + str(self.sensor.get_distance()))
                print('Interrupt:' + str(self.sensor.get_interrupt()))
                print('Energy:' + str(self.sensor.get_energy()))
                print('Ruido:' + str(self.sensor.get_noise_floor()))
                print('In Indoor:' + str(self.sensor.get_indoors()))
                print('Mask Disturber:' + str(self.sensor.get_mask_disturber()))
                print('--------------------------')
        else:
            if self.DEBUG:
                print('Se ha detectado algo no controlado aún, ¿Has provocado el irq?')
    """

    def check_exist_strike(self) -> bool:
        """
        Devuelve si ha ocurrido un evento de detección de rayos nuevo.
        :return:
        """
        return len(self.lightnings) > 0

    def get_noise_floor(self) -> int:
        return self.sensor.get_noise_floor()

    def get_distance(self):
        return self.sensor.get_distance()

    def get_type(self):
        return self.sensor.get_interrupt_src()

    def get_energy(self):
        return self.sensor.get_energy()


    def clear_datas(self):
        """

        :return:
        """
        self.lightnings = []

    def get_all_datas(self):
        """
        Devuelve una lista con todas las lecturas si se han podido tomar.
        :return:
        """

        if self.lightnings and len(self.lightnings):
            reads = self.lightnings

            self.clear_datas()

            return reads

        return None
