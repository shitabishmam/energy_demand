"""Generate scenario paramters for every year
"""
import os
from collections import defaultdict
from energy_demand.technologies import diffusion_technologies
from energy_demand import enduse_func

def calc_annual_switch_params(
        regional_strategy_vars,
        regions,
        rs_sig_param_tech,
        ss_sig_param_tech,
        is_sig_param_tech
    ):
    """
    """
    all_sim_yrs = range(2015, 2051)

    annual_tech_diff_params = {}

    for region in regions:
        annual_tech_diff_params[region] = {}

        # ------------------------
        # Submodel without sectors
        # ------------------------
        for enduse, region_tech_vals in rs_sig_param_tech.items():
            annual_tech_diff_params[region][enduse] = defaultdict(dict)

            if region_tech_vals[region] != []:
                for tech in region_tech_vals[region].keys():

                    # Sigmoid parameters
                    sig_param = region_tech_vals[region][tech]

                    # Iterate every year
                    for sim_yr in all_sim_yrs:

                        s_tech_p = enduse_func.get_service_diffusion(
                            sig_param, sim_yr)

                        # What about linear?? TODO??
                        annual_tech_diff_params[region][enduse][tech][sim_yr] = s_tech_p
            else:
                annual_tech_diff_params[region][enduse] = []

            dict(annual_tech_diff_params[region][enduse])

        # ------------------------
        # Submodels with sector
        # ------------------------
        for submodel in [ss_sig_param_tech, is_sig_param_tech]:

            for sector, enduse_region_tech_vals in submodel.items():
                annual_tech_diff_params[region][sector] = {}

                for enduse, reg_vals in enduse_region_tech_vals.items():
                    annual_tech_diff_params[region][sector][enduse] = defaultdict(dict)

                    if reg_vals[region] != []:
                        for tech in reg_vals[region].keys():

                            # Sigmoid parameters
                            sig_param = reg_vals[region][tech]

                            # Iterate every year
                            for sim_yr in all_sim_yrs:

                                s_tech_p = enduse_func.get_service_diffusion(
                                    sig_param, sim_yr)

                                # What about linear?? TODO??
                                annual_tech_diff_params[region][sector][enduse][tech][sim_yr] = s_tech_p
                    else:
                        annual_tech_diff_params[region][sector][enduse] = []

                    dict(annual_tech_diff_params[region][sector][enduse])

        # Add to regional_strategy_vars
        regional_strategy_vars[region]['annual_tech_diff_params'] = annual_tech_diff_params[region]

    return regional_strategy_vars

def generate_annual_param_vals(
        regions,
        strategy_vars,
        simulated_yrs,
        path=False
    ):
    """
    Calculate parameter values for every year based
    on defined narratives.

    Inputs
    -------
    regions : dict
        Regions
    strategy_vars : dict4
        Strategy variable infirmation
    simulated_yrs : list
        Simulated years
    path : str
        Path to local data

    Returns
    -------
    container_reg_param : dict
        Values for all simulated years for every region (all parameters for which values
        are provided for every region)
    container_non_reg_param : dict
        Values for all simulated years (all the same for very region)
    """
    container_reg_param = defaultdict(dict)
    container_non_reg_param = {}

    for parameter_name in strategy_vars.keys():

        path_file = os.path.join(
            path, "params_{}.{}".format(parameter_name, "csv"))

        # Calculate annual parameter value 
        regional_strategy_vary = generate_general_parameter(
            regions=regions,
            narratives=strategy_vars[parameter_name]['narratives'],
            simulated_yrs=simulated_yrs,
            path=path_file)

        # Test if regional specific or not based on first narrative
        for narrative in strategy_vars[parameter_name]['narratives'][:1]:
            reg_specific_crit = narrative['regional_specific']

        if reg_specific_crit:
            for region in regions:
                container_reg_param[region][parameter_name] = regional_strategy_vary[region]
        else:
            container_non_reg_param[parameter_name] = regional_strategy_vary

    return dict(container_reg_param), dict(container_non_reg_param)

def generate_general_parameter(
        regions,
        narratives,
        simulated_yrs,
        path=False
    ):
    """Based on narrative input, calculate
    the parameter value for every modelled year

    Arguments
    ---------
    regions : list
        Regions
    narratives : List
        List containing all narratives of how a model
        parameter changes over time
    simulated_yrs : list
        Simulated years

    Returns
    --------
    container : dict
        All model paramters containing either:
        - all values for each region and year
        - all values for each region
    """
    container = defaultdict(dict)
    #entries = []

    for narrative in narratives:

        # -- Regional paramters of narrative step
        if not narrative['sig_midpoint']:
            sig_midpoint = 0
        if not narrative['sig_steepness']:
            sig_steepness = 1

        # Modelled years
        narrative_yrs = range(narrative['base_yr'], narrative['end_yr'] + 1, 1)

        if not narrative['regional_specific']:

            for curr_yr in narrative_yrs:

                if curr_yr in simulated_yrs:

                    if narrative['diffusion_choice'] == 'linear':

                        lin_diff_factor = diffusion_technologies.linear_diff(
                            narrative['base_yr'],
                            curr_yr,
                            narrative['regional_vals_by'],
                            narrative['regional_vals_ey'],
                            narrative['end_yr'])

                        change_cy = lin_diff_factor

                    elif narrative['diffusion_choice'] == 'sigmoid': # Sigmoid diffusion

                        diff_value = narrative['regional_vals_ey'] - narrative['regional_vals_by']

                        sig_diff_factor = diffusion_technologies.sigmoid_diffusion(
                            narrative['base_yr'],
                            curr_yr,
                            narrative['end_yr'],
                            sig_midpoint,
                            sig_steepness)

                        change_cy = diff_value * sig_diff_factor

                    container[curr_yr] = change_cy
        else:
            for region in regions:

                # Iterate every modelled year
                for curr_yr in narrative_yrs:

                    if curr_yr in simulated_yrs:

                        if narrative['diffusion_choice'] == 'linear':

                            lin_diff_factor = diffusion_technologies.linear_diff(
                                narrative['base_yr'],
                                curr_yr,
                                narrative['regional_vals_by'][region],
                                narrative['regional_vals_ey'][region],
                                narrative['end_yr'])

                            change_cy = lin_diff_factor
                        elif narrative['diffusion_choice'] == 'sigmoid':

                            diff_value = narrative['regional_vals_ey'][region] - narrative['regional_vals_by'][region]

                            sig_diff_factor = diffusion_technologies.sigmoid_diffusion(
                                narrative['base_yr'],
                                curr_yr,
                                narrative['end_yr'],
                                sig_midpoint,
                                sig_steepness)

                            change_cy = diff_value * sig_diff_factor

                        container[region][curr_yr] = change_cy

                        '''entry = []
                        entry.append(region)
                        entry.append(curr_yr)
                        entry.append(change_cy)
                        entries.append(entry)'''

    # Write out to txt files
    '''# Create dataframe to store values of parameter
    col_names = ["region", "year", "value"]
    my_df = pd.DataFrame(entries, columns=col_names)
    my_df.to_csv(path, index=False) #Index prevents writing index rows'''
    return container