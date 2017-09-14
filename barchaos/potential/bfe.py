def dwek1995_G2_density(x, y, z, x0, y0, z0, Rmax):
    return dwek1995_G2_helper(x, y, z, x0, y0, z0, Rmax, lib=math, f=f)

def dwek1995_G2_density_arr(x, y, z, x0, y0, z0, Rmax):
    return dwek1995_G2_helper(x, y, z, x0, y0, z0, Rmax, lib=np, f=f_arr)


# ---

def cao2013_density(x, y, z, x0, y0, z0):
    rr = (((x/x0)**2 + (y/y0)**2)**2 + (z/z0)**4)**0.25
    return kn(0, rr)

density = dwek1995_G2_density
density_arr = dwek1995_G2_density_arr
args = (1.49, 0.58, 0.4, 100.)
