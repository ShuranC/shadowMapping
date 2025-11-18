import numpy as np
import trimesh
import moderngl as mgl
from pathlib import Path
from SceneControl import SceneControl
import glm

ground_name = 'ground'  # ground plane is a special case for cheap shadows

object_name = {ground_name, 'monkey3', 'monkey2', 'monkey1', 'tree1', 'tree2'}
object_colors = {'monkey1': (0.97, 0.09, 0.0, 1),
                 'monkey2': (0.06, 0.9, 0.02, 1),
                 'monkey3': (0.07, 0.04, 0.9, 1),
                 'tree1': (0.09, 0.67, 0.09, 1),
                 'tree2': (0.09, 0.87, 0.09, 1),
                 ground_name: (0.69, 0.5, 0.49, 1)}


class Camera:
    def __init__(self, R: glm.mat4, d: float):
        ''' A simple camera with rotation R and distance d from the origin along -Z axis in the rotated frame.
        Each view associated with a camera is responsible for updating these values based on current scene controls. '''
        self.R = R          # Rotation controlled by mouse movement (XYBall)
        self.distance = d   # Distance controlled by mouse wheel
        self.V = glm.translate(glm.mat4(1), glm.vec3(0, 0, -self.distance)) * self.R
        self.P = glm.mat4(1)
    def update_cam_distance(self, mult):
        self.distance *= np.power(1.1, mult)


class Scene:
    ''' A scene with objects, cameras, light, and shaders.
    There is only one light, and it is defined to be at the origin of the light view camera.
    The scene also contains controls for the GUI.
    '''
    def __init__(self):
        self.controls = SceneControl()  
        
        self.main_view_camera = Camera(glm.rotate(0.4, glm.vec3(1, 0, 0)), 10)
        self.light_view_camera = Camera(glm.rotate(glm.pi()/2, glm.vec3(1, 0, 0)), 5)
        self.third_person_camera = Camera(glm.rotate(0.6, glm.vec3(1, 1, 0)), 20)
        self.post_projection_camera = Camera(glm.rotate(0.2, glm.vec3(1, 0, 0)), 8)   # Camera(glm.rotate(-glm.pi()/2, glm.vec3(0, 0, 1)), 8)

        self.cameras = [
            self.main_view_camera,
            self.light_view_camera,
            self.third_person_camera,
            self.post_projection_camera
        ]

        self.view_vol = None # initialized in initGL
        self.axis = None     # initialized in initGL 

    def initGL(self, ctx: mgl.Context):
        self.ctx = ctx
        self.object_name = object_name
        self.object_colors = object_colors
        self.ground_name = ground_name

        # load and compile the shaders
        current_dir = Path(__file__).parent  # glsl folder in same directory as this code

        # load the GLSL program for drawing the depth map form the light view
        self.prog_depth = self.ctx.program(
            vertex_shader=open(current_dir / 'glsl/depth_vert.glsl').read(),
            fragment_shader=open(current_dir / 'glsl/depth_frag.glsl').read())

        # load the GLSL program for drawing the camera view with shadow map
        self.prog_shadow_map = self.ctx.program(
            vertex_shader=open(current_dir / 'glsl/render_with_sm_vert.glsl').read(),
            fragment_shader=open(current_dir / 'glsl/render_with_sm_frag.glsl').read())
        # assign textures unit ID to samplers in GLSL programs
        self.prog_shadow_map['u_sampler_shadow'].value = 0
        self.prog_shadow_map['u_sampler_shadow_map_raw'].value = 1

        # Geometry
        self.view_vol = View_Vol(self.ctx, self.prog_shadow_map)
        self.axis = Axis(self.ctx, self.prog_shadow_map)

        # Texture for shadown map
        self.texture = Texture(self.ctx)
        
        # We'll keep a buffer of scene verts (for computing bounds) starting with the origin in list of points in scene
        # for efficiency would be better just to keep convex hull of scene points
        self.verts = np.array([[0, 0, 0, 1]]).T
        
        # Vertex arrays for each object, 2 versions, the second being for the shadow map (no normals)
        self.vao_objects = {}
        self.vao_object_shadows = {}
        
        current_dir = Path(__file__).parent  # glsl folder in same directory as this code
        
        for name in object_name:
            # load geometry from current directory
            mesh = trimesh.load_mesh(current_dir / f'data/{name}.obj')
            
            # get relevant mesh information
            verts = mesh.vertices  # shape: (N, 3)
            indices = mesh.faces.flatten()
            normals = trimesh.geometry.mean_vertex_normals(verts.shape[0], mesh.faces, mesh.face_normals).astype('f4')
            
            if name == ground_name:
                # compute the ground plane assuming that the first vertex has the good normal for the whole plane
                self.ground_plane = glm.vec4(normals[0, 0], normals[0, 1], normals[0, 2], -np.dot(normals[0, :], verts[0, :]))
            
            verts_by_4 = np.hstack([verts, np.ones((verts.shape[0], 1))])
            self.verts = np.hstack((self.verts, verts_by_4.T))
            
            self.vao_objects[name] = make_vao(ctx, self.prog_shadow_map, verts, indices, normals, mode=mgl.TRIANGLES)
            self.vao_object_shadows[name] = make_vao(ctx, self.prog_depth, verts, indices, normals=None, mode=mgl.TRIANGLES)
    
    def get_ground_plane(self) -> glm.vec4:
        ''' return the ground plane as a 4-vector (a,b,c,d) so that ax + by + cz + d = 0 '''
        return self.ground_plane

    def get_light_pos_in_world( self ) -> glm.vec4:
        ''' return the light position in world coordinates. 
        Recall that the light is at the origin in the light view as defined by the light_view_camera. '''

        # TODO OBJECTIVE: compute the appropriate return value for this funciton!
        #get the inverse of view matrix.
        V_inverse = glm.inverse(self.light_view_camera.V)
        light_position = V_inverse * glm.vec4(0, 0, 0, 1)
        return  light_position

    def get_light_pos_in_view( self, V: glm.mat4 ) -> glm.vec3:
        ''' Given viewing matrix V, return the light position in that view. '''        
        pos = V * self.get_light_pos_in_world()
        pos = pos.xyz / pos.w  # normalize by w, only needed if view matrix has perspective (e.g., a post perspective view)
        return pos

    def get_all_scene_verts(self) -> np.ndarray:
        ''' return all vertices in the scene as a 4xN array of homogeneous coordinates.
        This is useful for computing scene bounds, e.g., near and far clipping planes, or l,r,t,b for the light view frustum '''
        return self.verts
    
    def compute_nf_from_view(self, V: glm.mat4):
        ''' Given a viewing matrix V, compute near and far values that just fit the scene vertices. 
        Recall that near and far are the positive distances along the -Z axis of the view. '''

        # TODO: OBJECTIVE: compute n and f for the scene verts and return these values!
        #get the list of vertices
        verts = self.get_all_scene_verts()
        z_coords = []
        for i in range(verts.shape[1]):
            v = glm.vec4(verts[0, i], verts[1, i], verts[2, i], verts[3, i])
            #only apply the viewing matrix
            v_view = V * v
            z_coords.append(v_view.z)

        z_coords = np.array(z_coords)

        n = -np.max(z_coords)   # TODO: replace this arbitrary value!
        f = -np.min(z_coords)  # TODO: replace this arbitrary value!
        return n, f

    def compute_lrbt_for_projection(self, V: glm.mat4, n: float, f: float):
        ''' Given a viewing matrix V, and near and far values, compute l,r,b,t values that just fit the scene vertices. '''

        # TODO: OBJECTIVE: compute l,r,b,t for the scene vertices, given the near and far values, and return these values!
        verts = self.get_all_scene_verts()

        # Convert to numpy and transform
        V_np = np.array(V).reshape(4, 4).T
        verts_view = V_np @ verts

        x_coords = verts_view[0, :]  # all X coordinates
        y_coords = verts_view[1, :]  # all Y coordinates

        min_x = np.min(x_coords)
        max_x = np.max(x_coords)
        min_y = np.min(y_coords)
        max_y = np.max(y_coords)

        # Project to near plane use similar triangle
        l = min_x * (n/f)  # TODO: replace this arbitrary value!
        r = max_x * (n/f)  # TODO: replace this arbitrary value!
        b = min_y * (n/f)  # TODO: replace this arbitrary value!
        t = max_y * (n/f)  # TODO: replace this arbitrary value!
        return l, r, b, t

    def render_shadow_pass(self):
        ''' render shadow-map (depth framebuffer -> texture) from light view '''
        # render to the shadow map texture (an offscreen framebuffer)
        self.texture.set_fbo()  
        if self.controls.use_culling:
            self.ctx.enable(mgl.CULL_FACE)
            self.ctx.cull_face = 'front'   # reduce self-shadowing

        # TODO: OBJECTIVE: set up the appropraite matrix for drawing the shadow map view
        V_light = self.light_view_camera.V
        P_light = self.light_view_camera.P

        mvp = P_light * V_light # TODO: compute the appropriate matrix to use for rendering the shadow map for the light camera
        self.prog_depth['u_mvp'].write( mvp )    
        self.render_for_shadow_map()

        # return settings to normal 
        self.ctx.screen.use() 
        self.ctx.cull_face = 'back'
        self.ctx.disable(mgl.CULL_FACE)

        # TODO: OBJECTIVE: set the light space transform that takes vertices in world coordinates to texture coordinates in the shadow map
        window_transform = glm.mat4(
            0.5, 0.0, 0.0, 0.0,
            0.0, 0.5, 0.0, 0.0,
            0.0, 0.0, 0.5, 0.0,
            0.5, 0.5, 0.5, 1.0
        )
        light_space_transform = window_transform * P_light * V_light # TODO: compute the appropraite matrix!
        self.prog_shadow_map['u_light_space_transform'].write(light_space_transform)


    def render_for_view(self, draw_ground=True):
        ''' render all objects in the scene using currently set up GLSL program.
        If these objects had different modeling transforms, then we would need to combine the current MVP with the modeling transform.
        but all objects were modeled in a common coordinate system, so we can just use the current MVP for all objects (i.e.,
        modeling transform is identity for all objects).'''
        for name in self.object_name:
            self.prog_shadow_map['u_color'] = object_colors[name]
            self.vao_objects[name].render()
    
    def render_cheap_shadows(self, darken_factor: float = 0.3 ):
        ''' render all objects in the scene, *except* for the ground plane. 
        The GLSL program's uniform matrices should be set up to project this geometry onto the ground plane.
        Here the colours of the objects are set to a darkened version of the object colour. '''
        # render all objects projected onto the ground, except the ground itself
        for name in object_name:
            if name == ground_name:
                continue
            self.prog_shadow_map['u_color'].write(np.array(np.array(object_colors[ground_name]) * darken_factor, dtype='f4').tobytes())
            self.vao_objects[name].render()
    
    def render_for_shadow_map(self):
        ''' render all objects in the scene without normals or colours '''
        for name in self.object_name:
            self.vao_object_shadows[name].render()

    def render_cube_and_grid(self):
        ''' render a [-1,1]^3 cube with a grid on the side corresponding to the near plane '''
        self.view_vol.cube_vao.render()
        self.view_vol.grid_vao.render()
    
    def render_cube(self):
        ''' render a [-1,1]^3 cube '''
        self.view_vol.cube_vao.render()

    def render_axis(self):
        ''' render a 3D axis '''
        self.axis.render()


def make_vao(
        ctx: mgl.Context,
        prog: mgl.Program,
        vertices: np.ndarray,
        indices: np.ndarray,
        normals: np.ndarray = None,
        mode=mgl.LINES
) -> mgl.VertexArray:
    ''' helper function to create a vertex array object from vertex and index buffer for line geometry '''
    vbo = ctx.buffer(vertices.astype("f4").tobytes())
    ibo = ctx.buffer(indices.astype("i4").tobytes())
    if normals is None:
        return ctx.vertex_array(
            prog,
            [(vbo, '3f', 'in_position')],
            index_buffer=ibo,
            mode=mode)
    vbo2 = ctx.buffer(normals.astype("f4").tobytes())
    vao = ctx.vertex_array(
        prog,
        [(vbo, '3f', 'in_position'),
         (vbo2, '3f', 'in_normal')],
        index_buffer=ibo,
        mode=mode)
    return vao


class View_Vol:
    ''' A wireframe cube and grid on the near plane to show the viewing volume of a camera.
    Cube can be also drawn on its own, or both the cube and the near plane grid. '''
    def __init__(self, ctx, program):        
        # create cube vertices and indices for drawing edges of a wire cube of size 2
        vertices = np.array([-1, -1, -1, 1, -1, -1, 1, 1, -1, -1, 1, -1, -1, -1, 1, 1, -1, 1, 1, 1, 1, -1, 1, 1],
                            dtype='f4')
        indices = np.array([0, 1, 1, 2, 2, 3, 3, 0, 4, 5, 5, 6, 6, 7, 7, 4, 0, 4, 1, 5, 2, 6, 3, 7], dtype='i4')
        self.cube_vao = make_vao(ctx, program, vertices, indices)
        # make a grid of lines on the near plane
        n = 8
        vertices = -np.ones((3, n * 4), dtype='f4')
        coords = np.linspace(-1, 1, n)
        vertices[0:2, 1::2] = 1
        vertices[0, 0:n * 2:2] = coords
        vertices[0, 1:n * 2:2] = coords
        vertices[1, n * 2::2] = coords
        vertices[1, n * 2 + 1::2] = coords
        indices = np.array(range(0, 40), dtype='i4')
        self.grid_vao = make_vao(ctx, program, vertices.T, indices, normals=None, mode=mgl.LINES)


class Axis:
    ''' A simple line drawn 3D axis object with red, green, blue lines for x, y, z axis directions. '''
    def __init__(self, ctx, program):
        self.program = program
        # make the axis lines
        self.line_x_vao = make_vao(ctx, self.program, np.array([0, 0, 0, 1, 0, 0]), np.array([0, 1]), normals=None, mode=mgl.LINES)
        self.line_y_vao = make_vao(ctx, self.program, np.array([0, 0, 0, 0, 1, 0]), np.array([0, 1]), normals=None, mode=mgl.LINES)
        self.line_z_vao = make_vao(ctx, self.program, np.array([0, 0, 0, 0, 0, 1]), np.array([0, 1]), normals=None, mode=mgl.LINES)
    
    def render(self):
        # draw a coordinate frame with red green blue axis colours
        # (note that lighting should be disabled when using  this function)
        self.program['u_color'] = (1, 0, 0, 1)
        self.line_x_vao.render()
        self.program['u_color'] = (0, 1, 0, 1)
        self.line_y_vao.render()
        self.program['u_color'] = (0, 0, 1, 1)
        self.line_z_vao.render()
        
        
class Texture:
    ''' A shadow map texture, with associated framebuffer object and samplers for accessing the texture in different ways.'''
    def __init__(self, ctx: mgl.Context):
        shadow_size = (2 << 7, 2 << 7)  # 512²
        self.tex_depth = ctx.depth_texture(shadow_size)
        self.tex_color_depth = ctx.texture(shadow_size, components=1, dtype='f4')
        self.fbo_depth = ctx.framebuffer(color_attachments=[self.tex_color_depth], depth_attachment=self.tex_depth)
        self.sampler_depth = ctx.sampler(
            filter=(mgl.LINEAR, mgl.LINEAR),
            compare_func='>=',
            repeat_x=False,
            repeat_y=False,
            texture=self.tex_depth)
        self.sampler_depth_map_raw = ctx.sampler(
            filter=(mgl.NEAREST, mgl.NEAREST),
            repeat_x=False,
            repeat_y=False,
            texture=self.tex_depth)
        self.sampler_depth.use(location=0)  # Assign the texture and sampling parameters to the texture unit
        self.sampler_depth_map_raw.use(location=1)  # Assign the texture and sampling parameters to the texture unit

    def set_filter(self, use_linear_filter: bool):
        ''' set the texture filtering mode for the shadow map texture '''
        if use_linear_filter:
            self.sampler_depth.filter = (mgl.LINEAR, mgl.LINEAR)    # percentage closer filtering
        else:
            self.sampler_depth.filter = (mgl.NEAREST, mgl.NEAREST)  # nearest neighbour filtering

    def set_fbo(self, depth_clear_value: float = 1.0 ):
        ''' set the framebuffer object for and clear it in preparation for rendering the shadow map. 
        The depth_clear_value should be 1.0 for standard depth test, or 0.0 if the depth test is inverted.
        '''
        self.fbo_depth.use()
        self.fbo_depth.clear(1, 1, 1, 1, depth=depth_clear_value)