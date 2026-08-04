"""OpenGL-based AI core widget with a simple GLSL fragment shader.
This provides a GPU-accelerated holographic core with time-based animation and
simple bloom-like glow using a shader. It's a foundation: the shader can be
extended to add rings, hexagons, particles and scanlines entirely on the GPU.
"""
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtGui import QOpenGLShaderProgram, QOpenGLShader
from PySide6.QtCore import QTimer, QSize
import math
import time
import logging

logger = logging.getLogger(__name__)

# GL constant for triangles (safe fallback without PyOpenGL)
GL_TRIANGLES = 4

VERTEX_SHADER = r"""
#version 330 core
void main() {
    const vec2 verts[3] = vec2[3](
        vec2(-1.0, -1.0),
        vec2(3.0, -1.0),
        vec2(-1.0, 3.0)
    );
    gl_Position = vec4(verts[gl_VertexID], 0.0, 1.0);
}
"""

FRAGMENT_SHADER = r"""
#version 330 core
out vec4 FragColor;
uniform float iTime;
uniform vec2 iResolution;

// Simple palette
vec3 pal(float t) {
    return mix(vec3(0.02,0.04,0.06), vec3(0.06,0.9,1.0), smoothstep(0.0,1.0,t));
}

float ring(vec2 p, float r, float w) {
    return smoothstep(r + w, r, length(p)) - smoothstep(r, r - w, length(p));
}

// 2D rotation
mat2 rot(float a) {
    float s = sin(a), c = cos(a);
    return mat2(c, -s, s, c);
}

// hexagonal modulation via 6-fold symmetry
float hex_mod(vec2 p) {
    float ang = atan(p.y, p.x);
    return cos(6.0 * ang) * 0.02;
}

// soft blur approximation by sampling neighbouring offsets
vec3 soft_bloom(vec2 uv, float t, vec2 res) {
    vec3 acc = vec3(0.0);
    float total = 0.0;
    float radius = 0.02;
    for (int i = 0; i < 8; ++i) {
        float a = float(i) * 3.14159 * 2.0 / 8.0 + t * 0.2;
        vec2 off = vec2(cos(a), sin(a)) * radius;
        float w = 0.6 * (1.0 - length(off) / radius);
        // recreate scene-like contribution at offset (cheap)
        vec2 p = uv + off * (res.x / res.y);
        float d = length(p);
        float g = exp(-d * 6.0);
        acc += vec3(0.05, 0.6, 1.0) * g * w;
        total += w;
    }
    return acc / max(total, 1.0);
}

void main() {
    vec2 uv = (gl_FragCoord.xy / iResolution.xy) * 2.0 - 1.0;
    uv.x *= iResolution.x / iResolution.y;
    float t = iTime;

    vec2 p = uv;
    float dist = length(p);

    // base glow
    float glow = exp(-dist * 6.5);

    // rotating rings, more layers
    float rings = 0.0;
    for (int i = 0; i < 5; ++i) {
        float ri = 0.12 + float(i) * 0.1 + 0.01 * sin(t * (0.6 + float(i) * 0.3));
        float w = 0.006 + 0.003 * float(i);
        float a = ring(p, ri, w);
        float ang = atan(p.y, p.x) + t * (0.2 + float(i) * 0.12);
        a *= 0.7 + 0.3 * sin(ang * 3.0 + float(i));
        rings += a;
    }

    // inner hex pulse
    float inner = smoothstep(0.028 + hex_mod(p), 0.018 + hex_mod(p), dist);

    // scanlines subtle
    float scan = 0.5 + 0.5 * sin((uv.y + t * 0.2) * 80.0) * 0.02;

    // particles
    float particles = 0.0;
    for (int i = 0; i < 7; ++i) {
        float a = t * (0.8 + float(i) * 0.25) + float(i) * 0.9;
        vec2 pp = (rot(t * 0.2 + float(i) * 0.7) * vec2(1.0, 0.0)) * (0.45 + 0.18 * sin(t * (1.0 + float(i) * 0.2)));
        float d = length(p - pp);
        particles += smoothstep(0.02, 0.0, d) * 0.9;
    }

    // radar sweep
    float sweep = max(0.0, 1.0 - length(p - vec2(cos(t*0.8), sin(t*0.8)) * 0.0) * 9.0);

    vec3 base = pal(dist) * (0.25 + 0.75 * glow);
    vec3 detail = vec3(0.05, 0.7, 1.0) * (rings * 1.8 + inner * 2.6 + particles * 1.4 + sweep * 0.6);

    // soft bloom from nearby sampling
    vec3 bloom = soft_bloom(p, t, iResolution) * 0.9;

    vec3 color = base + detail + bloom * 0.8;
    color *= 1.0 - 0.35 * dist;
    color = pow(color, vec3(0.85));
    color *= scan;

    FragColor = vec4(color, 1.0);
}
"""

class AICoreGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._program = None
        self._start = time.time()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(16)
        self.setMinimumSize(QSize(400, 400))
        self._fbo_supported = False

    def initializeGL(self):
        # Compile shaders
        self._program = QOpenGLShaderProgram(self.context())
        vert_ok = self._program.addShaderFromSourceCode(QOpenGLShader.Vertex, VERTEX_SHADER)
        if not vert_ok:
            logger.error('Vertex shader compile error: %s', self._program.log())
        frag_ok = self._program.addShaderFromSourceCode(QOpenGLShader.Fragment, FRAGMENT_SHADER)
        if not frag_ok:
            logger.error('Fragment shader compile error: %s', self._program.log())
        if not self._program.link():
            logger.error('Shader program link error: %s', self._program.log())

        # Try to probe FBO support (best-effort)
        try:
            from PySide6.QtGui import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat
            fmt = QOpenGLFramebufferObjectFormat()
            fmt.setAttachment(QOpenGLFramebufferObject.CombinedDepthStencil)
            fbo = QOpenGLFramebufferObject(max(4, self.width()), max(4, self.height()), fmt)
            self._fbo_supported = fbo.isValid()
            del fbo
        except Exception as e:
            logger.debug('FBO probe failed: %s', e)
            self._fbo_supported = False

    def resizeGL(self, w: int, h: int):
        # nothing special for now
        pass

    def paintGL(self):
        if not self._program:
            return
        self._program.bind()
        iTime = float(time.time() - self._start)
        self._program.setUniformValue('iTime', iTime)
        res = self.size()
        self._program.setUniformValue('iResolution', res.width(), res.height())
        # draw full-screen triangle
        funcs = None
        try:
            funcs = self.context().functions()
            funcs.glDrawArrays(GL_TRIANGLES, 0, 3)
        except Exception as e:
            # Some platforms may not allow raw glDrawArrays via these wrappers; fallback to Qt drawing
            logger.debug('glDrawArrays failed (%s); falling back to update-only', e)
        self._program.release()

    def get_diagnostics(self) -> dict:
        """Return diagnostics information for display in the diagnostics panel."""
        info = {
            'fbo_supported': getattr(self, '_fbo_supported', False),
            'shader_log': None,
            'gl_version': 'unknown',
            'is_valid': False,
        }
        try:
            ctx = self.context()
            if ctx is not None:
                fmt = ctx.format()
                info['gl_version'] = f"GL {fmt.majorVersion()}.{fmt.minorVersion()} profile={fmt.profile()}"
                info['is_valid'] = ctx.isValid()
            if self._program is not None:
                info['shader_log'] = self._program.log()
        except Exception:
            pass
        return info
