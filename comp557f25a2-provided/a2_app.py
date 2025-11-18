from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QApplication, QLabel
from ViewSceneControlWidget import QGLViewSceneControlWidget

#Name: Shuran, Cui
#ID: 261275097
class ShadowMappingApplication(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shadow Mapping Assignment 2 - COMP 557 F2025 - Shuran Cui - 261275097")
        
        main_layout = QHBoxLayout()

        view_and_labels_layout = QVBoxLayout()
        top_row_labels_layout = QHBoxLayout()
        top_row_labels_layout.addWidget(QLabel("Main View"))
        top_row_labels_layout.addWidget(QLabel("Light View"))
        view_and_labels_layout.addLayout(top_row_labels_layout)
        self.view_grid = QGLViewSceneControlWidget()
        view_and_labels_layout.addWidget( self.view_grid, stretch=1)
        bottom_row_labels_layout = QHBoxLayout()
        bottom_row_labels_layout.addWidget(QLabel("Third Person View"))
        bottom_row_labels_layout.addWidget(QLabel("Post Projection View"))
        view_and_labels_layout.addLayout(bottom_row_labels_layout)
        main_layout.addLayout(view_and_labels_layout, stretch=1)

        control_panel = QWidget()
        control_layout = QVBoxLayout()
        self.view_grid.scene.controls.get_controls(control_layout)
        control_layout.addStretch()  # Push controls to top
        control_panel.setLayout(control_layout)
        control_panel.setFixedWidth(400)
        main_layout.addWidget(control_panel)

        self.setLayout(main_layout)

        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.timer_update)
        self.anim_timer.start(16)

    def keyPressEvent(self, event):
        self.view_grid.scene.controls.keyEvent(event)

    def timer_update(self):
        for child in self.findChildren(QWidget):
            child.update()

app = QApplication([])
window = ShadowMappingApplication()
window.resize(1280, 720)
window.show()
app.exec_()