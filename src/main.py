from args import args
import jax
from jax.config import config
config.update("jax_enable_x64", True)
import numpy as np
import jax.numpy as jnp
from jax import jit,value_and_grad
from loss import optimize_runtime_loss
from loadwrite import initialT,savelog,savelog_trivial
from exact import eg

# Manopt
from pymanopt.manifolds import Stiefel
from pymanopt import Problem
from pymanopt.solvers import TrustRegions,ConjugateGradient

if __name__ == '__main__':
# TEMP:
    np.random.seed(args.seed)
    Nv = args.Nv
    Tsize = 8*Nv+4
    LoadKey = "/home/qiyang/source/jaxgfpeps/result/Nv{}C{}.h5".format(args.Nv,args.loadlabel)
    Key = "/home/qiyang/source/jaxgfpeps/result/Nv{}C{}.h5".format(args.Nv,args.label)
#
    T = initialT(LoadKey,Tsize)
    #
    # Project T to Stiefel Manifold
    U,S,V = np.linalg.svd(T)
    T = U @ V
#
    lossT = jit(optimize_runtime_loss(Nv=args.Nv,Lx=args.Lx,Ly=args.Ly,
    hoping=args.ht,DeltaX=args.DeltaX,DeltaY=args.DeltaY,Mu=args.Mu),backend='gpu')
#
    def egrad(x): return np.array(jax.grad(lossT)(jnp.array(x)))
    #
    @jax.jit
    def hvp_loss(primals, tangents): return jax.jvp(jax.grad(lossT), primals, tangents)[1]
    # def ehess(x): return np.array(jax.hessian(lossT)(jnp.array(x)))
    # def ehessa(x,a): return np.array(jnp.einsum('ijkl,kl->ij',jax.hessian(lossT)(jnp.array(x)),jnp.array(a)))
    def ehessa(x,v): return np.array(hvp_loss((jnp.array(x),), (jnp.array(v),)))
    #
    Eg = eg(args.Lx,args.Ly,args.ht,args.DeltaX,args.DeltaY,args.Mu)
    print("Eg = {}\n".format(Eg))
    # Optimizer
    manifold = Stiefel(Tsize, Tsize)
    problem = Problem(manifold=manifold, cost=lossT,egrad=egrad,ehess=ehessa)
    if args.optimizer == 'trust-ncg':
        solver = TrustRegions(maxiter=args.MaxIter)
    elif args.optimizer == 'conj-grad':
        solver = ConjugateGradient(maxiter=args.MaxIter)
#
    Xopt = solver.solve(problem,x=T)
#
    savelog_trivial(Key,Xopt,lossT(Xopt),Eg,args)