

class Config:
    font_size = 40
    w_location_x = 0
    w_location_y = 0
    w_width = 800
    w_height = 500
    token_info: dict = None

    def __init__(self):
        self.font_size = 40
        self.token_info = None

    @classmethod
    def from_dict(cls, config_dict):
        config = cls()
        config.font_size = config_dict.get("font_size", 40)
        config.w_location_x = config_dict.get("w_location_x", 0)
        config.w_location_y = config_dict.get("w_location_y", 0)
        config.w_width = config_dict.get("w_width", 800)
        config.w_height = config_dict.get("w_height", 500)
        config.token_info = config_dict.get("token_info", None)
        return config

    def to_dict(self):
        config_dict = {
            "font_size": self.font_size,
            "w_location_x": self.w_location_x,
            "w_location_y": self.w_location_y,
            "w_width": self.w_width,
            "w_height": self.w_height,
            "token_info": self.token_info
        }
        return config_dict

