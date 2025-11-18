import moderngl as mgl
from pyglm import glm
from Scene import Scene	
from ViewSecond import ViewSecond
from ViewMain import ViewMain
from ViewLight import ViewLight
from ViewPostPerspective import ViewPostPerspective

from PyQt5 import QtOpenGL

class QGLViewSceneControlWidget(QtOpenGL.QGLWidget):
    """ OpenGL widget for rendering the scene with 4 different views and a control panel """

    def __init__(self):
        fmt = QtOpenGL.QGLFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QtOpenGL.QGLFormat.CoreProfile)
        fmt.setSampleBuffers(True)
        super(QGLViewSceneControlWidget, self).__init__(fmt, None)
        self.scene = Scene()
        
    def initializeGL(self):
        self.ctx = mgl.create_context()
        self.scene.initGL(self.ctx)
        self.ctx.disable(mgl.CULL_FACE)  # have thin non-closed objets, so disable culling by default
        self.ctx.enable(mgl.DEPTH_TEST)  # always use depth test!
        self.views = [
            ViewMain(self.scene, self.scene.cameras[0], self.ctx),
            ViewLight(self.scene, self.scene.cameras[1], self.ctx),
            ViewSecond(self.scene, self.scene.cameras[2], self.ctx),
            ViewPostPerspective(self.scene, self.scene.cameras[3], self.ctx)
        ]

    def paintGL(self):

        # Draw the shadow pass first!
        self.scene.render_shadow_pass()

        # Set some GLSL program parameters for everyone based on the scene controls
        self.scene.prog_shadow_map['u_use_bias'] = self.scene.controls.use_depth_bias
        self.scene.prog_shadow_map['u_bias_slope_factor'] = self.scene.controls.bias_slope_factor
        self.scene.texture.set_filter(self.scene.controls.use_linear_filter)
        self.scene.prog_shadow_map['u_draw_depth'] = self.scene.controls.draw_depth         # draw depth to light instead of colour
        self.scene.prog_shadow_map['u_draw_depth_map'] = self.scene.controls.draw_depth_map # draw the shadow map depth instead of colour
        self.scene.prog_shadow_map['u_use_shadow_map'] = self.scene.controls.use_shadow_map # enable use of the shadow map
        # We use a scissor test to restrict clearing and drawing to each desired viewport
        self.ctx.scissor = self.ctx.viewport = (0, 0, self.w, self.h) # whole window
        self.ctx.clear(1,1,1) # clear the whole drawing surface
        for v in range(4):
            self.ctx.viewport = self.ctx.scissor = self.view_ports[v]        
            self.views[v].paintGL( self.aspect_ratio ) 

    def resizeGL(self, w, h):
        ''' recompute the 4 viewports on window resize '''
        self.w = w
        self.h = h
        # Given the current window size, define 4 viewports that leave a small border between them
        border = 4 # must be an even number of pixels
        hw = int(self.w/2)
        hh = int(self.h/2)
        w = hw - 1.5*border; h = hh - 1.5*border; 
        self.view_ports = [
            (border, hh + border/2, w, h),  # top-left
            (hw + border/2, hh + border/2, w, h),  # top-right
            (border, border, w, h),  # bottom-left
            (hw + border/2, border, w, h)  # bottom-right
        ]
        self.aspect_ratio = w/h  # aspect ratio of each of the baby viewports

    def get_quadrant(self, x, y):
        ''' return the quadrant (0,1,2,3) for the given x,y mouse position '''
        if x < self.w/2 and y < self.h/2:
            return 0
        elif x >= self.w/2 and y < self.h/2:
            return 1 
        elif x < self.w/2 and y >= self.h/2:
            return 2 
        else:
            return 3 

    def mousePressEvent(self, event):
        ''' remember the last mouse position and which quadrant we are in '''
        self.last_mouse_pos = (event.x(), event.y())
        self.quadrant = self.get_quadrant( *self.last_mouse_pos )        

    def mouseMoveEvent(self, event):
        ''' update the rotation of the camera corresponding to the quadrant we are in '''
        new_x, new_y = event.x(), event.y()
        rx = glm.rotate(glm.mat4(1), (new_y - self.last_mouse_pos[1]) * 0.01, glm.vec3(1, 0, 0))
        ry = glm.rotate(glm.mat4(1), (new_x - self.last_mouse_pos[0]) * 0.01, glm.vec3(0, 1, 0))
        self.scene.cameras[self.quadrant].R = ry * rx * self.scene.cameras[self.quadrant].R
        self.last_mouse_pos = (new_x, new_y)

    def wheelEvent(self, event):        
        ''' zoom the camera corresponding to the quadrant we are in '''
        mult = event.angleDelta().y() / 120
        self.scene.cameras[self.get_quadrant( event.x(), event.y())].update_cam_distance(mult)