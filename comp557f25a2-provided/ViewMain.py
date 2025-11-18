import moderngl as mgl
from pyglm import glm
from Scene import Scene, Camera


class ViewMain():
    def __init__(self, scene: Scene, camera: Camera, ctx: mgl.Context):
        self.scene = scene
        self.camera = camera
        self.ctx = ctx

    def paintGL(self, aspect_ratio: float):
        self.ctx.clear(0, 0, 0)
        self.ctx.enable(mgl.DEPTH_TEST)

        # set up projection and view matrix for the main camera vew
        fov = glm.radians(self.scene.controls.main_view_fov)
        self.camera.V = glm.translate(glm.mat4(1), glm.vec3(0, 0, -self.camera.distance)) * self.camera.R
        n, f = self.scene.compute_nf_from_view(self.camera.V)
        self.camera.P = glm.perspective(fov, aspect_ratio, n, f)

        cam_mvp = self.camera.P * self.camera.V
        cam_mv = self.camera.V

        self.scene.prog_shadow_map['u_mv'].write(cam_mv)
        self.scene.prog_shadow_map['u_mvp'].write(cam_mvp)
        light_pos = self.scene.get_light_pos_in_view(self.camera.V)
        self.scene.prog_shadow_map['u_light_pos'].write(light_pos)
        self.scene.prog_shadow_map['u_use_lighting'] = True
        self.scene.render_for_view()

        if self.scene.controls.cheap_shadows:
            # TODO: OBJECTIVE: Implement cheap shadows
            # NOTE: This will be easiest to do following the explanation from class, using a composition of transformations

            ground_plane_in_world_coords = self.scene.get_ground_plane()
            light_pos_in_world_coords = self.scene.get_light_pos_in_world()

            a = ground_plane_in_world_coords.x
            b = ground_plane_in_world_coords.y
            c = ground_plane_in_world_coords.z
            d = ground_plane_in_world_coords.w

            # build coordinate frame at the light
            n = glm.normalize(glm.vec3(a, b, c))
            w = n
            L = glm.vec3(light_pos_in_world_coords)

            if abs(w.x) < 0.9:
                arbitrary = glm.vec3(1, 0, 0)
            else:
                arbitrary = glm.vec3(0, 1, 0)

            #the other two unit vectors
            u = glm.normalize(glm.cross(arbitrary, w))
            v = glm.normalize(glm.cross(w, u))

            #viewing transformation of moving the origin to the position of the light
            V = glm.mat4(
                glm.vec4(u.x, u.y, u.z, 0),
                glm.vec4(v.x, v.y, v.z, 0),
                glm.vec4(w.x, w.y, w.z, 0),
                glm.vec4(L.x, L.y, L.z, 1)
            )

            distance = a * L.x + b * L.y + c * L.z + d
            distance -= 0.001

            #projection matrix
            P = glm.mat4(
                glm.vec4(distance, 0, 0, 0),
                glm.vec4(0, distance, 0, 0),
                glm.vec4(0, 0, distance, -1),
                glm.vec4(0, 0, 0, 0)
            )

            cheap_shadow_modelling_transformation = V @ P @ glm.inverse(V)  # TODO: compute the appropriate matrix

            cam_mvp = self.camera.P * self.camera.V * cheap_shadow_modelling_transformation
            self.scene.prog_shadow_map['u_mvp'].write(cam_mvp)
            self.scene.prog_shadow_map['u_use_lighting'] = False
            self.scene.prog_shadow_map['u_use_shadow_map'] = False
            self.scene.render_cheap_shadows()
            self.scene.prog_shadow_map['u_use_lighting'] = True
            self.scene.prog_shadow_map['u_use_shadow_map'] = self.scene.controls.use_shadow_map
