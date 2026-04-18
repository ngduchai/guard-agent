import math
L  = 1.12
dn = 0.001

Main(
    geometry = "1Dcartesian",
    interpolation_order = 2,
    cell_length = [0.01],
    grid_length  = [L],
    number_of_patches = [ 16 ],
    timestep = 0.0095,
    simulation_time = 10.,
    EM_boundary_conditions = [ ['periodic'] ],
)

Species(
    name = 'ion',
    position_initialization = 'regular',
    momentum_initialization = 'cold',
    particles_per_cell = 10,
    mass = 1836.0,
    charge = 1.0,
    number_density = 1.,
    time_frozen = 0.1,
    boundary_conditions = [['periodic']],
)
Species(
    name = 'eon',
    position_initialization = 'regular',
    momentum_initialization = 'cold',
    particles_per_cell = 10,
    mass = 1.0,
    charge = -1.0,
    number_density = cosine(1.,xamplitude=dn,xlength=L),
    boundary_conditions = [['periodic']],
)
