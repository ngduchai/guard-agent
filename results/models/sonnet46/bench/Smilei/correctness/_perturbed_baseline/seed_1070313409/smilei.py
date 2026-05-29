# coding: utf-8

"""
    GENERAL DEFINITIONS FOR SMILEI
"""

import math, os, gc, operator

def _add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    # Taken from module "six" for compatibility with python 2 and 3
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str): slots = [slots]
            for slots_var in slots: orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


class SmileiComponentType(type):
    """Metaclass to all Smilei components"""

    # Constructor of classes
    def __init__(self, name, bases, attrs):
        self._list = []
        self._verify = True
        # Run standard metaclass init
        super(SmileiComponentType, self).__init__(name, bases, attrs)

    # Functions to define the iterator
    def __iter__(self):
        self.current = 0
        return self
    def next(self):
        if self.current >= len(self._list):
            raise StopIteration
        self.current += 1
        return self._list[self.current - 1]
    __next__ = next #python3

    # Function to return one given instance, for example DiagParticleBinning[0]
    # Special case: species can also be indexed by their name: Species["ion1"]
    # Special case: diagnostics can also be indexed by their label: DiagParticleBinning["x-px"]
    def __getitem__(self, key):
        try:
            for obj in self._list:
                if obj.name == key:
                    return obj
        except:
            pass
        return self._list[key]
    
    def has(self, key):
        if type(key) is int and key < len(self._list):
            return True
        for obj in self._list:
            if obj.name == key:
                return True
        return False
    
    # Function to return the number of instances, for example len(Species)
    def __len__(self):
        return len(self._list)

    # Function to display the list of instances
    def __repr__(self):
        if len(self._list)==0:
            return "<Empty list of "+self.__name__+">"
        else:
            l = []
            for obj in self._list: l.append(str(obj))
            return "["+", ".join(l)+"]"

@_add_metaclass(SmileiComponentType)
class SmileiComponent(object):
    """Smilei component generic class"""

    # Function to initialize new components
    def _fillObjectAndAddToList(self, cls, obj, **kwargs):
        # add all kwargs as internal class variables
        if kwargs is not None:
            deprecated = {
                "output_format":"See documentation for radiation reaction",
                "clrw":"See https://smileipic.github.io/Smilei/namelist.html#main-variables",
                "h_chipa_min":"See documentation for radiation reaction",
                "h_chipa_max":"See documentation for radiation reaction",
                "h_dim":"See documentation for radiation reaction",
                "h_computation_method":"See documentation for radiation reaction",
                "integfochi_chipa_min":"See documentation for radiation reaction",
                "integfochi_chipa_max":"See documentation for radiation reaction",
                "integfochi_dim":"See documentation for radiation reaction",
                "xip_chipa_min":"See documentation for radiation reaction",
                "xip_chipa_max":"See documentation for radiation reaction",
                "xip_power":"See documentation for radiation reaction or Breit-Wheeler",
                "xip_threshold":"See documentation for radiation reaction or Breit-Wheeler",
                "xip_chipa_dim":"See documentation for radiation reaction or Breit-Wheeler",
                "xip_chiph_dim":"See documentation for radiation reaction or Breit-Wheeler",
                "compute_table":"See documentation for Breit-Wheeler",
                "T_chiph_min":"See documentation for Breit-Wheeler",
                "T_chiph_max":"See documentation for Breit-Wheeler",
                "T_dim":"See documentation for Breit-Wheeler",
                "xip_chiph_min":"See documentation for Breit-Wheeler",
                "xip_chiph_max":"See documentation for Breit-Wheeler",
            }
            for key, value in kwargs.items():
                if key in deprecated:
                    raise Exception("Deprecated `"+key+"` parameter. "+deprecated[key])
                if key=="_list":
                    print("Python warning: in "+cls.__name__+": cannot have argument named '_list'. Discarding.")
                elif not hasattr(cls, key):
                    raise Exception("ERROR in the namelist: cannot define `"+key+"` in block "+cls.__name__+"()");
                else:
                    setattr(obj, key, value)
        # add the new component to the "_list"
        cls._list.append(obj)

    # Constructor for all SmileiComponents
    def __init__(self, **kwargs):
        self._fillObjectAndAddToList(type(self), self, **kwargs)

    def __repr__(self):
        return "<Smilei "+type(self).__name__+">"


class SmileiSingletonType(SmileiComponentType):
    """Metaclass to all Smilei singletons"""

    def __repr__(self):
        return "<Smilei "+str(self.__name__)+">"

@_add_metaclass(SmileiSingletonType)
class SmileiSingleton(SmileiComponent):
    """Smilei singleton generic class"""

    # Prevent having two instances
    def __new__(cls, **kwargs):
        if len(cls._list) >= 1:
            raise Exception("ERROR in the namelist: cannot define block "+cls.__name__+"() twice")
        return super(SmileiSingleton, cls).__new__(cls)

    # Constructor for all SmileiSingletons
    def __init__(self, **kwargs):
        cls = type(self)
        self._fillObjectAndAddToList(cls, cls, **kwargs)
        # Change all methods to static
        for k,v in cls.__dict__.items():
            if k[0]!='_' and hasattr(v,"__get__"):
               setattr(cls, k, staticmethod(v))

class ParticleData(object):
    """Container for particle data at run-time (for exposing particles in numpy)"""
    _verify = True

class Main(SmileiSingleton):
    """Main parameters"""

    # Default geometry info
    geometry = None
    cell_length = []
    grid_length = []
    number_of_cells = []
    timestep = None
    simulation_time = None
    number_of_timesteps = None
    interpolation_order = 2
    interpolator = "momentum-conserving"
    custom_oversize = 2
    number_of_patches = None
    patch_arrangement = "hilbertian"
    cluster_width = -1
    every_clean_particles_overhead = 100
    timestep = None
    number_of_AM = 2
    number_of_AM_relativistic_field_initialization = 1
    number_of_AM_classical_Poisson_solver = 1
    timestep_over_CFL = None
    cell_sorting = None
    gpu_computing = False                      # Activate the computation on GPU
    
    # PXR tuning
    spectral_solver_order = []
    initial_rotational_cleaning = False

    # Poisson tuning
    solve_poisson = True
    poisson_max_iteration = 50000
    poisson_max_error = 1.e-14

    # Relativistic Poisson tuning
    solve_relativistic_poisson = False
    relativistic_poisson_max_iteration = 50000
    relativistic_poisson_max_error = 1.e-22
    
    # BTIS3 interpolator
    use_BTIS3_interpolation = False

    # Default fields
    maxwell_solver = 'Yee'
    EM_boundary_conditions = [["periodic"]]
    EM_boundary_conditions_k = []
    save_magnectic_fields_for_SM = True
    number_of_pml_cells = [[10]]

    def default_sigma(x):
        return 20. * x**2  
    def default_integrate_sigma(x):
        return 20./3. * x**3  
    def default_kappa(x):
        return 1 + 79. * x**4  
    def default_integrate_kappa(x):
        return x + 79./5. * x**5  

    pml_sigma = [default_sigma, default_sigma, default_sigma, default_integrate_sigma]
    pml_kappa = [default_kappa, default_kappa, default_kappa, default_integrate_kappa]
    time_fields_frozen = 0.
    Laser_Envelope_model = False

    # Default Misc
    reference_angular_frequency_SI = 0.
    print_every = None
    random_seed = None
    print_expected_disk_usage = True

    terminal_mode = True

    def __init__(self, **kwargs):
        # Load all arguments to Main()
        super(Main, self).__init__(**kwargs)

        # Initialize grid_length if not defined based on number_of_cells and cell_length
        if (    len(Main.grid_length + Main.number_of_cells) == 0
             or len(Main.grid_length + Main.cell_length) == 0
             or len(Main.number_of_cells + Main.cell_length) == 0
             or len(Main.number_of_cells) * len(Main.grid_length) * len(Main.cell_length) != 0
           ):
                raise Exception("ERROR in the namelist in Main: you must define exactly two parameters among grid_length, number_of_cells and cell_length")

        if len(Main.grid_length) == 0:
            Main.grid_length = [a*b for a,b in zip(Main.number_of_cells, Main.cell_length)]

        if len(Main.cell_length) == 0:
            Main.cell_length = [a/b for a,b in zip(Main.grid_length, Main.number_of_cells)]

        if len(Main.number_of_cells) == 0:
            Main.number_of_cells = [int(round(float(a)/float(b))) for a,b in zip(Main.grid_length, Main.cell_length)]
            old_grid_length = Main.grid_length
            Main.grid_length = [a*b for a,b in zip(Main.number_of_cells, Main.cell_length)]
            if smilei_mpi_rank == 0:
                different = [abs((a-b)/(a+b))>1e-10 for a,b in zip(Main.grid_length, old_grid_length)]
                if any(different):
                    print("\t[Python WARNING] Main.grid_length="+str(Main.grid_length)+" (was "+str(old_grid_length)+")")


        # Initialize timestep if not defined based on timestep_over_CFL
        if Main.timestep is None:
            if Main.timestep_over_CFL is None:
                raise Exception("ERROR in the namelist in Main: timestep and timestep_over_CFL not defined")
            else:
                # Yee solver or Terzani solver
                if Main.maxwell_solver in ['Yee','Terzani']:
                    if Main.geometry=="AMcylindrical":
                        alpha = [0.210486, 0.591305, 3.5234, 8.51041, 15.5059]
                        if Main.number_of_AM < 6:
                            alpha = 1. + alpha[Main.number_of_AM-1]
                        else:
                            alpha = (Main.number_of_AM-1)**2
                        Main.timestep = Main.timestep_over_CFL / math.sqrt(1./Main.cell_length[0]**2 + alpha/Main.cell_length[1]**2 )
                        if Main.maxwell_solver == "Terzani":
                            print("WARNING CFL: The timestep has been set as for a Yee solver but the maximum stable timestep for the Terzani solver may be slightly smaller.")
                    else:
                        dim = int(Main.geometry[0])
                        Main.timestep = Main.timestep_over_CFL / math.sqrt(sum([1./l**2 for l in Main.cell_length]))

                # Grassi
                elif Main.maxwell_solver == 'Grassi':
                    if Main.geometry == '2Dcartesian':
                        Main.timestep = Main.timestep_over_CFL * 0.7071067811*Main.cell_length[0];
                    else:
                        raise Exception("ERROR in the namelist in Main: timestep_over_CFL for the Grassi solver not implemented in geometry "+Main.geometry)

                # GrassiSpL
                elif Main.maxwell_solver == 'GrassiSpL':
                    if Main.geometry == '2Dcartesian':
                        Main.timestep = Main.timestep_over_CFL * 0.6471948469*Main.cell_length[0];
                    else:
                        raise Exception("ERROR in the namelist in Main: timestep_over_CFL for the GrassiSpL solver not implemented in geometry "+Main.geometry)

                # M4
                elif Main.maxwell_solver == 'M4':
                    if Main.geometry == '1Dcartesian':
                        Main.timestep = Main.timestep_over_CFL * Main.cell_length[0];
                    elif Main.geometry == '2Dcartesian':
                        Main.timestep = Main.timestep_over_CFL * min(Main.cell_length[0:2])
                    elif Main.geometry == '3Dcartesian':
                        Main.timestep = Main.timestep_over_CFL * min(Main.cell_length)
                    else:
                        raise Exception("ERROR in the namelist in Main: timestep_over_CFL for the M4 solver not implemented in geometry "+Main.geometry)

                # None recognized solver
                else:
                    raise Exception("ERROR in the namelist in Main: timestep_over_CFL not implemented for the solver "+Main.maxwell_solver)

        # Constraint on timestep for WT interpolation
        if Main.interpolator.lower() == "wt":
            if Main.geometry == '1Dcartesian':
                if Main.timestep > 0.5 * Main.cell_length[0]:
                    raise Exception("timestep for WT cannot be larger than 0.5*dx")
            elif Main.geometry == '2Dcartesian':
                if Main.timestep > 0.5 * min(Main.cell_length[0:2]):
                    raise Exception("timestep for WT cannot be larger than 0.5*min(dx,dy)")
            elif Main.geometry == '3Dcartesian':
                if Main.timestep > 0.5 * min(Main.cell_length):
                    raise Exception("timestep for WT cannot be larger than 0.5*min(dx,dy,dz)")
            else:
                raise Exception("WT interpolation not implemented in geometry "+Main.geometry)

        # Initialize simulation_time if not defined by the user
        if Main.simulation_time is None:
            if Main.number_of_timesteps is None:
                raise Exception("ERROR in the namelist in Main: simulation_time and number_of_timesteps are not defined")
            Main.simulation_time = Main.timestep * Main.number_of_timesteps

class LoadBalancing(SmileiSingleton):
    """Load balancing parameters"""

    every                = 150
    initial_balance      = True
    cell_load            = 1.0
    frozen_particle_load = 0.1

class MultipleDecomposition(SmileiSingleton):
    """Multiple Decomposition parameters"""
    region_ghost_cells   = 2

# Radiation reaction configuration (continuous and MC algorithms)
class Vectorization(SmileiSingleton):
    """
    Vectorization parameters
    """
    mode                = "off"
    reconfigure_every   = 20
    initial_mode        = "off"


class MovingWindow(SmileiSingleton):
    """Moving window parameters"""

    time_start = 0.
    velocity_x = 1.
    number_of_additional_shifts = 0
    additional_shifts_time = 0.


class CurrentFilter(SmileiSingleton):
    """Current filtering parameters"""
    model = "binomial"
    passes = [0]
    kernelFIR = [0.25,0.5,0.25]

class FieldFilter(SmileiSingleton):
    """Fields filtering parameters"""
    model = "Friedman"
    theta = 0.

class Species(SmileiComponent):
    """Species parameters"""
    name = None
    position_initialization = None
    momentum_initialization = ""
    particles_per_cell = None
    regular_number = []
    c_part_max = 1.0
    mass = None
    charge = None
    charge_density = None
    number_density = None
    mean_velocity = []  # Default value is     0, set in ParticleCreator function in species.cpp
    mean_velocity_AM = []
    temperature = []    # Default value is 1e-10, set in ParticleCreator function in species.cpp
    thermal_boundary_temperature = []
    thermal_boundary_velocity = [0.,0.,0.]
    pusher = "boris"

    # Radiation species parameters
    radiation_model = "none"
    radiation_photon_species = None
    radiation_photon_sampling = 1
    radiation_photon_gamma_threshold = 2.
    radiation_max_emissions = 10

    # Multiphoton Breit-Wheeler parameters
    multiphoton_Breit_Wheeler = [None,None]
    multiphoton_Breit_Wheeler_sampling = [1,1]

    # Particle merging species Parameters
    merging_method = "none"
    merge_every = 0
    merge_min_packet_size = 4
    merge_max_packet_size = 4
    merge_min_particles_per_cell = 4
    merge_min_momentum_cell_length = [1e-10,1e-10,1e-10]
    merge_momentum_cell_size = [16,16,16]
    merge_accumulation_correction = True
    merge_discretization_scale = "linear"
    merge_min_momentum = 1e-5

    time_frozen = 0.0
    radiating = False
    relativistic_field_initialization = False
    boundary_conditions = [["periodic"]]
    ionization_model = "none"
    bsi_model = "none"
    ionization_electrons = None
    ionization_rate = None
    atomic_number = None
    maximum_charge_state = 0
    ionization_tl_parameter = 6
    is_test = False
    relativistic_field_initialization = False
    keep_interpolated_fields = []

class ParticleInjector(SmileiComponent):
    """Parameters for particle injection at boundaries"""
    name = None
    species = None
    box_side = "xmin"
    position_initialization = "species"
    momentum_initialization = "species"
    mean_velocity = []  # Default value is     0, set in ParticleCreator function
    temperature = []    # Default value is 1e-10, set in ParticleCreator function
    charge_density = None
    number_density = None
    particles_per_cell = None
    regular_number = []
    time_envelope = 1
    
    
class Laser(SmileiComponent):
    """Laser parameters"""
    box_side = "xmin"
    omega = 1.
    chirp_profile = 1.
    time_envelope = 1.
    space_envelope = [1., 0.]
    phase = [0., 0.]
    delay_phase = [0., 0.]
    space_time_profile = None
    space_time_profile_AM = None
    file = None
    _offset = None

class LaserEnvelope(SmileiSingleton):
    """Laser Envelope parameters"""
    omega = 1.
    #time_envelope = 1.
    #space_envelope = [1., 0.]
    envelope_solver = "explicit"
    envelope_profile = None
    Envelope_boundary_conditions = [["reflective"]]
    '''
    Defaut parameters tested in AM geometry for
    dx = 0.5 ; dy = 2*dx ; dt = 0.8*dx with 'envelope_reduced_dispersion' solver
    PML cells = 16
    Give good results for a propagation during 40 000 dt
    '''
    Env_pml_sigma_parameters = [[0.00,2],[20.0,2],[20.0,2]]
    Env_pml_kappa_parameters = [[1.00,1.00,2],[1.00,1.00,2],[1.00,1.00,2]]
    Env_pml_alpha_parameters = [[0.00,0.00,1],[0.05,0.05,1],[0.05,0.05,1]]
    polarization_phi = 0.
    ellipticity = 0.
    box_side = "inside" #"xmin"


class Collisions(SmileiComponent):
    """Collisions parameters"""
    species1 = None
    species2 = None
    coulomb_log = 0.
    coulomb_log_factor = 1.
    every = 1
    debug_every = 0
    time_frozen = 0
    ionizing = False
    nuclear_reaction = None
    nuclear_reaction_multiplier = 0.


#diagnostics
class DiagProbe(SmileiComponent):
    """Probe diagnostic"""
    name = ""
    every = None
    number = []
    origin = []
    corners = []
    vectors = []
    fields = []
    flush_every = 1
    time_integral = False
    datatype = "double"

class DiagParticleBinning(SmileiComponent):
    """Particle Binning diagnostic"""
    name = ""
    deposited_quantity = None
    time_average = 1
    species = None
    axes = []
    every = None
    flush_every = 1

class DiagRadiationSpectrum(SmileiComponent):
    """Radiation Spectrum diagnostic"""
    name = ""
    time_average = 1
    species = None
    photon_energy_axis = None
    axes = []
    every = None
    flush_every = 1

class DiagScreen(SmileiComponent):
    """Screen diagnostic"""
    name = ""
    shape = None
    point = None
    vector = None
    direction = "both"
    deposited_quantity = None
    species = None
    axes = []
    time_average = 1
    every = None
    flush_every = 1

class DiagScalar(SmileiComponent):
    """Scalar diagnostic"""
    every = None
    precision = 10
    vars = []

class DiagFields(SmileiComponent):
    """Field diagnostic"""
    name = ""
    every = None
    fields = []
    time_average = 1
    subgrid = None
    flush_every = 1
    datatype = "double"

class DiagTrackParticles(SmileiComponent):
    """Track diagnostic"""
    name = ""
    species = None
    every = 0
    flush_every = 1
    filter = None
    attributes = ["x", "y", "z", "px", "py", "pz", "w"]

class DiagNewParticles(SmileiComponent):
    """Track diagnostic"""
    name = ""
    species = None
    every = 0
    flush_every = 1
    filter = None
    attributes = ["x", "y", "z", "px", "py", "pz", "w"]

class DiagPerformances(SmileiSingleton):
    """Performances diagnostic"""
    every = 0
    flush_every = 1
    patch_information = True

# external fields
class ExternalField(SmileiComponent):
    """External Field"""
    field = None
    profile = None

# external time fields
class PrescribedField(SmileiComponent):
    """External Time Field"""
    field = None
    profile = None

# external current (antenna)
class Antenna(SmileiComponent):
    """Antenna"""
    field = None
    time_profile  = None
    space_profile = None
    space_time_profile = None

# Particle wall
class PartWall(SmileiComponent):
    """Particle Wall"""
    kind = "none"
    x = None
    y = None
    z = None


# Radiation reaction configuration (continuous and MC algorithms)
class RadiationReaction(SmileiComponent):
    """
    Fine-tuning of synchrotron-like radiation reaction
    (classical continuous, quantum correction, stochastics and MC algorithms)
    """
    # Minimum particle_chi value for the discontinuous radiation
    # Under this value, the discontinuous approach is not applied
    minimum_chi_discontinuous = 1e-2
    # Threshold on particle_chi: if particle_chi < 1E-3 no radiation reaction
    minimum_chi_continuous = 1e-3

    # Path to read or write the tables/databases
    table_path = ""

    # Parameters for computing the tables
    Niel_computation_method = "table"

# MultiphotonBreitWheeler pair creation
class MultiphotonBreitWheeler(SmileiComponent):
    """
    Photon decay into electron-positron pairs
    """
    # Path the tables/databases
    table_path = ""

# Smilei-defined
smilei_mpi_rank = 0
smilei_mpi_size = 1
smilei_omp_threads = 1
smilei_total_cores = 1

# Variable to set to False for the actual run (useful for the test mode)
_test_mode = True
smilei_version='491d8929c-main'
smilei_mpi_size = 4
smilei_omp_threads = 8
smilei_total_cores = 32
# Some predefined profiles (see doc)

def constant(value, xvacuum=-float("inf"), yvacuum=-float("inf"), zvacuum=-float("inf")):
    global Main
    if len(Main)==0:
        raise Exception("constant profile has been defined before `Main()`")
    if Main.geometry == "1Dcartesian":
        f = lambda x,t=0: value if x>=xvacuum else 0.
    if (Main.geometry == "2Dcartesian" or Main.geometry == "AMcylindrical"):
        f = lambda x,y,t=0: value if (x>=xvacuum and y>=yvacuum) else 0.
    if Main.geometry == "3Dcartesian":
        f = lambda x,y,z,t=0: value if (x>=xvacuum and y>=yvacuum and z>=zvacuum) else 0.
    f.profileName = "constant"
    f.value   = value
    f.xvacuum = xvacuum
    f.yvacuum = yvacuum
    f.zvacuum = zvacuum
    return f
constant._reserved = True

def trapezoidal(max,
                xvacuum=0., xplateau=None, xslope1=0., xslope2=0.,
                yvacuum=0., yplateau=None, yslope1=0., yslope2=0.,
                zvacuum=0., zplateau=None, zslope1=0., zslope2=0. ):
    global Main
    if len(Main)==0:
        raise Exception("trapezoidal profile has been defined before `Main()`")
    if len(Main.grid_length)>0 and xplateau is None: xplateau = Main.grid_length[0]-xvacuum
    if len(Main.grid_length)>1 and yplateau is None: yplateau = Main.grid_length[1]-yvacuum
    if len(Main.grid_length)>2 and zplateau is None: zplateau = Main.grid_length[2]-zvacuum
    def trapeze(max, vacuum, plateau, slope1, slope2):
        def f(position):
            # vacuum region
            if position < vacuum: return 0.
            # linearly increasing density
            elif position < vacuum+slope1: return max*(position-vacuum) / slope1
            # density plateau
            elif position < vacuum+slope1+plateau: return max
            # linearly decreasing density
            elif position < vacuum+slope1+plateau+slope2:
                return max*(1. - ( position - (vacuum+slope1+plateau) ) / slope2)
            # beyond the plasma
            else: return 0.0
        return f
    if   Main.geometry == "1Dcartesian": dim = 1
    elif (Main.geometry == "2Dcartesian" or Main.geometry == "AMcylindrical"): dim = 2
    elif Main.geometry == "3Dcartesian": dim = 3
    fx = trapeze(max, xvacuum, xplateau, xslope1, xslope2)
    f = fx
    if dim > 1:
        fy = trapeze(1. , yvacuum, yplateau, yslope1, yslope2)
        f = lambda x,y: fx(x)*fy(y)
    if dim > 2:
        fz = trapeze(1. , zvacuum, zplateau, zslope1, zslope2)
        f = lambda x,y,z: fx(x)*fy(y)*fz(z)
    f.profileName = "trapezoidal"
    f.value    = max
    f.xvacuum  = xvacuum
    f.xplateau = xplateau
    f.xslope1  = xslope1
    f.xslope2  = xslope2
    if dim > 1:
        f.yvacuum  = yvacuum
        f.yplateau = yplateau
        f.yslope1  = yslope1
        f.yslope2  = yslope2
    if dim > 2:
        f.zvacuum  = zvacuum
        f.zplateau = zplateau
        f.zslope1  = zslope1
        f.zslope2  = zslope2
    return f

def gaussian(max,
             xvacuum=0., xlength=float("inf"), xfwhm=None, xcenter=None, xorder=2,
             yvacuum=0., ylength=float("inf"), yfwhm=None, ycenter=None, yorder=2,
             zvacuum=0., zlength=float("inf"), zfwhm=None, zcenter=None, zorder=2 ):
    import math
    global Main
    if len(Main)==0:
        raise Exception("gaussian profile has been defined before `Main()`")
    if len(Main.grid_length)>0:
        if xlength is None: xlength = Main.grid_length[0]-xvacuum
        if xfwhm   is None: xfwhm   = (Main.grid_length[0]-xvacuum)/3.
        if xcenter is None: xcenter = xvacuum + (Main.grid_length[0]-xvacuum)/2.
    if len(Main.grid_length)>1:
        if ylength is None: ylength = Main.grid_length[1]-yvacuum
        if yfwhm   is None: yfwhm   = (Main.grid_length[1]-yvacuum)/3.
        if ycenter is None: ycenter = yvacuum + (Main.grid_length[1]-yvacuum)/2.
    if len(Main.grid_length)>2:
        if zlength is None: zlength = Main.grid_length[2]-zvacuum
        if zfwhm   is None: zfwhm   = (Main.grid_length[2]-zvacuum)/3.
        if zcenter is None: zcenter = zvacuum + (Main.grid_length[2]-zvacuum)/2.
    def gauss(max, vacuum, length, sigma, center, order):
        def f(position):
            if order == 0: return max
            # vacuum region
            if position < vacuum: return 0.
            # gaussian
            elif position < vacuum+length: return max*math.exp( -(position-center)**order / sigma )
            # beyond
            else: return 0.0
        return f
    if Main.geometry == "1Dcartesian": dim = 1
    if (Main.geometry == "2Dcartesian" or Main.geometry == "AMcylindrical"): dim = 2
    if Main.geometry == "3Dcartesian": dim = 3
    xsigma = (0.5*xfwhm)**xorder/math.log(2.0)
    fx = gauss(max, xvacuum, xlength, xsigma, xcenter, xorder)
    f = fx
    if dim > 1:
        ysigma = (0.5*yfwhm)**yorder/math.log(2.0)
        fy = gauss(1., yvacuum, ylength, ysigma, ycenter, yorder)
        f = lambda x,y: fx(x)*fy(y)
    if dim > 2:
        zsigma = (0.5*zfwhm)**zorder/math.log(2.0)
        fz = gauss(1., zvacuum, zlength, zsigma, zcenter, zorder)
        f = lambda x,y,z: fx(x)*fy(y)*fz(z)
    f.profileName = "gaussian"
    f.value   = max
    f.xvacuum = xvacuum
    f.xlength = xlength
    f.xsigma  = xsigma
    f.xcenter = xcenter
    f.xorder  = xorder
    if dim > 1:
        f.yvacuum = yvacuum
        f.ylength = ylength
        f.ysigma  = ysigma
        f.ycenter = ycenter
        f.yorder  = yorder
    if dim > 2:
        f.zvacuum = zvacuum
        f.zlength = zlength
        f.zsigma  = zsigma
        f.zcenter = zcenter
        f.zorder  = zorder
    return f


def polygonal(xpoints=[], xvalues=[]):
    global Main
    if len(Main)==0:
        raise Exception("polygonal profile has been defined before `Main()`")
    if len(xpoints)!=len(xvalues):
        raise Exception("polygonal profile requires as many points as values")
    if len(Main.grid_length)>0 and len(xpoints)==0:
        xpoints = [0., Main.grid_length[0]]
        xvalues = [1., 1.]
    N = len(xpoints)
    xpoints = [float(x) for x in xpoints]
    xvalues = [float(x) for x in xvalues]
    xslopes = [0. for i in range(1,N)]
    for i in range(1,N):
        if xpoints[i] == xpoints[i-1]: continue
        xslopes[i-1] = (xvalues[i]-xvalues[i-1])/(xpoints[i]-xpoints[i-1])
    def f(x,y=0.,z=0.):
        if x < xpoints[0]: return 0.0;
        for i in range(1,N):
            if x<xpoints[i]: return xvalues[i-1] + xslopes[i-1] * ( x-xpoints[i-1] )
        return 0.
    f.profileName = "polygonal"
    f.xpoints = xpoints
    f.xvalues = xvalues
    f.xslopes = xslopes
    return f

def cosine(base,
           xamplitude=1., xvacuum=0., xlength=None, xphi=0., xnumber=2,
           yamplitude=1., yvacuum=0., ylength=None, yphi=0., ynumber=2,
           zamplitude=1., zvacuum=0., zlength=None, zphi=0., znumber=2):
    import math
    global Main
    if len(Main)==0:
        raise Exception("cosine profile has been defined before `Main()`")

    if len(Main.grid_length)>0 and xlength is None: xlength = Main.grid_length[0]-xvacuum
    if len(Main.grid_length)>1 and ylength is None: ylength = Main.grid_length[1]-yvacuum
    if len(Main.grid_length)>2 and zlength is None: zlength = Main.grid_length[2]-zvacuum

    def cos(base, amplitude, vacuum, length, phi, number):
        def f(position):
            #vacuum region
            if position < vacuum: return 0.
            # profile region
            elif position < vacuum+length:
                return base + amplitude * math.cos(phi + 2.*math.pi * number * (position-vacuum)/length)
            # beyond
            else: return 0.
        return f
    if Main.geometry == "1Dcartesian": dim = 1
    if (Main.geometry == "2Dcartesian" or Main.geometry == "AMcylindrical"): dim = 2
    if Main.geometry == "3Dcartesian": dim = 3
    fx = cos(base, xamplitude, xvacuum, xlength, xphi, xnumber)
    f = fx
    if dim > 1:
        fy = cos(base, yamplitude, yvacuum, ylength, yphi, ynumber)
        f = lambda x,y: fx(x)*fy(y)
    if dim > 2:
        fz = cos(base, zamplitude, zvacuum, zlength, zphi, znumber)
        f = lambda x,y,z: fx(x)*fy(y)*fz(z)
    f.profileName = "cosine"
    f.base        = base
    f.xamplitude  = xamplitude
    f.xvacuum     = xvacuum
    f.xlength     = xlength
    f.xphi        = xphi
    f.xnumber     = float(xnumber)
    if dim > 1:
        f.yamplitude  = yamplitude
        f.yvacuum     = yvacuum
        f.ylength     = ylength
        f.yphi        = yphi
        f.ynumber     = float(ynumber)
    if dim > 2:
        f.zamplitude  = zamplitude
        f.zvacuum     = zvacuum
        f.zlength     = zlength
        f.zphi        = zphi
        f.znumber     = float(znumber)
    return f

def polynomial(**kwargs):
    global Main
    if len(Main)==0:
        raise Exception("polynomial profile has been defined before `Main()`")
    x0 = 0.
    y0 = 0.
    z0 = 0.
    coeffs = dict()
    for k, a in kwargs.items():
        if   k=="x0":
            x0 = a
        elif k=="y0":
            y0 = a
        elif k=="z0":
            z0 = a
        elif k[:5]=="order":
            if type(a) is not list: a = [a]
            order = int(k[5:])
            coeffs[ order ] = a
            if Main.geometry=="1Dcartesian":
                if len(a)!=1:
                    raise Exception("1D polynomial profile must have one coefficient at order "+str(order))
            elif (Main.geometry=="2Dcartesian" or Main.geometry == "AMcylindrical"):
                if len(a)!=order+1:
                    raise Exception("2D polynomial profile must have "+str(order+1)+" coefficients at order "+str(order))
            elif Main.geometry=="3Dcartesian":
                if len(a)!=(order+1)*(order+2)/2:
                    raise Exception("3D polynomial profile must have "+str((order+1)*(order+2)/2)+" coefficients at order "+str(order))
    if Main.geometry=="1Dcartesian":
        def f(x):
            r = 0.
            xx0 = x-x0
            xx = 1.
            currentOrder = 0
            for order, c in sorted(coeffs.items()):
                while currentOrder<order:
                    currentOrder += 1
                    xx *= xx0
                r += c[0] * xx
            return r
    elif (Main.geometry=="2Dcartesian" or Main.geometry == "AMcylindrical"):
        def f(x,y):
            r = 0.
            xx0 = x-x0
            yy0 = y-y0
            xx = [1.]
            currentOrder = 0
            for order, c in sorted(coeffs.items()):
                while currentOrder<order:
                    currentOrder += 1
                    yy = xx[-1]*yy0
                    xx = [ xxx * xx0 for xxx in xx ] + [yy]
                for i in range(order+1): r += c[i]*xx[i]
            return r
    elif Main.geometry=="3Dcartesian":
        def f(x,y,z):
            r = 0.
            xx0 = x-x0
            yy0 = y-y0
            zz0 = z-z0
            xx = [1.]
            currentOrder = 0
            for order, c in sorted(coeffs.items()):
                while currentOrder<order:
                    currentOrder += 1
                    zz = xx[-1]*zz0
                    yy = [ xxx * yy0 for xxx in xx[-currentOrder-1:] ] + [zz]
                    xx = [ xxx * xx0 for xxx in xx ] + yy
                for i in range(len(c)): r += c[i]*xx[i]
            return r
    else:
        raise Exception("polynomial profiles are not available in this geometry yet")
    f.profileName = "polynomial"
    f.x0 = x0
    f.y0 = y0
    f.z0 = z0
    f.orders = []
    f.coeffs = []
    for order, c in sorted(coeffs.items()):
        f.orders.append( order )
        f.coeffs.append( c     )
    return f



def tconstant(start=0.):
    def f(t):
        return 1. if t>=start else 0.
    f.profileName = "tconstant"
    f.start       = start
    return f
tconstant._reserved = True

def ttrapezoidal(start=0., plateau=None, slope1=0., slope2=0.):
    global Main
    if len(Main)==0:
        raise Exception("ttrapezoidal profile has been defined before `Main()`")
    if plateau is None: plateau = Main.simulation_time - start
    def f(t):
        if t < start: return 0.
        elif t < start+slope1: return (t-start) / slope1
        elif t < start+slope1+plateau: return 1.
        elif t < start+slope1+plateau+slope2:
            return 1. - ( t - (start+slope1+plateau) ) / slope2
        else: return 0.0
    f.profileName = "ttrapezoidal"
    f.start       = start
    f.plateau     = plateau
    f.slope1      = slope1
    f.slope2      = slope2
    return f

def tgaussian(start=0., duration=None, fwhm=None, center=None, order=2):
    import math
    global Main
    if len(Main)==0:
        raise Exception("tgaussian profile has been defined before `Main()`")
    if duration is None: duration = Main.simulation_time-start
    if fwhm     is None: fwhm     = duration/3.
    if center   is None: center   = start + duration/2.
    sigma = (0.5*fwhm)**order/math.log(2.0)
    def f(t):
        if t < start: return 0.
        elif t < start+duration: return math.exp( -(t-center)**order / sigma )
        else: return 0.0
    f.profileName = "tgaussian"
    f.start       = start
    f.duration    = duration
    f.sigma       = sigma
    f.center      = center
    f.order       = order
    return f

def tpolygonal(points=[], values=[]):
    global Main
    if len(Main)==0:
        raise Exception("tpolygonal profile has been defined before `Main()`")
    if len(points)==0:
        points = [0., Main.simulation_time]
        values = [1., 1.]
    N = len(points)
    points = [float(x) for x in points]
    values = [float(x) for x in values]
    slopes = [0. for i in range(1,N)]
    for i in range(1,N):
        if points[i] == points[i-1]: continue
        slopes[i-1] = (values[i]-values[i-1])/(points[i]-points[i-1])
    def f(t):
        if t < points[0]: return 0.0;
        for i in range(1,N):
            if t<points[i]: return values[i-1] + slopes[i-1] * ( t-points[i-1] )
        return 0.
    f.profileName = "tpolygonal"
    f.points      = points
    f.values      = values
    f.slopes      = slopes
    return f

def tcosine(base=0., amplitude=1., start=0., duration=None, phi=0., freq=1.):
    import math
    global Main
    if len(Main)==0:
        raise Exception("tcosine profile has been defined before `Main()`")
    if duration is None: duration = Main.simulation_time-start
    def f(t):
        if t < start: return 0.
        elif t < start+duration:
            return base + amplitude * math.cos(phi + freq*(t-start))
        else: return 0.
    f.profileName = "tcosine"
    f.base        = base
    f.amplitude   = amplitude
    f.start       = start
    f.duration    = duration
    f.phi         = phi
    f.freq        = freq
    return f

def tpolynomial(**kwargs):
    t0 = 0.
    coeffs = dict()
    for k, a in kwargs.items():
        if   k=="t0":
            t0 = a
        elif k[:5]=="order":
            order = int(k[5:])
            try: coeffs[ order ] = a*1.
            except: raise Exception("tpolynomial profile must have one coefficient per order")
    def f(t):
        r = 0.
        tt0 = t-t0
        tt = 1.
        currentOrder = 0
        for order, c in sorted(coeffs.items()):
            while currentOrder<order:
                currentOrder += 1
                tt *= tt0
            r += c * tt
        return r
    f.profileName = "tpolynomial"
    f.t0 = t0
    f.orders = []
    f.coeffs = []
    for order, c in sorted(coeffs.items()):
        f.orders.append( order )
        f.coeffs.append( c     )
    return f

def tsin2plateau(start=0., fwhm=0., plateau=None, slope1=None, slope2=None):
    import math
    global Main
    if len(Main)==0:
        raise Exception("tsin2plateau profile has been defined before `Main()`")
    if plateau is None: plateau = 0 # default is a simple sin2 profile (could be used for a 2D or 3D laserPulse too)
    if slope1 is None: slope1 = fwhm
    if slope2 is None: slope2 = slope1
    def f(t):
        if t < start:
            return 0.
        elif (t < start+slope1) and (slope1!=0.):
            return math.pow( math.sin(0.5*math.pi*(t-start)/slope1) , 2 )
        elif t < start+slope1+plateau:
            return 1.
        elif t < start+slope1+plateau+slope2 and (slope2!=0.):
            return math.pow(  math.cos(0.5*math.pi*(t-start-slope1-plateau)/slope2) , 2 )
        else:
            return 0.
    f.profileName = "tsin2plateau"
    f.start       = start
    #f.fwhm        = fwhm
    f.plateau     = plateau
    f.slope1      = slope1
    f.slope2      = slope2
    return f


def transformPolarization(polarization_phi, ellipticity):
    from math import pi, sqrt, sin, cos, tan, atan2
    e2 = ellipticity**2
    p = (1.-e2)*sin(2.*polarization_phi)/2.
    dephasing = atan2(ellipticity, p)
    amplitude = sqrt(1./(1.+e2))
    c2 = cos(polarization_phi)**2
    s2 = 1. - c2
    amplitudeY = amplitude * sqrt(c2 + e2*s2)
    amplitudeZ = amplitude * sqrt(s2 + e2*c2)
    return [dephasing, amplitudeY, amplitudeZ]

def LaserPlanar1D( box_side="xmin", a0=1., omega=1.,
        polarization_phi=0., ellipticity=0., time_envelope=tconstant(),phase_offset=0.):
    # Polarization and amplitude
    [dephasing, amplitudeY, amplitudeZ] = transformPolarization(polarization_phi, ellipticity)
    amplitudeY *= a0 * omega
    amplitudeZ *= a0 * omega
    # Create Laser
    Laser(
        box_side        = box_side,
        omega          = omega,
        chirp_profile  = tconstant(),
        time_envelope  = time_envelope,
        space_envelope = [ amplitudeZ, amplitudeY ],
        phase          = [ dephasing-phase_offset, -phase_offset ],
        delay_phase    = [ 0., dephasing ]
    )

def LaserEnvelopePlanar1D( a0=1., omega=1., time_envelope=tconstant(),
        envelope_solver = "explicit",box_side = "inside",Envelope_boundary_conditions = [["reflective"]],
        polarization_phi = 0.,ellipticity = 0.):
    from numpy import vectorize, sqrt

    def spatial_envelope1D(x):
        polarization_amplitude_factor = 1/sqrt(1.+ellipticity**2)
        return (a0*polarization_amplitude_factor)
    
    if (box_side=="inside"):
        def envelope_profile(x,t):
            return spatial_envelope1D(x)*complex( vectorize(time_envelope)(t) )
    elif (box_side=="xmin"):
        def envelope_profile(t):
            return spatial_envelope1D(0)*complex( vectorize(time_envelope)(t) )
    else:
        print("LaserEnvelope error: box_side must be either 'inside' or 'xmin'. ")

    # Create Laser Envelope
    LaserEnvelope(
        omega                        = omega,
        envelope_profile             = envelope_profile,
        envelope_solver              = envelope_solver,
        box_side                     = box_side,
        Envelope_boundary_conditions = Envelope_boundary_conditions,
        polarization_phi             = polarization_phi,
        ellipticity                  = ellipticity
    )


def LaserGaussian2D( box_side="xmin", a0=1., omega=1., focus=None, waist=3., incidence_angle=0.,
        polarization_phi=0., ellipticity=0., time_envelope=tconstant(), phase_offset=0.):
    from math import pi, cos, sin, tan, atan, sqrt, exp
    assert len(focus)==2, "LaserGaussian2D: focus must be a list of length 2."
    global Main
    assert len(Main)==1, "LaserGaussian2D profile has been defined before `Main()`"
    grid_length = Main.grid_length
    # Polarization and amplitude
    dephasing, amplitudeZ, amplitudeY = transformPolarization(polarization_phi, ellipticity)
    amplitudeY *= a0 * omega
    amplitudeZ *= a0 * omega
    delay_phase = [0., dephasing]
    # Injection on ymin/ymax
    if box_side[0] == "y":
        focus = focus[::-1]
        grid_length = grid_length[::-1]
        amplitudeY = -amplitudeY
    # Injection on max boundary
    if box_side.endswith("max"):
        focus[0] = grid_length[0] - focus[0]
    # Space and phase envelopes
    Zr = omega * waist**2/2.
    if incidence_angle == 0.:
        w  = sqrt(1./(1.+(focus[0]/Zr)**2))
        invWaist2 = (w/waist)**2
        coeff = -omega * focus[0] * w**2 / (2.*Zr**2)
        def spatial(y):
            return sqrt(w) * exp( -invWaist2*(y-focus[1])**2 )
        def phase(y):
            return coeff * (y-focus[1])**2
    else:
        invZr  = sin(incidence_angle) / Zr
        invZr2 = invZr**2
        invZr3 = (cos(incidence_angle) / Zr)**2 / 2.
        invWaist2 = (cos(incidence_angle) / waist)**2
        omega_ = omega * sin(incidence_angle)
        Y1 = focus[1] + focus[0]/tan(incidence_angle)
        Y2 = focus[1] - focus[0]*tan(incidence_angle)
        amplitudeY *= cos(incidence_angle)
        def spatial(y):
            w2 = 1./(1. + invZr2*(y-Y1)**2)
            return sqrt(sqrt(w2)) * exp( -invWaist2*w2*(y-Y2)**2 )
        def phase(y):
            dy = y-Y1
            return omega_*dy*(1.+ invZr3*(y-Y2)**2/(1.+invZr2*dy**2)) - 0.5*atan(invZr*dy)
        # Adjust the phase to match that of a laser that could come from another face
        if Y2 < 0:
            distance_to_boundary = focus[1] / sin(incidence_angle)
        elif Y2 < grid_length[1]:
            distance_to_boundary = focus[0] / cos(incidence_angle)
        else:
            distance_to_boundary = (focus[1] - grid_length[1]) / sin(incidence_angle)
        phase_offset -= omega * distance_to_boundary - 0.5*atan(distance_to_boundary/Zr)
    # Create Laser
    Laser(
        box_side       = box_side,
        omega          = omega,
        chirp_profile  = tconstant(),
        time_envelope  = time_envelope,
        space_envelope = [ lambda y:amplitudeY*spatial(y), lambda y:amplitudeZ*spatial(y) ],
        phase          = [ lambda y:phase(y)-phase_offset+delay_phase[1], lambda y:phase(y)-phase_offset+delay_phase[0] ],
        delay_phase    = delay_phase
    )

def rotation(x,y,ang) :
    '''
    Lineare tranformation: Rotation matrix
    (x,y)->(x',y')
    '''
    from math import cos, sin
    xrot = +cos(ang)*x + sin(ang)*y
    yrot = -sin(ang)*x + cos(ang)*y
    return xrot,yrot

def transform(x,y,xf,yf,L,ang) :
    '''
    Function to transform coordinate of laser-RPP formula
    x,y : Lab/Simulation box coordinate
    X,Y : Coordinate where X is the propagation axis of the laser, Y is transvers axis
    X,Y are rotated and translated coordinate in order the user define the 'focal spot' xf,yf in box coordinate and the angle of incidence with respect of x-axis of the simulated box
    '''
    from math import cos,sin,tan
    X,Y = rotation(x,y,ang)
    X = X+(L-xf/cos(ang))-(yf-tan(ang)*xf)*sin(ang)
    Y = Y-(yf-tan(ang)*xf)*cos(ang)
    return X,Y

def LaserSmoothing2D(box_side="xmin", a0=1., omega=1., focus=None, incidence_angle=0.,polarization_phi=0.,ellipticity=0.,phase_zero=0.,
               Lf=3.00e6,fnumber=8.00,
               N=6,rpp_random_seed=10.,
               temporal_smoothing=None,temporal_smoothing_random_seed=42,
               omega_m=0.,modulation_depth=0,rpp_per_mode=False,rpp_seed_per_mode=[42],
               omega_m_trans=0.,modulation_depth_trans=0,mode2generate_trans=None,chirp_profile=tconstant(),
               omega_m_longi=0.,modulation_depth_longi=0,mode2generate_longi=None,
               space_envelope=lambda y:1.,time_envelope=tconstant()):
    '''
    Default values are in code units
    incidence_angle in radian
    a0                     : Maximum of the envelope at focal spot for 1 speckle (i.e. N=40 and no random phase between element, or N=1). Otherwise, for N=40, a = a0/sqrt(N=40) in the simulation box.
    Lf                     : Longueur focale without SSD
    fnumber                : F-number
    N                      : Number of phase plate element
    rpp_random_seed        : Seed in order to have a Random Phase Plate (None is = no random, all element have zero phase-shift),
    temporal_smoothing     : None/Broadband/TSSD/LSSD
    omega_m                : modulation frequency for Broadband Laser
    modulation_depth       : depth 'm' of modulation and frequency bandwith = 2m for Broadband Laser
    rpp_per_mode           : False/True : Change the RPP for each mode
    rpp_seed_per_mode      : Seed for RRP
    omega_m_trans          : modulation frequency for transverse TSSD
    omega_m_longi          : modulation frequency for longitudinal LSSD
    modulation_depth_trans : depth 'm' of modulation and frequency bandwith = 2m for transverse SSD
    modulation_depth_longi : depth 'm' of modulation and frequency bandwith = 2m for longitudinal SSD
    '''
    import numpy as np
    from math import pi, sqrt, cos, sin, tan, fabs
    from cmath import exp,rect,polar
    from scipy.special import erf,jv
    
    global Main

    if temporal_smoothing==None:
        omega_m=0.
        modulation_depth=0
        omega_m_trans=0.
        modulation_depth_trans=0
        omega_m_longi=0.
        modulation_depth_longi=0
    elif temporal_smoothing=='Broadband':
        omega_m_trans=0.
        modulation_depth_trans=0
        omega_m_longi=0.
        modulation_depth_longi=0
    elif temporal_smoothing=='TSSD':
        omega_m=0.
        modulation_depth=0
        omega_m_longi=0.
        modulation_depth_longi=0
    elif temporal_smoothing=='LSSD':
        omega_m=0.
        modulation_depth=0
        omega_m_trans=0.
        modulation_depth_trans=0

    if len(Main)==0:
        raise Exception("LaserRPP2D profile has been defined before `Main()`") 
        
    k0 = omega
    waist = fnumber*N*(2.00*pi/omega)
    D = Lf/fnumber #taille lame de phase
    d = D/N #taille element lame de phase
    R = sqrt(waist*d/pi)

    x_focus,y_focus = focus[0],focus[1]

    El = (a0*omega/N)/np.sqrt(k0*d**2/(2*Lf*np.pi**2))
    # Polarization and amplitude
    dephasing, amplitudeZ, amplitudeY = transformPolarization(polarization_phi, ellipticity)
    amplitudeY *= El * cos(incidence_angle)
    amplitudeZ *= El
    delay_phase = [0., dephasing]

    krpp = np.linspace(-D/2,D/2,N+1)
    phik = np.zeros(N)
    if rpp_random_seed != None :
        np.random.seed(rpp_random_seed) # Meme suite de nombre aleatoire utilisee pour comparer des cas avec meme lame de phase
        phikinit = np.random.rand(N)
        for i in range(0,N):
            phik[i] = 2*pi*phikinit[i] # remplissage avec phi entre 0 et 2pi

    m_broadband = modulation_depth
    m_trans = modulation_depth_trans
    m_longi = modulation_depth_longi
    alpha_t = 2*pi/D
    alpha_x = 1/omega

    modes_trans = range(-m_trans,m_trans+1,1)
    modes_longi = range(-m_longi,m_longi+1,1)
    modes_broadband = range(-m_broadband,m_broadband+1,1)
    
    if temporal_smoothing=='Broadband':
        if temporal_smoothing_random_seed != None :
            np.random.seed(temporal_smoothing_random_seed)
            phase_w = 2*pi*np.random.rand(len(modes_broadband))
            Ebb = np.ones(len(modes_broadband))/np.sqrt(len(modes_broadband))
        else :
            phase_w = np.zeros(len(modes_broadband))
            Ebb = np.ones(len(modes_broadband))/np.sqrt(len(modes_broadband))

    def ERPP(y,imode,imode_t,imode_l,phik) :
        '''
        Formula (24) of "Cross-beam energy transfer between spatially smoothed laser beams" [A. Oudin, A. Debayle, C. Ruyer]
        Spatial envelope definition at x=0 of the simulation domain.
        For a fixed SSD mode. SSD is treated as a Laser() superposition at different frequency.
        '''

        X,Y = transform(0,y,x_focus,y_focus,Lf,incidence_angle)

        Lfw = Lf*(1+alpha_x*imode_l*omega_m_longi)
        # K   = sqrt( fabs( k0/(2*X) - 1/R**2 ) )
        K = sqrt( fabs( k0*(Lfw-X)/(2*X*Lfw) ) )
        sum_erfm = 0+0*1j
        factm    = 0+0*1j

        if (temporal_smoothing == None) & ((imode_t != 0) | (imode_l != 0)):
            raise Exception("Input inconsistency : No temporal smoothing selected but non-zero 'modulation depth'")

        # Valid for X<L
        if X<Lfw :
            factm = (1/np.sqrt(pi))*0.5*sqrt(Lfw/(Lfw-X))*exp( -1j*k0*Y**2/(2*(Lfw-X)) + 1j*(imode_t*alpha_t*Y-(imode_t*alpha_t)**2*X/(2*k0))*Lfw/(Lfw-X)) # Phase RPP+TSSD
            for n in range (0,N):
                  # sum_erfm += (erf(exp(-1j*pi/4)*K*(krpp[n+1]-(Y-imode_t*alpha_t*X/k0)*k0/2/X/K**2)) - erf(exp(-1j*pi/4)*K*(krpp[n]-(Y-imode_t*alpha_t*X/k0)*k0/2/X/K**2)))*exp(1j*phik[n])
                  sum_erfm += (erf(exp(-1j*pi/4)*K*(krpp[n+1]-(Y-imode_t*alpha_t*X/k0)*Lfw/(Lfw-X))) - erf(exp(-1j*pi/4)*K*(krpp[n]-(Y-imode_t*alpha_t*X/k0)*Lfw/(Lfw-X))))*exp(1j*phik[n])
        # At focus
        elif X==Lfw :
           factm = exp(-1j*pi*0.25)*sqrt(k0*d*d/(2*pi*pi*Lfw))*exp(1j*k0*Y**2/(2*Lfw))*sin(k0*d/(2*Lfw)*(Y-imode_t*alpha_t*X/k0))/(k0*d/(2*Lfw)*(Y-imode_t*alpha_t*X/k0))
           for n in range (0,N):
               sum_erfm += exp(1j*phik[n]-1j*k0/Lfw*(Y-imode_t*alpha_t*X/k0)*(krpp[n+1]+krpp[n])/2)
        # Beyond focus
        else :
            factm = (1/np.sqrt(pi))*0.5*exp(-1j*pi*0.5)*sqrt(Lfw/fabs(Lfw-X))*exp(-1j*k0*Y**2/(2*(Lfw-X)) + 1j*(imode_t*alpha_t*Y-(imode_t*alpha_t)**2*X/(2*k0))*Lfw/(Lfw-X)) # Phase RPP+TSSD
            for n in range (0,N):
                # sum_erfm += (erf(exp(+1j*pi/4)*fabs(K)*(krpp[n+1]-k0*(Y-imode_t*alpha_t*X/k0)/2/X/K**2)) - erf(exp(+1j*pi/4)*fabs(K)*(krpp[n]-k0*(Y-imode_t*alpha_t*X/k0)/2/X/K**2)))*exp(1j*phik[n]) # Somme des erf
                sum_erfm += (erf(exp(+1j*pi/4)*fabs(K)*(krpp[n+1]-(Y-imode_t*alpha_t*X/k0)*Lfw/(Lfw-X))) - erf(exp(+1j*pi/4)*fabs(K)*(krpp[n]-(Y-imode_t*alpha_t*X/k0)*Lfw/(Lfw-X))))*exp(1j*phik[n])

        if temporal_smoothing==None:
            Einit = sum_erfm*factm*exp(1j*k0*X)#*exp(1j*k0*X*imode_l*omega_m_longi/k0)*exp(1j*k0*X*imode_t*omega_m_trans/k0)
        elif (temporal_smoothing=='TSSD') | (temporal_smoothing=='LSSD'):
            Einit = jv(imode_t,m_trans)*jv(imode_l,m_longi)*sum_erfm*factm*exp(1j*k0*X)*exp(1j*k0*X*imode_l*omega_m_longi/k0)*exp(1j*k0*X*imode_t*omega_m_trans/k0)
        elif temporal_smoothing=='Broadband':
            Einit = Ebb[imode]*sum_erfm*factm*exp(1j*k0*X)*exp(1j*phase_w[imode])*exp(1j*k0*X*imode*omega_m/k0)
        else :
            raise Exception("Temporal_smoothing method not implemented yet")

        Amp,Phase = polar(Einit)
        return Amp,Phase

    def ERPP_ampBz(y,imode_,imode_t_,imode_l_,phik_) :
        return amplitudeZ*space_envelope(y)*ERPP(y,imode=imode_,imode_t=imode_t_,imode_l=imode_l_,phik=phik_)[0]
    def ERPP_ampBy(y,imode_,imode_t_,imode_l_,phik_) :
        return amplitudeY*space_envelope(y)*ERPP(y,imode=imode_,imode_t=imode_t_,imode_l=imode_l_,phik=phik_)[0]
    def ERPP_phaseBz(y,imode_,imode_t_,imode_l_,phik_) :
        return ERPP(y,imode=imode_,imode_t=imode_t_,imode_l=imode_l_,phik=phik_)[1]-phase_zero+delay_phase[0]
    def ERPP_phaseBy(y,imode_,imode_t_,imode_l_,phik_) :
        return ERPP(y,imode=imode_,imode_t=imode_t_,imode_l=imode_l_,phik=phik_)[1]-phase_zero+delay_phase[1]

    fct_amp_By = []
    fct_amp_Bz = []
    fct_phase_By = []
    fct_phase_Bz = []

    if temporal_smoothing=='Broadband':
        for mode in modes_broadband :
            if rpp_per_mode==True:
                if len(rpp_seed_per_mode)!=len(modes_broadband):
                    raise Exception("len(rpp_seed_per_mode): "+str(len(rpp_seed_per_mode))+". len(modes_broadband): "+str(len(modes_broadband))+". Length of rpp_seed_per_mode have to be equal to 2 x modulation_depth + 1 ")
                phik = np.zeros(N)
                np.random.seed(rpp_seed_per_mode[mode+m_broadband]) # Meme suite de nombre aleatoire utilisee pour comparer des cas avec meme lame de phase
                phikinit = np.random.rand(N)
                for i in range(0,N):
                    phik[i] = 2*pi*phikinit[i] # remplissage avec phi entre 0 et 2pi
            fct_amp_By.append(lambda y,imode_tmp=mode,imode_t_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_ampBy(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
            fct_amp_Bz.append(lambda y,imode_tmp=mode,imode_t_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_ampBz(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
            fct_phase_By.append(lambda y,imode_tmp=mode,imode_t_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_phaseBy(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
            fct_phase_Bz.append(lambda y,imode_tmp=mode,imode_t_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_phaseBz(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
        fct_amp_By = np.array(fct_amp_By)
        fct_amp_Bz = np.array(fct_amp_Bz)
        fct_phase_By = np.array(fct_phase_By)
        fct_phase_Bz = np.array(fct_phase_Bz)
    else :
        for mode_t in modes_trans :
            for mode_l in modes_longi :
                fct_amp_By.append(lambda y,imode_tmp=0,imode_t_tmp=mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_ampBy(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                fct_amp_Bz.append(lambda y,imode_tmp=0,imode_t_tmp=mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_ampBz(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                fct_phase_By.append(lambda y,imode_tmp=0,imode_t_tmp=mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_phaseBy(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                fct_phase_Bz.append(lambda y,imode_tmp=0,imode_t_tmp=mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_phaseBz(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
        fct_amp_By = np.reshape(np.array(fct_amp_By),(2*m_trans+1,2*m_longi+1))
        fct_amp_Bz = np.reshape(np.array(fct_amp_Bz),(2*m_trans+1,2*m_longi+1))
        fct_phase_By = np.reshape(np.array(fct_phase_By),(2*m_trans+1,2*m_longi+1))
        fct_phase_Bz = np.reshape(np.array(fct_phase_Bz),(2*m_trans+1,2*m_longi+1))

    if temporal_smoothing=='Broadband':
        for mode in modes_broadband :
            im = int(mode+m_broadband)
            Laser(
                box_side       = box_side,
                omega          = omega*(1.+mode*omega_m/omega),
                # omega          = omega,
                # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega))
                time_envelope  = time_envelope,
                space_envelope = [fct_amp_By[im],fct_amp_Bz[im]],
                phase          = [fct_phase_By[im],fct_phase_Bz[im]],
                delay_phase    = delay_phase
            )
    else :
        if mode2generate_trans != None :
            mode_t = 1.*mode2generate_trans
            if mode2generate_longi != None :
                mode_l = 1.*mode2generate_longi
                im_t = int(mode_t+m_trans)
                im_l = int(mode_l+m_longi)
                Laser(
                    box_side       = box_side,
                    omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                    # omega          = omega,
                    # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega))
                    time_envelope  = time_envelope,
                    space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                    phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                    delay_phase    = delay_phase
                )
            else :
                for mode_l in modes_longi :
                    im_t = int(mode_t+m_trans)
                    im_l = int(mode_l+m_longi)
                    Laser(
                        box_side       = box_side,
                        omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                        # omega          = omega,
                        # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega))
                        time_envelope  = time_envelope,
                        space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                        phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                        delay_phase    = delay_phase
                    )
        else :
            if mode2generate_longi != None :
                mode_l = mode2generate_longi
                for mode_t in modes_trans :
                    im_t = int(mode_t+m_trans)
                    im_l = int(mode_l+m_longi)
                    Laser(
                        box_side       = box_side,
                        omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                        # omega          = omega,
                        # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega)),
                        time_envelope  = time_envelope,
                        space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                        phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                        delay_phase    = delay_phase
                    )
            else :
                for mode_t in modes_trans :
                    for mode_l in modes_longi :
                        im_t = int(mode_t+m_trans)
                        im_l = int(mode_l+m_longi)
                        Laser(
                            box_side       = box_side,
                            omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                            # omega          = omega,
                            # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega)),
                            time_envelope  = time_envelope,
                            space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                            phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                            delay_phase    = delay_phase
                        )

def LaserSmoothingPeriodic2D(box_side="xmin", a0=1., omega=1., focus=None, incidence_angle=0.,polarization_phi=0.,ellipticity=0.,phase_zero=0.,
               Lf=3.00e6,fnumber=8.00,
               N=6,rpp_random_seed=10.,
               temporal_smoothing=None,temporal_smoothing_random_seed=42,
               omega_m=0.,modulation_depth=0,rpp_per_mode=False,rpp_seed_per_mode=[42],
               omega_m_trans=0.,modulation_depth_trans=0,mode2generate_trans=None,chirp_profile=tconstant(),
               omega_m_longi=0.,modulation_depth_longi=0,mode2generate_longi=None,
               space_envelope=lambda y:1.,time_envelope=tconstant()):
    '''
    Default values are in code units
    incidence_angle in radian
    a0                     : Maximum of the envelope at focal spot for 1 speckle (i.e. N=40 and no random phase between element, or N=1). Otherwise, for N=40, a = a0/sqrt(N=40) in the simulation box.
    Lf                     : Longueur focale without SSD
    fnumber                : F-number
    N                      : Number of phase plate element
    rpp_random_seed        : Seed in order to have a Random Phase Plate (None is = no random, all element have zero phase-shift),
    temporal_smoothing     : None/Broadband/TSSD/LSSD
    omega_m                : modulation frequency for Broadband Laser
    modulation_depth       : depth 'm' of modulation and frequency bandwith = 2m for Broadband Laser
    rpp_per_mode           : False/True : Change the RPP for each mode
    rpp_seed_per_mode      : Seed for RRP
    omega_m_trans          : modulation frequency for transverse TSSD
    omega_m_longi          : modulation frequency for longitudinal LSSD
    modulation_depth_trans : depth 'm' of modulation and frequency bandwith = 2m for transverse SSD
    modulation_depth_longi : depth 'm' of modulation and frequency bandwith = 2m for longitudinal SSD
    '''
    import numpy as np
    from math import pi, sqrt, cos, sin, tan, fabs
    from cmath import exp,rect,polar
    from scipy.special import erf,jv
    
    global Main

    if temporal_smoothing==None:
        omega_m=0.
        modulation_depth=0
        omega_m_trans=0.
        modulation_depth_trans=0
        omega_m_longi=0.
        modulation_depth_longi=0
    elif temporal_smoothing=='Broadband':
        omega_m_trans=0.
        modulation_depth_trans=0
        omega_m_longi=0.
        modulation_depth_longi=0
    elif temporal_smoothing=='TSSD':
        omega_m=0.
        modulation_depth=0
        omega_m_longi=0.
        modulation_depth_longi=0
    elif temporal_smoothing=='LSSD':
        omega_m=0.
        modulation_depth=0
        omega_m_trans=0.
        modulation_depth_trans=0

    if len(Main)==0:
        raise Exception("LaserRPP2D profile has been defined before `Main()`") 
        
    k0 = omega
    waist = fnumber*N*(2.00*pi/omega)
    D = Lf/fnumber #taille lame de phase
    d = D/N #taille element lame de phase
    R = sqrt(waist*d/pi)

    x_focus,y_focus = focus[0],focus[1]

    El = (a0*omega/N)/np.sqrt(k0*d**2/(2*Lf*np.pi**2))
    # Polarization and amplitude
    dephasing, amplitudeZ, amplitudeY = transformPolarization(polarization_phi, ellipticity)
    amplitudeY *= El * cos(incidence_angle)
    amplitudeZ *= El
    delay_phase = [0., dephasing]

    krpp = np.linspace(-D/2,D/2,N+1)
    phik = np.zeros(N)
    if rpp_random_seed != None :
        np.random.seed(rpp_random_seed) # Meme suite de nombre aleatoire utilisee pour comparer des cas avec meme lame de phase
        phikinit = np.random.rand(N)
        for i in range(0,N):
            phik[i] = 2*pi*phikinit[i] # remplissage avec phi entre 0 et 2pi

    m_broadband = modulation_depth
    m_trans = modulation_depth_trans
    m_longi = modulation_depth_longi
    alpha_t = 2*pi/D
    alpha_x = 1/omega

    modes_trans = range(-m_trans,m_trans+1,1)
    modes_longi = range(-m_longi,m_longi+1,1)
    modes_broadband = range(-m_broadband,m_broadband+1,1)
    
    if temporal_smoothing=='Broadband':
        if temporal_smoothing_random_seed != None :
            np.random.seed(temporal_smoothing_random_seed)
            phase_w = 2*pi*np.random.rand(len(modes_broadband))
            Ebb = np.ones(len(modes_broadband))/np.sqrt(len(modes_broadband))
        else :
            phase_w = np.zeros(len(modes_broadband))
            Ebb = np.ones(len(modes_broadband))/np.sqrt(len(modes_broadband))

    def ERPP(y,imode,imode_t,imode_l,phik) :
        '''
        Formula (24) of "Cross-beam energy transfer between spatially smoothed laser beams" [A. Oudin, A. Debayle, C. Ruyer]
        Spatial envelope definition at x=0 of the simulation domain.
        For a fixed SSD mode. SSD is treated as a Laser() superposition at different frequency.
        '''

        X,Y = transform(0,y,x_focus,y_focus,Lf,incidence_angle)

        Lfw = Lf*(1+alpha_x*imode_l*omega_m_longi)
        # K   = sqrt( fabs( k0/(2*X) - 1/R**2 ) )
        K = sqrt( fabs( k0*(Lfw-X)/(2*X*Lfw) ) )
        sum_erfm = 0+0*1j
        factm    = 0+0*1j

        if (temporal_smoothing == None) & ((imode_t != 0) | (imode_l != 0)):
            raise Exception("Input inconsistency : No temporal smoothing selected but non-zero 'modulation depth'")

        factm = exp(-1j*pi*0.25)*sqrt(k0*d*d/(2*pi*pi*Lfw))
        for n in range (0,N):
            sum_erfm += exp(1j*phik[n]-1j*k0/Lfw*(Y-imode_t*alpha_t*X/k0)*(krpp[n+1]+krpp[n])/2)

        if temporal_smoothing==None:
            Einit = sum_erfm*factm*exp(1j*k0*X)#*exp(1j*k0*X*imode_l*omega_m_longi/k0)*exp(1j*k0*X*imode_t*omega_m_trans/k0)
        elif (temporal_smoothing=='TSSD') | (temporal_smoothing=='LSSD'):
            Einit = jv(imode_t,m_trans)*jv(imode_l,m_longi)*sum_erfm*factm*exp(1j*k0*X)*exp(1j*k0*X*imode_l*omega_m_longi/k0)*exp(1j*k0*X*imode_t*omega_m_trans/k0)
        elif temporal_smoothing=='Broadband':
            Einit = Ebb[imode]*sum_erfm*factm*exp(1j*k0*X)*exp(1j*phase_w[imode])*exp(1j*k0*X*imode*omega_m/k0)
        else :
            raise Exception("Temporal_smoothing method not implemented yet")

        Amp,Phase = polar(Einit)
        return Amp,Phase

    def ERPP_ampBz(y,imode_,imode_t_,imode_l_,phik_) :
        return amplitudeZ*space_envelope(y)*ERPP(y,imode=imode_,imode_t=imode_t_,imode_l=imode_l_,phik=phik_)[0]
    def ERPP_ampBy(y,imode_,imode_t_,imode_l_,phik_) :
        return amplitudeY*space_envelope(y)*ERPP(y,imode=imode_,imode_t=imode_t_,imode_l=imode_l_,phik=phik_)[0]
    def ERPP_phaseBz(y,imode_,imode_t_,imode_l_,phik_) :
        return ERPP(y,imode=imode_,imode_t=imode_t_,imode_l=imode_l_,phik=phik_)[1]-phase_zero+delay_phase[0]
    def ERPP_phaseBy(y,imode_,imode_t_,imode_l_,phik_) :
        return ERPP(y,imode=imode_,imode_t=imode_t_,imode_l=imode_l_,phik=phik_)[1]-phase_zero+delay_phase[1]

    fct_amp_By = []
    fct_amp_Bz = []
    fct_phase_By = []
    fct_phase_Bz = []

    if temporal_smoothing=='Broadband':
        for mode in modes_broadband :
            if rpp_per_mode==True:
                if len(rpp_seed_per_mode)!=len(modes_broadband):
                    raise Exception("len(rpp_seed_per_mode): "+str(len(rpp_seed_per_mode))+". len(modes_broadband): "+str(len(modes_broadband))+". Length of rpp_seed_per_mode have to be equal to 2 x modulation_depth + 1 ")
                phik = np.zeros(N)
                np.random.seed(rpp_seed_per_mode[mode+m_broadband]) # Meme suite de nombre aleatoire utilisee pour comparer des cas avec meme lame de phase
                phikinit = np.random.rand(N)
                for i in range(0,N):
                    phik[i] = 2*pi*phikinit[i] # remplissage avec phi entre 0 et 2pi
            fct_amp_By.append(lambda y,imode_tmp=mode,imode_t_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_ampBy(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
            fct_amp_Bz.append(lambda y,imode_tmp=mode,imode_t_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_ampBz(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
            fct_phase_By.append(lambda y,imode_tmp=mode,imode_t_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_phaseBy(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
            fct_phase_Bz.append(lambda y,imode_tmp=mode,imode_t_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_phaseBz(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
        fct_amp_By = np.array(fct_amp_By)
        fct_amp_Bz = np.array(fct_amp_Bz)
        fct_phase_By = np.array(fct_phase_By)
        fct_phase_Bz = np.array(fct_phase_Bz)
    else :
        for mode_t in modes_trans :
            for mode_l in modes_longi :
                fct_amp_By.append(lambda y,imode_tmp=0,imode_t_tmp=mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_ampBy(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                fct_amp_Bz.append(lambda y,imode_tmp=0,imode_t_tmp=mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_ampBz(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                fct_phase_By.append(lambda y,imode_tmp=0,imode_t_tmp=mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_phaseBy(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                fct_phase_Bz.append(lambda y,imode_tmp=0,imode_t_tmp=mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_phaseBz(y,imode_=imode_tmp,imode_t_=imode_t_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
        fct_amp_By = np.reshape(np.array(fct_amp_By),(2*m_trans+1,2*m_longi+1))
        fct_amp_Bz = np.reshape(np.array(fct_amp_Bz),(2*m_trans+1,2*m_longi+1))
        fct_phase_By = np.reshape(np.array(fct_phase_By),(2*m_trans+1,2*m_longi+1))
        fct_phase_Bz = np.reshape(np.array(fct_phase_Bz),(2*m_trans+1,2*m_longi+1))

    if temporal_smoothing=='Broadband':
        for mode in modes_broadband :
            im = int(mode+m_broadband)
            Laser(
                box_side       = box_side,
                omega          = omega*(1.+mode*omega_m/omega),
                # omega          = omega,
                # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega))
                time_envelope  = time_envelope,
                space_envelope = [fct_amp_By[im],fct_amp_Bz[im]],
                phase          = [fct_phase_By[im],fct_phase_Bz[im]],
                delay_phase    = delay_phase
            )
    else :
        if mode2generate_trans != None :
            mode_t = 1.*mode2generate_trans
            if mode2generate_longi != None :
                mode_l = 1.*mode2generate_longi
                im_t = int(mode_t+m_trans)
                im_l = int(mode_l+m_longi)
                Laser(
                    box_side       = box_side,
                    omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                    # omega          = omega,
                    # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega))
                    time_envelope  = time_envelope,
                    space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                    phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                    delay_phase    = delay_phase
                )
            else :
                for mode_l in modes_longi :
                    im_t = int(mode_t+m_trans)
                    im_l = int(mode_l+m_longi)
                    Laser(
                        box_side       = box_side,
                        omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                        # omega          = omega,
                        # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega))
                        time_envelope  = time_envelope,
                        space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                        phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                        delay_phase    = delay_phase
                    )
        else :
            if mode2generate_longi != None :
                mode_l = mode2generate_longi
                for mode_t in modes_trans :
                    im_t = int(mode_t+m_trans)
                    im_l = int(mode_l+m_longi)
                    Laser(
                        box_side       = box_side,
                        omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                        # omega          = omega,
                        # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega)),
                        time_envelope  = time_envelope,
                        space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                        phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                        delay_phase    = delay_phase
                    )
            else :
                for mode_t in modes_trans :
                    for mode_l in modes_longi :
                        im_t = int(mode_t+m_trans)
                        im_l = int(mode_l+m_longi)
                        Laser(
                            box_side       = box_side,
                            omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                            # omega          = omega,
                            # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega)),
                            time_envelope  = time_envelope,
                            space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                            phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                            delay_phase    = delay_phase
                        )

def LaserEnvelopeGaussian2D( a0=1., omega=1., focus=None, waist=3., time_envelope=tconstant(),
        envelope_solver = "explicit",box_side = "inside",Envelope_boundary_conditions = [["reflective"]],
        polarization_phi = 0.,ellipticity = 0.):
    import cmath
    from numpy import exp, sqrt, arctan, vectorize
    assert len(focus)==2, "LaserEnvelopeGaussian2D: focus must be a list of length 2."

    def gaussian_beam2D(x,y):
        polarization_amplitude_factor = 1/sqrt(1.+ellipticity**2)
        Zr = omega * waist**2/2.
        w  = sqrt(1./(1.+   ( (x-focus[0])/Zr  )**2 ) )
        coeff = omega * (x-focus[0]) * w**2 / (2.*Zr**2)
        phase = coeff * ( (y-focus[1])**2 )
        exponential_with_total_phase = exp(1j*(phase-arctan( (x-focus[0])/Zr )))
        invWaist2 = (w/waist)**2
        spatial_amplitude = a0 *polarization_amplitude_factor * sqrt(w) * exp( -invWaist2*(y-focus[1])**2)
        return spatial_amplitude * exponential_with_total_phase
        
    if (box_side=="inside"):
        def envelope_profile(x,y,t):
            return gaussian_beam2D(x,y)*vectorize(time_envelope)(t)
    elif (box_side=="xmin"):
        def envelope_profile(y,t):
            return gaussian_beam2D(0,y)*vectorize(time_envelope)(t)
    else:
        print("LaserEnvelope error: box_side must be either 'inside' or 'xmin'. ")

    # Create Laser Envelope
    LaserEnvelope(
        omega                        = omega,
        envelope_profile             = envelope_profile,
        envelope_solver              = envelope_solver,
        box_side      = box_side,
        Envelope_boundary_conditions = Envelope_boundary_conditions,
        polarization_phi             = polarization_phi,
        ellipticity                  = ellipticity
    )

def LaserGaussian3D( box_side="xmin", a0=1., omega=1., focus=None, waist=3., incidence_angle=[0.,0.],
        polarization_phi=0., ellipticity=0., time_envelope=tconstant(), phase_offset=0.):
    from math import pi, cos, sin, tan, atan, sqrt, exp
    assert len(focus)==3, "LaserGaussian3D: focus must be a list of length 3."
    global Main
    assert len(Main)==1, "LaserGaussian3D profile has been defined before `Main()`"
    grid_length = Main.grid_length
    # Polarization and amplitude
    [dephasing, amplitudeZ, amplitudeY] = transformPolarization(polarization_phi, ellipticity)
    amplitudeY *= a0 * omega
    amplitudeZ *= a0 * omega
    # Injection on ymin/ymax or zmin/zmax
    if box_side[0] == "y":
        focus = [focus[1],focus[0],focus[2]]
        grid_length = [grid_length[1],grid_length[0],grid_length[2]]
        amplitudeY = -amplitudeY
    elif box_side[0] == "z":
        focus = [focus[2],focus[0],focus[1]]
        grid_length = [grid_length[2],grid_length[0],grid_length[1]]
    # Injection on max boundary
    if box_side.endswith("max"):
        focus[0] = grid_length[0] - focus[0]
    # Space and phase envelopes
    Zr = omega * waist**2/2.
    if incidence_angle == [0.,0.]:
        w  = sqrt(1./(1.+(focus[0]/Zr)**2))
        invWaist2 = (w/waist)**2
        coeff = -omega * focus[0] * w**2 / (2.*Zr**2)
        def spatial(y,z):
            return w * exp( -invWaist2*((y-focus[1])**2 + (z-focus[2])**2 )  )
        def phase(y,z):
            return coeff * ( (y-focus[1])**2 + (z-focus[2])**2 )
    else:
        invZr = 1./Zr
        invW  = 1./waist
        alpha = omega * Zr
        cy = cos(incidence_angle[0]); sy = sin(incidence_angle[0])
        cz = cos(incidence_angle[1]); sz = sin(incidence_angle[1])
        cycz = cy*cz; cysz = cy*sz; sycz = sy*cz; sysz = sy*sz
        amplitudeZ = sysz * amplitudeY + cy * amplitudeZ
        amplitudeY *= cz
        def spatial(y,z):
            X = invZr * (-focus[0]*cycz + (y-focus[1])*cysz - (z-focus[2])*sy )
            Y = invW  * ( focus[0]*sz   + (y-focus[1])*cz                     )
            Z = invW  * (-focus[0]*sycz + (y-focus[1])*sysz + (z-focus[2])*cy )
            invW2 = 1./(1.+X**2)
            return sqrt(invW2) * exp(-(Y**2+Z**2)*invW2)
        def phase(y,z):
            X = invZr * (-focus[0]*cycz + (y-focus[1])*cysz - (z-focus[2])*sy )
            Y = invZr * ( focus[0]*sz   + (y-focus[1])*cz                     )
            Z = invZr * (-focus[0]*sycz + (y-focus[1])*sysz + (z-focus[2])*cy )
            return alpha * X*(1.+0.5*(Y**2+Z**2)/(1.+X**2)) - atan(X)
        # Adjust the phase to match that of a laser that could come from another face
        faces = (focus[0],focus[1],focus[2],focus[1]-grid_length[1],focus[2]-grid_length[2])
        denominators = (cycz, cysz, -sy, cysz, -sy)
        distance_to_boundary = min([N/D for N,D in zip(faces,denominators) if D != 0 and N/D > 0])
        phase_offset -= omega * distance_to_boundary - atan(distance_to_boundary/Zr)
    # Create Laser
    Laser(
        box_side       = box_side,
        omega          = omega,
        chirp_profile  = tconstant(),
        time_envelope  = time_envelope,
        space_envelope = [ lambda y,z:amplitudeY*spatial(y,z), lambda y,z:amplitudeZ*spatial(y,z) ],
        phase          = [ lambda y,z:phase(y,z)-phase_offset+dephasing, lambda y,z:phase(y,z)-phase_offset ],
        delay_phase    = [ 0., dephasing ]
    )

# We will assume in 3D that angle is only in the (x,y) plane
# Transverse SSD along Y or Z in order to have a transverse SSD in the angle plane or perpendicular to the plane

def rotation_3d(x,y,z,ang) :
    '''
    Lineare tranformation: Rotation matrix
    (x,y)->(x',y')
    '''
    from math import cos, sin
    xrot = +cos(ang)*x + sin(ang)*y
    yrot = -sin(ang)*x + cos(ang)*y
    return xrot,yrot,z

def transform_3d(x,y,z,xf,yf,zf,L,ang) :
    '''
    Function to transform coordinate of laser-RPP formula
    x,y : Lab/Simulation box coordinate
    X,Y : Coordinate where X is the propagation axis of the laser, Y is transvers axis
    X,Y are rotated and translated coordinate in order the user define the 'focal spot' xf,yf in box coordinate and the angle of incidence with respect of x-axis of the simulated box
    '''
    from math import cos,sin,tan
    X,Y,Z = rotation_3d(x,y,z,ang)
    X = X+(L-xf/cos(ang))-(yf-tan(ang)*xf)*sin(ang)
    Y = Y-(yf-tan(ang)*xf)*cos(ang)
    Z = Z-zf
    return X,Y,Z

def LaserSmoothing3D(box_side="xmin", a0=1., omega=1., focus=None, incidence_angle=0.,polarization_phi=0.,ellipticity=0.,phase_zero=0.,
               Lf=3.00e6,fnumber=8.00,
               N=[6,6],rpp_random_seed=10.,
               temporal_smoothing=None,temporal_smoothing_random_seed=42,
               omega_m=0.,modulation_depth=0,rpp_per_mode=False,rpp_seed_per_mode=[42],
               omega_m_trans=0.,modulation_depth_trans=0,mode2generate_trans=None,direction='y',chirp_profile=tconstant(),
               omega_m_longi=0.,modulation_depth_longi=0,mode2generate_longi=None,
               space_envelope=lambda y,z:1.,time_envelope=tconstant()):
    '''
    Default values are in code units
    incidence_angle in radian ONLY IN (X,Y) PLANE
    a0                     : Maximum of the envelope at focal spot for 1 speckle (i.e. N=40 and no random phase between element, or N=1). Otherwise, for N=40, a = a0/sqrt(N=40) in the simulation box.
    Lf                     : Longueur focale without SSD
    fnumber                : F-number
    N                      : List of number of phase plate element per direction (for Ntot=36, then N=[6,6])
    rpp_random_seed        : Seed in order to have a Random Phase Plate (None is = no random, all element have zero phase-shift),
    temporal_smoothing     : None/'Broadband'/'TSSD'/'LSSD'
    omega_m                : modulation frequency for Broadband Laser
    modulation_depth       : depth 'm' of modulation and frequency bandwith = 2m for Broadband Laser
    rpp_per_mode           : False/True : Change the RPP for each mode
    rpp_seed_per_mode      : Seed for RRP
    omega_m_trans          : modulation frequency for transverse TSSD
    omega_m_longi          : modulation frequency for longitudinal LSSD
    modulation_depth_trans : depth 'm' of modulation and frequency bandwith = 2m for transverse SSD
    modulation_depth_longi : depth 'm' of modulation and frequency bandwith = 2m for longitudinal SSD
    direction              : direction of transverse TSSD : 'y' or 'z'
    '''
    import numpy as np
    from math import pi, sqrt, cos, sin, tan, fabs
    from cmath import exp,rect,polar
    from scipy.special import erf,jv
    
    global Main

    if temporal_smoothing==None:
        omega_m=0.
        modulation_depth=0
        omega_m_trans=0.
        modulation_depth_trans=0
        omega_m_longi=0.
        modulation_depth_longi=0
    elif temporal_smoothing=='Broadband':
        omega_m_trans=0.
        modulation_depth_trans=0
        omega_m_longi=0.
        modulation_depth_longi=0
    elif temporal_smoothing=='TSSD':
        omega_m=0.
        modulation_depth=0
        omega_m_longi=0.
        modulation_depth_longi=0
    elif temporal_smoothing=='LSSD':
        omega_m=0.
        modulation_depth=0
        omega_m_trans=0.
        modulation_depth_trans=0

    if len(Main)==0:
        raise Exception("LaserRPP2D profile has been defined before `Main()`") 
        
    k0 = omega
    Ny,Nz = N[0],N[1]
    Ntot = int(Ny*Nz)
    waist_y = fnumber*Ny*(2.00*pi/omega)
    waist_z = fnumber*Nz*(2.00*pi/omega)
    D = Lf/fnumber #taille lame de phase : On fait l'hypothese/le choix ici que l'ouverture du faisceau est identique avant la lame de phase (D et fnumber pareil pour y et z)
    dy = D/Ny #taille element lame de phase y
    dz = D/Nz #taille element lame de phase z
    Ry = sqrt(waist_y*dy/pi)
    Rz = sqrt(waist_z*dz/pi)

    x_focus,y_focus,z_focus = focus[0],focus[1],focus[2]

    El = (a0*omega/Ntot)/np.sqrt(k0*dy**2/(2*Lf*np.pi**2))/np.sqrt(k0*dz**2/(2*Lf*np.pi**2))
    # Polarization and amplitude
    dephasing, amplitudeZ, amplitudeY = transformPolarization(polarization_phi, ellipticity)
    amplitudeY *= El * cos(incidence_angle)
    amplitudeZ *= El
    delay_phase = [0., dephasing]

    krpp_y = np.linspace(-D/2,D/2,Ny+1)
    krpp_z = np.linspace(-D/2,D/2,Nz+1)

    #phik_y = np.zeros(Ny)
    #phik_z = np.zeros(Nz)
    #if rpp_random_seed != None :
    #    np.random.seed(rpp_random_seed) # Meme suite de nombre aleatoire utilisee pour comparer des cas avec meme lame de phase
    #    phikinit = np.random.rand(int(Ny+Nz))
    #    for i in range(0,Ny):
    #        phik_y[i] = 2*pi*phikinit[i] # remplissage avec phi entre 0 et 2pi
    #    for i in range(Ny,Ny+Nz):
    #        phik_z[i] = 2*pi*phikinit[i] # remplissage avec phi entre 0 et 2pi

    phik = np.zeros(Ntot)
    if rpp_random_seed != None :
        np.random.seed(rpp_random_seed) # Meme suite de nombre aleatoire utilisee pour comparer des cas avec meme lame de phase
        phikinit = np.random.rand(Ntot)
        for i in range(0,Ntot):
            phik[i] = 2*pi*phikinit[i] # remplissage avec phi entre 0 et 2pi

    m_broadband = modulation_depth
    m_trans = modulation_depth_trans
    m_longi = modulation_depth_longi
    alpha_t = 2*pi/D
    alpha_x = 1/omega

    modes_trans = range(-m_trans,m_trans+1,1)
    modes_longi = range(-m_longi,m_longi+1,1)
    modes_broadband = range(-m_broadband,m_broadband+1,1)
    
    if temporal_smoothing=='Broadband':
        if temporal_smoothing_random_seed != None :
            np.random.seed(temporal_smoothing_random_seed)
            phase_w = 2*pi*np.random.rand(len(modes_broadband))
            Ebb = np.ones(len(modes_broadband))/np.sqrt(len(modes_broadband))
        else :
            phase_w = np.zeros(len(modes_broadband))
            Ebb = np.ones(len(modes_broadband))/np.sqrt(len(modes_broadband))

    def ERPP(y,z,imode,imode_tY,imode_tZ,imode_l,phik) :
        '''
        Formula (24) of "Cross-beam energy transfer between spatially smoothed laser beams" [A. Oudin, A. Debayle, C. Ruyer]
        Spatial envelope definition at x=0 of the simulation domain.
        For a fixed SSD mode. SSD is treated as a Laser() superposition at different frequency.
        '''

        X,Y,Z = transform_3d(0,y,z,x_focus,y_focus,z_focus,Lf,incidence_angle)

        Lfw = Lf*(1+alpha_x*imode_l*omega_m_longi)
        # K   = sqrt( fabs( k0/(2*X) - 1/R**2 ) )
        K = sqrt( fabs( k0*(Lfw-X)/(2*X*Lfw) ) )
        sum_erfm = 0+0*1j
        sum_erfm_y = 0+0*1j
        sum_erfm_z = 0+0*1j
        factm    = 0+0*1j

        if (temporal_smoothing == None) & ((imode_tY != 0) | (imode_tZ != 0)  | (imode_l != 0)):
            raise Exception("Input inconsistency : No temporal smoothing selected but non-zero 'modulation depth'")

        # Valid for X<L
        if X<Lfw :
            factm = (1/np.sqrt(pi))*0.5*sqrt(Lfw/(Lfw-X))*exp(-1j*k0*Y**2/(2*(Lfw-X)) + 1j*(imode_tY*alpha_t*Y-(imode_tY*alpha_t)**2*X/(2*k0))*Lfw/(Lfw-X)) # Phase RPP+TSSD
            factm *= (1/np.sqrt(pi))*0.5*sqrt(Lfw/(Lfw-X))*exp(-1j*k0*Z**2/(2*(Lfw-X)) + 1j*(imode_tZ*alpha_t*Z-(imode_tZ*alpha_t)**2*X/(2*k0))*Lfw/(Lfw-X))
            for ny in range (0,Ny):
                for nz in range (0,Nz):
                    sum_erfm_y = (erf(exp(-1j*pi/4)*K*(krpp_y[ny+1]-(Y-imode_tY*alpha_t*X/k0)*Lfw/(Lfw-X))) - erf(exp(-1j*pi/4)*K*(krpp_y[ny]-(Y-imode_tY*alpha_t*X/k0)*Lfw/(Lfw-X))))
                    sum_erfm_z = (erf(exp(-1j*pi/4)*K*(krpp_z[nz+1]-(Z-imode_tZ*alpha_t*X/k0)*Lfw/(Lfw-X))) - erf(exp(-1j*pi/4)*K*(krpp_z[nz]-(Z-imode_tZ*alpha_t*X/k0)*Lfw/(Lfw-X))))
                    sum_erfm += sum_erfm_y*sum_erfm_z*exp(1j*phik[ny*Nz+nz])
        # At focus
        elif X==Lfw :
           factm = exp(-1j*pi*0.25)*sqrt(k0*dy*dy/(2*pi*pi*Lfw))*exp(1j*k0*Y**2/(2*Lfw))*sin(k0*d/(2*Lfw)*(Y-imode_tY*alpha_t*X/k0))/(k0*d/(2*Lfw)*(Y-imode_tY*alpha_t*X/k0))
           factm *= exp(-1j*pi*0.25)*sqrt(k0*dz*dz/(2*pi*pi*Lfw))*exp(1j*k0*Z**2/(2*Lfw))*sin(k0*d/(2*Lfw)*(Z-imode_tZ*alpha_t*X/k0))/(k0*d/(2*Lfw)*(Z-imode_tZ*alpha_t*X/k0))
           for ny in range (0,Ny):
               for nz in range (0,Nz):
                   sum_erfm_y = exp(-1j*k0/Lfw*(Y-imode_tY*alpha_t*X/k0)*(krpp_y[ny+1]+krpp_y[ny])/2)
                   sum_erfm_z = exp(-1j*k0/Lfw*(Z-imode_tZ*alpha_t*X/k0)*(krpp_z[nz+1]+krpp_z[nz])/2)
                   sum_erfm += sum_erfm_y*sum_erfm_z*exp(1j*phik[ny*Nz+nz])
        # Beyond focus
        else :
            factm = (1/np.sqrt(pi))*0.5*sqrt(Lfw/fabs(Lfw-X))*exp(-1j*k0*Y**2/(2*(Lfw-X)) + 1j*(imode_tY*alpha_t*Y-(imode_tY*alpha_t)**2*X/(2*k0))*Lfw/(Lfw-X))*exp(-1j*pi*0.5)# Phase RPP+TSSD
            factm *= (1/np.sqrt(pi))*0.5*sqrt(Lfw/fabs(Lfw-X))*exp(-1j*k0*Z**2/(2*(Lfw-X)) + 1j*(imode_tZ*alpha_t*Z-(imode_tZ*alpha_t)**2*X/(2*k0))*Lfw/(Lfw-X))*exp(-1j*pi*0.5)
            for ny in range (0,Ny):
                for nz in range (0,Nz):
                    sum_erfm_y = (erf(exp(+1j*pi/4)*fabs(K)*(krpp_y[ny+1]-(Y-imode_tY*alpha_t*X/k0)*Lfw/(Lfw-X))) - erf(exp(+1j*pi/4)*fabs(K)*(krpp_y[ny]-(Y-imode_tY*alpha_t*X/k0)*Lfw/(Lfw-X))))
                    sum_erfm_z = (erf(exp(+1j*pi/4)*fabs(K)*(krpp_z[nz+1]-(Z-imode_tZ*alpha_t*X/k0)*Lfw/(Lfw-X))) - erf(exp(+1j*pi/4)*fabs(K)*(krpp_z[nz]-(Z-imode_tZ*alpha_t*X/k0)*Lfw/(Lfw-X))))
                    sum_erfm += sum_erfm_y*sum_erfm_z*exp(1j*phik[ny*Nz+nz])

        if temporal_smoothing==None:
            Einit = sum_erfm*factm*exp(1j*k0*X)#*exp(1j*k0*X*imode_l*omega_m_longi/k0)*exp(1j*k0*X*imode_t*omega_m_trans/k0)
        elif (temporal_smoothing=='TSSD') | (temporal_smoothing=='LSSD'):
            if direction=='y':
                Einit = jv(imode_tY,m_trans)*jv(imode_l,m_longi)*sum_erfm*factm*exp(1j*k0*X)*exp(1j*k0*X*imode_l*omega_m_longi/k0)*exp(1j*k0*X*imode_tY*omega_m_trans/k0)
            elif direction=='z':
                Einit = jv(imode_tZ,m_trans)*jv(imode_l,m_longi)*sum_erfm*factm*exp(1j*k0*X)*exp(1j*k0*X*imode_l*omega_m_longi/k0)*exp(1j*k0*X*imode_tZ*omega_m_trans/k0)
            else :
                raise Exception("'direction' parameter for TSSD unknown")
        elif temporal_smoothing=='Broadband':
            Einit = Ebb[imode]*sum_erfm*factm*exp(1j*k0*X)*exp(1j*phase_w[imode])*exp(1j*k0*X*imode*omega_m/k0)
        else :
            raise Exception("Temporal_smoothing method not implemented yet")

        Amp,Phase = polar(Einit)
        return Amp,Phase

    def ERPP_ampBz(y,z,imode_,imode_tY_,imode_tZ_,imode_l_,phik_) :
        return amplitudeZ*space_envelope(y,z)*ERPP(y,z,imode=imode_,imode_tY=imode_tY_,imode_tZ=imode_tZ_,imode_l=imode_l_,phik=phik_)[0]
    def ERPP_ampBy(y,z,imode_,imode_tY_,imode_tZ_,imode_l_,phik_) :
        return amplitudeY*space_envelope(y,z)*ERPP(y,z,imode=imode_,imode_tY=imode_tY_,imode_tZ=imode_tZ_,imode_l=imode_l_,phik=phik_)[0]
    def ERPP_phaseBz(y,z,imode_,imode_tY_,imode_tZ_,imode_l_,phik_) :
        return ERPP(y,z,imode=imode_,imode_tY=imode_tY_,imode_tZ=imode_tZ_,imode_l=imode_l_,phik=phik_)[1]-phase_zero+delay_phase[0]
    def ERPP_phaseBy(y,z,imode_,imode_tY_,imode_tZ_,imode_l_,phik_) :
        return ERPP(y,z,imode=imode_,imode_tY=imode_tY_,imode_tZ=imode_tZ_,imode_l=imode_l_,phik=phik_)[1]-phase_zero+delay_phase[1]

    fct_amp_By = []
    fct_amp_Bz = []
    fct_phase_By = []
    fct_phase_Bz = []

    if temporal_smoothing=='Broadband':
        for mode in modes_broadband :
            if rpp_per_mode==True:
                if len(rpp_seed_per_mode)!=len(modes_broadband):
                    raise Exception("len(rpp_seed_per_mode): "+str(len(rpp_seed_per_mode))+". len(modes_broadband): "+str(len(modes_broadband))+". Length of rpp_seed_per_mode have to be equal to 2 x modulation_depth + 1 ")
                phik = np.zeros(Ntot)
                np.random.seed(rpp_seed_per_mode[mode+m_broadband]) # Meme suite de nombre aleatoire utilisee pour comparer des cas avec meme lame de phase
                phikinit = np.random.rand(Ntot)
                for i in range(0,Ntot):
                    phik[i] = 2*pi*phikinit[i] # remplissage avec phi entre 0 et 2pi
            fct_amp_By.append(lambda y,z,imode_tmp=mode,imode_tY_tmp=0,imode_tZ_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_ampBy(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
            fct_amp_Bz.append(lambda y,z,imode_tmp=mode,imode_tY_tmp=0,imode_tZ_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_ampBz(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
            fct_phase_By.append(lambda y,z,imode_tmp=mode,imode_tY_tmp=0,imode_tZ_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_phaseBy(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
            fct_phase_Bz.append(lambda y,z,imode_tmp=mode,imode_tY_tmp=0,imode_tZ_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_phaseBz(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
        fct_amp_By = np.array(fct_amp_By)
        fct_amp_Bz = np.array(fct_amp_Bz)
        fct_phase_By = np.array(fct_phase_By)
        fct_phase_Bz = np.array(fct_phase_Bz)
    else :
        for mode_t in modes_trans :
            for mode_l in modes_longi :
                if (m_trans==0) | (direction=='y') :
                    fct_amp_By.append(lambda y,z,imode_tmp=0,imode_tY_tmp=1*mode_t,imode_tZ_tmp=0*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_ampBy(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                    fct_amp_Bz.append(lambda y,z,imode_tmp=0,imode_tY_tmp=1*mode_t,imode_tZ_tmp=0*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_ampBz(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                    fct_phase_By.append(lambda y,z,imode_tmp=0,imode_tY_tmp=1*mode_t,imode_tZ_tmp=0*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_phaseBy(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                    fct_phase_Bz.append(lambda y,z,imode_tmp=0,imode_tY_tmp=1*mode_t,imode_tZ_tmp=0*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_phaseBz(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                elif direction=='z':
                    fct_amp_By.append(lambda y,z,imode_tmp=0,imode_tY_tmp=0*mode_t,imode_tZ_tmp=1*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_ampBy(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                    fct_amp_Bz.append(lambda y,z,imode_tmp=0,imode_tY_tmp=0*mode_t,imode_tZ_tmp=1*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_ampBz(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                    fct_phase_By.append(lambda y,z,imode_tmp=0,imode_tY_tmp=0*mode_t,imode_tZ_tmp=1*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_phaseBy(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                    fct_phase_Bz.append(lambda y,z,imode_tmp=0,imode_tY_tmp=0*mode_t,imode_tZ_tmp=1*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_phaseBz(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                else :
                     raise Exception(" m_trans != 0 and direction for transverse SSD unknown : Have to be 'y' or 'z' ")
        fct_amp_By = np.reshape(np.array(fct_amp_By),(2*m_trans+1,2*m_longi+1))
        fct_amp_Bz = np.reshape(np.array(fct_amp_Bz),(2*m_trans+1,2*m_longi+1))
        fct_phase_By = np.reshape(np.array(fct_phase_By),(2*m_trans+1,2*m_longi+1))
        fct_phase_Bz = np.reshape(np.array(fct_phase_Bz),(2*m_trans+1,2*m_longi+1))

    if temporal_smoothing=='Broadband':
        for mode in modes_broadband :
            im = int(mode+m_broadband)
            Laser(
                box_side       = box_side,
                omega          = omega*(1.+mode*omega_m/omega),
                # omega          = omega,
                # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega))
                time_envelope  = time_envelope,
                space_envelope = [fct_amp_By[im],fct_amp_Bz[im]],
                phase          = [fct_phase_By[im],fct_phase_Bz[im]],
                delay_phase    = delay_phase
            )
    else :
        if mode2generate_trans != None :
            mode_t = 1.*mode2generate_trans
            if mode2generate_longi != None :
                mode_l = 1.*mode2generate_longi
                im_t = int(mode_t+m_trans)
                im_l = int(mode_l+m_longi)
                Laser(
                    box_side       = box_side,
                    omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                    # omega          = omega,
                    # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega))
                    time_envelope  = time_envelope,
                    space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                    phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                    delay_phase    = delay_phase
                )
            else :
                for mode_l in modes_longi :
                    im_t = int(mode_t+m_trans)
                    im_l = int(mode_l+m_longi)
                    Laser(
                        box_side       = box_side,
                        omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                        # omega          = omega,
                        # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega))
                        time_envelope  = time_envelope,
                        space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                        phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                        delay_phase    = delay_phase
                    )
        else :
            if mode2generate_longi != None :
                mode_l = mode2generate_longi
                for mode_t in modes_trans :
                    im_t = int(mode_t+m_trans)
                    im_l = int(mode_l+m_longi)
                    Laser(
                        box_side       = box_side,
                        omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                        # omega          = omega,
                        # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega)),
                        time_envelope  = time_envelope,
                        space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                        phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                        delay_phase    = delay_phase
                    )
            else :
                for mode_t in modes_trans :
                    for mode_l in modes_longi :
                        im_t = int(mode_t+m_trans)
                        im_l = int(mode_l+m_longi)
                        Laser(
                            box_side       = box_side,
                            omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                            # omega          = omega,
                            # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega)),
                            time_envelope  = time_envelope,
                            space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                            phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                            delay_phase    = delay_phase
                        )

def LaserSmoothingPeriodic3D(box_side="xmin", a0=1., omega=1., focus=None, incidence_angle=0.,polarization_phi=0.,ellipticity=0.,phase_zero=0.,
               Lf=3.00e6,fnumber=8.00,
               N=[6,6],rpp_random_seed=10.,
               temporal_smoothing=None,temporal_smoothing_random_seed=42,
               omega_m=0.,modulation_depth=0,rpp_per_mode=False,rpp_seed_per_mode=[42],
               omega_m_trans=0.,modulation_depth_trans=0,mode2generate_trans=None,direction='y',chirp_profile=tconstant(),
               omega_m_longi=0.,modulation_depth_longi=0,mode2generate_longi=None,
               space_envelope=lambda y,z:1.,time_envelope=tconstant()):
    '''
    Default values are in code units
    incidence_angle in radian ONLY IN (X,Y) PLANE
    a0                     : Maximum of the envelope at focal spot for 1 speckle (i.e. N=40 and no random phase between element, or N=1). Otherwise, for N=40, a = a0/sqrt(N=40) in the simulation box.
    Lf                     : Longueur focale without SSD
    fnumber                : F-number
    N                      : List of number of phase plate element per direction (for Ntot=36, then N=[6,6])
    rpp_random_seed        : Seed in order to have a Random Phase Plate (None is = no random, all element have zero phase-shift),
    temporal_smoothing     : None/'Broadband'/'TSSD'/'LSSD'
    omega_m                : modulation frequency for Broadband Laser
    modulation_depth       : depth 'm' of modulation and frequency bandwith = 2m for Broadband Laser
    rpp_per_mode           : False/True : Change the RPP for each mode
    rpp_seed_per_mode      : Seed for RRP
    omega_m_trans          : modulation frequency for transverse TSSD
    omega_m_longi          : modulation frequency for longitudinal LSSD
    modulation_depth_trans : depth 'm' of modulation and frequency bandwith = 2m for transverse SSD
    modulation_depth_longi : depth 'm' of modulation and frequency bandwith = 2m for longitudinal SSD
    direction              : direction of transverse TSSD : 'y' or 'z'
    '''
    import numpy as np
    from math import pi, sqrt, cos, sin, tan, fabs
    from cmath import exp,rect,polar
    from scipy.special import erf,jv
    
    global Main

    if temporal_smoothing==None:
        omega_m=0.
        modulation_depth=0
        omega_m_trans=0.
        modulation_depth_trans=0
        omega_m_longi=0.
        modulation_depth_longi=0
    elif temporal_smoothing=='Broadband':
        omega_m_trans=0.
        modulation_depth_trans=0
        omega_m_longi=0.
        modulation_depth_longi=0
    elif temporal_smoothing=='TSSD':
        omega_m=0.
        modulation_depth=0
        omega_m_longi=0.
        modulation_depth_longi=0
    elif temporal_smoothing=='LSSD':
        omega_m=0.
        modulation_depth=0
        omega_m_trans=0.
        modulation_depth_trans=0

    if len(Main)==0:
        raise Exception("LaserRPP2D profile has been defined before `Main()`") 
        
    k0 = omega
    Ny,Nz = N[0],N[1]
    Ntot = int(Ny*Nz)
    waist_y = fnumber*Ny*(2.00*pi/omega)
    waist_z = fnumber*Nz*(2.00*pi/omega)
    D = Lf/fnumber #taille lame de phase : On fait l'hypothese/le choix ici que l'ouverture du faisceau est identique avant la lame de phase (D et fnumber pareil pour y et z)
    dy = D/Ny #taille element lame de phase y
    dz = D/Nz #taille element lame de phase z
    Ry = sqrt(waist_y*dy/pi)
    Rz = sqrt(waist_z*dz/pi)

    x_focus,y_focus,z_focus = focus[0],focus[1],focus[2]

    El = (a0*omega/Ntot)/np.sqrt(k0*dy**2/(2*Lf*np.pi**2))/np.sqrt(k0*dz**2/(2*Lf*np.pi**2))
    # Polarization and amplitude
    dephasing, amplitudeZ, amplitudeY = transformPolarization(polarization_phi, ellipticity)
    amplitudeY *= El * cos(incidence_angle)
    amplitudeZ *= El
    delay_phase = [0., dephasing]

    krpp_y = np.linspace(-D/2,D/2,Ny+1)
    krpp_z = np.linspace(-D/2,D/2,Nz+1)

    #phik_y = np.zeros(Ny)
    #phik_z = np.zeros(Nz)
    #if rpp_random_seed != None :
    #    np.random.seed(rpp_random_seed) # Meme suite de nombre aleatoire utilisee pour comparer des cas avec meme lame de phase
    #    phikinit = np.random.rand(int(Ny+Nz))
    #    for i in range(0,Ny):
    #        phik_y[i] = 2*pi*phikinit[i] # remplissage avec phi entre 0 et 2pi
    #    for i in range(Ny,Ny+Nz):
    #        phik_z[i] = 2*pi*phikinit[i] # remplissage avec phi entre 0 et 2pi

    phik = np.zeros(Ntot)
    if rpp_random_seed != None :
        np.random.seed(rpp_random_seed) # Meme suite de nombre aleatoire utilisee pour comparer des cas avec meme lame de phase
        phikinit = np.random.rand(Ntot)
        for i in range(0,Ntot):
            phik[i] = 2*pi*phikinit[i] # remplissage avec phi entre 0 et 2pi

    m_broadband = modulation_depth
    m_trans = modulation_depth_trans
    m_longi = modulation_depth_longi
    alpha_t = 2*pi/D
    alpha_x = 1/omega

    modes_trans = range(-m_trans,m_trans+1,1)
    modes_longi = range(-m_longi,m_longi+1,1)
    modes_broadband = range(-m_broadband,m_broadband+1,1)
    
    if temporal_smoothing=='Broadband':
        if temporal_smoothing_random_seed != None :
            np.random.seed(temporal_smoothing_random_seed)
            phase_w = 2*pi*np.random.rand(len(modes_broadband))
            Ebb = np.ones(len(modes_broadband))/np.sqrt(len(modes_broadband))
        else :
            phase_w = np.zeros(len(modes_broadband))
            Ebb = np.ones(len(modes_broadband))/np.sqrt(len(modes_broadband))

    def ERPP(y,z,imode,imode_tY,imode_tZ,imode_l,phik) :
        '''
        Formula (24) of "Cross-beam energy transfer between spatially smoothed laser beams" [A. Oudin, A. Debayle, C. Ruyer]
        Spatial envelope definition at x=0 of the simulation domain.
        For a fixed SSD mode. SSD is treated as a Laser() superposition at different frequency.
        '''

        X,Y,Z = transform_3d(0,y,z,x_focus,y_focus,z_focus,Lf,incidence_angle)

        Lfw = Lf*(1+alpha_x*imode_l*omega_m_longi)
        # K   = sqrt( fabs( k0/(2*X) - 1/R**2 ) )
        K = sqrt( fabs( k0*(Lfw-X)/(2*X*Lfw) ) )
        sum_erfm = 0+0*1j
        sum_erfm_y = 0+0*1j
        sum_erfm_z = 0+0*1j
        factm    = 0+0*1j

        if (temporal_smoothing == None) & ((imode_tY != 0) | (imode_tZ != 0)  | (imode_l != 0)):
            raise Exception("Input inconsistency : No temporal smoothing selected but non-zero 'modulation depth'")

        factm = exp(-1j*pi*0.25)*sqrt(k0*dy*dy/(2*pi*pi*Lfw))
        factm *= exp(-1j*pi*0.25)*sqrt(k0*dz*dz/(2*pi*pi*Lfw))
        for ny in range (0,Ny):
            for nz in range (0,Nz):
                sum_erfm_y = exp(-1j*k0/Lfw*(Y-imode_tY*alpha_t*X/k0)*(krpp_y[ny+1]+krpp_y[ny])/2)
                sum_erfm_z = exp(-1j*k0/Lfw*(Z-imode_tZ*alpha_t*X/k0)*(krpp_z[nz+1]+krpp_z[nz])/2)
                sum_erfm += sum_erfm_y*sum_erfm_z*exp(1j*phik[ny*Nz+nz])

        if temporal_smoothing==None:
            Einit = sum_erfm*factm*exp(1j*k0*X)#*exp(1j*k0*X*imode_l*omega_m_longi/k0)*exp(1j*k0*X*imode_t*omega_m_trans/k0)
        elif (temporal_smoothing=='TSSD') | (temporal_smoothing=='LSSD'):
            if direction=='y':
                Einit = jv(imode_tY,m_trans)*jv(imode_l,m_longi)*sum_erfm*factm*exp(1j*k0*X)*exp(1j*k0*X*imode_l*omega_m_longi/k0)*exp(1j*k0*X*imode_tY*omega_m_trans/k0)
            elif direction=='z':
                Einit = jv(imode_tZ,m_trans)*jv(imode_l,m_longi)*sum_erfm*factm*exp(1j*k0*X)*exp(1j*k0*X*imode_l*omega_m_longi/k0)*exp(1j*k0*X*imode_tZ*omega_m_trans/k0)
            else :
                raise Exception("'direction' parameter for TSSD unknown")
        elif temporal_smoothing=='Broadband':
            Einit = Ebb[imode]*sum_erfm*factm*exp(1j*k0*X)*exp(1j*phase_w[imode])*exp(1j*k0*X*imode*omega_m/k0)
        else :
            raise Exception("Temporal_smoothing method not implemented yet")

        Amp,Phase = polar(Einit)
        return Amp,Phase

    def ERPP_ampBz(y,z,imode_,imode_tY_,imode_tZ_,imode_l_,phik_) :
        return amplitudeZ*space_envelope(y,z)*ERPP(y,z,imode=imode_,imode_tY=imode_tY_,imode_tZ=imode_tZ_,imode_l=imode_l_,phik=phik_)[0]
    def ERPP_ampBy(y,z,imode_,imode_tY_,imode_tZ_,imode_l_,phik_) :
        return amplitudeY*space_envelope(y,z)*ERPP(y,z,imode=imode_,imode_tY=imode_tY_,imode_tZ=imode_tZ_,imode_l=imode_l_,phik=phik_)[0]
    def ERPP_phaseBz(y,z,imode_,imode_tY_,imode_tZ_,imode_l_,phik_) :
        return ERPP(y,z,imode=imode_,imode_tY=imode_tY_,imode_tZ=imode_tZ_,imode_l=imode_l_,phik=phik_)[1]-phase_zero+delay_phase[0]
    def ERPP_phaseBy(y,z,imode_,imode_tY_,imode_tZ_,imode_l_,phik_) :
        return ERPP(y,z,imode=imode_,imode_tY=imode_tY_,imode_tZ=imode_tZ_,imode_l=imode_l_,phik=phik_)[1]-phase_zero+delay_phase[1]

    fct_amp_By = []
    fct_amp_Bz = []
    fct_phase_By = []
    fct_phase_Bz = []

    if temporal_smoothing=='Broadband':
        for mode in modes_broadband :
            if rpp_per_mode==True:
                if len(rpp_seed_per_mode)!=len(modes_broadband):
                    raise Exception("len(rpp_seed_per_mode): "+str(len(rpp_seed_per_mode))+". len(modes_broadband): "+str(len(modes_broadband))+". Length of rpp_seed_per_mode have to be equal to 2 x modulation_depth + 1 ")
                phik = np.zeros(Ntot)
                np.random.seed(rpp_seed_per_mode[mode+m_broadband]) # Meme suite de nombre aleatoire utilisee pour comparer des cas avec meme lame de phase
                phikinit = np.random.rand(Ntot)
                for i in range(0,Ntot):
                    phik[i] = 2*pi*phikinit[i] # remplissage avec phi entre 0 et 2pi
            fct_amp_By.append(lambda y,z,imode_tmp=mode,imode_tY_tmp=0,imode_tZ_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_ampBy(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
            fct_amp_Bz.append(lambda y,z,imode_tmp=mode,imode_tY_tmp=0,imode_tZ_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_ampBz(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
            fct_phase_By.append(lambda y,z,imode_tmp=mode,imode_tY_tmp=0,imode_tZ_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_phaseBy(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
            fct_phase_Bz.append(lambda y,z,imode_tmp=mode,imode_tY_tmp=0,imode_tZ_tmp=0,imode_l_tmp=0,phik_tmp=phik: ERPP_phaseBz(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
        fct_amp_By = np.array(fct_amp_By)
        fct_amp_Bz = np.array(fct_amp_Bz)
        fct_phase_By = np.array(fct_phase_By)
        fct_phase_Bz = np.array(fct_phase_Bz)
    else :
        for mode_t in modes_trans :
            for mode_l in modes_longi :
                if (m_trans==0) | (direction=='y') :
                    fct_amp_By.append(lambda y,z,imode_tmp=0,imode_tY_tmp=1*mode_t,imode_tZ_tmp=0*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_ampBy(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                    fct_amp_Bz.append(lambda y,z,imode_tmp=0,imode_tY_tmp=1*mode_t,imode_tZ_tmp=0*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_ampBz(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                    fct_phase_By.append(lambda y,z,imode_tmp=0,imode_tY_tmp=1*mode_t,imode_tZ_tmp=0*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_phaseBy(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                    fct_phase_Bz.append(lambda y,z,imode_tmp=0,imode_tY_tmp=1*mode_t,imode_tZ_tmp=0*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_phaseBz(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                elif direction=='z':
                    fct_amp_By.append(lambda y,z,imode_tmp=0,imode_tY_tmp=0*mode_t,imode_tZ_tmp=1*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_ampBy(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                    fct_amp_Bz.append(lambda y,z,imode_tmp=0,imode_tY_tmp=0*mode_t,imode_tZ_tmp=1*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_ampBz(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                    fct_phase_By.append(lambda y,z,imode_tmp=0,imode_tY_tmp=0*mode_t,imode_tZ_tmp=1*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_phaseBy(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                    fct_phase_Bz.append(lambda y,z,imode_tmp=0,imode_tY_tmp=0*mode_t,imode_tZ_tmp=1*mode_t,imode_l_tmp=mode_l,phik_tmp=phik: ERPP_phaseBz(y,z,imode_=imode_tmp,imode_tY_=imode_tY_tmp,imode_tZ_=imode_tZ_tmp,imode_l_=imode_l_tmp,phik_=phik_tmp))
                else :
                     raise Exception(" m_trans != 0 and direction for transverse SSD unknown : Have to be 'y' or 'z' ")
        fct_amp_By = np.reshape(np.array(fct_amp_By),(2*m_trans+1,2*m_longi+1))
        fct_amp_Bz = np.reshape(np.array(fct_amp_Bz),(2*m_trans+1,2*m_longi+1))
        fct_phase_By = np.reshape(np.array(fct_phase_By),(2*m_trans+1,2*m_longi+1))
        fct_phase_Bz = np.reshape(np.array(fct_phase_Bz),(2*m_trans+1,2*m_longi+1))

    if temporal_smoothing=='Broadband':
        for mode in modes_broadband :
            im = int(mode+m_broadband)
            Laser(
                box_side       = box_side,
                omega          = omega*(1.+mode*omega_m/omega),
                # omega          = omega,
                # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega))
                time_envelope  = time_envelope,
                space_envelope = [fct_amp_By[im],fct_amp_Bz[im]],
                phase          = [fct_phase_By[im],fct_phase_Bz[im]],
                delay_phase    = delay_phase
            )
    else :
        if mode2generate_trans != None :
            mode_t = 1.*mode2generate_trans
            if mode2generate_longi != None :
                mode_l = 1.*mode2generate_longi
                im_t = int(mode_t+m_trans)
                im_l = int(mode_l+m_longi)
                Laser(
                    box_side       = box_side,
                    omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                    # omega          = omega,
                    # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega))
                    time_envelope  = time_envelope,
                    space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                    phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                    delay_phase    = delay_phase
                )
            else :
                for mode_l in modes_longi :
                    im_t = int(mode_t+m_trans)
                    im_l = int(mode_l+m_longi)
                    Laser(
                        box_side       = box_side,
                        omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                        # omega          = omega,
                        # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega))
                        time_envelope  = time_envelope,
                        space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                        phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                        delay_phase    = delay_phase
                    )
        else :
            if mode2generate_longi != None :
                mode_l = mode2generate_longi
                for mode_t in modes_trans :
                    im_t = int(mode_t+m_trans)
                    im_l = int(mode_l+m_longi)
                    Laser(
                        box_side       = box_side,
                        omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                        # omega          = omega,
                        # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega)),
                        time_envelope  = time_envelope,
                        space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                        phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                        delay_phase    = delay_phase
                    )
            else :
                for mode_t in modes_trans :
                    for mode_l in modes_longi :
                        im_t = int(mode_t+m_trans)
                        im_l = int(mode_l+m_longi)
                        Laser(
                            box_side       = box_side,
                            omega          = omega*(1.+mode_t*omega_m_trans/omega+mode_l*omega_m_longi/omega),
                            # omega          = omega,
                            # chirp_profile  = tpolynomial(t0=0.0, order0=(1.+mode*omega_m/omega)),
                            time_envelope  = time_envelope,
                            space_envelope = [fct_amp_By[im_t,im_l],fct_amp_Bz[im_t,im_l]],
                            phase          = [fct_phase_By[im_t,im_l],fct_phase_Bz[im_t,im_l]],
                            delay_phase    = delay_phase
                        )

def LaserEnvelopeGaussian3D( a0=1., omega=1., focus=None, waist=3., time_envelope=tconstant(),
        envelope_solver = "explicit",Envelope_boundary_conditions = [["reflective"]], box_side = "inside",
        polarization_phi = 0.,ellipticity = 0.):
    import cmath
    from numpy import exp, sqrt, arctan, vectorize
    assert len(focus)==3, "LaserEnvelopeGaussian3D: focus must be a list of length 3."
    
    def gaussian_beam3D(x,y,z):
        polarization_amplitude_factor = 1/sqrt(1.+ellipticity**2)
        Zr = omega * waist**2/2.
        w  = sqrt(1./(1.+   ( (x-focus[0])/Zr  )**2 ) )
        coeff = omega * (x-focus[0]) * w**2 / (2.*Zr**2)
        phase = coeff * ( (y-focus[1])**2 + (z-focus[2])**2 )
        exponential_with_total_phase = exp(1j*(phase-arctan( (x-focus[0])/Zr )))
        invWaist2 = (w/waist)**2
        spatial_amplitude = a0*polarization_amplitude_factor* w * exp( -invWaist2*(  (y-focus[1])**2 + (z-focus[2])**2 )  )
        return spatial_amplitude * exponential_with_total_phase
    
    if (box_side=="inside"):
        def envelope_profile(x,y,z,t):
            return gaussian_beam3D(x,y,z)*vectorize(time_envelope)(t)
    elif (box_side=="xmin"):
        def envelope_profile(y,z,t):
            return gaussian_beam3D(0,y,z)*vectorize(time_envelope)(t)
    else:
        print("LaserEnvelope error: box_side must be either 'inside' or 'xmin'. ")

    # Create Laser Envelope
    LaserEnvelope(
        omega                        = omega,
        envelope_profile             = envelope_profile,
        envelope_solver              = envelope_solver,
        box_side                     = box_side,
        Envelope_boundary_conditions = Envelope_boundary_conditions,
        polarization_phi             = polarization_phi,
        ellipticity                  = ellipticity
    )


def LaserGaussianAM( box_side="xmin", a0=1., omega=1., focus=None, waist=3.,
        polarization_phi=0., ellipticity=0., time_envelope=tconstant(), phase_offset=0.):
    from math import cos, sin, tan, atan, sqrt, exp
    if (len(focus)<1) or (len(focus)>2): 
        print("ERROR: focus should be a list of length 1")
        exit(1)
    elif (len(focus)==2):
        print("WARNING: deprecated focus in LaserGaussianAM should be a list of length 1")
    # Polarization and amplitude
    [dephasing, amplitudeY, amplitudeZ] = transformPolarization(polarization_phi, ellipticity)
    amplitudeY *= a0 * omega
    amplitudeZ *= a0 * omega
    # Space and phase envelopes
    Zr = omega * waist**2/2.
    w  = sqrt(1./(1.+(focus[0]/Zr)**2))
    invWaist2 = (w/waist)**2
    coeff = -omega * focus[0] * w**2 / (2.*Zr**2)
    def spatial(r):
        return w * exp( -invWaist2*(r)**2 )
    def phase(r):
        return coeff * (r)**2
    # Create Laser
    Laser(
        box_side        = box_side,
        omega          = omega,
        chirp_profile  = tconstant(),
        time_envelope  = time_envelope,
        space_envelope = [ lambda r:amplitudeZ*spatial(r), lambda r:amplitudeY*spatial(r) ],
        phase          = [ lambda r:phase(r)-phase_offset+dephasing, lambda r:phase(r)-phase_offset ],
        delay_phase    = [ 0., dephasing ]
    )


def LaserEnvelopeGaussianAM( a0=1., omega=1., focus=None, waist=3., time_envelope=tconstant(),
        envelope_solver = "explicit",box_side = "inside",Envelope_boundary_conditions = [["reflective"]],
        Env_pml_sigma_parameters = [[0.90,2],[10.0,2],[10.0,2]],
        Env_pml_kappa_parameters = [[1.00,1.00,2],[1.00,1.00,2],[1.00,1.00,2]],
        Env_pml_alpha_parameters = [[0.90,0.90,1],[0.75,0.75,1],[0.75,0.75,1]],
        polarization_phi = 0.,ellipticity = 0.):
    import cmath
    from numpy import exp, sqrt, arctan, vectorize
    if (len(focus)<1) or (len(focus)>2): 
        print("ERROR: focus should be a list of length 1")
        exit(1)
    elif (len(focus)==2):
        print("WARNING: deprecated focus in LaserEnvelopeGaussianAM should be a list of length 1")

    def gaussian_beamAM(x,r):
        polarization_amplitude_factor = 1/sqrt(1.+ellipticity**2)
        Zr = omega * waist**2/2.
        w  = sqrt(1./(1.+   ( (x-focus[0])/Zr  )**2 ) )
        coeff = omega * (x-focus[0]) * w**2 / (2.*Zr**2)
        phase = coeff * ( r**2 )
        exponential_with_total_phase = exp(1j*(phase-arctan( (x-focus[0])/Zr )))
        invWaist2 = (w/waist)**2
        spatial_amplitude = a0 * polarization_amplitude_factor * w * exp( -invWaist2*(  r**2  ) )
        return spatial_amplitude  * exponential_with_total_phase
        
    if (box_side=="inside"):
        def envelope_profile(x,r,t):
            return gaussian_beamAM(x,r)*vectorize(time_envelope)(t)
    elif (box_side=="xmin"):
        def envelope_profile(r,t):
            return gaussian_beamAM(0,r)*vectorize(time_envelope)(t)
    else:
        print("LaserEnvelope error: box_side must be either 'inside' or 'xmin'. ")
            
    # Create Laser Envelope
    LaserEnvelope(
        omega                        = omega,
        envelope_profile             = envelope_profile,
        envelope_solver              = envelope_solver,
        box_side                     = box_side,
        Envelope_boundary_conditions = Envelope_boundary_conditions,
        Env_pml_sigma_parameters     = Env_pml_sigma_parameters,
        Env_pml_kappa_parameters     = Env_pml_kappa_parameters,
        Env_pml_alpha_parameters     = Env_pml_alpha_parameters,
        polarization_phi             = polarization_phi,
        ellipticity                  = ellipticity
    )

# Define the tools for the propagation of a laser profile
try:
    import numpy as np
    
    _N_LaserOffset = 0
    
    def LaserOffset(box_side="xmin", space_time_profile=[], offset=0., angle=0., extra_envelope=lambda *a:1.,
            fft_time_window=None, fft_time_step=None, keep_n_strongest_modes=100,
            number_of_processes=None, file=None):
        global _N_LaserOffset
        
        file_ = file or ('LaserOffset'+str(_N_LaserOffset)+'.h5')
        
        L = Laser(
            box_side = box_side,
            file = file_,
        )
        
        L._offset = offset
        L._extra_envelope = extra_envelope
        L._profiles = space_time_profile
        L._fft_time_window = fft_time_window or Main.simulation_time
        L._fft_time_step = fft_time_step or Main.timestep
        L._keep_n_strongest_modes = keep_n_strongest_modes
        L._angle = angle
        L._number_of_processes = number_of_processes
        if file:
            if not os.path.exists(file):
                raise Exception("File not found or not accessible: "+file)
            L._propagate = False
        else:
            L._propagate = True
        
        _N_LaserOffset += 1

except:
    
    def LaserOffset(box_side="xmin", space_time_profile=[], offset=0., fft_time_window=None, extra_envelope=lambda *a:1., keep_n_strongest_modes=100, angle=0., number_of_processes=None, file=None):
        L = Laser(
            box_side = box_side,
            file = "none",
            time_envelope = extra_envelope
        )
        print("WARNING: LaserOffset unavailable because numpy was not found")



"""
-----------------------------------------------------------------------
BEGINNING OF THE USER NAMELIST
"""

import math
L  = 1.12
dn = 1.002676e-03

Main(
    geometry = "1Dcartesian",
    interpolation_order = 2,
    cell_length = [0.01],
    grid_length  = [L],
    number_of_patches = [ 16 ],
    timestep = 0.0095,
    simulation_time = 35.,
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


"""
    END OF THE USER NAMELIST
-----------------------------------------------------------------------
"""

gc.collect()
import math
from glob import glob
from re import search

def _mkdir(role, path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except:
            raise Exception("ERROR in the namelist: "+role+" "+path+" cannot be created")
    elif not os.path.isdir(path):
        raise Exception("ERROR in the namelist: "+role+" "+path+" exists but is not a directory")


def _smilei_check():
    """Do checks over the script"""
    
    # Verify classes were not overriden
    for CheckClassName in ["SmileiComponent","Species", "Laser","Collisions",
            "DiagProbe","DiagParticleBinning", "DiagScalar","DiagFields",
            "DiagTrackParticles","DiagNewParticles","DiagPerformances",
            "ExternalField","PrescribedField",
            "SmileiSingleton","Main","LoadBalancing","MovingWindow",
            "RadiationReaction", "ParticleData", "MultiphotonBreitWheeler",
            "Vectorization", "MultipleDecomposition"]:
        CheckClass = globals()[CheckClassName]
        try:
            if not CheckClass._verify: raise Exception("")
        except:
            raise Exception("ERROR in the namelist: it seems that the name `"+CheckClassName+"` has been overriden")
    
    
    # Verify that constant() and tconstant() were not redefined
    if not hasattr(constant, "_reserved") or not hasattr(tconstant, "_reserved"):
        raise Exception("Names `constant` and `tconstant` cannot be overriden")
    
    # Convert float profiles to constant() or tconstant()
    def toSpaceProfile(input):
        try   : return constant(input*1.)
        except: return input
    def toTimeProfile(input):
        try:
            input*1.
            return tconstant()
        except: return input
    Main.pml_sigma = [ toSpaceProfile(p) for p in (Main.pml_sigma ) ]
    Main.pml_kappa = [ toSpaceProfile(p) for p in (Main.pml_kappa ) ]
    for s in Species:
        s.number_density      = toSpaceProfile(s.number_density)
        s.charge_density  = toSpaceProfile(s.charge_density)
        s.particles_per_cell = toSpaceProfile(s.particles_per_cell)
        s.charge          = toSpaceProfile(s.charge)
        s.mean_velocity   = [ toSpaceProfile(p) for p in s.mean_velocity ]
        s.mean_velocity_AM = [ toSpaceProfile(p) for p in s.mean_velocity_AM ]
        s.temperature     = [ toSpaceProfile(p) for p in s.temperature   ]
    for e in ExternalField:
        e.profile         = toSpaceProfile(e.profile)
    for e in PrescribedField:
        e.profile         = toSpaceProfile(e.profile)
    for a in Antenna:
        a.space_profile   = toSpaceProfile(a.space_profile   )
        a.time_profile    = toTimeProfile (a.time_profile    )
    for l in Laser:
        l.chirp_profile   = toTimeProfile( l.chirp_profile )
        l.time_envelope   = toTimeProfile( l.time_envelope )
        l.space_envelope  = [ toSpaceProfile(p) for p in l.space_envelope ]
        l.phase           = [ toSpaceProfile(p) for p in l.phase          ]
    for s in ParticleInjector:
        s.number_density = toSpaceProfile(s.number_density)
        s.charge_density = toSpaceProfile(s.charge_density)
        s.time_envelope  = toTimeProfile(s.time_envelope)
        s.particles_per_cell = toSpaceProfile(s.particles_per_cell )
        s.mean_velocity   = [ toSpaceProfile(p) for p in s.mean_velocity ]
        s.temperature     = [ toSpaceProfile(p) for p in s.temperature   ]

# this function will be called after initialising the simulation, just before entering the time loop
# if it returns false, the code will call a Py_Finalize();
def _keep_python_running():
    # Verify all temporal profiles, and all profiles that depend on the moving window or on the load balancing
    profiles = []
    for las in Laser:
        profiles += [las.time_envelope]
        profiles += [las.chirp_profile]
        if type(las.space_time_profile) is list:
            profiles += las.space_time_profile
        if type(las.space_time_profile_AM) is list:
            profiles += las.space_time_profile_AM
        if hasattr(las, "_extra_envelope"):
            profiles += [las._extra_envelope]
    profiles += [ant.time_profile for ant in Antenna]
    profiles += [ant.space_time_profile for ant in Antenna]
    profiles += [e.profile for e in PrescribedField]
    if len(MovingWindow)>0 or len(LoadBalancing)>0:
        # Verify if PML are used
        for bcs in Main.EM_boundary_conditions:
            for bc in bcs:
                if (bc == "PML"):
                    return True
        for s in Species:
            profiles += [s.number_density, s.charge_density, s.particles_per_cell, s.charge] + s.mean_velocity + s.mean_velocity_AM + s.temperature
    if len(MovingWindow)>0:
        profiles += [e.profile for e in ExternalField]
    for i in ParticleInjector:
        s = Species[i.species]
        profiles += [
                i.time_envelope,
                i.number_density or s.number_density,
                i.charge_density or s.charge_density,
                i.particles_per_cell or s.particles_per_cell
            ] + i.mean_velocity or s.mean_velocity + i.temperature or s.temperature
    for prof in profiles:
        if callable(prof) and not hasattr(prof,"profileName"):
            return True
    # Verify SDMD grids
    if len(LoadBalancing)>0 and len(MultipleDecomposition)>0:
        return True
    # Verify the tracked species that require a particle selection
    if any([d.filter for d in DiagTrackParticles]) or any([d.filter for d in DiagNewParticles]):
        return True
    # Verify the particle binning having a function for deposited_quantity or axis type
    for d in DiagParticleBinning._list + DiagScreen._list:
        if type(d.deposited_quantity) is not str:
            return True
        for ax in d.axes:
            if type(ax[0]) is not str:
                return True
    # Verify the radiation spectrum having a function for deposited_quantity or axis type
    for d in DiagRadiationSpectrum._list:
        if type(d.photon_energy_axis[0]) is not str:
            return True
        for ax in d.axes:
            if type(ax[0]) is not str:
                return True
    # Verify if ionization from rate is used
    for s in Species:
        if s.ionization_rate is not None:
            return True
    # Verify if the envelope is injected from the xmin border through a space-temporal profile
    if len(LaserEnvelope)>0:
        if LaserEnvelope.box_side=="xmin":
            return True
    # else False
    return False

# Prevent creating new components (by mistake)
def _noNewComponents(cls, *args, **kwargs):
    print("Please do not create a new "+cls.__name__)
    return None
SmileiComponent.__new__ = staticmethod(_noNewComponents)

# Writes some information in a pickle file for fast post-processing (set scan=False in happi)
def writeInfo():
    def pickable(var):
        if var is None or type(var) in [float, int, complex, str, bytes, bool]:
            return True
        elif type(var) in [list, tuple]:
            return all([pickable(v) for v in var])
        elif type(var) is dict:
            return all([pickable(var[k]) for k in var])
        else:
            try:
                import numpy
                if type(var) is numpy.ndarray and var.size < 10000:
                    return True
            except Exception:
                pass
            return False
    
    import shelve
    singletons = {}
    components = {}
    with shelve.open("info.shelf", "n") as f:
        for name,var in globals().items():
            if type(var) is type(Main):
                singletons[name] = {k:v for k,v in var.__dict__.items() if not k.startswith("_") and pickable(v)}
            elif type(var) is type(Species):
                components[name] = [{k:v for k,v in component.__dict__.items() if not k.startswith("_") and pickable(v)} for component in var]
            elif not name.startswith("_") and pickable(var):
                f[name] = var
        f["_singletons"] = singletons
        f["_components"] = components
Main.cluster_width= 7
