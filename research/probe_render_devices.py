"""Report EGL ordinals and their CUDA/DRM identities without creating a context."""
import ctypes
import ctypes.util
import json

def main():
    library=ctypes.CDLL(ctypes.util.find_library('EGL'))
    library.eglGetProcAddress.argtypes=[ctypes.c_char_p]
    library.eglGetProcAddress.restype=ctypes.c_void_p
    query=ctypes.CFUNCTYPE(ctypes.c_uint,ctypes.c_int,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_int))(
        library.eglGetProcAddress(b'eglQueryDevicesEXT'))
    string=ctypes.CFUNCTYPE(ctypes.c_char_p,ctypes.c_void_p,ctypes.c_int)(
        library.eglGetProcAddress(b'eglQueryDeviceStringEXT'))
    attribute=ctypes.CFUNCTYPE(ctypes.c_uint,ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_ssize_t))(
        library.eglGetProcAddress(b'eglQueryDeviceAttribEXT'))
    devices=(ctypes.c_void_p*32)();count=ctypes.c_int()
    assert query(32,devices,ctypes.byref(count))
    rows=[]
    for i in range(count.value):
        row={'egl_index':i}
        for name,constant in [('drm',0x3233),('render_node',0x3377),('extensions',0x3055)]:
            value=string(devices[i],constant);row[name]=value.decode() if value else None
        cuda=ctypes.c_ssize_t()
        row['cuda_device']=cuda.value if attribute(devices[i],0x323A,ctypes.byref(cuda)) else None
        rows.append(row)
    print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
