from machine import Pin, SPI, I2C
from time import sleep_ms

#https://www.embeddedadventures.com/datasheets/AS3935_Datasheet_EN_v2.pdf
#https://www.improwis.com/projects/sw_chip_AS3935/
#https://www.improwis.com/projects/sw_chip_AS3935/as3935.py

class SensorCJMCUAS3935:
    def __init__ (self, i2c=None, spi=None, address=None, debug=False):
        """Inicializa la instancia del sensor CJMCU AS3935.

        Uno de `i2c` o `spi` debe ser proporcionado.

        Parameters
        ----------
        i2c : I2C, optional
            Instancia configurada de I2C.
        spi : SPI, optional
            Instancia configurada de SPI.
        address : int, optional
            Dirección I2C del sensor o pin CS para SPI
        debug : bool, optional
            Si es True, mostrará información de depuración, por defecto False
        """
        self.DEBUG = debug
        self.i2c = i2c
        self.spi = spi

        if i2c is not None:
            self.address = address
            # Imprime información de depuración si DEBUG es True
            if self.DEBUG:
                print('Escaneando dispositivos I2C en el bus:')
                print(self.i2c.scan())
        elif spi is not None:
            self.cs = Pin(address, Pin.OUT)
        else:
            raise ValueError(
                "Uno de los argumentos i2c o spi debe ser proporcionado.")

        # Inicializa la estructura de los registros
        self.registers = bytearray(8)

    def calibrate (self, tun_cap=None):
        """Calibra el sensor AS3935. Esto puede tomar hasta medio segundo.

        Parameters
        ----------
        tun_cap : int, optional
            Valor entre 0 y 15 para configurar los condensadores internos de ajuste (0-120pF en pasos de 8pF).
            Si se pasa None, se calibrará automáticamente usando una fuente de reloj interna, por defecto None.
        """
        """Calibra el sensor AS3935."""
        sleep_ms(80)
        self.read_data()

        # Verifica que se han leído los registros correctamente
        if len(self.registers) < 9:
            raise Exception(
                "No se leyeron correctamente los registros del sensor")

        if tun_cap is not None:
            if 0 <= tun_cap < 16:
                self.set_byte(0x08, (self.registers[0x08] & 0xF0) | tun_cap)
                sleep_ms(2)
            else:
                raise ValueError("TUN_CAP debe estar entre 0 y 15")

        self.set_byte(0x3D, 0x96)
        sleep_ms(2)
        self.read_data()
        self.set_byte(0x08, self.registers[0x08] | 0x20)
        sleep_ms(2)
        self.set_byte(0x08, self.registers[0x08] & 0xDF)
        sleep_ms(2)

    def reset (self):
        """Restablece todos los registros a su valor predeterminado en la alimentación."""
        self.set_byte(0x3C, 0x96)

    def get_interrupt (self):
        """Obtiene el valor del registro de interrupciones.

        Returns
        -------
        int
            Valor entre 0-15 representando el motivo de la interrupción (ruido, perturbador, relámpago).
            El valor devuelto es una combinación bit a bit de las cuatro siguientes alertas:
            0x01: Demasiado ruido -> significa que el sensor ha detectado un nivel de ruido que podría interferir con la detección de relámpagos.
            0x04: Perturbador detectado -> se ha detectado un posible evento de relámpago, pero la fuente es probablemente una interferencia (por ejemplo, motores, interruptores).
            0x08: Relámpago detectado -> se ha identificado un evento de relámpago.
            Por lo tanto, el valor devuelto puede ser cualquier número entre 0 y 15, cada uno representa una combinación única de las condiciones anteriores.

            Un valor de 7 (0x07) significaría que el sensor ha registrado demasiado ruido, un perturbador detectado y un relámpago detectado.
            Un valor de 3 (0x03) indicaría que el sensor ha registrado demasiado ruido y un perturbador detectado.
            Un valor de 12 (0x0C) indicaría un perturbador y un relámpago detectados.
        """
        self.read_data()
        return self.registers[0x03] & 0x0F

    def get_distance (self):
        """Obtiene la distancia estimada del evento de rayo más reciente.

        Returns
        -------
        int
            Valor entre 0-63 estimando la distancia hasta el evento de rayo en kilómetros, un valor de 63 significa fuera de rango.
        """
        self.read_data()
        return (self.registers[0x07] & 0x3F) if (self.registers[0x07] & 0x3F) != 0x3F else False

    def get_energy (self):
        """Obtiene la energía calculada del evento de rayo más reciente.

        Returns
        -------
        int
            Valor de energía calculado del evento de rayo.
        """
        self.read_data()
        return ((self.registers[0x06] & 0x1F) << 16) | (self.registers[0x05] << 8) | self.registers[0x04]

    def get_noise_floor (self):
        """Obtiene el valor del piso de ruido.

        Returns
        -------
        int
            Nivel de piso de ruido en el sensor en pasos de milivoltios.
        """
        self.read_data()
        return (self.registers[0x01] & 0x70) >> 4

    def set_noise_floor (self, noisefloor):
        """Establece el nivel de piso de ruido.

        Parameters
        ----------
        noisefloor : int
            Nivel de piso de ruido deseado en pasos de milivoltios.
        """
        self.read_data()
        noisefloor = (noisefloor & 0x07) << 4
        write_data = (self.registers[0x01] & 0x8F) + noisefloor
        self.set_byte(0x01, write_data)

    def get_indoors (self):
        """Determina si el sensor está configurado para uso en interiores.

        Returns
        -------
        bool
            True si está configurado para interiores, False en caso contrario.
        """
        self.read_data()
        return bool(self.registers[0x00] & 0x20)

    def set_indoors (self, indoors):
        """Establece si el sensor debe usar una configuración interior.

        Parameters
        ----------
        indoors : bool
            True para configurar el sensor para interiores, False para exteriores.
        """
        self.read_data()
        write_value = (self.registers[0x00] & 0xC1) | (
            0x24 if indoors else 0x1C)
        self.set_byte(0x00, write_value)

    def set_byte(self, register, value):
        """Escribe un byte en una dirección de registro específica del sensor."""
        if register < len(self.registers):
            if self.i2c is not None:
                self.i2c.writeto(self.address, bytes([register, value]))
            elif self.spi is not None:
                self.cs.value(0)  # CS en LOW
                sleep_ms(1)  # Espera para estabilizar

                self.spi.write(bytes([register | 0x80,
                                      value]))  # Ajusta para operación de escritura
                self.cs.value(1)  # CS en HIGH
        else:
            raise IndexError(f"Registro fuera de rango: {register}")

    def read_data (self):
        """Lee un bloque de datos desde el sensor y lo almacena.

        Este método no lee registros exactos, ya que necesitamos actualizar todos los registros de una vez.

        Este método raramente debería ser llamado directamente.
        """
        if self.i2c is not None:
            self.i2c.readfrom_into(self.address, self.registers)
        elif self.spi is not None:
            self.cs.value(0)  # CS en LOW
            sleep_ms(1)  # Espera para estabilizar

            # Envía el comando de lectura
            self.spi.write(bytes([0x00]))  # Comando para leer registros
            self.spi.readinto(self.registers)  # Lee los registros en el buffer
            self.cs.value(1)  # CS en HIGH
            print("Registros leídos:", self.registers)



    def set_mask_disturber (self, mask_dist):
        """
        Establece si los perturbadores deben ser enmascarados (no interrupciones para
        lo que el sensor determina son eventos de origen humano)

        Parameters
        ----------
        mask_dist : bool
            Si es True, enmascara los eventos de perturbación. Si es False, eventos de perturbaciones generan una interrupción.
        """
        self.read_data()
        self.set_byte(0x03, (self.registers[0x03] | 0x20) if mask_dist else
        self.registers[0x03] & 0xDF)

    def get_mask_disturber (self):
        """
        Obtiene si los perturbadores están enmascarados o no.

        Returns
        -------
        bool
            True si las interrupciones están enmascaradas, False en caso contrario.
        """
        self.read_data()
        return bool(self.registers[0x03] & 0x20)

    def set_disp_lco (self, display_lco):
        """
        Hace que la señal interna del oscilador LC se muestre en el pin de interrupción para su medición.

        Parameters
        ----------
        display_lco : bool
            Si es True, habilita la salida. Si es False, la deshabilita.
        """
        self.read_data()
        self.set_byte(0x08, (self.registers[0x08] | 0x80) if display_lco else
        self.registers[0x08] & 0x7F)

    def get_disp_lco (self):
        """
        Determina si el oscilador LC interno se muestra en el pin de interrupción.

        Returns
        -------
        bool
            True si el oscilador LC se muestra en el pin de interrupción, False en caso contrario.
        """
        self.read_data()
        return bool(self.registers[0x08] & 0x80)
