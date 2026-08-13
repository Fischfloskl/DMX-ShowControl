import threading


class ShowController:

    def __init__(self,
                 sequence_manager,
                 fade_engine,
                 dmx_manager,
                 strobe_manager):

        self.sequence_manager = sequence_manager
        self.fade_engine = fade_engine
        self.dmx_manager = dmx_manager
        self.strobe_manager = strobe_manager

        self.stop_event = threading.Event()

    def should_stop(self):
        return self.stop_event.is_set()
    
    def emergency_stop(self):
        self.stop_all()

    def stop_all(self):

        print("STOP ALL")

        self.stop_event.set()

        self.sequence_manager.stop()
        self.fade_engine.stop()
        self.strobe_manager.stop()



        self.dmx_manager.reset_all()

    def reset(self):

        self.stop_event.clear()


    def stopped(self):

        return self.stop_event.is_set()