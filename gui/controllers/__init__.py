#from gtkmvc import Controller as _Controller
from wader.vmb.contrib.gtkmvc import Controller as _Controller


class Controller(_Controller):

    def close_controller(self):
        self.model.unregister_observer(self)
        self.view.get_top_widget().destroy()
        self.view = None
        self.model = None
