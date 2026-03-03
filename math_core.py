import numpy as np
import math

try:
   from scipy.stats import norm
   SCIPY_AVAILABLE = True
except Exception:
   SCIPY_AVAILABLE = False

def cholesky_from_corr(corr):
   A = np.array(corr, dtype=float)
   return np.linalg.cholesky(A + 1e-12 * np.eye(A.shape[0]))

def gaussian_copula_draw(L, rng, n, iters=None):
   # If 'iters' is passed, draw a matrix for high-speed vectorization. 
   # Otherwise, draw a vector to keep the legacy construction engine working.
   size = (n, iters) if iters is not None else n
   
   z = rng.standard_normal(size=size)
   cz = L @ z
   
   if SCIPY_AVAILABLE: 
       u = norm.cdf(cz)
   else: 
       u = 0.5 * (1.0 + (2.0 / math.sqrt(math.pi)) * np.vectorize(math.erf)(cz / math.sqrt(2)))
       
   return cz, np.clip(u, 1e-9, 1 - 1e-9)

def sample_lognormal_from_z(mu, sigma, z):
   # Removed the strict float() cast so this computes across an entire array instantly
   return np.exp(mu + sigma * z)
