
# built in
import pandas as pd
import matplotlib.pyplot as plt
from enum import Enum
from typing import Optional

# qis
import qis.utils.dates as da
import qis.utils.np_ops as npn
import qis.perfstats.returns as ret
import qis.plots.time_series as pts
import qis.plots.utils as put
import qis.plots.heatmap as phe
import qis.models.linear.corr_cov_matrix as ccm
import qis.models.linear.ewm as ewm
from qis.models.linear.corr_cov_matrix import CorrMatrixOutput
from qis.models.linear.ewm import InitType
from qis.perfstats.config import PerfParams

from qis.perfstats.regime_classifier import add_bnb_regime_shadows, BenchmarkReturnsQuantileRegimeSpecs


def plot_corr_table(prices: pd.DataFrame,
                    var_format: str = '{:.0%}',
                    freq: Optional[str] = None,
                    cmap: str = 'PiYG',
                    ax: plt.Subplot = None,
                    **kwargs
                    ) -> plt.Figure:

    returns = ret.to_returns(prices=prices, is_log_returns=True, freq=freq)
    corr = ccm.compute_masked_covar_corr(returns=returns, is_covar=False)
    fig = phe.plot_heatmap(df=corr,
                           var_format=var_format,
                           cmap=cmap,
                           ax=ax,
                           **kwargs)
    return fig


def plot_ewm_corr_table(prices: pd.DataFrame,
                        ewm_lambda: float = 0.94,
                        var_format: str = '{:.0%}',
                        init_type: InitType = InitType.ZERO,
                        freq: Optional[str] = None,
                        cmap: str = 'PiYG',
                        ax: plt.Subplot = None,
                        is_average: bool = True,
                        **kwargs
                        ) -> plt.Figure:

    returns = ret.to_returns(prices=prices, is_log_returns=True, freq=freq)

    init_value = ewm.set_init_dim2(data=returns.to_numpy(), init_type=init_type)
    corr = ewm.compute_ewm_covar_tensor(a=returns.to_numpy(),
                                          ewm_lambda=ewm_lambda,
                                          covar0=init_value,
                                          is_corr=True)
    if is_average:
        ar = npn.tensor_mean(corr)
    else:
        ar = corr[-1]

    df = pd.DataFrame(ar, index=prices.columns, columns=prices.columns)
    fig = phe.plot_heatmap(df=df,
                           var_format=var_format,
                           cmap=cmap,
                           ax=ax,
                           **kwargs)
    return fig


def plot_corr_matrix_time_series(prices: pd.DataFrame,
                                 corr_matrix_output: CorrMatrixOutput = CorrMatrixOutput.FULL,
                                 time_period: da.TimePeriod = None,
                                 freq: str = 'B',
                                 ewm_lambda: float = 0.97,
                                 init_type: InitType = InitType.X0,
                                 var_format: str = '{:.0%}',
                                 legend_line_type: pts.LegendLineType = pts.LegendLineType.AVG_LAST,
                                 trend_line: put.TrendLine = put.TrendLine.AVERAGE,
                                 regime_benchmark_str: str = None,
                                 regime_params: BenchmarkReturnsQuantileRegimeSpecs = BenchmarkReturnsQuantileRegimeSpecs(),
                                 perf_params: PerfParams = None,
                                 ax: plt.Subplot = None,
                                 **kwargs
                                 ) -> None:

    """
    plot time series
    """
    returns = ret.to_returns(prices=prices, is_log_returns=False, freq=freq)
    corr_pandas = ccm.compute_ewm_corr_df(returns=returns,
                                          corr_matrix_output=corr_matrix_output,
                                          ewm_lambda=ewm_lambda,
                                          init_type=init_type)
    if time_period is not None:
        corr_pandas = time_period.locate(corr_pandas)

    pts.plot_time_series(df=corr_pandas,
                         legend_line_type=legend_line_type,
                         trend_line=trend_line,
                         var_format=var_format,
                         ax=ax,
                         **kwargs)
    if regime_benchmark_str is not None:
        if regime_benchmark_str in prices.columns:
            pivot_prices = prices[regime_benchmark_str].reindex(index=corr_pandas.index, method='ffill')
        else:
            raise KeyError(f"{regime_benchmark_str} not in {prices.columns}")

        if regime_benchmark_str is not None and regime_params is not None:
            add_bnb_regime_shadows(ax=ax,
                                   pivot_prices=pivot_prices,
                                   benchmark=regime_benchmark_str,
                                   regime_params=regime_params,
                                   perf_params=perf_params)


class UnitTests(Enum):
    CORR_TABLE = 1
    CORR_MATRIX = 2
    EWMA_CORR = 3


def run_unit_test(unit_test: UnitTests):

    from qis.data.yf_data import load_etf_data
    prices = load_etf_data().dropna()

    if unit_test == UnitTests.CORR_TABLE:
        plot_corr_table(prices=prices)

    elif unit_test == UnitTests.CORR_MATRIX:
        fig, ax = plt.subplots(1, 1, figsize=(10, 10), constrained_layout=True)
        plot_corr_matrix_time_series(prices=prices, regime_benchmark_str='SPY', ax=ax)

    elif unit_test == UnitTests.EWMA_CORR:
        plot_ewm_corr_table(prices=prices.iloc[:, :5])

    plt.show()


if __name__ == '__main__':

    unit_test = UnitTests.CORR_MATRIX

    is_run_all_tests = False
    if is_run_all_tests:
        for unit_test in UnitTests:
            run_unit_test(unit_test=unit_test)
    else:
        run_unit_test(unit_test=unit_test)