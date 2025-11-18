import moderngl as mgl
from pyglm import glm
from Scene import Scene, Camera

class ViewLight():
	def __init__(self, scene: Scene, camera: Camera, ctx: mgl.Context):
		self.scene = scene
		self.camera = camera
		self.ctx = ctx

	def paintGL(self, aspect_ratio: float):		
		self.ctx.clear(0,0,0)
		self.ctx.enable(mgl.DEPTH_TEST)
		
		# set up projection and view matrix for the light view	
		self.camera.V = glm.translate(glm.mat4(1), glm.vec3(0, 0, -self.camera.distance)) * self.camera.R		
		n, f = self.scene.compute_nf_from_view(self.camera.V)
		if self.scene.controls.manual_light_fov:
			fov = glm.radians(self.scene.controls.light_view_fov)
			self.camera.P = glm.perspective(fov, aspect_ratio, n, f)
		else:
			l,r,b,t = self.scene.compute_lrbt_for_projection(self.camera.V, n, f)
			self.camera.P = glm.frustum(l,r,b,t,n,f)
		
		cam_mvp = self.camera.P * self.camera.V 
		cam_mv = self.camera.V 

		self.scene.prog_shadow_map['u_mv'].write(cam_mv)
		self.scene.prog_shadow_map['u_mvp'].write(cam_mvp)
		self.scene.prog_shadow_map['u_light_pos'].write( glm.vec3(0,0,0) ) # light is at the origin in the light view
		self.scene.prog_shadow_map['u_use_shadow_map'] = False # disable shadow map when rendering from light
		self.scene.render_for_view()
		self.scene.prog_shadow_map['u_use_shadow_map'] = self.scene.controls.use_shadow_map