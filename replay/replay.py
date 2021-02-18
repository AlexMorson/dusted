class Replay:
    def __init__(self, data=None):
        if data is None:
            self._data = {
                "header": {
                    "version": "3",
                    "players": 1,
                    "frames": 0,
                    "characters": [0],
                    "level": ""
                },
                "inputs": [
                    []
                ],
                "entityFrameContainers": [],
                "meta": {
                    "username": ""
                }
            }
        else:
            self._data = data

    @property
    def data(self):
        return self._data

    @property
    def players(self):
        return self._data["header"]["players"]

    @property
    def characters(self):
        return self._data["header"]["characters"]

    @characters.setter
    def characters(self, x):
        self._data["header"]["players"] = len(x)
        self._data["header"]["characters"] = x

    @property
    def level(self):
        return self._data["header"]["level"]

    @level.setter
    def level(self, x):
        self._data["header"]["level"] = x

    @property
    def inputs(self):
        return self._data["inputs"]

    @inputs.setter
    def inputs(self, x):
        self._data["inputs"] = x

    @property
    def username(self):
        return self._data["meta"]["username"]

    @username.setter
    def username(self, x):
        self._data["meta"]["username"] = x
