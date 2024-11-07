from time import sleep_ms


class SensorCJMCUAS3935:
    def __init__ (self, i2c, address=0x03, debug=False, indoor=True):
        """
        Inicializa la instancia del sensor CJMCU AS3935.

        Parámetros
        ----------
        i2c : I2C
            Instancia configurada de I2C.
        address : int, opcional
            Dirección I2C del sensor (por defecto es 0x03).
        debug : bool, opcional
            Si es True, mostrará información de depuración. Por defecto es False.
        indoor : bool, opcional
            Si es True, configura el sensor para su uso en interiores. Por defecto es True.
        """
        self.DEBUG = debug
        self.i2cbus = i2c
        self.address = address

        # Inicializa la estructura de los registros
        self.registers = None

        self.set_indoors(indoor)
        self.set_noise_floor(0)
        self.calibrate(tun_cap=0x0F)

    def get_interrupt_src (self):
        """
        Obtiene el origen de la interrupción.

        Retorna:
        --------
        0 : No hay interrupción.
        1 : Se detectó un rayo.
        2 : Se detectó un perturbador.
        3 : Nivel de ruido demasiado alto.
        """
        reason = self.get_interrupt()
        if reason == 0x01:
            if self.DEBUG:
                print("Nivel de ruido demasiado alto - ajustando")
            self.raise_noise_floor()
            return 3
        elif reason == 0x04:
            if self.DEBUG:
                print("Perturbador detectado - enmascarando")
            self.set_mask_disturber(True)
            return 2
        elif reason == 0x08:
            if self.DEBUG:
                print("¡Se detectó un rayo!")
            return 1
        return 0

    def calibrate (self, tun_cap=None):
        """
        Calibra el sensor de rayos. Este proceso puede durar hasta medio segundo
        y es bloqueante.

        El valor de tun_cap debe estar entre 0 y 15 y se utiliza para configurar
        los condensadores de ajuste internos (de 0 a 120pF en pasos de 8pF).
        """
        sleep_ms(80)
        self.read_data()
        if tun_cap is not None:
            if 0 <= tun_cap < 0x10:
                self.set_byte(0x08, (self.registers[0x08] & 0xF0) | tun_cap)
                sleep_ms(3)
            else:
                raise ValueError("El valor de TUN_CAP debe estar entre 0 y 15")
        self.set_byte(0x3D, 0x96)
        sleep_ms(3)

        self.read_data()
        self.set_byte(0x08, self.registers[0x08] | 0x20)
        sleep_ms(3)
        self.set_byte(0x08, self.registers[0x08] & 0xDF)
        sleep_ms(3)

    def reset (self):
        """
        Resetea todos los registros a sus valores predeterminados de encendido.
        """
        self.set_byte(0x3C, 0x96)

    def get_interrupt (self):
        """
        Obtiene el valor del registro de interrupción.

        Retorna:
        --------
        0x01 - Ruido excesivo
        0x04 - Perturbador
        0x08 - Rayo detectado
        """
        self.read_data()
        return self.registers[0x03] & 0x0F

    def get_distance (self):
        """
        Obtiene la distancia estimada del evento de rayo más reciente.

        Retorna:
        --------
        False si no hay datos disponibles.
        Un valor numérico con la distancia estimada.
        """
        self.read_data()
        if self.registers[0x07] & 0x3F == 0x3F:
            return False
        else:
            return self.registers[0x07] & 0x3F

    def get_energy (self):
        """
        Obtiene la energía calculada del evento de rayo más reciente.

        Retorna:
        --------
        Un valor entero representando la energía.
        """
        self.read_data()
        return ((self.registers[0x06] & 0x1F) << 16) | (
                    self.registers[0x05] << 8) | self.registers[0x04]

    def get_noise_floor (self):
        """
        Obtiene el valor del piso de ruido (nivel mínimo de ruido aceptable).

        Retorna:
        --------
        Un valor entre 0 y 7 que representa el nivel de ruido.
        """
        self.read_data()
        return (self.registers[0x01] & 0x70) >> 4

    def set_noise_floor (self, noisefloor):
        """
        Configura el valor del piso de ruido.

        El valor de noisefloor debe estar entre 0 y 7, ya que este es el rango
        del registro en el sensor.
        """
        self.read_data()
        noisefloor = (noisefloor & 0x07) << 4
        write_data = (self.registers[0x01] & 0x8F) + noisefloor
        self.set_byte(0x01, write_data)

    def lower_noise_floor (self, min_noise=0):
        """
        Reduce el piso de ruido en un paso, sin bajar de un valor mínimo.

        Parámetros:
        -----------
        min_noise : int
            El valor mínimo del piso de ruido (por defecto 0).

        Retorna:
        --------
        El nuevo valor del piso de ruido.
        """
        floor = self.get_noise_floor()
        if floor > min_noise:
            floor -= 1
            self.set_noise_floor(floor)
        return floor

    def raise_noise_floor (self, max_noise=7):
        """
        Aumenta el piso de ruido en un paso, sin exceder un valor máximo.

        Parámetros:
        -----------
        max_noise : int
            El valor máximo del piso de ruido (por defecto 7).

        Retorna:
        --------
        El nuevo valor del piso de ruido.
        """
        floor = self.get_noise_floor()
        if floor < max_noise:
            floor += 1
            self.set_noise_floor(floor)
        return floor

    def get_min_strikes (self):
        """
        Obtiene el número de detecciones de rayos necesarias antes de generar
        una interrupción.

        Retorna:
        --------
        El número de rayos mínimos requeridos para generar una interrupción.
        """
        self.read_data()
        value = (self.registers[0x02] >> 4) & 0x03
        return { 0: 1, 1: 5, 2: 9, 3: 16 }.get(value, 1)

    def set_min_strikes (self, minstrikes):
        """
        Configura el número de detecciones de rayos necesarias antes de generar
        una interrupción.

        Parámetros:
        -----------
        minstrikes : int
            El número de rayos mínimos necesarios. Puede ser 1, 5, 9 o 16.
        """
        if minstrikes not in [1, 5, 9, 16]:
            raise ValueError("El valor debe ser 1, 5, 9 o 16.")

        mapping = { 1: 0, 5: 1, 9: 2, 16: 3 }
        minstrikes = mapping[minstrikes] << 4

        self.read_data()
        write_data = (self.registers[0x02] & 0xCF) | minstrikes
        self.set_byte(0x02, write_data)

    def get_indoors (self):
        """
        Determina si el sensor está configurado para uso en interiores.

        Retorna:
        --------
        True si está configurado para interiores, False si no lo está.
        """
        self.read_data()
        return bool(self.registers[0x00] & 0x20)

    def set_indoors (self, indoors):
        """
        Configura el sensor para uso en interiores o exteriores.

        Parámetros:
        -----------
        indoors : bool
            Si es True, configura el sensor para interiores, si es False,
            para exteriores.
        """
        self.read_data()
        write_value = (self.registers[0x00] & 0xC1) | (
            0x24 if indoors else 0x1C)
        self.set_byte(0x00, write_value)

    def set_mask_disturber (self, mask_dist):
        """
        Configura si los perturbadores deben ser enmascarados (sin interrupciones
        para lo que el sensor detecta como eventos creados por humanos).

        Parámetros:
        -----------
        mask_dist : bool
            Si es True, se enmascaran los perturbadores, si es False, no se enmascaran.
        """
        self.read_data()
        write_value = self.registers[0x03] | 0x20 if mask_dist else \
        self.registers[0x03] & 0xDF
        self.set_byte(0x03, write_value)

    def get_mask_disturber (self):
        """
        Obtiene si los perturbadores están enmascarados o no.

        Retorna:
        --------
        True si los perturbadores están enmascarados, False si no lo están.
        """
        self.read_data()
        return bool(self.registers[0x03] & 0x20)

    def set_disp_lco (self, display_lco):
        """
        Activa o desactiva la señal del oscilador LC interno en el pin de interrupción.

        Parámetros:
        -----------
        display_lco : bool
            Si es True, muestra la señal LC en el pin de interrupción. Si es False,
            la desactiva.
        """
        self.read_data()
        if display_lco:
            self.set_byte(0x08, self.registers[0x08] | 0x80)
        else:
            self.set_byte(0x08, self.registers[0x08] & 0x7F)
        sleep_ms(3)

    def get_disp_lco (self):
        """
        Verifica si la señal del oscilador LC se está mostrando en el pin de interrupción.

        Retorna:
        --------
        True si la señal LC está en el pin de interrupción, False si no lo está.
        """
        self.read_data()
        return bool(self.registers[0x08] & 0x80)

    def set_byte (self, register, value):
        """
        Escribe un byte en una dirección específica del sensor.

        Este método debería usarse de manera interna, no directamente.
        """
        self.i2cbus.writeto_mem(self.address, register, bytes([value]))

    def read_data (self):
        """
        Lee un bloque de datos del sensor y lo almacena en la variable 'registers'.

        Este método no lee registros exactos debido a las limitaciones de las
        bibliotecas de I2C en MicroPython.
        """
        self.registers = self.i2cbus.readfrom_mem(self.address, 0x00,
                                                  16)  # 16 bytes desde la dirección 0x00
