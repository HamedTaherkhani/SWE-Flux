# PyBaMM Project Memory

Purpose: PyBaMM builds symbolic battery models, processes parameters and geometry,
discretises symbolic PDE/DAE systems, solves them numerically, and exposes processed
solution variables for analysis, plotting, and experiments.

## Top-Level Shape

- `pybamm/__init__.py` flattens the public API. Most classes are imported through
  `pybamm.<Name>`, even when implemented in subpackages.
- Main runtime path:
  `Model -> ParameterValues -> Geometry/Mesh -> Discretisation -> Solver -> Solution`.
- `Simulation` is the user-facing orchestrator for that path.

## Core Symbolic Layer

Package: `src/pybamm/expression_tree`

- `symbol.py`
  - `Symbol` is the root expression-tree node.
  - Tracks `name`, immutable-ish `children`, `domains`, cached `id`, mesh metadata,
    traversal (`pre_order`, `post_order`), operator overloads, evaluation, shape, and
    differentiation hooks.
  - Domain levels are `primary`, `secondary`, `tertiary`, `quaternary`.
- `binary_operators.py`
  - `BinaryOperator` subclasses include `Addition`, `Subtraction`, `Multiplication`,
    `Division`, `Power`, `MatrixMultiplication`, `Minimum`, `Maximum`, `Modulo`,
    heaviside variants.
  - Helper constructors like `add`, `multiply`, `divide` do simplification and
    broadcasting.
- `unary_operators.py`
  - `UnaryOperator` subclasses include math functions and spatial operators:
    `Gradient`, `Divergence`, `Laplacian`, `Integral`, `BoundaryValue`,
    `BoundaryGradient`, `EvaluateAt`, `Upwind`, `Downwind`.
- `variable.py`, `parameter.py`, `input_parameter.py`, `state_vector.py`
  - `Variable` and `VariableDot` are symbolic model unknowns.
  - `Parameter` and `FunctionParameter` are placeholders replaced by
    `ParameterValues`.
  - `InputParameter` remains runtime supplied.
  - `StateVector`/`StateVectorDot` are post-discretisation state slices.
- `broadcasts.py`, `concatenations.py`
  - Handle domain lifting and domain-wise combination, central to PDE discretisation.
- `operations/`
  - `Jacobian`, `CasadiConverter`, `EvaluatorPython`, `EvaluatorJax`,
    serialisation, latex, symbol unpacking.

## Model Layer

Package: `src/pybamm/models`

- `base_model.py`
  - `BaseModel` owns `rhs`, `algebraic`, `initial_conditions`,
    `boundary_conditions`, `variables`, `events`, `submodels`, mass matrix,
    Jacobians, discretisation state, and geometry.
  - Build flow:
    1. `build_fundamental()`: ask each submodel for independent variables.
    2. `build_coupled_variables()`: repeatedly revisit submodels until all required
       variables exist; raises `ModelError` if a dependency never resolves.
    3. `build_model_equations()`: ask submodels to set rhs/algebraic/BC/IC/events,
       merge into the full model.
    4. `check_well_posedness()`: under/over-determined checks, IC/BC checks,
       repeated key checks.
- `event.py`
  - `Event` plus `EventType` classify termination, switch, discontinuity, and
    interpolant extrapolation events.
- `models/submodels/base_submodel.py`
  - `BaseSubModel` defines the public submodel interface:
    `get_fundamental_variables`, `get_coupled_variables`, `set_rhs`,
    `set_algebraic`, `set_boundary_conditions`, `set_initial_conditions`,
    `add_events_from`.
  - Most physics classes inherit this via base classes in each submodel family.

## Battery Models and Options

Package: `src/pybamm/models/full_battery_models`

- `base_battery_model.py`
  - `BatteryModelOptions` validates and normalizes large option dictionaries.
  - `BaseBatteryModel` extends `BaseModel` with default geometry, var points,
    submesh types, spatial methods, output variables, voltage/SOC/degradation
    variables, and common submodel selection methods.
  - Important option-dispatch methods:
    `set_external_circuit_submodel`, `set_transport_efficiency_submodels`,
    `set_thermal_submodel`, `set_current_collector_submodel`,
    `get_intercalation_kinetics`.
- `lithium_ion/base_lithium_ion_model.py`
  - Lithium-ion `BaseModel` creates `LithiumIonParameters`, standard output
    variables, and default submodel setup order.
  - Dispatch-heavy methods include OCP, SEI, lithium plating, particle mechanics,
    active material, porosity, and Li-metal counter-electrode submodels.
- `lithium_ion/spm.py`, `spme.py`, `dfn.py`
  - Concrete model classes choose submodels for particles, electrolyte,
    electrode potentials, and kinetics.
  - `SPM` is x-averaged and simpler; `DFN` is full-order; `SPMe` mixes SPM
    particle behavior with electrolyte dynamics.
- Other model families:
  - `lead_acid/`: full, LOQS, basic lead-acid models.
  - `equivalent_circuit/`: Thevenin/ECM models.
  - `sodium_ion/`: sodium-ion basic DFN.

## Parameters, Geometry, Mesh, Discretisation

- `parameters/parameter_values.py`
  - `ParameterValues` wraps a fuzzy parameter dictionary.
  - `update()` validates values, converts string numerics, handles `[input]`, and
    clears processed-symbol cache.
  - `process_model()` replaces parameters in equations, variables, ICs, BCs, and
    events.
  - `_process_symbol()` recursively handles `Parameter`, `FunctionParameter`,
    `UnaryOperator`, `BinaryOperator`, `Concatenation`, `Function`, and `Variable`.
  - Adds interpolant extrapolation events.
- `geometry/battery_geometry.py`, `geometry/geometry.py`
  - Build and store geometric domain limits and tab data.
- `meshes/meshes.py`
  - `Mesh` evaluates processed geometry, constructs submeshes, combines domains on
    demand, and adds ghost-cell submeshes for 1D domains.
  - Submesh implementations live in `one_dimensional_submeshes.py`,
    `zero_dimensional_submesh.py`, and scikit FEM files.
- `discretisations/discretisation.py`
  - `Discretisation.process_model()` performs the post-parameter numerical
    transformation.
  - Key stages: check model, set variable slices and bounds, process BCs, add
    internal BCs, process ICs, process variables, process rhs/algebraic equations,
    process events, create mass matrix, check model.
  - `_process_symbol()` dispatches by symbol type. Spatial operators are delegated
    to the domain spatial method.
- `spatial_methods/`
  - `SpatialMethod` is the base interface.
  - `FiniteVolume` is the dominant 1D method; implements gradient/divergence,
    integrals, ghost nodes, boundary values, upwind/downwind, edge/node shifts.
  - `ZeroDimensionalSpatialMethod`, `SpectralVolume`, and scikit FEM methods cover
    other domains.

## Simulation and Solvers

- `simulation.py`
  - `Simulation` is the main orchestration class.
  - `__init__()` chooses operating mode:
    `without experiment`, `drive cycle`, or `with experiment`.
  - `build()` runs parameter processing, mesh creation, discretisation, and clears
    solver setup cache.
  - `build_for_experiment()` processes each unique experiment step into a separate
    built model and solver copy.
  - `solve()` handles simple solves and the full experiment loop with cycles,
    steps, padding rests, infeasibility checks, summary variables, and callbacks.
- `solvers/base_solver.py`
  - `BaseSolver` validates model/solver compatibility, sets up initial conditions,
    converts expressions to callables, configures events, handles consistent DAE
    initialization, splits solves at discontinuities, calls `_integrate()`, checks
    events/extrapolation, and returns `Solution`.
  - Concrete solvers implement `_integrate()`.
- Solver implementations:
  - `scipy_solver.py`: SciPy ODE solve path.
  - `casadi_solver.py`: CasADi modes and integrator cache.
  - `idaklu_solver.py`: IDA/KLU DAE solver, parallel solve support, sensitivities.
  - `algebraic_solver.py`, `casadi_algebraic_solver.py`: root/algebraic solving.
  - `jax_solver.py`, `jax_bdf_solver.py`, `idaklu_jax.py`: JAX-related paths.
- `solvers/solution.py`
  - `Solution` stores time/state chunks, model references, inputs, events,
    sensitivities, cycles, summary variables, processed-variable cache, and data
    export.
- `processed_variable.py`, `summary_variable.py`
  - Convert symbolic model variables into evaluated/interpolated data over a
    solution, including 0D/1D/2D/3D variants and cycle summaries.

## Experiments and Callbacks

- `experiment/experiment.py`
  - `Experiment` normalizes step sequences into cycles, handles periods,
    temperatures, tags, start times, and global termination conditions.
- `experiment/step/base_step.py`
  - `BaseStep` stores value, duration, termination, period, temperature, tags,
    direction, start/end time.
  - `BaseStepExplicit` changes current parameter.
  - `BaseStepImplicit` changes the external-circuit control submodel.
  - Parsing helpers convert strings like time, temperature, current, voltage, power,
    resistance, and termination clauses.
- `experiment/step/steps.py`
  - Public constructors and classes for current, C-rate, voltage, power, resistance,
    rest, and custom explicit/implicit steps.
- `experiment/step/step_termination.py`
  - Builds event objects for voltage/current/C-rate/custom termination.
- `callbacks.py`
  - `Callback`, `CallbackList`, and `LoggingCallback`; used by experiment solve loop.

## Dependency Map

- `expression_tree` is the foundation. Models, parameters, discretisation, solvers,
  and processed variables all depend on `Symbol` subclasses.
- `models` depend on `expression_tree`, `parameters` symbols, `events`, and
  submodel classes.
- `full_battery_models` depend on `submodels` plus parameter classes.
- `ParameterValues` depends on expression-tree traversal and produces parameterized
  models/geometries.
- `Geometry` feeds `Mesh`; `Mesh` feeds `Discretisation`.
- `Discretisation` depends on `Mesh`, `SpatialMethod`, model dictionaries, and
  expression-tree dispatch.
- `Solvers` require discretised models and depend on expression evaluators,
  Jacobian/CasADi/JAX conversion, events, and `Solution`.
- `Simulation` coordinates almost all layers.
- `Experiment` and `step` classes modify parameters/submodels before simulation and
  drive repeated calls to `solver.step`.

## High-Value Dynamic QA Targets

- `BaseModel.build_coupled_variables`: loop retries submodels until dependencies are
  satisfied.
- `BatteryModelOptions.__init__` and `BaseBatteryModel.options`: option validation,
  tuple handling, incompatible-option exceptions.
- Lithium-ion submodel dispatch methods:
  `set_open_circuit_potential_submodel`, `set_sei_submodel`,
  `set_lithium_plating_submodel`, `set_particle_submodel`.
- `ParameterValues.update` and `_process_symbol`: type/branch-heavy processing of
  parameters, functions, input parameters, operators, and variables.
- `Mesh.__init__`, `combine_submeshes`, `add_ghost_meshes`: domain and geometry
  processing loops.
- `Discretisation.set_variable_slices`, `process_boundary_conditions`,
  `_process_symbol`, `create_mass_matrix`: state sizes, BC paths, spatial dispatch.
- `FiniteVolume.add_ghost_nodes`, `boundary_value_or_flux`, `shift`,
  `upwind_or_downwind`: rich line-level numerical control flow.
- `Simulation.solve`: experiment cycle/step control flow, infeasible-step paths,
  `save_at_cycles`, padding rest, termination checks.
- `BaseSolver.solve`, `_set_up_events`, `_get_discontinuity_start_end_indices`,
  `_check_events_with_initialization`: event and solver-control behavior.
- `ProcessedVariable.__call__` and `process_variable`: shape-based dispatch across
  0D/1D/2D/3D variables.

## Implemented M5 Def-Use QA Instances

- `experiment_step_string_def_use_intersection_suite`
  - Target: `pybamm.experiment.step.steps.string`.
- `experiment_base_step_init_def_use_intersection_suite`
  - Indirect path: public `pybamm.step.*` constructors call
    `BaseStep.__init__`.
- `parameter_values_update_def_use_intersection_suite`
  - Indirect path: `pybamm.ParameterValues(dict)` calls
    `ParameterValues.update`.
- `experiment_read_termination_def_use_intersection_suite`
  - Indirect path: `pybamm.Experiment(..., termination=...)` calls
    `Experiment.read_termination`.
- `fuzzy_dict_search_def_use_intersection_suite`
  - Indirect path: `pybamm.ParameterValues.search(...)` delegates to
    `FuzzyDict.search`.
- `binary_add_def_use_intersection_suite`
  - Indirect path: the PyBaMM symbolic `+` operator calls
    `pybamm.expression_tree.binary_operators.add`.
- `symbol_domains_setter_def_use_intersection_suite`
  - Expression-tree target. Indirect path: `pybamm.Symbol(...)` calls
    `Symbol.__init__`, which assigns `self.domains = ...` and invokes the
    `Symbol.domains` property setter.
- `primary_broadcast_check_domains_def_use_intersection_suite`
  - Expression-tree target. Indirect path: `pybamm.PrimaryBroadcast(...)` calls
    `PrimaryBroadcast.check_and_set_domains`.
- `interpolant_function_evaluate_def_use_intersection_suite`
  - Expression-tree target. Indirect path: `pybamm.Interpolant(...).evaluate()`
    enters inherited `Function.evaluate`, which calls
    `Interpolant._function_evaluate`.
- `state_vector_jac_same_vector_def_use_intersection_suite`
  - Expression-tree target with overlapping state-vector slices. Indirect path:
    `pybamm.StateVector(...).jac(variable)` dispatches through `Jacobian` to
    `StateVectorBase._jac_same_vector`.
- `interpolant_init_create_copy_def_use_intersection_suite`
  - Expression-tree target with 3D interpolant grids. Indirect path:
    prebuilt `pybamm.Interpolant` objects are copied with `create_copy(...)`,
    which constructs a new `Interpolant` through `Interpolant.__init__`.
- `domain_concatenation_init_def_use_intersection_suite`
  - Expression-tree target with domain-aware vectors and secondary-domain repeats.
    Indirect path: `pybamm.simplified_domain_concatenation(...)` constructs
    `DomainConcatenation.__init__`.
- `binary_subtract_cancellation_def_use_intersection_suite`
  - Direct expression-tree target: `pybamm.subtract(left, right)` on nested
    `(anchor + right) - right` cancellation shapes.
- `binary_multiply_division_cancellation_def_use_intersection_suite`
  - Direct expression-tree target: `pybamm.multiply(base, numerator / base)` with
    nested nonconstant operands built through constructors.
- `binary_divide_product_cancellation_def_use_intersection_suite`
  - Direct expression-tree target: `pybamm.divide(shared * tail, shared)` with
    nested nonconstant operands built through constructors.
- `battery_model_options_init_def_use_intersection_suite`
  - Hard project target: `BatteryModelOptions.__init__`.
  - Direct path: each test constructs `pybamm.BatteryModelOptions(options)` once
    with complex lithium-ion option dictionaries covering tuple options, thermal
    and geometry options, degradation options, MSMR choices, surface form, plating,
    contact resistance, and external-circuit modes.
- `base_model_build_coupled_variables_def_use_intersection_suite`
  - Hard project target: `BaseModel.build_coupled_variables`.
  - Indirect path: each test builds a `pybamm.BaseModel` with fake submodels whose
    coupled-variable dependencies require retry ordering, then calls
    `model.build_model()`, which calls the target method exactly once.
- `parameter_values_process_boundary_conditions_def_use_intersection_suite`
  - Hard project target: `ParameterValues.process_boundary_conditions`.
  - Indirect path: each test calls `ParameterValues.process_model(...)` on a
    parameterized `BaseModel` containing rhs equations, variables, initial
    conditions, and boundary conditions over `left`, `right`, `x_min`, and `x_max`;
    `process_model` calls the target method exactly once.
- `discretisation_process_dict_def_use_diverse_suite`
  - Hard project target: `Discretisation.process_dict`.
  - Direct path: each test calls the target once on a manually sliced
    zero-dimensional `Discretisation`, with dictionaries mixing scalar broadcasts,
    symbolic state-vector expressions, string-key diagnostics, scaled variables,
    and `ics=True`/`ics=False`. The parser enforces non-identical per-test def-use
    sets; validation observed 4 unique per-test sets.
- `base_model_set_initial_conditions_from_def_use_diverse_suite`
  - Hard project target: `BaseModel.set_initial_conditions_from`.
  - Direct path: each test calls the target once with dictionary-backed final-state
    data over single variables and concatenated domain variables, array ranks 0-4,
    discretised and non-discretised models, both return types, and both `inplace`
    settings. The parser enforces non-identical per-test def-use sets; validation
    observed 9 unique per-test sets.

## Implemented M2 Call-Coverage QA Instances

- `parameter_values_process_model_call_coverage_suite`
  - Target: `ParameterValues.process_model`.
  - M2.1 call coverage over the dynamic extent of each `process_model` call,
    including nested calls and taking the union across 10 tests.
  - Inputs use `ParameterValues` plus `BaseModel` objects with parameterized rhs
    equations, optional algebraic equations, optional boundary conditions, model
    variables, events, `FunctionParameter`, and non-extrapolating `Interpolant`
    expressions. The whitelist covers `parameter_values`, `base_model`, and
    `expression_tree` frames. Validation harvested 132 covered functions.
- `discretisation_process_model_call_coverage_suite`
  - Target: `Discretisation.process_model`.
  - M2.1 call coverage over zero-dimensional ODE/DAE models and finite-volume
    spatial diffusion models, varying algebraic equations, boundary conditions,
    nonlinear expressions, model checks, and in-place processing.
  - The whitelist covers discretisation, spatial methods, base-model checks,
    events, and expression-tree frames. Validation harvested 210 covered functions.
- `experiment_init_call_coverage_suite`
  - Target: `Experiment.__init__`.
  - M2.1 call coverage over heterogeneous string-defined and preconstructed steps,
    cycles, duplicate steps, scheduled start times, tags, periods, temperatures,
    step terminations, and global capacity/voltage/time terminations.
  - The whitelist covers experiment and experiment-step frames. Validation
    harvested 29 covered functions.
- `mesh_init_call_coverage_suite`
  - Target: `Mesh.__init__`.
  - M2.1 call coverage over uniform, Chebyshev, exponential, symbolic uniform,
    spherical-polar, multi-domain, and zero-dimensional mesh configurations.
  - The whitelist covers mesh implementations and expression-tree frames.
    Validation harvested 19 covered functions.
- `base_solver_solve_call_coverage_suite`
  - Target: `BaseSolver.solve`.
  - M2.1 call coverage over several SciPy integration methods and CasADi solver
    modes, varying time-grid forms, input parameters, multiple states, and
    terminal events.
  - The whitelist covers solver implementations, solutions, model/event access,
    and expression-tree evaluation/conversion. Validation harvested 107 covered
    functions.
- `simulation_build_call_coverage_suite`
  - Target: `Simulation.build`.
  - M2.1 call coverage across parameterized and unparameterized zero-dimensional
    models, already-discretised models, and parameterized finite-volume spatial
    models with linear and nonlinear equations.
  - The whitelist covers simulation orchestration, parameter processing, meshes,
    discretisation, spatial methods, base models, and expression trees. Validation
    harvested 251 covered functions.
- `process_variable_call_coverage_suite`
  - Target: `pybamm.solvers.processed_variable.process_variable`.
  - M2.1 call coverage over `Solution.__getitem__` dispatch for scalar expressions,
    nonlinear scalar functions, node-based spatial variables, and edge-based
    gradient variables.
  - The whitelist covers processed-variable implementations, base processed
    variables, solution access, and expression trees. Validation harvested 28
    covered functions.
- `lithium_ion_spm_init_call_coverage_suite`
  - Target: `pybamm.models.full_battery_models.lithium_ion.spm.SPM.__init__`.
  - M2.1 call coverage over ten directly constructed SPMs with default,
    distribution, x-full thermal, mechanics, alternate particle and kinetics,
    degradation, half-cell, multiphase, surface-form, and voltage-control options.
  - The whitelist covers full battery-model and base-model construction, particle,
    interface, and thermal submodels, and citations. Validation harvested 199
    covered functions.
- `quick_plot_init_call_coverage_suite`
  - Target: `pybamm.plotting.quick_plot.QuickPlot.__init__`.
  - M2.1 call coverage over scalar, grouped, 1D, and 2D outputs; long and short
    timescales; fixed, tight, and explicit limits; custom layout and styles;
    multiple solutions; and mixed Simulation/Solution inputs.
  - Solution construction occurs before the target dynamic extent. The whitelist
    covers QuickPlot, solution access, processed-variable implementations, and
    expression trees. Validation harvested 73 covered functions.

## Implemented M6 Exceptional-Behavior QA Instances

- `battery_model_options_exception_region_suite`
  - Target: `BatteryModelOptions.__init__`.
  - M6.1 exception-region partition over ten complex option dictionaries. Each
    test calls the target exactly once and intentionally leaves target exceptions
    uncaught.
  - Cases exercise default rewriting and compatibility interactions involving
    particle-size distributions, SEI film resistance, particle phases, contact
    resistance, x-full thermal models, and SEI on cracks.
  - Validation observed 4 safe tests and 6 crashing tests. Escaping exception
    kinds are `OptionError` and `NotImplementedError`.
- `discretisation_process_model_exception_region_suite`
  - Target: `Discretisation.process_model`.
  - M6.1 exception-region partition over zero-dimensional ODE/DAE models and
    finite-volume spatial models. Cases vary initial-condition completeness and
    bounds, equation/IC shapes, empty models, spatial-method availability, and
    boundary-condition keys.
  - Validation observed 4 safe tests and 6 crashing tests. Escaping exception
    kinds are `ModelError`, `DiscretisationError`, and `KeyError`.
- `simulation_solve_exception_region_suite`
  - Target: `Simulation.solve`.
  - M6.1 exception-region partition over ODE, algebraic, and input-parameter
    models with differing time grids, solve-only options, inputs, and concrete
    solvers. Model, simulation, and solver construction occurs before the target
    call.
  - Validation observed 3 safe tests and 7 crashing tests. Escaping exception
    kinds are `SolverError` and `ValueError`.
- `symbol_to_casadi_exception_diversity_suite`
  - Target: `Symbol.to_casadi`, including nested `CasadiConverter` calls.
  - M6.2 exception diversity over scalar, state-vector, state-vector-dot, input,
    binary, concatenation, and unsupported symbolic trees. Each test generically
    catches target exceptions, so all tests pass without encoding expected kinds.
  - Exception-trace validation observed `KeyError`, `TypeError`, and `ValueError`;
    this includes internally caught converter cache-miss `KeyError`s.
- `serialise_load_model_exception_diversity_suite`
  - Target: `Serialise.load_model`.
  - M6.2 exception diversity over valid serialized models and JSON files with
    missing schema fields, absent or invalid object paths, missing files, and
    malformed JSON. Each test generically catches target exceptions, so all pass.
  - Exception-trace validation observed `AttributeError`, `FileNotFoundError`,
    `JSONDecodeError`, `KeyError`, `ModuleNotFoundError`, and `TypeError`,
    including exceptions caught internally during class reconstruction.
- `mesh_init_exception_diversity_suite`
  - Target: `Mesh.__init__`.
  - M6.2 exception diversity over numeric, zero-dimensional, parameterized,
    symbolic, malformed, and incompletely configured geometries. Each test
    generically catches target exceptions, so all tests pass.
  - Exception-trace validation observed `AttributeError`, `DiscretisationError`,
    `GeometryError`, `KeyError`, `NotImplementedError`, and `TypeError`, including
    exceptions caught and translated during symbolic geometry evaluation.
- `parameter_values_process_symbol_exception_diversity_suite`
  - Target: the top-level call to `ParameterValues.process_symbol`, including its
    recursive `process_symbol` calls.
  - M6.2 exception diversity over known, missing, NaN, and invalid parameters;
    scalar, NaN, invalid, and callable function parameters; and nested symbolic
    expressions. Each test generically catches target exceptions, so all pass.
  - Exception-trace validation observed `KeyError`, `TypeError`, and `ValueError`,
    including internally caught processed-symbol cache misses.
- `solution_save_data_exception_diversity_suite`
  - Target: `Solution.save_data`.
  - M6.2 exception diversity across JSON, pickle, MATLAB, CSV, and invalid-format
    exports; missing variables; invalid MATLAB names; and spatial CSV data.
    Solutions are constructed before the target call and all target exceptions
    are generically caught by the tests.
  - Exception-trace validation observed `AttributeError`, `KeyError`, and
    `ValueError`, including internally caught solution-property lookups.
- `interpolant_init_exception_region_suite`
  - Target: `Interpolant.__init__`.
  - M6.1 exception-region partition over long 1D, 2D, and 3D grids with linear,
    cubic, and PCHIP interpolation; matrix-valued output; extrapolation settings;
    mismatched grid/value shapes; non-monotonic coordinates; and child-arity
    mismatches.
  - Validation observed 4 safe tests and 6 crashing tests. The concrete escaping
    exception kind is `ValueError`.
- `batch_study_solve_exception_region_suite`
  - Target: `BatchStudy.solve`.
  - M6.1 exception-region partition over paired and Cartesian studies with several
    nonlinear two-state models, input-parameter models, solver dictionaries,
    output-variable dictionaries, repeated solves, and varied time grids.
  - Validation observed 4 safe tests and 6 crashing tests. Escaping exception
    kinds are `SolverError` and `ZeroDivisionError`.
- `base_model_export_casadi_exception_region_suite`
  - Target: `BaseModel.export_casadi_objects`.
  - M6.1 exception-region partition over nonlinear ODE, input-parameter, DAE, and
    undiscretised spatial models with long requested-variable lists and differing
    input orders.
  - Validation observed 5 safe tests and 5 crashing tests. Escaping exception
    kinds are `ValueError`, `KeyError`, and `DiscretisationError`.
