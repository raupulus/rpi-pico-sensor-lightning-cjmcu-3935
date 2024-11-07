import utime


#https://github.com/ecodina/python_as3935/blob/master/as3935/AS3935.py


INT_NH = 0b0001
INT_D = 0b0100
INT_L = 0b1000


class SensorCJMCUAS3935:
    def __init__ (self, i2c, address=0x03, debug=False):
        """
        Configure the main parameters of AS3935.

        :param i2c: (I2C) Instancia configurada de I2C.
        :param address: (int, optional) Dirección del dispositivo I2C. Default = 0x03
        :param debug: (bool, optional) Indica si habilita depuración y logs. Default = False
        """
        self.address = address
        self.i2c = i2c
        self.DEBUG = debug

    # ------ FUNCIONES CRUZADAS ------ #

    def read_byte (self, register):
        """
        Returns the value of the byte stored at register.

        :param register: (int) the register to read from
        :return: (int) the value of the register
        """
        return self.i2c.readfrom_mem(self.address, register, 1)[0]

    def write_byte (self, register, value):
        """
        Writes value at register. Raises ValueError if the value is not correct.
        It sleeps for 2 ms after writing the value

        :param register: (int) the register to write to
        :param value: (int) the byte value (between 0x00 and 0xFF)
        """
        if not 0 <= value <= 255:
            raise ValueError("The value should be between 0x00 and 0xFF")
        self.i2c.writeto_mem(self.address, register, bytearray([value]))
        utime.sleep_ms(2)

    def full_calibration (self, tuning_cap):
        """
        Performs a full calibration: antenna and RCO

        :param tuning_cap: int: tuning number for the antenna. Can be calculated with self.calculate_tuning_cap()
        """
        self.set_tune_antenna(tuning_cap)
        self.calibrate_trco()

    # ------ MODOS DE OPERACIÓN ------ #

    def power_down_mode (self):
        """
        Sets the AS3935 on power down mode (PWD)
        """
        self.write_byte(0x00, self.read_byte(0x00) & 0b11111111)

    def listening_mode (self):
        """
        Sets the AS3935 on listening mode (PWD)
        """
        self.write_byte(0x00, self.read_byte(0x00) & 0b11111110)

    # ------ COMANDOS DIRECTOS ------ #

    def set_default_values (self):
        """
        Sends a direct command to 0x3C to reset to default values.
        """
        self.write_byte(0x3C, 0x96)

    def calibrate_rco (self):
        """
        Sends a direct command to 0x3D to calibrate the RCO (CALIB_RCO)
        """
        self.write_byte(0x3D, 0x96)

    def calibrate_trco(self):
        """
        Calibrate TRCO by setting the appropriate bit and restore after a short pause.
        """
        original_value = self.read_byte(0x08)
        self.write_byte(0x08, original_value | 0x08)
        utime.sleep_ms(2)
        self.write_byte(0x08, original_value & ~0x08)

    # ------ AFE Y WATCHDOG ------ #

    def get_indoors (self):
        """
        Checks whether the device is configured to be run indoors. (AFE_GB)

        :return: (bool) whether the device is configured to be run indoors
        """
        return self.read_byte(0x00) & 0b100000 == 0b100000

    def set_indoors (self, indoors):
        """
        Configures the device to be run indoors or outdoors. (AFE_GB)

        :param indoors: (bool) configure the AS3935 to be run indoors
        """
        current_value = self.read_byte(0x00)
        if indoors:
            write_value = (current_value & 0b11000001) | 0b100100
        else:
            write_value = (current_value & 0b11000001) | 0b11100
        self.write_byte(0x00, write_value)

    def get_watchdog_threshold (self):
        """
        Returns the watchdog threshold (WDTH)

        :return: (int) the current watchdog threshold
        """
        return self.read_byte(0x01) & 0b00001111

    def set_watchdog_threshold (self, value=0b0001):
        """
        Sets the watchdog threshold to value (WDTH). If called without parameters,
        it sets it to the default configuration.
        Can raise a ValueError if not 0 <= value <= 0b1111

        :param value: (int, optional) The value to be set. From 0b0000 to 0b1111. Default=0b0001
        """
        if not 0 <= value <= 0b1111:
            raise ValueError("Value should be from 0b0010 to 0b1111")
        self.write_byte(0x01, (self.read_byte(0x01) & 0x11110000) | value)

    # ------ CALIBRACIÓN DE RUIDO ------ #

    def get_noise_floor (self):
        """
        Checks the current noise floor threshold (NF_LEV).

        :return: (int) the current noise floor threshold
        """
        return (self.read_byte(0x01) & 0b1110000) >> 4

    def set_noise_floor (self, noise_floor=0b010):
        """
        Sets a new noise floor threshold (NF_LEV). If called without parameters, it sets it to the default configuration.
        Can raise a ValueError if not 0 <= noise_floor <= 0b111

        :param noise_floor: (int, optional) The value to be set. From 0b000 to 0b111
        """
        if not 0 <= noise_floor <= 0b1111:
            raise ValueError("noise_floor should be from 0b000 to 0b111")
        self.write_byte(0x01, (self.read_byte(0x01) & 0b10001111) + (
                    (noise_floor & 0x07) << 4))

    def lower_noise_floor (self, min_noise=0b000):
        """
        Lowers the noise floor threshold by one step (subtracts 1 to the current NF_LEV)
        if it is currently higher than min_noise.
        Can raise a ValueError if not 0 <= min_noise <= 0b111

        :param min_noise: (int, optional) the minimum NF_LEV the device should be set at. Default = 0b000
        :return: (int) the new noise floor threshold
        """
        if not 0 <= min_noise <= 0b1111:
            raise ValueError("min_noise should be from 0b000 to 0b111")
        floor = self.get_noise_floor()
        if floor > min_noise:
            floor = floor - 1
            self.set_noise_floor(floor)
        return floor

    def raise_noise_floor (self, max_noise=0b111):
        """
        Raises the noise floor threshold by one step (adds 1 to the current NF_LEV)
        if it is currently lower than max_noise
        Can raise a ValueError if not 0 <= max_noise <= 0b111

        :param max_noise: (int, optional) the maximum  NF_LEV the device should be set at. Default 0b111
        :return: (int) the new noise floor threshold
        """
        if not 0 <= max_noise <= 0b1111:
            raise ValueError("max_noise should be from 0b000 to 0b111")
        floor = self.get_noise_floor()
        if floor < max_noise:
            floor = floor + 1
            self.set_noise_floor(floor)
        return floor

    # ------ ALGORITMO DE RAYOS ------ #

    def get_spike_rejection (self):
        """
        Checks the current spike rejection settings (SREJ)

        :return: (int) the current spike rejection setting (SREJ)
        """
        return self.read_byte(0x02) & 0b00001111

    def set_spike_rejection (self, value=0b0010):
        """
        Sets a new setting for the spike rejection algorithm (SREJ). If the function is called without any parameter,
        it sets it to the default value of 0b0010
        Can raise a ValueError if not 0 <= value <= 0b1111

        :param value: (int, optional) the value to set SREJ. Default = 0b0010
        """
        if not 0 <= value <= 0b1111:
            raise ValueError("Value should be from 0b0000 to 0b1111")
        clean_byte = self.read_byte(0x02) & 0b11110000
        self.write_byte(0x02, clean_byte | value)

    def get_energy (self):
        """
        Checks the last lightning strike's energy calculation. It does not have any physical meaning.
        (Energy of the Single Lightning *SBYTE)

        :return: (int) last strike's energy
        """
        return ((self.read_byte(0x06) & 0x1F) << 16) | (
                    self.read_byte(0x05) << 8) | self.read_byte(0x04)

    def get_distance (self):
        """
        Checks the estimation of the last lightning strike's distance in km (DISTANCE).

        :return: (int/None) last strike's distance in km. None if out of range, 0 if overhead
        """
        dist = self.read_byte(0x07) & 0b00111111
        if dist == 0b111111:
            return None
        elif dist == 0b000001:
            return 0
        return dist

    def get_interrupt (self):
        """
        Checks the reason of the interruption (INT). To know what it is, use the constants:
            INT_NH: noise level too high
            INT_D: disturber detected
            INT_L: lightning strike detected

        It sleeps for 2 ms before retrieving the value, as specified at the datasheet.

        :return: (int) the interruption reason
        """
        utime.sleep_ms(2)
        return self.read_byte(0x03) & 0x0F

    def set_mask_disturber (self, mask_dist):
        """
        Sets whether disturbers should be masked (MASK_DIST).

        :param mask_dist: (bool) whether disturbers should be masked
        """
        if mask_dist:
            self.write_byte(0x03, self.read_byte(0x03) | 0b100000)
        else:
            self.write_byte(0x03, self.read_byte(0x03) & 0b11011111)

    def get_mask_disturber (self):
        """
        Checks whether disturbers are currently masked (MASK_DIST).

        :return: (bool) whether disturbers are currently masked
        """
        return self.read_byte(0x03) & 0b100000 == 0b100000

    def get_min_strikes (self):
        """
        Checks the current configuration of how many strikes AS3935 has to detect in 15 minutes to issue an interrupt
        (MIN_NUM_LIG).
        In case of an error, it raises a LookupError

        :return: (int) number of strikes. Possible values: 1, 5, 9, 16
        """
        bin_min = self.read_byte(0x02) & 0b00110000
        if bin_min == 0b00000000:
            return 1
        elif bin_min == 0b00010000:
            return 5
        elif bin_min == 0b00100000:
            return 9
        elif bin_min == 0b00110000:
            return 16
        raise LookupError("Could not get MIN_NUM_LIGH")

    def set_min_strikes (self, min_strikes):
        """
        Sets the minumum number of lightning strikes the AS3935 has to detect in 15 minutes to issue an interrupt
        (MIN_NUM_LIG).
        Can raise a ValueError if min_strikes is not an accepted value.

        :param min_strikes: (int) min number of strikes to issue an interrupt. Possible values: 1, 5, 9, 16
        """
        if min_strikes == 1:
            bin_min = 0b00000000
        elif min_strikes == 5:
            bin_min = 0b00010000
        elif min_strikes == 9:
            bin_min = 0b00100000
        elif min_strikes == 16:
            bin_min = 0b00110000
        else:
            raise ValueError("Allowed values for min_strikes: 1, 5, 9, 16.")
        self.write_byte(0x02, (self.read_byte(0x02) & 0b11001111) | bin_min)

    def clear_lightning_stats (self):
        """
        Clears the statistics built up by the lightning distance estimation algorithm (CL_STAT)
        """
        original_byte = self.read_byte(0x02)
        self.write_byte(0x02, original_byte & 0b10111111)
        utime.sleep_ms(1)
        self.write_byte(0x02, original_byte)

    # ------ SINTONIZACIÓN DE ANTENA ------ #

    def get_display_lco (self):
        """
        Checks whether the antenna resonance frequency is currently displayed on the IRQ pin (DISP_LCO)

        :return: (bool) whether the antenna resonance frequency is currently displayed
        """
        return self.read_byte(0x08) & 0b10000000 == 0b10000000

    def set_display_lco (self, display_lco):
        """
        Sets whether the antenna resonance frequency should be displayed on the IRQ pin(DISP_LCO).

        :param display_lco: (bool) whether the antenna resonance frequency should be displayed
        """
        current_value = self.read_byte(0x08)
        if display_lco:
            self.write_byte(0x08, (current_value | 0x80))
        else:
            self.write_byte(0x08, (current_value & 0x7F))

    def set_tune_antenna (self, tuning_cap):
        """
        Sets the antenna calibration. It adds or removes internal capacitors according to tuning_cap (TUN_CAP).
        If tuning_cap is unknown, this could be calculated by calculate_tuning_cap(self, frequency_divisor, tries_frequency)
        Can raise a ValueError if not 0 <= tuning_cap <= 15

        :param tuning_cap: (int) the number to calibrate the antenna
        """
        if not 0 <= tuning_cap <= 15:
            raise ValueError(
                "The value of the tuning_cap should be less than 15.")
        self.write_byte(0x08, (self.read_byte(0x08) & 0b11110000) | tuning_cap)

    def get_frequency_division_ratio (self):
        """
        Gets the current frequency division ratio. Number by which the real antenna resonance frequency is divided to
        display on the IRQ pin (LCO_FDIV).
        Can raise a LookupError if there is an error checkig the configuration.

        :return: (int) frequency division ratio. Possible numbers: 16, 32, 64, 128
        """
        lco_fdiv = self.read_byte(0x03) & 0b11000000
        if lco_fdiv == 0:
            return 16
        elif lco_fdiv == 64:
            return 32
        elif lco_fdiv == 128:
            return 64
        elif lco_fdiv == 192:
            return 128
        raise LookupError("Could not get the LCO_FDIV value.")

    def set_frequency_division_ratio (self, divisor=16):
        """
        Sets a new frequency division ration by which the antenna resonance frequency is divided to display on the IRQ pin
        (LCO_FDIV).If called with no parameter, it defaults to 16.
        Can raise a ValueError if *divisor* is not an accepted number.

        :param divisor: (int, optional) frequency divisor ratio. Accepted values = (16, 32, 64, 128). Default = 16
        """
        values = { 16: 0b0, 32: 0b01000000, 64: 0b10000000, 128: 0b11000000 }
        if divisor not in values:
            raise ValueError("Accepted values: 16, 32, 64, 128")
        new_lco_fdiv = (self.read_byte(0x03) & 0b00111111) | values[divisor]
        self.write_byte(0x03, new_lco_fdiv)

    # ------ GENERACIÓN DE RELOJ ------ #

    def get_display_srco (self):
        """
        Checks whether the SRCO frequency is being displayed on the IRQ pin.

        :return: (bool) whether the SRCO frequency is currently displayed
        """
        return self.read_byte(0x08) & 0b01000000 == 0b01000000

    def set_display_srco (self, display_srco):
        """
        Sets whether the SRCO frequency should be displayed on the IRQ pin.

        :param display_srco: (bool) whether the SRCO frequency should be displayed
        """
        current_value = self.read_byte(0x08)
        if display_srco:
            self.write_byte(0x08, (current_value | 0b01000000))
        else:
            self.write_byte(0x08, (current_value & 0b10111111))

    def get_display_trco (self):
        """
        Checks' whether the TRCO frequency is being displayed on the IRQ pin.

        :return: (bool) whether the TRCO frequency is currently displayed
        """
        return self.read_byte(0x08)

    def set_display_trco (self, display_trco):
        """
        Sets whether the TRCO frequency should be displayed on the IRQ pin.

        :param display_trco: (bool) whether the TRCO frequency should be displayed
        """
        current_value = self.read_byte(0x08)
        if display_trco:
            self.write_byte(0x08, (current_value | 0x04))
        else:
            self.write_byte(0x08, (current_value & ~0x04))