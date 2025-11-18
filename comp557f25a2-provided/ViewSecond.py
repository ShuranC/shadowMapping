import moderngl as mgl
from pyglm import glm
from Scene import Scene


class ViewSecond():
    def __init__(self, scene: Scene, camera, ctx):
        self.scene = scene
        self.camera = camera
        self.ctx = ctx

    def paintGL(self, aspect_ratio):
        self.ctx.enable(mgl.DEPTH_TEST)
        self.ctx.clear(0.2, 0.2, 0.2)

        # set up projection and view matrix for the second view
        self.camera.V = glm.translate(glm.mat4(1), glm.vec3(0, 0, -self.camera.distance)) * self.camera.R
        self.camera.P = glm.perspective(glm.radians(60.0), aspect_ratio, 0.1, 100.0)

        # compute matriceds needed for GLSL
        cam_mvp = self.camera.P * self.camera.V
        cam_mv = self.camera.V

        # Draw the scene with lighting enabled
        self.scene.prog_shadow_map['u_mv'].write(cam_mv)
        self.scene.prog_shadow_map['u_mvp'].write(cam_mvp)
        light_pos = self.scene.get_light_pos_in_view(self.camera.V)
        self.scene.prog_shadow_map['u_light_pos'].write(light_pos)
        self.scene.prog_shadow_map['u_use_lighting'] = True
        self.scene.render_for_view()

        # Draw the camera frustums, if enabled, with lighting disabled (i.e., draw solid colours)
        self.scene.prog_shadow_map['u_use_lighting'] = False
        self.ctx.enable(mgl.BLEND)  # slightly nicer lines with alpha provided in colour (4th component)

        # draw world frame
        self.scene.prog_shadow_map['u_mvp'].write(cam_mvp)
        self.scene.axis.render()

        if self.scene.controls.show_light_camera:
            # TODO: OBJECTIVE: draw the light camera frustum  and axis
            light_V_inverse = glm.inverse(self.scene.light_view_camera.V)
            light_P_inverse = glm.inverse(self.scene.light_view_camera.P)

            M = self.camera.P * self.camera.V * light_V_inverse * light_P_inverse  # TODO: compute the appropriate matrix to draw the light camera frustum for this view

            self.scene.prog_shadow_map['u_mvp'].write(M)
            self.scene.prog_shadow_map['u_color'] = (1, 1, 0, 0.75)  # make light frustum yellow
            self.scene.render_cube_and_grid()

            M = self.camera.P * self.camera.V * light_V_inverse  # TODO: compute the appropriate matrix to draw the light camera axis for this view
            self.scene.prog_shadow_map['u_mvp'].write(M)
            self.scene.axis.render()

        if self.scene.controls.show_main_camera:
            # TODO: OBJECTIVE: draw the main camera frustum  and axis
            main_V_inverse = glm.inverse(self.scene.main_view_camera.V)
            main_P_inverse = glm.inverse(self.scene.main_view_camera.P)

            M = self.camera.P * self.camera.V * main_V_inverse * main_P_inverse # TODO: compute the appropriate matrix to draw the main camera frustum for this view
            self.scene.prog_shadow_map['u_mvp'].write(M)
            self.scene.prog_shadow_map['u_color'] = (1, 1, 1, 0.75)  # make main frustum white
            self.scene.render_cube()

            M = self.camera.P * self.camera.V * main_V_inverse  # TODO: compute the appropriate matrix to draw the main camera axis for this view
            self.scene.prog_shadow_map['u_mvp'].write(M)
            self.scene.axis.render()

        self.ctx.disable(mgl.BLEND)
