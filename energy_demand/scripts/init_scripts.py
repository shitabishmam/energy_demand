"""Script functions which are executed after
model installation and after each scenario definition
"""
import logging
from collections import defaultdict
import numpy as np

from energy_demand.geography import spatial_diffusion
from energy_demand.read_write import read_data
from energy_demand.scripts import (s_fuel_to_service, s_generate_sigmoid)
from energy_demand.technologies import fuel_service_switch
from energy_demand.scripts import s_generate_scenario_parameters

def get_all_narrative_timesteps(switches_list):
    """Read all defined narrative timesteps
    from switches

    Arguments
    ---------
    switches : list
        All different switches

    Returns
    -------
    narrative_timesteps : dict
        All defined timesteps in narrative per enduse
        provided as lists in dict
    """
    narrative_timesteps = {}

    '''for switches in switches_list:
        enduses = fuel_service_switch.get_all_enduses_of_switches(switches)

        enduses = fuel_service_switch.get_all_enduses_of_switches(switches_list)
        for enduse in enduses:
            narrative_timesteps[enduse] = set([])

            for switch in switches:
                if switch.enduse == enduse:
                    narrative_timesteps[enduse].add(switch.switch_yr)

            # Convert to list
            narrative_timesteps[enduse] = list(narrative_timesteps[enduse])

            # Sort
            narrative_timesteps[enduse].sort()'''
    # SNAKE
    enduses = fuel_service_switch.get_all_enduses_of_switches(switches_list)

    for enduse in enduses:
        narrative_timesteps[enduse] = set([])

        for switch in switches_list:
            if switch.enduse == enduse:
                narrative_timesteps[enduse].add(switch.switch_yr)

        # Convert to list
        narrative_timesteps[enduse] = list(narrative_timesteps[enduse])

        # Sort
        narrative_timesteps[enduse].sort()

    return narrative_timesteps

def create_spatial_diffusion_factors(
        strategy_vars,
        fuel_disagg,
        regions,
        real_values,
        speed_con_max,
        p_outlier=5
    ):
    """

    p_outlier : float or int
        Nr of min and max outliers to flatten

    TODO. improve
    """
    if strategy_vars['spatial_explicit_diffusion']['scenario_value']:

        # Define diffusion speed
        speed_con_max = speed_con_max

        # Criteria whether a spatially differentiated diffusion is applied depending on real_values
        crit_all_the_same = False
    else:

        # NEW If not spatial different, set speed_con_max to 1
        speed_con_max = 1

        # Define that the penetration levels are the same for every region
        crit_all_the_same = True

    f_reg, f_reg_norm, f_reg_norm_abs = spatial_diffusion.calc_spatially_diffusion_factors(
        regions=regions,
        fuel_disagg=fuel_disagg,
        real_values=real_values,
        low_congruence_crit=True,
        speed_con_max=speed_con_max,
        p_outlier=p_outlier)

    '''plot_fig_paper = False
    if plot_fig_paper:
        from energy_demand.plotting import result_mapping
        # Global value to distribute
        global_value = 50

        # Select spatial diffusion factor
        #diffusion_vals = f_reg                                  # not weighted
        diffusion_vals = f_reg_norm['ss_space_heating']         # Weighted with enduse
        #diffusion_vals = f_reg_norm_abs['rs_space_heating']    # Absolute distribution (only for capacity installements)

        path_shapefile_input = os.path.abspath(
            'C:/Users/cenv0553/ED/data/_raw_data/C_LAD_geography/lad_2016_uk_simplified.shp')

        result_mapping.plot_spatial_mapping_example(
            diffusion_vals=diffusion_vals,
            global_value=global_value,
            paths=data['result_paths'],
            regions=data['regions'],
            path_shapefile_input=path_shapefile_input,
            plotshow=True)'''

    return f_reg, f_reg_norm, f_reg_norm_abs, crit_all_the_same

def switch_calculations(
        simulated_yrs,
        data,
        f_reg,
        f_reg_norm,
        f_reg_norm_abs,
        crit_all_the_same
    ):
    """This function creates sigmoid diffusion values based
    on defined switches

    Arguments
    ----------
    simulated_yrs : list
        Simulated years
    data : dict
        Data container
    f_reg, f_reg_norm, f_reg_norm_abs : str
        Different spatial diffusion values
    crit_all_the_same : dict
        Criteria whether the diffusion is spatial explicit or not

    Returns
    -------
    annual_tech_diff_params : dict
        All values for every simluation year for every technology
    """
    # ---------------------------------------
    # Convert base year fuel input assumptions to energy service for every submodule
    # ---------------------------------------
    s_tech_by_p = {}
    s_fueltype_by_p = {}
    for submodel in data['assumptions'].submodels_names:
        for sector in data['sectors']['sectors'][submodel]:
            s_tech_by_p[sector], s_fueltype_by_p[sector] = s_fuel_to_service.get_s_fueltype_tech(
                data['enduses']['enduses'][submodel],
                data['lookups']['fueltypes'],
                data['assumptions'].fuel_tech_p_by,
                data['fuels']['fuels'][submodel],
                data['technologies'],
                sector)

    # Get all defined narrative timesteps of all switch types
    narrative_timesteps = {}
    narrative_timesteps.update(get_all_narrative_timesteps(data['assumptions'].service_switches))
    narrative_timesteps.update(get_all_narrative_timesteps(data['assumptions'].fuel_switches))
    narrative_timesteps.update(get_all_narrative_timesteps(data['assumptions'].capacity_switches))

    # ========================================================================================
    # Capacity switches
    #
    # Calculate service shares considering potential capacity installations
    # ========================================================================================

    # Convert globally defined switches to regional switches
    f_diffusion = f_reg_norm_abs #TODO EXPLAIN # Select diffusion value 

    reg_capacity_switches = global_to_reg_capacity_switch(
        data['regions'], data['assumptions'].capacity_switches, f_diffusion=f_diffusion)

    service_switches_incl_cap = fuel_service_switch.capacity_switch(
        narrative_timesteps,
        data['regions'],
        reg_capacity_switches,
        data['technologies'],
        data['fuels']['aggr_sector_fuels'],
        data['assumptions'].fuel_tech_p_by,
        data['assumptions'].base_yr) 

    print("--------finished capacity switches")
    # ======================================================================================
    # Service switches
    #
    # Get service shares of technologies for future year by considering
    # service switches. Potential capacity switches are used as inputs.
    #
    # Autocomplement defined service switches with technologies not
    # explicitly specified in switch on a global scale and distribute spatially
    # in oder that all technologies match up to 100% service share
    # ========================================================================================

    # Select spatial diffusion
    f_diffusion = f_reg_norm

    #share_s_tech_ey_p, switches_autocompleted = fuel_service_switch.autocomplete_switches(
    share_s_tech_ey_p = fuel_service_switch.autocomplete_switches(
        data['assumptions'].service_switches,
        data['assumptions'].specified_tech_enduse_by,
        s_tech_by_p,
        data['sectors']['enduse_sector_match'],
        crit_all_the_same=crit_all_the_same,
        regions=data['regions'],
        f_diffusion=f_diffusion,
        techs_affected_spatial_f=data['assumptions'].techs_affected_spatial_f,
        service_switches_from_capacity=service_switches_incl_cap)
    print("--------finished service switches")

    # ========================================================================================
    # Fuel switches
    #
    # Calculate sigmoid diffusion considering fuel switches
    # and service switches. As inputs, service (and thus also capacity switches) are used
    # ========================================================================================
    sig_param_tech = defaultdict(dict)

    # Get all enduses to iterate:
    #affected_enduses = set()
    #affected_sectors = []
    #
    #for sector, enduses_data in share_s_tech_ey_p.items():
    #    affected_sectors.append(sector)
    #    for enduse in enduses_data.keys():
    #        affected_enduses.add(enduse)

    #affected_enduses_fuel_switches = fuel_service_switch.get_all_enduses_of_switches(data['assumptions'].fuel_switches)
    ## for enduse in affected_enduses_fuel_switches:
    #    affected_enduses.add(enduse)
    #affected_enduses = list(affected_enduses)

    #for sector in affected_sectors:
    for submodel in data['assumptions'].submodels_names: #SNAKE REMOVE
        for enduse in data['enduses']['enduses'][submodel]:
            for sector in data['sectors']['sectors'][submodel]:
                
                print("FFF {}  {}  {}".format(submodel, enduse, sector))
                #print(share_s_tech_ey_p[sector][enduse])
                sig_param_tech[enduse][sector] = sig_param_calc_incl_fuel_switch(
                    narrative_timesteps,
                    data['assumptions'].base_yr,
                    data['assumptions'].crit_switch_happening,
                    data['technologies'],
                    enduse=enduse,
                    fuel_switches=data['assumptions'].fuel_switches,
                    #service_switches=switches_autocompleted[sector], #SNAKE
                    s_tech_by_p=s_tech_by_p[sector][enduse],
                    s_fueltype_by_p=s_fueltype_by_p[sector][enduse],
                    share_s_tech_ey_p=share_s_tech_ey_p,#,[sector][enduse],
                    fuel_tech_p_by=data['assumptions'].fuel_tech_p_by[enduse],
                    regions=data['regions'],
                    sector=sector,
                    crit_all_the_same=crit_all_the_same)

    # ------------------
    # Calculate annual values based on calculated sigmoid parameters
    # for every simulation year
    # ------------------
    annual_tech_diff_params = s_generate_scenario_parameters.calc_annual_switch_params(
        simulated_yrs,
        data['regions'],
        sig_param_tech)

    return annual_tech_diff_params

def spatial_explicit_modelling_strategy_vars(
        assumptions,
        regions,
        fuel_disagg,
        f_reg,
        f_reg_norm,
        f_reg_norm_abs
    ):
    """
    Spatial explicit modelling of scenario variables
    based on narratives. From UK factors to regional specific factors
    Convert strategy variables to regional variables

    Arguments
    ---------
    assumptions : dict
    regions

    """
    # Iterate strategy variables and calculate regional variable
    for var_name, strategy_var in assumptions.strategy_vars.items():
        logging.info("Spatially explicit diffusion modelling %s", var_name)

        new_narratives = []
        for narrative in strategy_var['narratives']:
            regional_vars_by = {}
            regional_vars_ey = {}
            if not narrative['regional_specific']:
                narrative['regional_vals_ey'] = narrative['value_ey']
                narrative['regional_vals_by'] = narrative['value_by']
                new_narratives.append(narrative)
            else:
                # Check whether scenario varaible is regionally modelled
                if var_name not in assumptions.spatially_modelled_vars:

                    # Variable is not spatially modelled
                    for region in regions:
                        regional_vars_ey[region] = float(narrative['value_ey'])
                        regional_vars_by[region] = float(narrative['value_by'])
                else:
                    if strategy_var['affected_enduse'] == []:
                        logging.info(
                            "For scenario var %s no affected enduse is defined. Thus speed is used for diffusion",
                                var_name)

                    # Get enduse specific fuel for each region
                    fuels_reg = spatial_diffusion.get_enduse_regs(
                        enduse=strategy_var['affected_enduse'],
                        fuels_disagg=[
                            fuel_disagg['rs_fuel_disagg'],
                            fuel_disagg['ss_fuel_disagg'],
                            fuel_disagg['is_fuel_disagg']])

                    # Calculate regional specific strategy variables values
                    reg_specific_variables_ey = spatial_diffusion.factor_improvements_single(
                        factor_uk=narrative['value_ey'],
                        regions=regions,
                        f_reg=f_reg,
                        f_reg_norm=f_reg_norm,
                        f_reg_norm_abs=f_reg_norm_abs,
                        fuel_regs_enduse=fuels_reg)

                    reg_specific_variables_by = spatial_diffusion.factor_improvements_single(
                        factor_uk=narrative['value_by'],
                        regions=regions,
                        f_reg=f_reg,
                        f_reg_norm=f_reg_norm,
                        f_reg_norm_abs=f_reg_norm_abs,
                        fuel_regs_enduse=fuels_reg)

                    # Add regional specific strategy variables values
                    for region in regions:
                        regional_vars_ey[region] = float(reg_specific_variables_ey[region])
                        regional_vars_by[region] = float(reg_specific_variables_by[region])

                narrative['regional_vals_by'] = regional_vars_by
                narrative['regional_vals_ey'] = regional_vars_ey
                new_narratives.append(narrative)

        assumptions.strategy_vars[var_name]['narratives'] = new_narratives

    return assumptions.strategy_vars

def global_to_reg_capacity_switch(
        regions,
        global_capactiy_switch,
        f_diffusion
    ):
    """Conversion of global capacity switch installations
    to regional installation

    Arguments
    ---------
    regions : list
        Regions
    global_capactiy_switch : float
        Global switch
    f_diffusion : dict

    Returns
    -------
    reg_capacity_switch : dict
        Regional capacity switch
    """
    reg_capacity_switch = {}

    # Get all affected enduses of capacity switches
    switch_enduses = fuel_service_switch.get_all_enduses_of_switches(
        global_capactiy_switch)

    for region in regions:
        reg_capacity_switch[region] = []

        for enduse in switch_enduses:

            # Get all capacity switches related to this enduse
            enduse_capacity_switches = fuel_service_switch.get_switches_of_enduse(
                global_capactiy_switch, enduse, crit_region=False)

            for switch in enduse_capacity_switches:

                global_capacity = switch.installed_capacity
                regional_capacity = global_capacity  * f_diffusion[switch.enduse][region]

                new_switch = read_data.CapacitySwitch(
                    enduse=switch.enduse,
                    technology_install=switch.technology_install,
                    switch_yr=switch.switch_yr,
                    installed_capacity=regional_capacity,
                    sector=switch.sector)

                reg_capacity_switch[region].append(new_switch)

    return reg_capacity_switch

def sum_across_all_submodels_regs(
        fueltypes_nr,
        regions,
        submodels
    ):
    """Calculate total sum of fuel per region
    """
    fuel_aggregated_regs = {}

    for region in regions:

        tot_reg = np.zeros((fueltypes_nr), dtype="float")

        for submodel_fuel_disagg in submodels:

            for fuel_sector_enduse in submodel_fuel_disagg[region].values():

                # Test if fuel for sector
                if isinstance(fuel_sector_enduse, dict):
                    for sector_fuel in fuel_sector_enduse.values():
                        tot_reg += sector_fuel
                else:
                    tot_reg += fuel_sector_enduse

        fuel_aggregated_regs[region] = tot_reg

    return fuel_aggregated_regs

def sum_across_sectors_all_regs(fuel_disagg_reg):
    """Sum fuel across all sectors for every region

    Arguments
    ---------
    fuel_disagg_reg : dict
        Fuel per region, sector and enduse

    Returns
    -------
    fuel_aggregated : dict
        Aggregated fuel per region and enduse
    """
    fuel_aggregated = {}
    for reg, entries in fuel_disagg_reg.items():
        fuel_aggregated[reg] = {}
        for enduse in entries:
            for sector in entries[enduse]:
                fuel_aggregated[reg][enduse] = 0

        for enduse in entries:
            for sector in entries[enduse]:
                fuel_aggregated[reg][enduse] += np.sum(entries[enduse][sector])

    return fuel_aggregated

def sig_param_calc_incl_fuel_switch(
        narrative_timesteps,
        base_yr,
        crit_switch_happening,
        technologies,
        enduse,
        fuel_switches,
        #service_switches,
        s_tech_by_p,
        s_fueltype_by_p,
        share_s_tech_ey_p,
        fuel_tech_p_by,
        regions=False,
        sector=False,
        crit_all_the_same=True
    ):
    """Calculate sigmoid diffusion paramaters considering
    fuel or service switches. Test if service switch and
    fuel switch are defined simultaneously (raise error if true).

    Arguments
    ---------
    narrative_timesteps : list
        All defined narrative years
    base_yr : int
        Base year
    technologies : dict
        technologies
    enduse : str
        enduse
    fuel_switches : dict
        fuel switches
    service_switches : dict
        service switches
    s_tech_by_p : dict
        Service share per technology in base year
    s_fueltype_by_p : dict
        Service share per fueltype for base year
    share_s_tech_ey_p : dict
        Service share per technology for end year
    fuel_tech_p_by : dict
        Fuel share per technology in base year
    regions : dict
        Regions

    Returns
    -------
    sig_param_tech : dict
        Sigmoid parameters for all affected technologies
    service_switches_out : list
        Service switches
    TODO
    """
    if sum(s_tech_by_p.values()) == 0: # no fuel is defined for enduse
        #print("no fuel is defined for enduse `{}` and sector `{}`".format(enduse, sector))
        sig_param_tech = {}
    elif sector not in list(share_s_tech_ey_p.keys()) or enduse not in list(share_s_tech_ey_p[sector].keys()):
        sig_param_tech = {}
    else:

        # Neyl added SNAKE (vorher ganz am anfang)
        if not sector:
            fuel_tech_p_by = fuel_tech_p_by
        else:
            fuel_tech_p_by = fuel_tech_p_by[sector]

        if share_s_tech_ey_p == {}:
            print("fmmmmmmmmm")
            pass
        else:
            print("why error {}  {}".format(sector, enduse))
            share_s_tech_ey_p = share_s_tech_ey_p[sector][enduse]

        # ----------------------------------------
        # Test if fuel switch is defined for enduse
        # Get affected technologies in fuel switch
        # ----------------------------------------
        _, crit_fuel_switch = s_generate_sigmoid.get_tech_installed(
            enduse, fuel_switches)

        # ------------------------------------------
        # Test if service switch is defined for enduse
        # ------------------------------------------ TODO WHY IS THIS REMOVED?
        #service_switches_enduse = fuel_service_switch.get_switches_of_enduse(
        #    service_switches, enduse)

        # ------------------------------------------
        # Initialisations
        # ------------------------------------------
        sig_param_tech = {}

        # Test if switch is defined
        crit_switch_service = fuel_service_switch.get_switch_criteria(
            enduse, sector, crit_switch_happening)

        if not crit_switch_service and not crit_fuel_switch:
            pass # no switches defined
        elif crit_switch_service and crit_fuel_switch:
            raise Exception("Error: a fuel and service switch is defined at the same time %s", enduse)
        else:

            # Only calculate for one reg
            any_region = regions[0]

            # Years of narrative
            switch_yrs = narrative_timesteps[enduse]

            # Iterate over years defined in narrative
            for switch_yr_cnt, switch_yr in enumerate(switch_yrs):

                sig_param_tech[switch_yr] = {}

                # ------------------------------------------
                # SERVICE switch
                #
                # Calculate service shares considering service
                # switches and the diffusion parameters
                # ------------------------------------------
                if crit_switch_service:
                    print("+++++++++ SERVICE SWITCH")
                    # Calculate only from service switch
                    s_tech_switched_p = share_s_tech_ey_p

                    # Calculate sigmoid diffusion parameters
                    l_values_sig = s_generate_sigmoid.get_l_values(
                        technologies=technologies,
                        technologies_to_consider=s_tech_by_p.keys(),
                        regions=regions)
                elif crit_fuel_switch:
                    s_tech_switched_p = defaultdict(dict)
                    l_values_sig = {}
                else:
                    s_tech_switched_p = defaultdict(dict)

                print(
                    "Switch criteria: Service switch: %s, fuel switch: %s",
                    crit_switch_service, crit_fuel_switch)

                # ------------------------------------------
                # FUEL switch
                # ------------------------------------------
                if crit_fuel_switch:
                    """
                    Calculate future service share after fuel switches
                    and calculte sigmoid diffusion paramters.
                    """
                    print("+++++++++ FUEL SWITCH")
                    # Get fuel switches of enduse and switch_yr
                    enduse_fuel_switches = fuel_service_switch.get_switches_of_enduse(
                        fuel_switches, enduse, switch_yr, crit_region=False) #NEW TODO crit_region=False

                    if crit_all_the_same:

                        # Calculate service demand after fuel switches for each technology
                        s_tech_switched_p_values_all_regs = s_generate_sigmoid.calc_service_fuel_switched(
                            enduse_fuel_switches,
                            technologies,
                            s_fueltype_by_p,
                            s_tech_by_p,
                            fuel_tech_p_by,
                            'actual_switch')

                        # Calculate L for every technology for sigmod diffusion
                        l_values_all_regs = s_generate_sigmoid.tech_l_sigmoid(
                            s_tech_switched_p_values_all_regs,
                            enduse_fuel_switches,
                            technologies,
                            s_tech_by_p.keys(),
                            s_fueltype_by_p,
                            s_tech_by_p,
                            fuel_tech_p_by)

                        for region in regions:
                            s_tech_switched_p[region][switch_yr] = s_tech_switched_p_values_all_regs
                            l_values_sig[region] = l_values_all_regs
                    else:
                        for region in regions:

                            # Calculate service demand after fuel switches for each technology
                            s_tech_switched_p[region][switch_yr] = s_generate_sigmoid.calc_service_fuel_switched(
                                enduse_fuel_switches,
                                technologies,
                                s_fueltype_by_p,
                                s_tech_by_p,
                                fuel_tech_p_by,
                                'actual_switch')

                            # Calculate L for every technology for sigmod diffusion
                            l_values_sig[region] = s_generate_sigmoid.tech_l_sigmoid(
                                s_tech_switched_p[region][switch_yr],
                                enduse_fuel_switches,
                                technologies,
                                s_tech_by_p.keys(),
                                s_fueltype_by_p,
                                s_tech_by_p,
                                fuel_tech_p_by)

                # -----------------------------------------------
                # Calculates parameters for sigmoid diffusion of
                # technologies which are switched to/installed.
                # -----------------------------------------------
                print("---------- switches %s %s %s", enduse, crit_switch_service, crit_fuel_switch)

                if crit_all_the_same:

                    # -------------------------
                    # Get starting year of narrative story
                    # -------------------------
                    if switch_yr_cnt == 0: 
                        switch_yr_start = base_yr
                    else: # If more than one switch_yr, then take previous year
                        switch_yr_start = switch_yrs[switch_yr_cnt - 1]

                    # Calculate for one region
                    sig_param_tech_all_regs_value = s_generate_sigmoid.tech_sigmoid_parameters(
                        switch_yr,
                        switch_yr_start,
                        technologies,
                        l_values_sig[any_region],
                        s_tech_by_p,
                        s_tech_switched_p[any_region][switch_yr])

                    for region in regions:
                        sig_param_tech[switch_yr][region] = sig_param_tech_all_regs_value
                else:
                    for region in regions:
                        sig_param_tech[switch_yr][region] = s_generate_sigmoid.tech_sigmoid_parameters(
                            switch_yr,
                            switch_yr_start,
                            technologies,
                            l_values_sig[region],
                            s_tech_by_p,
                            s_tech_switched_p[region][switch_yr])

    return sig_param_tech

def get_sector_switches(sector_to_match, switches):
    """Get all switches of a sector if the switches are
    defined specifically for a sector. If the switches are
    not specifically for a sector, return all switches

    Arguments
    ----------
    sector_to_match : int
        Sector to find switches
    switches : list
        Switches

    Returns
    -------
    switches : list
        Switches of sector
    """
    # Get all sectors for this enduse
    switches_out = set([])

    for switch in switches:

        # If sector is None
        '''if not switch.sector and not sector_to_match:
            switches.add(switch)
        else:'''

        if switch.sector == sector_to_match:
            switches_out.add(switch)
        elif not switch.sector: # Not defined specifically for sectors and add all
            switches_out.add(switch)
        else:
            pass

    return list(switches_out)

def get_sector__enduse_switches(sector_to_match, enduse_to_match, switches):
    """Get all switches of a sector if the switches are
    defined specifically for a sector. If the switches are
    not specifically for a sector, return all switches

    Arguments
    ----------
    sector_to_match : int
        Sector to find switches
    switches : list
        Switches

    Returns
    -------
    switches : list
        Switches of sector
    """
    # Get all sectors for this enduse
    switches_out = set([])

    for switch in switches:

        # If sector is None
        '''if not switch.sector and not sector_to_match:
            switches.add(switch)
        else:'''

        if switch.sector == sector_to_match and switch.enduse == enduse_to_match:
            switches_out.add(switch)
        elif not switch.sector and switch.enduse == enduse_to_match: # Not defined specifically for sectors and add all
            switches_out.add(switch)
        else:
            pass

    return list(switches_out)