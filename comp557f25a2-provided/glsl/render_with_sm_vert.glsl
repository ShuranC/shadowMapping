#version 330

uniform mat4 u_mv;
uniform mat4 u_mvp;
uniform mat4 u_light_space_transform;

in vec3 in_position;
in vec3 in_normal;
in vec2 in_texcoord_0;

out vec3 v_vert;
out vec3 v_norm;
out vec4 v_shadow_coord;

void main() {
	gl_Position = u_mvp * vec4(in_position, 1.0);
	v_shadow_coord = u_light_space_transform * vec4(in_position, 1.0);
	v_vert = (u_mv * vec4(in_position, 1.0)).xyz;
	v_norm = (u_mv * vec4(in_normal, 0.0)).xyz; // should use the inverse transpose of u_mv if there is non-uniform scaling !!
}