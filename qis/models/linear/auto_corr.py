# packages
import numpy as np
import pandas as pd
from typing import Union, Tuple
from numba import njit
from statsmodels.tsa.stattools import pacf, acf

# qis
from qis.models.linear.ewm import MeanAdjType, compute_rolling_mean_adj


def estimate_path_acf(paths: Union[np.ndarray, pd.DataFrame],
                      nlags: int = 10,
                      is_pacf: bool = True
                      ) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    if isinstance(paths, pd.DataFrame):
        columns = paths.columns
        paths = paths.to_numpy()
    else:
        columns = None

    nb_path = paths.shape[1]
    acfs = np.zeros((nlags + 1, nb_path))
    for path in np.arange(nb_path):
        data = paths[:, path]
        data = data[np.isnan(data)==False]
        if len(data) > 2.0*nlags:
            if is_pacf:
                acfs[:, path] = pacf(data, nlags=nlags)
            else:
                acfs[:, path] = acf(data, nlags=nlags)
        else:
            acfs[:, path] = np.nan
    acfs = pd.DataFrame(acfs, columns=columns)
    m_acf = pd.Series(np.nanmean(acfs, axis=1), name='mean')
    std_acf = pd.Series(np.nanstd(acfs, axis=1), name='str')
    return acfs, m_acf, std_acf


def compute_autocorr(x: Union[np.ndarray, pd.Series],
                     num_lags: int = 1,
                     axis: int = None
                     ) -> np.ndarray:
    """
    partial correlation
    """
    if isinstance(x, pd.Series) or isinstance(x, pd.DataFrame):
        x = x.to_numpy()
    if len(x) == 1:
        corr = np.zeros(num_lags)
    else:
        corr = auto_corr(a=x, num_lags=num_lags)
    if num_lags == 1:
        return corr[0]
    else:
        return np.array(corr)


@njit
def auto_corr(a: np.ndarray,
              num_lags: int = 20
              ) -> np.ndarray:
    acorr = np.ones(num_lags)
    for idx in range(1, num_lags):
        acorr[idx] = np.corrcoef(a[idx:], a[:-idx], rowvar=False)[0][1]
    return acorr


@njit
def compute_ewm_autocovar(a: np.ndarray,
                           ewm_lambda: float = 0.94,
                           covar0: np.ndarray = None,
                           lag: int = 1,
                           aggregation_type: str = 'mean',
                           is_normalize: bool = True
                           ) -> (np.ndarray, np.ndarray):
    """
    x is T*N arrays
    """
    ewm_lambda_1 = 1.0 - ewm_lambda

    if a.ndim == 1:  # ndarry
        raise TypeError(f"time dimension must be higher than one")
    else:
        n = a.shape[1]  # array of ndarray
        num_off_diag = n * (n - 1)
        t = a.shape[0]

    if covar0 is None:
        covar = np.zeros((n, n))
        auto_covar = np.zeros((n, n))
    else:
        covar = covar0
        auto_covar = covar0

    trace_cov = np.zeros(t)
    trace_off = np.zeros(t)
    for idx in range(lag, t):  # row in x:
        x_t = a[idx]
        auto_covar = ewm_lambda_1 * np.outer(a[idx - lag], x_t) + ewm_lambda * auto_covar
        covar = ewm_lambda_1 * np.outer(x_t, x_t) + ewm_lambda * covar

        if is_normalize:
            auto_covar_t = auto_covar / covar
        else:
            auto_covar_t = auto_covar

        if aggregation_type == 'mean':
            trace_cov[idx] = np.nansum(np.diag(auto_covar_t)) / n
            trace_off[idx] = (np.nansum(auto_covar_t) - np.nansum(np.diag(auto_covar_t)))/num_off_diag

        elif aggregation_type == 'median':
            trace_cov[idx] = np.nanmedian(np.diag(auto_covar_t))
            trace_off[idx] = np.nanmedian(auto_covar_t)

    return trace_cov, trace_off


def compute_auto_corr(data: pd.DataFrame,
                      num_lags: int = 20
                      ) -> pd.DataFrame:
    """
    compute auto correlation columns wise
    """
    acorrs = []
    for column in data:
        acorrs.append(auto_corr(a=data[column].dropna().to_numpy(), num_lags=num_lags))

    data = pd.DataFrame(data=np.column_stack(acorrs),
                        index=range(0, num_lags),
                        columns=data.columns)
    return data


def compute_dynamic_auto_corr(data: pd.DataFrame,
                              ewm_lambda: float = 0.94,
                              mean_adj_type: MeanAdjType = MeanAdjType.EWMA,
                              lag: int = 1,
                              aggregation_type: str = 'mean',
                              is_normalize: bool = True
                              ) -> pd.DataFrame:
    """
    compute auto correlation columns wise
    """
    if len(data.index) == 1:
        raise TypeError('data must be time series')

    data = data.fillna(method='ffill').dropna()
    x = compute_rolling_mean_adj(data=data.to_numpy(),
                                 mean_adj_type=mean_adj_type,
                                 ewm_lambda=ewm_lambda)

    trace_cov, trace_corr = compute_ewm_autocovar(a=x,
                                                   ewm_lambda=ewm_lambda,
                                                   lag=lag,
                                                   aggregation_type=aggregation_type,
                                                   is_normalize=is_normalize)

    data = pd.DataFrame(data=np.column_stack((trace_cov, trace_corr)),
                        index=data.index,
                        columns=['diagonal', 'off-diag'])
    return data
