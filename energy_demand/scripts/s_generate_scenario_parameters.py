"""Generate scenario paramters for every year
"""
import os
from collections import defaultdict
import pandas as pd
from energy_demand.technologies import diffusion_technologies

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

        path_file = os.path.join(path, "params_{}.{}".format(parameter_name, "csv"))

        regional_strategy_vary, reg_specific_crit = generate_general_parameter(
            regions=regions,
            narratives=strategy_vars[parameter_name]['narratives'],
            simulated_yrs=simulated_yrs,
            path=path_file)

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
    """Based on narrative input, calculate the parameter
    value for every modelled year
    """
    container = defaultdict(dict)
    reg_specific_crit = True
    entries = []

    # Iterate narratives
    for narrative in narratives:

        # -- Regional paramters of narrative step
        if not narrative['sig_midpoint']:
            sig_midpoint = 0
        if not narrative['sig_steepness']:
            sig_steepness = 1

        # Modelled years
        narrative_yrs = range(narrative['base_yr'], narrative['end_yr'] + 1, 1)

        # If not regional specific parameter
        if not narrative['regional_specific']:
            reg_specific_crit = False

            # Iterate every modelled year
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

                    # Sigmoid diffusion up to cy
                    elif narrative['diffusion_choice'] == 'sigmoid':

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

            # Iterate regions
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

                        # Sigmoid diffusion up to cy
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

                        entry = []
                        entry.append(region)
                        entry.append(curr_yr)
                        entry.append(change_cy)
                        entries.append(entry)

    # Write out to txt files
    # Create dataframe to store values of parameter
    col_names = ["region", "year", "value"]
    my_df = pd.DataFrame(entries, columns=col_names)
    my_df.to_csv(path, index=False) #Index prevents writing index rows

    return container, reg_specific_crit
