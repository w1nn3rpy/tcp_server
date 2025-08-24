class Navtelecom:
    def __init__(self):
        self._device_id = None
        self._authorized = False
        self._flex_confirmed = False
        self._flex_v = 1

    @property
    def device_id(self):
        return self._device_id

    @device_id.setter
    def device_id(self, value: int):
        self._device_id = value

    @property
    def version(self):
        return self._flex_v

    @version.setter
    def version(self, version: int):
        if not isinstance(version, int):
            raise TypeError('Версия может быть только числом от 1 до 3')
        elif version not in (1, 2, 3):
            raise ValueError('Версия не может быть меньше 1 и выше 3')
        self._flex_v = version

navtelecom = Navtelecom()