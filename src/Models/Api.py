#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import urequests
#import ujson
import utime

class Api:
    """
    A class representing an API connection with methods to interact with the endpoint.

    :param controller: The controller object for raspberry pi pico.
    :param url: The base URL of the API.
    :param path: The specific path for the API endpoint.
    :param token: The authentication token for accessing the API.
    :param device_id: The unique identifier of the device.
    :param debug: Optional boolean flag for debugging mode.
    """

    def __init__ (self, controller, url, path, token, device_id, debug=False):
        self.URL = url
        self.TOKEN = token
        self.DEVICE_ID = device_id
        self.URL_PATH = path
        self.CONTROLLER = controller
        self.DEBUG = debug

    def save_lightnings (self, lightnings) -> bool:
        """
        Guarda los datos en la API.
        :return:
        """
        headers = {
            "Authorization": "Bearer " + self.TOKEN,
            "Content-Type": "application/json"
        }

        url = self.URL + '/' + self.URL_PATH

        try:
            # Preparo cuanto hace de la lectura del rayo
            for lightning in lightnings:
                lightning["read_seconds_ago"] = (utime.time() - lightning["timestamp_read"]) + 1

            payload = {
                "lightnings": lightnings,
                "hardware_device_id": self.DEVICE_ID
            }

            if self.DEBUG:
                print('Enviando datos a la API:', payload)

            response = urequests.post(url, headers=headers, json=payload)

            if self.DEBUG:
                print('Respuesta de la API:', response.text)

            if response.status_code == 201:
                return True
            else:
                return False

        except Exception as e:
            if self.DEBUG:
                print('')
                print("Error al obtener los datos de la api: ", e)
                print("lightnings: ", lightnings)
                print('')

            return False
