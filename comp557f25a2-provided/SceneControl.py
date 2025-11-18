from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QKeyEvent
QtWidgets.QApplication.setStyle("Fusion")

class SceneControl:
    def __init__(self):
        # Flags and values conrolled by UI elements (and keyboard) to adjust viewing and rendering options
        self.show_main_camera = True   # TODO: OBJECTIVE: SET DEFAULT TO TRUE ONCE YOU HAVE IMPLEMENTED DRAWING OF THE MAIN CAMERA FRUSTUM
        self.show_light_camera = True  # TODO: OBJECTIVE: SET DEFAULT TO TRUE ONCE YOU HAVE IMPLEMENTED DRAWING OF THE LIGHT CAMERA FRUSTUM
        self.use_linear_filter = False  # shadow map filtering
        self.use_culling = False        # front face culling  in light view to reduce self-shadowing
        self.cheap_shadows = False
        self.draw_depth = False         # draw the depth of fragments with respect to light position
        self.draw_depth_map = False     # draw the depth recorded from the light position
        self.use_shadow_map = True     # TODO: OBJECTIVE: SET DEFAULT TO TRUE ONCE YOU HAVE IMPLEMENTED SHADOW MAPPING
        self.use_depth_bias = True
        self.bias_slope_factor = 0.005
        self.manual_light_fov = True    # TODO: OBJECTIVE: SET DEFAULT TO FALSE ONCE YOU HAVE IMPLEMENTED AUTOMATIC FITTING OF LIGHT FRUSTUM
        self.light_view_fov = 45
        self.main_view_fov = 20

    def get_controls(self, layout: QtWidgets.QVBoxLayout):
        layout.addWidget(SliderControl("Main View fov", 1, 179, self.main_view_fov, lambda f: setattr(self, 'main_view_fov', f), scale=0.1))
        layout.addWidget(CheckboxControl("Manual Light fov", self.manual_light_fov, lambda x: setattr(self, 'manual_light_fov', x)))
        layout.addWidget(SliderControl("Light View fov", 1, 179, self.light_view_fov, lambda f: setattr(self, 'light_view_fov', f), scale=0.1))
        layout.addWidget(CheckboxControl("show main camera", self.show_main_camera, lambda x: setattr(self, 'show_main_camera', x)))
        layout.addWidget(CheckboxControl("show light camera", self.show_light_camera, lambda x: setattr(self, 'show_light_camera', x)))
        layout.addWidget(CheckboxControl("Use linear filter", self.use_linear_filter, lambda x: setattr(self, 'use_linear_filter', x)))
        layout.addWidget(CheckboxControl("Shadow pass front face culling", self.use_culling, lambda x: setattr(self, 'use_culling', x)))
        layout.addWidget(CheckboxControl("Use depth bias", self.use_depth_bias, lambda x: setattr(self, 'use_depth_bias', x)))
        layout.addWidget(SliderControl("Bias slope factor", 0.0, 0.05, self.bias_slope_factor, lambda f: setattr(self, 'bias_slope_factor', f), scale=0.001, digits=3))
        layout.addWidget(CheckboxControl("Draw cheap shadows", self.cheap_shadows, lambda x: setattr(self, 'cheap_shadows', x)))
        layout.addWidget(CheckboxControl("Use shadow map", self.use_shadow_map, lambda x: setattr(self, 'use_shadow_map', x)))
        layout.addWidget(RadioControl(["Fragment depth", "Map depth"], self.depth_callback, use_exclusion=True))


    def depth_callback(self, text):
        if text == "Fragment depth":
            # draw the depth of fragments with respect to light position
            self.draw_depth = True
            self.draw_depth_map = False
        elif text == "Map depth":
            # draw the depth recorded from the light position
            self.draw_depth = False
            self.draw_depth_map = True
        else:
            # regular render mode
            self.draw_depth = False
            self.draw_depth_map = False

    def keyEvent(self, event: QKeyEvent):
        ''' Keyboard interface for easy evaluation by TAs '''
        match event.key():
            case QtCore.Qt.Key.Key_F:
                self.use_linear_filter = not self.use_linear_filter  # shadow map filtering
            case QtCore.Qt.Key.Key_C:
                self.use_culling = not self.use_culling  # front face culling  in light view to reduce self-shadowing
            case QtCore.Qt.Key.Key_O:
                self.cheap_shadows = not self.cheap_shadows  # cheap shadows using a planar projection
            case QtCore.Qt.Key.Key_U:
                self.use_shadow_map = not self.use_shadow_map
            case QtCore.Qt.Key.Key_D:  # cycle through drawing depth or depth map
                if self.draw_depth:
                    self.draw_depth = False
                    self.draw_depth_map = True
                elif self.draw_depth_map:
                    self.draw_depth = False
                    self.draw_depth_map = False
                else:
                    self.draw_depth = True
            case QtCore.Qt.Key.Key_E:  # Toggle display of main camera (i.e., "eye" view)
                self.show_CAM1 = not self.show_CAM1
            case QtCore.Qt.Key.Key_L:  # Toggle display of light camera
                self.show_CAM2 = not self.show_CAM2
            case QtCore.Qt.Key.Key_M:  # Manual light FOV control
                self.manual_light_fov = not self.manual_light_fov  # (this only makes sense in the absence of tilting and shifting the light view)

class SliderControl(QtWidgets.QWidget):
    """Wrapper for creating sliders in UI."""

    def __init__(self, label, min_val, max_val, init_val, callback1, scale=1.0, digits=2):
        super().__init__()
        self.callback_val_update = callback1
        self.scale = scale
        self.value = init_val
        self.digits = digits
        layout = QtWidgets.QHBoxLayout()
        self.label = QtWidgets.QLabel(label)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setRange(int(min_val / scale), int(max_val / scale))
        self.slider.setValue(int(init_val / scale))
        self.slider.valueChanged.connect(self.on_value_changed)
        self.value_label = QtWidgets.QLabel(f"{init_val:.{self.digits}f}")
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        layout.addWidget(self.value_label)
        self.setLayout(layout)
        self.slider.setFixedWidth(150)

    def getValue(self):
        return self.value

    def setValue(self, val):
        self.slider.blockSignals(True)
        self.slider.setValue(int(val / self.scale))
        self.value_label.setText(f"{val:.{self.digits}f}")
        self.slider.blockSignals(False)

    def on_value_changed(self, value_scaled):
        self.value = value_scaled * self.scale
        self.value_label.setText(f"{self.value:.{self.digits}f}")
        self.callback_val_update(self.value)


class CheckboxControl(QtWidgets.QWidget):
    """Wrapper for creating labeled check box in UI."""
    def __init__(self, label, init_val: bool, callback1):
        super().__init__()
        layout = QtWidgets.QHBoxLayout()
        self.label = QtWidgets.QLabel(label)
        self.box = QtWidgets.QCheckBox()
        self.box.setChecked(init_val)
        self.box.stateChanged.connect(callback1)
        layout.addWidget(self.box)
        layout.addWidget(self.label)
        layout.addStretch()  # Push to left
        self.setLayout(layout)


class RadioControl(QtWidgets.QWidget):
    """Wrapper for creating sliders in UI."""

    def __init__(self, sub_labels, callback1, use_exclusion=False):
        super().__init__()
        self.callback = callback1
        # Radio buttons
        self.group = QtWidgets.QButtonGroup()
        self.group.setExclusive(True)

        layout = QtWidgets.QHBoxLayout()
        first_button = None
        for label in sub_labels:
            b1 = QtWidgets.QRadioButton(label)
            if not use_exclusion and first_button is None:
                first_button = b1
                b1.setChecked(True)
            b1.toggled.connect(self.check_buttons)
            self.group.addButton(b1)
            layout.addWidget(b1)
        if use_exclusion:
            b1 = QtWidgets.QRadioButton("Default")
            b1.setChecked(True)
            b1.toggled.connect(self.check_buttons)
            self.group.addButton(b1)
            layout.addWidget(b1)

        self.setLayout(layout)

    def check_buttons(self):
        rb = self.sender()
        if rb.isChecked():
            self.callback(rb.text())
