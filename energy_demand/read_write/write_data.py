"""Functions which are writing data
"""
import os
import logging
import numpy as np
import configparser
from energy_demand.basic import basic_functions, conversions
from energy_demand.geography import write_shp
import yaml
from yaml import Loader, Dumper
import collections
import csv

def write_array_to_txt(path_result, array):
    """Write scenario population for a year to txt file
    """
    np.savetxt(path_result, array, delimiter=',')

def write_pop(sim_yr, path_result, pop_y):
    """Write scenario population for a year to txt file

    Parameters
    ----------
    sim_yr : int
        Simulation year
    path_result : str
        Path to resulting folder
    pop_y : array
        Population of simulation year
    """
    path_file = os.path.join(
        path_result, "pop__{}__{}".format(sim_yr, ".txt"))

    np.savetxt(path_file, pop_y, delimiter=',')

def create_shp_results(data, results_container, paths, lookups, lu_reg):
    """Create csv file and merge with shape

    Arguments
    ---------
    results_container : dict
        Data container
    paths : dict
        Paths
    lookups : dict
        Lookups
    lu_reg : list
        Region in a list with order how they are stored in result array
    """
    logging.info("... create result shapefiles")
    print("... create result shapefiles")

    # ------------------------------------
    # Create shapefile with load factors
    # ------------------------------------
    field_names, csv_results = [], []
    # Iterate fueltpyes and years and add as attributes
    for year in results_container['load_factors_y'].keys():
        for fueltype in range(lookups['fueltypes_nr']):
            field_names.append('y_{}_{}'.format(year, fueltype))
            csv_results.append(
                basic_functions.array_to_dict(
                    results_container['load_factors_y'][year][fueltype], lu_reg))

        # Add population
        field_names.append('pop_{}'.format(year))
        csv_results.append(basic_functions.array_to_dict(data['scenario_data']['population'][year], lu_reg))

    write_shp.write_result_shapefile(
        paths['lad_shapefile'],
        os.path.join(paths['data_results_shapefiles'], 'lf_max_y'),
        field_names,
        csv_results)

    # ------------------------------------
    # Create shapefile with yearly total fuel all enduses
    # ------------------------------------
    field_names, csv_results = [], []

    # Iterate fueltpyes and years and add as attributes
    for year in results_container['results_every_year'].keys():
        for fueltype in range(lookups['fueltypes_nr']):

            # Calculate yearly sum
            yearly_sum = np.sum(results_container['results_every_year'][year][fueltype], axis=1)
            yearly_sum_gw = yearly_sum

            field_names.append('y_{}_{}'.format(year, fueltype))
            csv_results.append(
                basic_functions.array_to_dict(yearly_sum_gw, lu_reg))

        # Add population
        field_names.append('pop_{}'.format(year))
        csv_results.append(
            basic_functions.array_to_dict(data['scenario_data']['population'][year], lu_reg))

    write_shp.write_result_shapefile(
        paths['lad_shapefile'],
        os.path.join(paths['data_results_shapefiles'], 'fuel_y'),
        field_names,
        csv_results)

    # ------------------------------------
    # Create shapefile with peak demand in gwh
    # ------------------------------------
    #

    # ------------------------------------
    # Create shapefile with
    # ------------------------------------
    logging.info("... finished generating shapefiles")

def dump(data, file_path):
    """Write plain data to a file as yaml

    Parameters
    ----------
    file_path : str
        The path of the configuration file to write
    data
        Data to write (should be lists, dicts and simple values)
    """
    with open(file_path, 'w') as file_handle:
        return yaml.dump(data, file_handle, Dumper=Dumper, default_flow_style=False)

def write_yaml_output_keynames(path_yaml, key_names):
    """Generate YAML file where the outputs
    for the sector model can be easily copied

    Arguments
    ----------
    path_yaml : str
        Path where yaml file is saved
    key_names : dict
        Names of keys of supply_out dict
    """
    list_to_dump = []

    for key_name in key_names:
        dict_to_dump = {
            'name': key_name,
            'spatial_resolution': 'lad_uk_2016',
            'temporal_resolution': 'hourly',
            'units': 'GWh'
        }

        list_to_dump.append(dict_to_dump)

    dump(list_to_dump, path_yaml)

def write_yaml_param_scenario(path_yaml, dict_to_dump):
    """Write all strategy variables to YAML file

    Arguments
    ----------
    path_yaml : str
        Path where yaml file is saved
    dict_to_dump : dict
        Dict which is written to YAML
    """
    list_to_dump = [dict_to_dump]
    dump(list_to_dump, path_yaml)

def write_yaml_param_complete(path_yaml, dict_to_dump):
    """Write all strategy variables to YAML file

    Arguments
    ----------
    path_yaml : str
        Path where yaml file is saved
    dict_to_dump : dict
        Dict which is written to YAML
    """
    list_to_dump = []

    for paramter_info in dict_to_dump:
        dump_dict = {}
        dump_dict['suggested_range'] = paramter_info['suggested_range']
        dump_dict['absolute_range'] = paramter_info['absolute_range']
        dump_dict['description'] = paramter_info['description']
        dump_dict['name'] = paramter_info['name']
        dump_dict['default_value'] = paramter_info['default_value']
        dump_dict['units'] = paramter_info['units']
        list_to_dump.append(dump_dict)

    # Dump list
    dump(list_to_dump, path_yaml)

def write_simulation_inifile(path, sim_param, enduses, assumptions, reg_nrs, regions):
    """Create .ini file with simulation parameters which ared
    used to read in correctly the simulation results

    Arguments
    ---------
    path : str
        Path to result foder
    sim_param : dict
        Contains all information necessary to plot results
    enduses : dict
        Enduses
    assumptions : dict
        Assumptions
    reg_nrs : int
        Number of regions
    regions : dict
        Regions

    """
    path_ini_file = os.path.join(
        path, 'model_run_sim_param.ini')

    config = configparser.ConfigParser()

    config.add_section('SIM_PARAM')
    config['SIM_PARAM']['reg_nrs'] = str(reg_nrs)
    config['SIM_PARAM']['base_yr'] = str(sim_param['base_yr'])
    config['SIM_PARAM']['simulated_yrs'] = str(sim_param['simulated_yrs'])
    config['SIM_PARAM']['model_yearhours_nrs'] = str(assumptions['model_yearhours_nrs'])
    config['SIM_PARAM']['model_yeardays_nrs'] = str(assumptions['model_yeardays_nrs'])

    # ----------------------------
    # Other information to pass to plotting and summing function
    # ----------------------------
    config.add_section('ENDUSES')

    #convert list to strings
    config['ENDUSES']['rs_all_enduses'] = str(enduses['rs_all_enduses'])
    config['ENDUSES']['ss_all_enduses'] = str(enduses['ss_all_enduses'])
    config['ENDUSES']['is_all_enduses'] = str(enduses['is_all_enduses'])

    config.add_section('REGIONS')
    config['REGIONS']['lu_reg'] = str(regions)

    with open(path_ini_file, 'w') as f:
        config.write(f)
    pass

def write_lf(path_result_folder, path_new_folder, parameters, model_results, file_name):
    """Write numpy array to txt file

    """
    # Create folder and subolder
    basic_functions.create_folder(path_result_folder)
    path_result_sub_folder = os.path.join(path_result_folder, path_new_folder)
    basic_functions.create_folder(path_result_sub_folder)

    # Create full file_name
    for name_param in parameters:
        file_name += str("__") + str(name_param)

    # Generate full path
    path_file = os.path.join(path_result_sub_folder, file_name)

    # Write array to txt (only 2 dimensinal array possible)
    for fueltype_nr, fuel_fueltype in enumerate(model_results):
        path_file_fueltype = path_file + "__" + str(fueltype_nr) + "__" + ".txt"
        np.savetxt(path_file_fueltype, fuel_fueltype, delimiter=',')

    pass

def write_supply_results(
        sim_yr,
        name_new_folder,
        path_result,
        model_results,
        file_name
    ):
    """Write model results to text as follows:

        name of file: name_year_fueltype
        array in file:  np.array(region, timesteps)

    Arguments
    ---------
    sim_yr : int
        Simulation year
    name_new_folder : str
        Name of folder to create
    path_result : str
        Paths
    model_results : array
        Results to store to txt
    file_name : str
        File name
    """
    # Create folder and subolder
    path_result_sub_folder = os.path.join(path_result, name_new_folder)
    basic_functions.create_folder(path_result_sub_folder)

    # Write to txt
    for fueltype_nr, fuel in enumerate(model_results):
        path_file = os.path.join(
            path_result_sub_folder,
            "{}__{}__{}__{}".format(
                file_name,
                sim_yr,
                fueltype_nr,
                ".txt"))

        np.savetxt(path_file, fuel, delimiter=',')

def write_enduse_specific(sim_yr, path_result, model_results, filename):
    """Write out enduse specific results for every hour

    Store numpy array to txt
    """
    # Create folder for model simulation year
    basic_functions.create_folder(path_result)
    basic_functions.create_folder(path_result, "enduse_specific_results")

     # Write to txt
    for enduse, fuel in model_results.items():
        for fueltype_nr, fuel_fueltype in enumerate(fuel):
            path_file = os.path.join(
                os.path.join(path_result, "enduse_specific_results"),
                "{}__{}__{}__{}__{}".format(filename, enduse, sim_yr, fueltype_nr, ".txt"))
            logging.debug("... Write to file: {}  {}  {} ".format(sim_yr, enduse, np.sum(fueltype_nr)))
            np.savetxt(path_file, fuel_fueltype, delimiter=',')

    return

def write_max_results(sim_yr, path_result, result_foldername, model_results, filename):
    """Store yearly model resuls to txt

    Store numpy array to txt
    """
    # Create folder and subolder
    basic_functions.create_folder(path_result)
    basic_functions.create_folder(path_result, result_foldername)

    # Write to txt
    path_file = os.path.join(
        os.path.join(path_result, result_foldername),
        "{}__{}__{}".format(filename, sim_yr, ".txt"))
    np.savetxt(path_file, model_results, delimiter=',')

    return

def create_txt_shapes(
        end_use,
        path_txt_shapes,
        shape_peak_dh,
        shape_non_peak_y_dh,
        shape_peak_yd_factor,
        shape_non_peak_yd
    ):
    """Function collecting functions to write out arrays
    to txt files
    """
    write_array_to_txt(
        os.path.join(
            path_txt_shapes,
            str(end_use) + str("__") + str('shape_peak_dh') + str('.txt')),
        shape_peak_dh)

    write_array_to_txt(
        os.path.join(
            path_txt_shapes,
            str(end_use) + str("__") + str('shape_non_peak_y_dh') + str('.txt')),
        shape_non_peak_y_dh)

    write_array_to_txt(
        os.path.join(
            path_txt_shapes,
            str(end_use) + str("__") + str('shape_peak_yd_factor') + str('.txt')),
        np.array([shape_peak_yd_factor]))

    write_array_to_txt(
        os.path.join(
            path_txt_shapes,
            str(end_use) + str("__") + str('shape_non_peak_yd') + str('.txt')),
        shape_non_peak_yd)

    return


def create_csv_file(path, rows):
    """
    """
    with open(path, 'w') as csvfile:

        filewriter = csv.writer(
            csvfile,
            delimiter=',',
            quotechar='|',
            quoting=csv.QUOTE_MINIMAL)

        for row in rows:
            filewriter.writerow(row)
            #filewriter.writerow(['Spam', 'Lovely Spam', 'Wonderful Spam'])
