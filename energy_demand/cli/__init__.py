"""Provides an entry point from the command line to the energy demand model
"""
import os
import sys
from pkg_resources import Requirement
from pkg_resources import resource_filename
from argparse import ArgumentParser
import energy_demand
from energy_demand.main import energy_demand_model
from energy_demand.read_write import data_loader
from energy_demand.assumptions import assumptions
from energy_demand.scripts._execute_all_scripts import post_install_setup
from energy_demand.scripts._execute_all_scripts import scenario_initalisation
from energy_demand.read_write import read_data
from energy_demand.dwelling_stock import dw_stock
from energy_demand.plotting import plotting_results

def run_model(args):
    """
    Main function to run the energy demand model from the command line

    Notes
    -----
    - path_main is the path to the local data e.g. that stored in the package
    - local_data_path is the path to the restricted data which must be provided
    to the model

    """
    #Subfolder where module is installed
    path_main = resource_filename(Requirement.parse("energy_demand"), "")
    local_data_path = args.data_folder

    print("path_main:       " + str(path_main))
    print("local_data_path: " + str(local_data_path))

    # Load data
    data = {}
    data['paths'] = data_loader.load_paths(path_main)
    data['local_paths'] = data_loader.load_local_paths(local_data_path)
    data = data_loader.load_fuels(data)
    data = data_loader.load_data_tech_profiles(data)
    data = data_loader.load_data_profiles(data)
    data['assumptions'] = assumptions.load_assumptions(data)
    data['weather_stations'], data['temperature_data'] = data_loader.load_data_temperatures(
        data['local_paths']
        )

    # >>>>>>>>>>>>>>>DUMMY DATA GENERATION
    data = data_loader.dummy_data_generation(data)
    # <<<<<<<<<<<<<<<<<< FINISHED DUMMY GENERATION DATA

    # Load data from script calculations
    data = read_data.load_script_data(data)

    # Generate dwelling stocks over whole simulation period
    data['rs_dw_stock'] = dw_stock.rs_dw_stock(data['lu_reg'], data)
    data['ss_dw_stock'] = dw_stock.ss_dw_stock(data['lu_reg'], data)

    _, results = energy_demand_model(data)

    print(results)
    results_every_year = [results]
    plotting_results.plot_stacked_Country_end_use(
        "figure_stacked_country01.pdf", data, results_every_year, data['rs_all_enduses'], 'rs_tot_fuel_y_enduse_specific_h')
    plotting_results.plot_stacked_Country_end_use(
        "figure_stacked_country02.pdf", data, results_every_year, data['ss_all_enduses'], 'ss_tot_fuel_enduse_specific_h')

    print("Finished energy demand model from command line execution")

def parse_arguments():
    """Parse command line arguments

    Returns
    =======
    :class:`argparse.ArgumentParser`

    """
    parser = ArgumentParser(description='Command line tools for energy_demand')
    parser.add_argument('-V', '--version',
                        action='version',
                        version="energy_demand " + energy_demand.__version__,
                        help='show the current version of energy_demand')

    subparsers = parser.add_subparsers()

    # Run main model
    parser_run = subparsers.add_parser(
        'run',
        help='Run the model'
        )
    parser_run.add_argument(
        '-d',
        '--data_folder',
        default='./processed_data',
        help='Path to the input data folder'
        )
    parser_run.set_defaults(func=run_model)

    # Initialisation of energy demand model (processing raw files)
    parser_init = subparsers.add_parser(
        'post_install_setup',
        help='Executes the raw reading functions'
        )
    parser_init.add_argument(
        '-d',
        '--data_energy_demand',
        default='./energy_demand_data',
        help='Path to the input data folder'
        )

    parser_init.set_defaults(func=post_install_setup)

    # Scenario initialisation
    parser_init = subparsers.add_parser(
        'scenario_initialisation',
        help='Needs to be initialised')

    parser_init.add_argument(
        '-d',
        '--data_energy_demand',
        default='./data_energy_demand',
        help='Path to main data folder'
        )

    parser_init.set_defaults(func=scenario_initalisation)

    return parser

def main(arguments=None):
    """Parse args and run
    """
    parser = parse_arguments()
    args = parser.parse_args(arguments)

    if 'func' in args:
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main(sys.argv[1:])