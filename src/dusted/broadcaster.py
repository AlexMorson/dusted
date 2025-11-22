class Broadcaster:
    def __init__(self):
        self.callbacks = []

    def subscribe(self, callback):
        self.callbacks.append(callback)

    def broadcast(self):
        for callback in self.callbacks:
            callback()
