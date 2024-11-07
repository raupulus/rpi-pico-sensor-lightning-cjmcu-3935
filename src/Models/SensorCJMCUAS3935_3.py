#https://github.com/DFRobot/DFRobot_AS3935/blob/master/MicroPython/DFRobot_AS3935_Lib.py
import utime
from utime import sleep_ms


class SensorCJMCUAS3935:
    def __init__ (self, i2c, address=0x03, debug=False, indoor=True):
        """
        Configura los parámetros principales del AS3935.

        :param i2c: (I2C) Instancia configurada de I2C.
        :param address: (int, opcional) Dirección del dispositivo I2C. Predeterminado = 0x03
        :param debug: (bool, opcional) Indica si habilita depuración y logs. Predeterminado = False
        :param indoor: (bool, opcional) Establece si se inicializa en modo para interior. Predeterminado = True
        """
        self.register = None
        self.address = address
        self.i2cbus = i2c
        self.DEBUG = debug

        self.power_up()
        sleep_ms(200)

        if indoor:
            self.standard_indoor()
        else:
            self.standard_outdoor()

        # Para debug conectar IRQ y GND al osciloscopio y probar con esta configuración:
        # This will dispaly the antenna's resonance frequency/16 on IRQ pin (The resonance frequency will be divided by 16 on this pin)
        # Tuning AS3935_CAPACITANCE to make the frequency within 500/16 kHz plus 3.5% to 500/16 kHz minus 3.5%
        #self.set_lco_fdiv(0)
        #self.set_irq_output_source(3)

    def standard_indoor (self):
        self.set_indoors()
        # self.sensor.set_outdoors()
        self.disturber_en()
        # self.sensor.disturber_dis() # Deshabilita detección de perturbadores
        self.set_irq_output_source(0)
        sleep_ms(500)
        # Antenna tuning capacitance (must be integer multiple of 8, 8 - 120 pf)
        self.set_tuning_caps(96)

        # Set the noise level 1-7
        self.set_noise_floor(2)

        # Umbral para watchdog (0-15)
        self.set_watchdog_threshold(2)

        # SREJ Spike Rejection (0-15)
        self.set_spike_rejection(2)

    def standard_outdoor (self):
        self.set_outdoors()
        self.disturber_en()
        # self.sensor.disturber_dis() # Deshabilita detección de perturbadores
        self.set_irq_output_source(0)
        sleep_ms(500)
        # Antenna tuning capacitance (must be integer multiple of 8, 8 - 120 pf)
        self.set_tuning_caps(96)

        # Set the noise level 1-7
        self.set_noise_floor(2)

        # Umbral para watchdog (0-15)
        self.set_watchdog_threshold(2)

        # SREJ Spike Rejection (0-15)
        self.set_spike_rejection(2)

    def write_byte (self, register, value):
        """
        Escribe un byte en un registro específico.

        :param register: (int) Dirección del registro.
        :param value: (int) Valor a escribir en el registro.
        :return: (int) 1 si la escritura fue exitosa, 0 en caso contrario.
        """
        try:
            self.i2cbus.writeto_mem(self.address, register, bytes([value]))
            return 1
        except:
            return 0

    def read_data (self, register):
        """
        Lee un byte de un registro específico.

        :param register: (int) Dirección del registro.
        """
        self.register = self.i2cbus.readfrom_mem(self.address, register, 1)

    def manual_cal (self, capacitance, location, disturber):
        """
        Realiza una calibración manual del sensor.

        :param capacitance: (int) Valor de capacitancia.
        :param location: (int) Ubicación, 1 para interiores, 0 para exteriores.
        :param disturber: (int) Habilitar (1) o deshabilitar (0) la detección de perturbadores.
        """
        self.power_up()
        if location == 1:
            self.set_indoors()
        else:
            self.set_outdoors()

        if disturber == 0:
            self.disturber_dis()
        else:
            self.disturber_en()

        self.set_irq_output_source(0)
        utime.sleep(0.5)
        self.set_tuning_caps(capacitance)

    def set_tuning_caps (self, cap_val):
        """
        Establece la capacitancia de ajuste.

        :param cap_val: (int) Valor de capacitancia. Solo números divisibles por 8.
        """
        if cap_val > 120:  # Valor fuera de rango, asumir máxima capacitancia
            self.sing_reg_write(0x08, 0x0F,
                                0x0F)  # Configurar bits de capacitancia al máximo
        else:
            self.sing_reg_write(0x08, 0x0F,
                                cap_val >> 3)  # Configurar bits de capacitancia

        self.sing_reg_read(0x08)

        if self.DEBUG: print(
            'Capacitancia configurada a 8x%d' % (self.register[0] & 0x0F))

    def power_up (self):
        """
        Enciende el sensor.
        """
        self.sing_reg_write(0x00, 0x01, 0x00)
        self.cal_rco()  # Ejecutar comando de calibración RCO
        self.sing_reg_write(0x08, 0x20, 0x20)  # Configurar DISP_SRCO a 1
        utime.sleep(0.002)
        self.sing_reg_write(0x08, 0x20, 0x00)  # Configurar DISP_SRCO a 0

    def power_down (self):
        """
        Apaga el sensor.
        """
        self.sing_reg_write(0x00, 0x01, 0x01)

    def cal_rco (self):
        """
        Calibra el oscilador de referencia (RCO).
        """
        self.write_byte(0x3D, 0x96)
        utime.sleep(0.002)

    def set_indoors (self):
        """
        Configura el sensor para operar en interiores.
        """
        self.sing_reg_write(0x00, 0x3E, 0x24)
        if self.DEBUG: print("Configurado para el modelo de interiores")

    def set_outdoors (self):
        """
        Configura el sensor para operar en exteriores.
        """
        self.sing_reg_write(0x00, 0x3E, 0x1C)
        if self.DEBUG: print("Configurado para el modelo de exteriores")

    def disturber_dis (self):
        """
        Deshabilita la detección de perturbadores.
        """
        self.sing_reg_write(0x03, 0x20, 0x20)
        if self.DEBUG: print("Detección de perturbadores deshabilitada")

    def disturber_en (self):
        """
        Habilita la detección de perturbadores.
        """
        self.sing_reg_write(0x03, 0x20, 0x00)
        if self.DEBUG: print("Detección de perturbadores habilitada")

    def sing_reg_write (self, reg_add, data_mask, reg_data):
        """
        Escribe datos en un registro específico.

        :param reg_add: (int) Dirección del registro.
        :param data_mask: (int) Máscara de datos para los bits que se escribirán.
        :param reg_data: (int) Datos a escribir en el registro.
        """
        self.sing_reg_read(reg_add)
        new_reg_data = (self.register[0] & ~data_mask) | (reg_data & data_mask)
        self.write_byte(reg_add, new_reg_data)
        if self.DEBUG: print('Escrito: %02x' % new_reg_data)
        self.sing_reg_read(reg_add)
        if self.DEBUG: print('Actual: %02x' % self.register[0])

    def sing_reg_read (self, reg_add):
        """
        Lee datos de un registro específico.

        :param reg_add: (int) Dirección del registro.
        """
        self.read_data(reg_add)

    def get_interrupt_src (self):
        """
        Obtiene la fuente de la interrupción.

        :return: (int) Código identificando la fuente de la interrupción.
            0 = Fuente desconocida
            1 = Rayo detectado
            2 = Perturbador detectado
            3 = Nivel de ruido demasiado alto
        """
        utime.sleep(0.05)  # Esperar 5ms antes de leer (mínimo 2ms)
        self.sing_reg_read(0x03)
        int_src = self.register[0] & 0x0F

        if int_src == 0x08:
            return 1  # Interrupción causada por rayo
        elif int_src == 0x04:
            return 2  # Perturbador detectado
        elif int_src == 0x01:
            return 3  # Nivel de ruido demasiado alto
        else:
            return 0  # Resultado de interrupción no esperado

    def reset (self):
        """
        Reinicia el sensor.

        :return: (int) 1 si el reinicio fue exitoso, 0 en caso contrario.
        """
        err = self.write_byte(0x3C, 0x96)
        utime.sleep(0.002)  # Esperar 2ms para completar
        return err

    def set_lco_fdiv (self, fdiv):
        """
        Configura la frecuencia de LCO.

        :param fdiv: (int) Valor de la frecuencia.
        """
        self.sing_reg_write(0x03, 0xC0, (fdiv & 0x03) << 6)

    def set_irq_output_source (self, irq_select):
        """
        Configura la fuente de salida IRQ.

        :param irq_select: (int) Fuente de interrupción a mostrar en el pin IRQ.
            0 = NINGUNA
            1 = TRCO (Oscilador de temporización)
            2 = SRCO (Oscilador RC de sincronización)
            3 = LCO (Contador de rayos)
        """
        if irq_select == 1:
            # Establecer solo el bit TRCO (bit 5 en el registro 0x08)
            self.sing_reg_write(0x08, 0xE0, 0x20)
        elif irq_select == 2:
            # Establecer solo el bit SRCO (bit 6 en el registro 0x08)
            self.sing_reg_write(0x08, 0xE0, 0x40)
        elif irq_select == 3:
            # Establecer solo el bit LCO (bit 7 en el registro 0x08)
            self.sing_reg_write(0x08, 0xE0, 0x80)
        else:
            # Limpiar los bits de pantalla IRQ (bits 5, 6 y 7 en el registro 0x08)
            self.sing_reg_write(0x08, 0xE0, 0x00)

    def get_distance (self):
        """
        Obtiene la distancia estimada del rayo.

        :return: (int) Distancia en kilómetros.
        """
        self.sing_reg_read(0x07)
        return self.register[0] & 0x3F

    def get_energy (self):
        """
        Obtiene la energía del rayo detectado.

        :return: (float) Energía del rayo.
        """
        self.sing_reg_read(0x06)
        nrgy_raw = (self.register[0] & 0x1F) << 8
        self.sing_reg_read(0x05)
        nrgy_raw |= self.register[0]
        nrgy_raw <<= 8
        self.sing_reg_read(0x04)
        nrgy_raw |= self.register[0]

        return nrgy_raw / 16777

    def set_min_strikes (self, min_strk):
        """
        Configura el número mínimo de descargas detectadas.

        :param min_strk: (int) Número mínimo de descargas.
        :return: (int) Valor físico configurado (1, 5, 9 o 16 descargas).
        """
        if min_strk < 5:
            self.sing_reg_write(0x02, 0x30, 0x00)
            return 1
        elif min_strk < 9:
            self.sing_reg_write(0x02, 0x30, 0x10)
            return 5
        elif min_strk < 16:
            self.sing_reg_write(0x02, 0x30, 0x20)
            return 9
        else:
            self.sing_reg_write(0x02, 0x30, 0x30)
            return 16

    def clear_statistics (self):
        """
        Limpia las estadísticas del sensor.
        """
        self.sing_reg_write(0x02, 0x40, 0x40)  # alto
        self.sing_reg_write(0x02, 0x40, 0x00)  # bajo
        self.sing_reg_write(0x02, 0x40, 0x40)  # alto

    def get_noise_floor (self):
        """
        Obtiene el nivel de ruido del sensor.

        :return: (int) Nivel de ruido del 0 al 7.
        """
        self.sing_reg_read(0x01)
        return (self.register[0] & 0x70) >> 4

    def set_noise_floor (self, nf_sel):
        """
        Configura el nivel de ruido del sensor.

        :param nf_sel: (int) Nivel de ruido del 0 al 7.
        """
        if nf_sel <= 7:
            self.sing_reg_write(0x01, 0x70, (nf_sel & 0x07) << 4)
        else:
            self.sing_reg_write(0x01, 0x70, 0x20)

    def get_watchdog_threshold (self):
        """
        Obtiene el umbral del watchdog.

        :return: (int) Umbral del watchdog del 0 al 15.
        """
        self.sing_reg_read(0x01)
        return self.register[0] & 0x0F

    def set_watchdog_threshold (self, wdth):
        """
        Configura el umbral del watchdog.

        :param wdth: (int) Umbral del watchdog del 0 al 15.
        """
        self.sing_reg_write(0x01, 0x0F, wdth & 0x0F)

    def get_spike_rejection (self):
        """
        Obtiene el nivel de rechazo de picos del sensor.

        :return: (int) Nivel de rechazo de picos del 0 al 15.
        """
        self.sing_reg_read(0x02)
        return self.register[0] & 0x0F

    def set_spike_rejection (self, srej):
        """
        Configura el nivel de rechazo de picos del sensor.

        :param srej: (int) Nivel de rechazo de picos del 0 al 15.
        """
        self.sing_reg_write(0x02, 0x0F, srej & 0x0F)

    def print_all_regs (self):
        """
        Imprime todos los registros del sensor.
        """
        self.sing_reg_read(0x00)
        if self.DEBUG: print("Reg 0x00: %02x" % self.register[0])
        self.sing_reg_read(0x01)
        if self.DEBUG: print("Reg 0x01: %02x" % self.register[0])
        self.sing_reg_read(0x02)
        if self.DEBUG: print("Reg 0x02: %02x" % self.register[0])
        self.sing_reg_read(0x03)
        if self.DEBUG: print("Reg 0x03: %02x" % self.register[0])
        self.sing_reg_read(0x04)
        if self.DEBUG: print("Reg 0x04: %02x" % self.register[0])
        self.sing_reg_read(0x05)
        if self.DEBUG: print("Reg 0x05: %02x" % self.register[0])
        self.sing_reg_read(0x06)
        if self.DEBUG: print("Reg 0x06: %02x" % self.register[0])
        self.sing_reg_read(0x07)
        if self.DEBUG: print("Reg 0x07: %02x" % self.register[0])
        self.sing_reg_read(0x08)
        if self.DEBUG: print("Reg 0x08: %02x" % self.register[0])
        self.sing_reg_read(0x3A)
        if self.DEBUG: print("Reg 0x3A: %02x" % self.register[0])
        self.sing_reg_read(0x3B)
        if self.DEBUG: print("Reg 0x3B: %02x" % self.register[0])
