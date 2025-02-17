from typing import Union, List, Dict, Any
import matplotlib.pyplot as plt
from pathlib import Path
import itertools as itt
import pandas as pd
import subprocess
import numpy as np
import sys
import os


# drop duplicates
def dfr_duplicates(
    dfr: pd.DataFrame,
    col_sort: Union[List, str],
    col_drop: Union[List, str],
    keep_by: str = "min",
) -> pd.DataFrame:
    # keep_by = min/first - keep the smallest value, max/last - keep the largest value
    col_sort, col_drop = val_to_list(col_sort), val_to_list(col_drop)
    col_sort = col_drop + [col for col in col_sort if col not in col_drop]
    dfr = dfr.sort_values(
        col_sort, ascending=True
    )  # sort data by col_drop+col_sort in ascending order
    dfr = dfr.drop_duplicates(
        col_drop, keep=("first" if keep_by.lower() == "min" else "last"), ignore_index=True
    )
    return dfr


# compress multi-level columns to single-level
def dfr_columns(dfr: pd.DataFrame, col_name: Union[List, str]) -> pd.Index:
    col_name = val_to_list(col_name)
    return dfr.columns.map(
        lambda x: ".".join([f"{cx}{cv}" for cv, cx in zip(x, [""] + col_name)])
    )


def dfr_default(
    dfr: pd.DataFrame, col_used: Union[List, str], def_vals: Union[str, int, float]
) -> pd.DataFrame:
    col_used = [col_used] if isinstance(col_used, str) else col_used
    for col in col_used:
        dfr.loc[dfr[col].isin([0, "0", -8, -9, -10]), col] = def_vals
    return dfr


# filter zero from dataframe
def dfr_filter_zero(dfr: pd.DataFrame, col_used: Union[List, str]) -> pd.DataFrame:
    col_used = [col_used] if isinstance(col_used, str) else col_used
    return dfr.loc[(~dfr[col_used].isin([0, "0", -8, -9, -10])).all(axis=1)].reset_index(
        drop=True
    )


# filter mode values
def dfr_filter_mode(dfr: pd.DataFrame, inc_list: List, col_mode: str = "mode") -> pd.DataFrame:
    return dfr.loc[dfr[col_mode].isin(inc_list)].reset_index(drop=True)


# create a complete set of index values
def dfr_complete(
    dfr: pd.DataFrame, col_index: Union[List, str, None], col_unstk: Union[List, str]
) -> pd.DataFrame:
    col_index = [] if col_index is None else val_to_list(col_index)
    col_unstk = val_to_list(col_unstk)
    dfr = dfr.set_index(col_index) if len(col_index) > 0 else dfr
    for col in col_unstk:
        dfr = dfr.unstack(level=col, fill_value=0).stack(
            future_stack=True
        )  # future_stack implemented in pandas 2.1
    return dfr


# import csv to dataframe
def csv_to_dfr(
    csv_file: Union[str, Path], col_incl: Union[List, str] = None, nts_dtype: type = object
) -> Union[pd.DataFrame, bool]:
    log_stderr(f" .. read {txt_truncate(csv_file, 70)}")
    if isinstance(csv_file, str):
        _, _, _, csv_extn = split_file(csv_file)
    else:
        csv_extn = csv_file.parts[-1].split(".")[-1]
    csv_extn = "\t" if csv_extn.lower().endswith("tab") else ","
    if col_incl is not None:
        col_incl = [str_lower(col) for col in val_to_list(col_incl)]
    dfr = pd.read_csv(csv_file, sep=csv_extn, low_memory=False)
    dfr = dfr.rename(columns={key: key.lower().strip() for key in dfr.columns})
    try:
        dfr = dfr[col_incl] if col_incl is not None else dfr
    except KeyError as err:
        log_stderr(f"    !!! {split_file(str(csv_file))[2]} -> {err} !!!")
        dfr = (
            dfr[[col for col in col_incl if col in dfr.columns]]
            if col_incl is not None
            else dfr
        )

    dfr = dfr.fillna("0").replace(" ", "0")
    if nts_dtype is int:
        col_incl = [
            "w2",
            "w5",
            "w5xhh",
            "tripdisincsw",
            "triptravtime",
            "hholdoslaua_b01id",
            "hholdosward_b01id",
            "settlement2011ew_b01id",
            "stagedistance",
            "stagetime",
            "stagefarecost",
            "stagecost",
            "ticketcost",
            "tickettripcost",
        ]
        col_incl = [col for col in dfr.columns if col not in col_incl]
        try:
            dfr[col_incl] = dfr[col_incl].astype("int64")
        except ValueError as err:
            log_stderr(f"    error with {csv_file}: {err}")

    return dfr


# create directory
def mkdir(sub_fldr: Union[Path, str]) -> Union[Path, str]:
    os.makedirs(sub_fldr, exist_ok=True)
    return sub_fldr


# apply expansion
def nts_expanse(
    dfr: pd.DataFrame, exp_fact: pd.DataFrame, col_calc: Union[List, str] = None
) -> pd.DataFrame:
    dfr = pd.merge(dfr, exp_fact, how="left", on="individualid")
    col_calc = ["w2", "trips", "w5"] if col_calc is None else val_to_list(col_calc)
    for col in col_calc:
        if col in dfr.columns:
            dfr[col] = dfr[col].mul(dfr["exp_fact"])
    return dfr


# write dataframe to csv
def dfr_to_csv(
    dfr: pd.DataFrame,
    csv_path: Union[Path, str],
    csv_name: str,
    index: bool = True,
    header: bool = True,
    dec_4mat: Union[str, None] = None,
):
    csv_path = Path(csv_path) if isinstance(csv_path, str) else csv_path
    csv_name = f"{csv_name}.csv" if ".csv" not in csv_name.lower() else csv_name
    log_stderr(f" .. write to {txt_truncate(csv_path / csv_name, 70)}")
    mkdir(csv_path)
    dfr.to_csv(csv_path / csv_name, index=index, header=header, float_format=dec_4mat)


# convert itm to key
def itm_to_key(dct: Dict, key_lower: bool = True) -> Dict:
    # swap key to value
    dct = {key: [dct[key]] if not isinstance(dct[key], list) else dct[key] for key in dct}
    return {str_lower(val) if key_lower else val: key for key in dct for val in dct[key]}


# convert string to list
def val_to_list(str_text: Union[str, float, int, List, None]) -> List:
    return (
        [] if str_text is None else [str_text] if not isinstance(str_text, list) else str_text
    )


# convert list to dictionary
def list_to_dict(dct: Union[List, Dict]) -> Dict:
    if isinstance(dct, dict):
        dct = {str_lower(col): dct[col] for col in dct}
    else:
        dct = {str_lower(col): 1 for col in dct}
    return dct


def dfr_to_dict(dfr: pd.DataFrame, key: str, val: str) -> Dict:
    return dfr[[key, val]].set_index(key).to_dict()[val]


# create tuple from dataframe columns
def dfr_to_tuple(dfr: pd.DataFrame, col_used: List) -> pd.Series:
    # create tuple from dfr columns
    col_2zip = zip(*[dfr[col] for col in col_used])
    return (
        dfr[col_used[0]]
        if len(col_used) == 1
        else pd.Series([col for col in col_2zip], index=dfr.index)
    )


# convert str to lower()
def str_lower(val: Any) -> Any:
    if isinstance(val, str):
        return val.lower()
    elif isinstance(val, (tuple, list, dict, set)):
        return tuple(itm.lower() if isinstance(itm, str) else itm for itm in val)
    else:
        return val


# dataframe group_by
def dfr_grby(dfr: pd.DataFrame, col_grby: Union[List, str], observed: bool = True):
    return dfr.groupby(col_grby, observed=observed)


# convert dfr to dcat
def dfr_to_dcat(
    dfr: pd.DataFrame, col_dcat: Union[str, List], col_dnum: Union[List, str] = None
) -> pd.DataFrame:
    # similar to patsy.dmatrices
    col_dcat, col_dnum = val_to_list(col_dcat), val_to_list(col_dnum)
    dfr = dfr[col_dcat + col_dnum].reset_index(drop=True)
    out = pd.DataFrame(data={"intercept": [1.0] * len(dfr)}, index=dfr.index)
    out[col_dnum] = dfr[col_dnum]
    for col in col_dcat:
        tmp = pd.get_dummies(dfr[col], dtype=int)
        tmp = tmp.drop(columns=tmp.columns[0], errors="ignore")
        tmp = tmp.rename(columns={itm: f"{col}_{itm}" for itm in tmp.columns})
        out = pd.merge(out, tmp, how="left", left_index=True, right_index=True)
    return out


# convert formula to list
def form_to_list(reg_text: str) -> tuple:
    # convert regression model formula to list
    col_trip, col_spec = [col for col in reg_text.split("~")]
    col_spec = col_spec.split("|")[0]
    return col_trip.strip(), [col.strip() for col in col_spec.split("+")]


# scatter plots
def plt_scatter(
    title,
    x_val: np.ndarray,
    y_val: np.ndarray,
    x_label: str,
    y_label: str,
    out_fldr: Path,
    intercept: bool = True,
):
    plt.rc("font", size=8)
    plt.grid(True)
    p_fit = (
        np.append(np.linalg.lstsq(x_val.reshape(-1, 1), y_val, rcond=None)[0], [0])
        if not intercept
        else np.polyfit(x_val, y_val, 1)
    )
    l_fit = np.poly1d(p_fit)
    y_fit = l_fit(x_val)
    r_sqr = rsq_calc(y_val, y_fit)
    v_max = max(1.02 * x_val.max(), 1.02 * max(y_val.max(), y_fit.max()))
    plt.scatter(x_val, y_val, c="b", marker=".")
    plt.plot(x_val, y_fit, c="g")
    plt.ylabel(f"{y_label}", size=8)
    plt.xlabel(f"{x_label}", size=8)
    plt.xlim(0, v_max)
    plt.ylim(0, v_max)
    plt.title(title, size=10)
    plt.annotate(
        f"Slope = {p_fit[0]:.3f}\nIntercept = {p_fit[1]:.3f}\nR2 = {r_sqr:.3f}",
        (0.02 * v_max, 0.98 * v_max),
        ha="left",
        va="top",
        bbox=dict(boxstyle="round", fc="w"),
        size=8,
    )
    plt.savefig(out_fldr / f"{title}.png", dpi=300)
    plt.close()


def plt_tld(title, xlm_axis, ylm_axis, x_label: str, y_label: str, out_fldr: Path):
    xlm_mean = (xlm_axis * ylm_axis).sum() / ylm_axis.sum()
    ylm_trip = ylm_axis.sum()
    ylm_axis = ylm_axis / ylm_trip * 100
    plt.plot(
        xlm_axis,
        ylm_axis,
        "r-*",
        label=f"obs. mean = {xlm_mean: .3f}km ({ylm_trip: .0f} trips)",
    )
    plt.rc("font", size=8)
    plt.grid(True)
    plt.ylabel(f"{y_label}", size=8)
    plt.xlabel(f"{x_label}", size=8)
    plt.xlim(0, 1.02 * xlm_axis.max())
    plt.ylim(0, 1.02 * ylm_axis.max())
    plt.title(title, size=10)
    plt.savefig(out_fldr / f"{title}.png", dpi=300)
    plt.close()


# calculate R2
def rsq_calc(obs: np.ndarray, est: np.ndarray) -> float:
    return max(1 - np.sum((est - obs) ** 2) / np.sum((obs - np.mean(obs)) ** 2), 0)


# print
def log_stderr(*args):
    print(*args, file=sys.stderr, flush=True)


# subprocess - single
def cmd_single(cmd_list: Union[List, str]):
    cmd_list = cmd_list if type(cmd_list) is list else [cmd_list]
    for ts in cmd_list:
        pr = subprocess.Popen(ts, creationflags=subprocess.CREATE_NEW_CONSOLE, shell=True)
        pr.wait()


# subprocess - multic
def cmd_multic(cmd_list: List, num_cpus: int = 999):
    num_bloc = int(len(cmd_list) / num_cpus) + 1
    for bl in range(num_bloc):
        min_bloc = min(bl * num_cpus, len(cmd_list))
        max_bloc = min(min_bloc + num_cpus, len(cmd_list))
        exe_list = [
            subprocess.Popen(pr, creationflags=subprocess.CREATE_NEW_CONSOLE, shell=True)
            for pr in cmd_list[min_bloc:max_bloc]
        ]
        for pr in exe_list:
            pr.wait()


# expand string
def str_xpanse(str_text: str) -> str:
    str_list = str(str_text).replace(";", ",").replace(" ", "").split(",")
    out_text = ""
    for dx in range(len(str_list)):
        if "-" not in str_list[dx]:
            out_text += f"{str_list[dx]},"
        else:
            tmp_list = str_list[dx].split("-")
            for dy in range(int(tmp_list[0]), int(tmp_list[1]) + 1):
                out_text += f"{dy},"
    return out_text[:-1]


# string to value
def str_to_value(str_text: Union[str, int, float]) -> Union[str, int, float]:
    if type(str_text) is str:
        try:
            out_value = int(str_text)
        except ValueError:
            try:
                out_value = float(str_text)
            except ValueError:
                out_value = str_text.strip()
    else:
        out_value = str_text
    return out_value


# list to dictionary
def list_to_dict_item(uni_list: Union[List, Dict], key_start: int = 0) -> Dict:
    if type(uni_list) is not dict:
        uni_dict = {key: item for key, item in enumerate(uni_list, key_start)}
    else:
        uni_dict = uni_list
    return uni_dict


# split filename to path, name, extn
def split_file(str_file: Union[str, Path]) -> List:
    str_file, str_path = str(str_file), os.path.dirname(str_file)
    str_name, str_extn = os.path.splitext(str_file.replace("\\", "/").split("/")[-1])
    return [str_file, str_path, str_name, str_extn]


# file existence
def exist_file(str_file: Union[Path, str], err_index: bool = True) -> bool:
    if not os.path.isfile(str_file):
        err_index = False
        log_stderr(f"    >> file not found [{txt_truncate(str_file)}]")
    return err_index


# path existence
def exist_path(str_path: Union[Path, str], err_index: bool = True) -> bool:
    if not os.path.isdir(str_path):
        err_index = False
        log_stderr(f"    >> path not found [{txt_truncate(str_path)}]")
    return err_index


# reduced print
def txt_truncate(str_text: Union[Path, str], len_text: int = 50) -> str:
    str_text = str(str_text)
    out_text = str_text[-len_text:]
    pos_text = out_text.find("\\") if out_text.find("\\") > 0 else 0
    out_text = f".{out_text[pos_text:]}" if len(str_text) > len_text else str_text
    return out_text


# add path
def add_path(cur_path: str, str_file: str) -> str:
    return f"{cur_path}\\{str_file}" if "\\" not in str_file else str_file


# derive distance band
def dist_band(max_dist: Union[List, float], pow_incr: float = 2.2) -> np.ndarray:
    if isinstance(max_dist, float):
        max_dist = int(max_dist + 1)
        num_band = int(max_dist**0.51)
        arr_dist = np.array(
            [
                int(((0 if val == 0 else val + 1) / num_band) ** pow_incr * max_dist)
                for val in range(num_band)
            ]
        )
    else:
        arr_dist = np.array(max_dist)
    return arr_dist


# product function
def product(*args) -> List:
    return list(itt.product(*args))


def agg_prop(dfr: pd.DataFrame, col_grby: Union[List, str], col_calc: str) -> pd.Series:
    return dfr[col_calc].div(dfr.groupby(col_grby)[col_calc].transform("sum")).fillna(0)


# fill data from aggregate level
def agg_fill(
    dfr: pd.DataFrame,
    col_grby: Union[List, str],
    col_segm: Union[List, str],
    col_calc: str,
    val_vmin: float = 0,
) -> pd.Series:
    # col_grby: list of columns to aggregate, hierarchical level from right to left
    # e.g. col_grby = [at, hh, tt] -> calculate %split by [at, hh, tt] first,
    # else aggregate to [at, hh] type -> calc %split, then aggregate to [at] -> calc %split
    # col_segm: further segmentation to calculate %split

    def _calc_split():
        num = dfr.groupby(col_grby + col_segm, observed=True)[col_calc].transform("sum")
        den = dfr.groupby(col_grby, observed=True)[col_calc].transform("sum")
        msk = (out.isna()) & (den > val_vmin)
        out.loc[msk] = num.div(den).loc[msk]
        return out

    col_grby, col_segm = val_to_list(col_grby), val_to_list(col_segm)
    dfr = dfr[col_grby + col_segm + [col_calc]].copy()
    out = pd.Series(data=[np.nan] * len(dfr), index=dfr.index)
    for lev, _ in enumerate(col_grby):
        col_used = col_grby if lev == 0 else col_grby[:-lev]
        _calc_split()  # step 1

        # aggregate to hh & at subgroup
        key = col_used[-1]
        if key.startswith("hh_type"):
            dfr.loc[dfr[key].isin([1, 3, 6]), key] = 101  # 0 car
            dfr.loc[dfr[key].isin([4, 7]), key] = 102  # 1 car
            dfr.loc[dfr[key].isin([2, 5, 8]), key] = 103  # 2+ car
            _calc_split()  # step 2

            # step 3 - aggregate hh_type for london only
            if any([col.startswith("tfn_at") for col in dfr.columns]):
                col = [col for col in dfr.columns if col.startswith("tfn_at")][0]
                dfr.loc[dfr[col].isin([1, 2]), key] = 201
                _calc_split()

        # aggregate by area types
        if key.startswith("tfn_at"):
            # step 4 - level 1
            dfr.loc[dfr[key].isin([1, 2]), key] = 101  # London
            dfr.loc[dfr[key].isin([3]), key] = 102  # major EoE, SE
            dfr.loc[dfr[key].isin([4, 5, 6, 20]), key] = 103  # major WM, NW, NE, Scotland
            dfr.loc[dfr[key].isin([7, 8]), key] = 104  # major YH, minor YH, EM
            dfr.loc[dfr[key].isin([9, 10]), key] = 105  # city EoE + SE
            dfr.loc[dfr[key].isin([11, 12, 13, 14, 15]), key] = 106  # rest cities
            dfr.loc[dfr[key].isin([16, 17]), key] = 107  # towns
            dfr.loc[dfr[key].isin([18, 19]), key] = 108  # village
            _calc_split()
            # step 5 - level 2
            dfr.loc[dfr[key].isin([101, 102]), key] = 201  # london
            dfr.loc[dfr[key].isin([103, 104]), key] = 202  # major
            dfr.loc[dfr[key].isin([105, 106]), key] = 203  # city
            dfr.loc[dfr[key].isin([107, 108]), key] = 204  # rural
            _calc_split()
            # step 6 - level 3
            dfr.loc[dfr[key].isin([201, 202]), key] = 301  # london + major
            dfr.loc[dfr[key].isin([203, 204]), key] = 302  # city + rural
            _calc_split()
            # step 7 - level 4
            dfr.loc[dfr[key].isin([301, 302]), key] = 401  # all
            _calc_split()

    # finally, aggregate hh_type
    if "hh_type" in dfr.columns:
        dfr["hh_type"] = 201
        _calc_split()

    return out
