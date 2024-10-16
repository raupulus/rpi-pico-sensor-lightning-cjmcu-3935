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


from machine import Pin, I2C
import datetime
from time import sleep_ms
from SensorCJMCUAS3935 import SensorCJMCUAS3935


class Lightning:
    sensor = None
    lightnings = []

    def __init__(self, scl=21, sda=20, debug=False, indoor=True,
                 pin_irq=26):
        # Marco el modo debug para el modelo.
        self.DEBUG = debug

        # Aplico parámetros de configuración para que trabaje el modelo.
        sleep_ms(200)
        #self.sensor.set_indoors(indoor)
        sleep_ms(200)
        #self.sensor.set_noise_floor(0)
        sleep_ms(200)
        #self.sensor.calibrate(tun_cap=0x0F)
        sleep_ms(1000)

        # Preparo la conexión i2c
        i2c = I2C(0, scl=Pin(scl), sda=Pin(sda), freq=400000)

        if self.DEBUG:
            print('Escaneando dispositivos i2c en el bus:')
            print(self.i2c.scan())

        # Configuro el pin de interrupción cuando se detecta eventos
        pin = Pin(pin_irq, Pin.IN, Pin.PULL_UP)

        # Inicio Callback para en cada detección registrar rayo
        pin.irq(trigger=Pin.IRQ_FALLING, handler=self.handle_interrupt)

        # Instancio el sensor como atributo de este modelo.
        self.sensor = SensorCJMCUAS3935(scl=21, sda=20, debug=False, indoor=True,
                 pin_irq=26)  # Todo: plantear sensor

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

        # Momento actual en formato timestamp.
        now = datetime.datetime.utcnow()

        reason = sensor.get_interrupt()

        if reason == 0x01:
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
                "strike": self.strike(),
                "distance": self.distance(),
                "type": self.type(),
                "energy": self.energy(),
                "created_at": datetime.datetime.utcnow
            })

            if self.DEBUG:
                distance = sensor.get_distance()

                print('--------------------------')
                print('¡Se ha detectado un posible RAYO!')
                print('Timestamp: ' + str(now))
                print('rayo detectado')
                print("Está a " + str(distance) + "km de distancia. (%s)" % now)
                print("------------------------")
                print("All Data:")
                print('Distance:' + str(self.sensor.get_distance()))
                print('Interrupt:' + str(self.sensor.get_interrupt()))
                print('Energy:' + str(self.sensor.get_energy()))
                print('Noise Floor:' + str(self.sensor.get_noise_floor()))
                print('In Indoor:' + str(self.sensor.get_indoors()))
                print(
                    'Mask Disturber:' + str(self.sensor.get_mask_disturber()))
                print('Dis.lco:' + str(self.sensor.get_disp_lco()))
                print('--------------------------')
        else:
            if self.DEBUG:
                print('Se ha detectado algo no controlado aún')

    def strike(self):
        return None

    def distance(self):
        return self.sensor.get_distance()

    def type(self):
        return self.sensor.get_interrupt()

    def energy(self):
        return self.sensor.get_energy()

    def get_all_datas(self):
        """
        Devuelve una lista con todas las lecturas si se han podido tomar.
        :return:
        """

        if self.lightnings and len(self.lightnings):
            reads = self.lightnings
            self.lightnings = []

            return reads

        return None
