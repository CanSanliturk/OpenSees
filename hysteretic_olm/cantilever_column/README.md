# CANTILEVER COLUMN MODEL #

## MODEL INFO ##
* Cross-section: 0.5m * 0.5m
* Height: 3m
* Material
    * For Solid Model, nDMaterial('ElasticIsotropic', matTag, E, nu, rho=0.0), where E is 0.3
    * For Lattice Mode: uniaxialMaterial('Elastic', mat_tag, E)
* Lattice Horizon: 3^(0.5) * 1.01 -> to connect two edges of a cube

