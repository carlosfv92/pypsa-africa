# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: : 2022 PyPSA-Earth Authors
#
# coding: utf-8
"""
Execute a scenario optimization

Run iteratively the workflow under different conditions
and store the results in specific folders
"""
import os
import shutil
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pypsa
import xarray as xr
from _helpers import mock_snakemake, sets_path_to_root, to_csv_nafix
from build_test_configs import create_test_config
from ruamel.yaml import YAML
from shapely.validation import make_valid


def _multi_index_scen(rulename, keys):
    return pd.MultiIndex.from_product([[rulename], keys], names=["rule", "key"])


def _mock_snakemake(rule, **kwargs):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    snakemake = mock_snakemake(rule, **kwargs)
    sets_path_to_root("pypsa-earth")
    return snakemake


def generate_scenario_by_country(path_base, country_list):
    "Utility function to generate multiple scenario configs"

    from _helpers import three_2_two_digits_country
    from download_osm_data import create_country_list

    clean_country_list = create_country_list(country_list)

    df_landlocked = pd.read_csv(
        "https://raw.githubusercontent.com/openclimatedata/countrygroups/main/data/lldc.csv"
    )
    df_landlocked["countries"] = df_landlocked.Code.map(three_2_two_digits_country)

    n_clusters = {
        "MG": 4,  # Africa
        "BF": 1,
        "BI": 1,
        "BJ": 2,
        "DJ": 1,
        "GM": 2,
        "LR": 2,
        "LS": 3,
        "SL": 1,
        "TG": 1,
        "CG": 2,
        "ER": 1,
        "SS": 1,
        "ML": 1,
        "TD": 2,
        "CF": 1,
        "ER": 1,  # Africa
        "GF": 3,  # South America
        "SR": 2,  # South America
        "SG": 1,  # Asia
        "FJ": 4,  # Oceania
    }

    for c in clean_country_list:

        n_cluster = "5"
        if c in n_clusters.keys():
            n_cluster = str(n_clusters[c])

        modify_dict = {"countries": [c], "scenario": {"clusters": [n_cluster]}}
        if df_landlocked["countries"].str.contains(c).any():
            modify_dict["electricity"] = {
                "renewable_carriers": ["solar", "onwind", "hydro"]
            }

        create_test_config(path_base, modify_dict, f"configs/scenarios/{c}.yaml")


def collect_basic_osm_stats(path, rulename, header):
    if os.path.exists(path) and (os.stat(path).st_size > 0):
        df = gpd.read_file(path)
        n_elem = len(df)

        return pd.DataFrame(
            [n_elem], columns=_multi_index_scen(rulename, [header + "-size"])
        )

    else:
        return pd.DataFrame()


def collect_network_osm_stats(path, rulename, header, metric_crs="EPSG:3857"):
    if os.path.exists(path) and (os.stat(path).st_size > 0):
        try:
            df = gpd.read_file(path)
            n_elem = len(df)
            obj_length = (
                df["geometry"].apply(make_valid).to_crs(crs=metric_crs).geometry.length
            )
            len_obj = np.nansum(obj_length * df.circuits)

            len_dc_obj = 0.0
            if "frequency" in df.columns:
                coerced_vals = pd.to_numeric(df.frequency, errors="coerce")
                idx_dc = coerced_vals[coerced_vals.as_type(int) == 0].index
                len_dc_obj = float(obj_length.loc[idx_dc].sum())

            return pd.DataFrame(
                [[n_elem, len_obj, len_dc_obj]],
                columns=_multi_index_scen(
                    rulename,
                    [header + "-" + k for k in ["size", "length", "length_dc"]],
                ),
            )
        except Exception as inst:
            print(inst)
            return pd.DataFrame()
    else:
        return pd.DataFrame()


def collect_osm_stats(rulename, **kwargs):
    metric_crs = kwargs.pop("metric_crs", "EPSG:3857")
    only_basic = kwargs.pop("only_basic", False)

    df_list = []

    for k, v in kwargs.items():
        if not only_basic and (k in ["lines", "cables"]):
            df_list.append(
                collect_network_osm_stats(v, rulename, k, metric_crs=metric_crs)
            )
        else:
            df_list.append(collect_basic_osm_stats(v, rulename, k))

    return pd.concat(df_list, axis=1)


def collect_raw_osm_stats(rulename="download_osm_data", metric_crs="EPSG:3857"):
    snakemake = _mock_snakemake("download_osm_data")

    options_raw = dict(snakemake.output)
    options_raw.pop("generators_csv")

    return collect_osm_stats(
        rulename, only_basic=True, metric_crs=metric_crs, **options_raw
    )


def collect_clean_osm_stats(rulename="clean_osm_data", metric_crs="EPSG:3857"):
    snakemake = _mock_snakemake("clean_osm_data")

    options_clean = dict(snakemake.output)
    options_clean.pop("generators_csv")

    return collect_osm_stats(rulename, metric_crs=metric_crs, **options_clean)


def collect_network_stats(network_rule, config):

    wildcards = {
        k: str(config["scenario"][k][0]) for k in ["simpl", "clusters", "ll", "opts"]
    }

    snakemake = _mock_snakemake(network_rule, **wildcards)

    network_path = (
        snakemake.output["network"]
        if "network" in snakemake.output.keys()
        else snakemake.output[0]
    )

    def capacity_stats(df):
        if df.empty:
            return pd.Series(dtype=float)
        else:
            return df.groupby("carrier").p_nom.sum().astype(float)

    if os.path.exists(network_path):
        n = pypsa.Network(network_path)

        lines_length = float((n.lines.length * n.lines.num_parallel).sum())

        lines_capacity = float(n.lines.s_nom.sum())

        line_stats = pd.DataFrame(
            [[lines_length, lines_capacity]],
            columns=_multi_index_scen(network_rule, ["lines_length", "lines_capacity"]),
        )

        gen_stats = pd.concat(
            [capacity_stats(n.generators), capacity_stats(n.storage_units)], axis=0
        )

        if gen_stats.empty:
            network_stats = line_stats
        else:
            df_gen_stats = gen_stats.to_frame().transpose().reset_index()
            df_gen_stats.columns = _multi_index_scen(network_rule, df_gen_stats.columns)
            network_stats = pd.concat([line_stats, df_gen_stats], axis=1)

        return network_stats
    else:
        return pd.DataFrame()


def collect_shape_stats(rulename="build_shapes", area_crs="ESRI:54009"):
    snakemake = _mock_snakemake(rulename)

    if not os.path.exists(snakemake.output.africa_shape):
        return pd.DataFrame()

    df_continent = gpd.read_file(snakemake.output.africa_shape)
    continent_area = (
        df_continent["geometry"]
        .apply(make_valid)
        .to_crs(crs=area_crs)
        .geometry.area.iloc[0]
    )

    if not os.path.exists(snakemake.output.gadm_shapes):
        return pd.DataFrame()

    df_gadm = gpd.read_file(snakemake.output.gadm_shapes)
    pop_tot = float(df_gadm["pop"].sum())
    gdp_tot = float(df_gadm["gdp"].sum())
    gadm_size = len(df_gadm)
    gadm_country_matching_stats = df_gadm.country.value_counts(normalize=True)
    gadm_country_matching = float(gadm_country_matching_stats.iloc[0]) * 100

    return pd.DataFrame(
        [[continent_area, gadm_size, gadm_country_matching, pop_tot, gdp_tot]],
        columns=_multi_index_scen(
            rulename, ["area", "gadm_size", "country_matching", "pop", "gdp"]
        ),
    )


def collect_snakemake_stats(name, dict_dfs, config):
    ren_techs = [
        tech
        for tech in config["renewable"]
        if tech in config["electricity"]["renewable_carriers"]
    ]

    list_rules = [
        "download_osm_data",
        "clean_osm_data",
        "build_shapes",
        *[f"build_renewable_profiles_{rtech}" for rtech in ren_techs],
        "base_network",
        "add_electricity",
        "simplify_network",
        "cluster_network",
        "solve_network",
    ]

    return pd.DataFrame(
        [
            [
                (rule in dict_dfs.keys()) and not dict_dfs[rule].empty
                for rule in list_rules
            ]
        ],
        columns=_multi_index_scen(name, list_rules),
    )


def collect_renewable_stats(rulename, technology):
    snakemake = _mock_snakemake(rulename, technology=technology)

    if os.path.exists(snakemake.output.profile):
        res = xr.open_dataset(snakemake.output.profile)

        if technology == "hydro":
            potential = float(res.inflow.sum())
            avg_production_pu = float(res.inflow.mean(dim=["plant"]).sum())
        else:
            potential = float(res.potential.sum())
            avg_production_pu = float(res.profile.mean(dim=["bus"]).sum())

        return pd.DataFrame(
            [[potential, avg_production_pu]],
            columns=_multi_index_scen(rulename, ["potential", "avg_production_pu"]),
        )
    else:
        return pd.DataFrame()


def collect_computational_stats(rulename, timedelta):
    comp_time = timedelta.total_seconds()
    return pd.DataFrame(
        [[comp_time]],
        columns=_multi_index_scen(rulename, ["total"]),
    )


def calculate_stats(
    config, timedelta=None, metric_crs="EPSG:3857", area_crs="ESRI:54009"
):
    "Function to calculate statistics"

    df_osm_raw = collect_raw_osm_stats(metric_crs=metric_crs)
    df_osm_clean = collect_clean_osm_stats(metric_crs=metric_crs)
    df_shapes = collect_shape_stats(area_crs=area_crs)

    network_dict = {
        network_rule: collect_network_stats(network_rule, config)
        for network_rule in [
            "base_network",
            "add_electricity",
            "simplify_network",
            "cluster_network",
            "solve_network",
        ]
    }

    # build_renewable_profiles rule
    ren_rule = "build_renewable_profiles"
    renewables_dict = {
        f"{ren_rule}_{tech}": collect_renewable_stats(ren_rule, tech)
        for tech in config["renewable"]
        if tech in config["electricity"]["renewable_carriers"]
    }

    # network-related rules
    dict_dfs = {
        "download_osm_data": df_osm_raw,
        "clean_osm_data": df_osm_clean,
        "build_shapes": df_shapes,
        **renewables_dict,
        **network_dict,
    }

    dict_dfs["snakemake_status"] = collect_snakemake_stats(
        "snakemake_status", dict_dfs, config
    )

    if timedelta is not None:
        dict_dfs["computational_time"] = collect_computational_stats(
            "computational_time", timedelta
        )

    return dict_dfs


def run_scenario(dir_scenario, scenario, config):

    base_config = config.get("base_config", "./config.default.scenario.yaml")

    # create scenario config
    create_test_config(base_config, f"configs/scenarios/{scenario}.yaml", "config.yaml")

    # execute workflow
    start_dt = datetime.now()
    os.system("snakemake -j all solve_all_networks --forceall --rerun-incomplete")
    end_dt = datetime.now()
    timedelta = end_dt - start_dt

    # copy output files
    for f in ["resources", "networks", "results", "benchmarks"]:
        copy_dir = os.path.abspath(f"{dir_scenario}/{f}")
        if os.path.exists(copy_dir):
            shutil.rmtree(copy_dir)
        abs_f = os.path.abspath(f)
        if os.path.exists(abs_f):
            shutil.copytree(abs_f, copy_dir)
            shutil.rmtree(abs_f)

    shutil.copy("config.yaml", f"{dir_scenario}/config.yaml")


if __name__ == "__main__":
    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        snakemake = mock_snakemake("run_scenario", scenario="TD")

    sets_path_to_root("pypsa-earth")

    # generate_scenario_by_country("configs/scenarios/base.yaml", ["Africa"])

    scenario = snakemake.wildcards["scenario"]
    dir_scenario = snakemake.output["dir_scenario"]
    stats_scenario = snakemake.output["stats_scenario"]
    base_config = snakemake.config.get("base_config", "./config.default.scenario.yaml")

    # create scenario config
    create_test_config(base_config, f"configs/scenarios/{scenario}.yaml", "config.yaml")

    # execute workflow
    start_dt = datetime.now()
    os.system("snakemake -j all solve_all_networks --forceall --rerun-incomplete")
    end_dt = datetime.now()
    timedelta = end_dt - start_dt

    # create statistics
    stats = calculate_stats(snakemake.config, timedelta)
    stats = pd.concat(stats.values(), axis=1).set_index(pd.Index([scenario]))
    to_csv_nafix(stats, stats_scenario)

    # copy output files
    for f in ["resources", "networks", "results", "benchmarks"]:
        copy_dir = os.path.abspath(f"{dir_scenario}/{f}")
        if os.path.exists(copy_dir):
            shutil.rmtree(copy_dir)
        abs_f = os.path.abspath(f)
        if os.path.exists(abs_f):
            shutil.copytree(abs_f, copy_dir)
            shutil.rmtree(abs_f)

    shutil.copy("config.yaml", f"{dir_scenario}/config.yaml")
