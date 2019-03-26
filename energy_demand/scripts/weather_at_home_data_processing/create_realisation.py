"""Create weather realisation
"""
import os
import pandas as pd
import numpy as np

from energy_demand.read_write import write_data
from energy_demand.basic import basic_functions

def remap_year(year):
    """Remap year"""

    if year in range(2015, 2020):
        year_remapped = 2020
    elif year == 2050:
        year_remapped = 2049
    else:
        year_remapped = year

    return year_remapped

def generate_weather_at_home_realisation(
        path_results,
        path_stiching_table,
        scenarios=range(100),
        years=range(2015, 2051)
    ):
    """
    Before running, generate 2015 remapped data
    """
    # Create result path
    result_path_realizations = os.path.join(path_results, "_realizations")
    result_path_realizations = "C:/AAA"
    basic_functions.create_folder(result_path_realizations)

    # Read in stiching table
    df_path_stiching_table = pd.read_table(path_stiching_table, sep=" ")

    # Set year as index
    df_path_stiching_table = df_path_stiching_table.set_index('year')

    # Realisations
    realisations = list(df_path_stiching_table.columns)

    attributes = ['rsds', 'wss']

    for scenario_nr in scenarios:
        realisation = realisations[scenario_nr]

        for attribute in attributes:
            columns = ['timestep', 'station_id', 'longitude', 'latitude', 'yearday', attribute]

            print("... creating weather data for realisation " + str(realisation), flush=True)
            realisation_out = []

            for sim_yr in years:
                #print("   ... year: " + str(sim_yr), flush=True)
                year = remap_year(sim_yr)
                stiching_name = df_path_stiching_table[realisation][year]
                path_weather_data = os.path.join(path_results, '_cleaned_csv', str(year), stiching_name)
                
                path_attribute = os.path.join(path_weather_data, "{}.npy".format(attribute))
                path_attribute_stations = os.path.join(path_results, '_cleaned_csv', "stations_{}.csv".format(attribute))

                attribute_data = np.load(path_attribute)

                stations = pd.read_csv(path_attribute_stations)
                stations['timestep'] = sim_yr
                nr_stations_array = len(list(stations.values))

                for station_cnt in range(nr_stations_array):
                    attribute_station = attribute_data[station_cnt]
                    station_id = stations.loc[station_cnt]['station_id']
                    station_long = stations.loc[station_cnt]['longitude']
                    station_lat = stations.loc[station_cnt]['latitude']
                    for yearday in range(365):
                        realisation_out.append(
                            [sim_yr, station_id, station_long, station_lat, yearday, attribute_station[yearday]])

            # Write data to csv
            print("...writing out", flush=True)
            df = pd.DataFrame(realisation_out, columns=columns)
            path_out_csv = os.path.join(result_path_realizations, "weather_data_{}__{}.csv".format(realisation, attribute))
            df.to_csv(path_out_csv, index=False)
