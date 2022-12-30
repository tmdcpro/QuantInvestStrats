"""
plot returns heatmap table by monthly and annual
"""
# build in
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from typing import Union, List, Optional, Tuple, Dict
from enum import Enum

# qis
import qis.perfstats.returns as ret
import qis.utils.struct_ops as sop
import qis.plots.utils as put
import qis.plots.heatmap as phe
import qis.plots.table as ptb
import qis.utils.dates as da
from qis.plots.heatmap import plot_heatmap

MONTH_MAP = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}


def compute_periodic_returns_by_row_table(prices: pd.Series,
                                          heatmap_freq: str = 'A',
                                          column_period: str = 'M'
                                          ) -> pd.DataFrame:

    periodic_prices_by_row_period = da.split_df_by_freq(df=prices.to_frame(), freq=heatmap_freq)
    returns_table = None
    for key, prices in periodic_prices_by_row_period.items(): # fill table
        returns = ret.to_returns(prices=prices, freq=column_period, include_start_date=True, include_end_date=True, drop_first=True)
        if column_period in ['M', 'Q']:
            year_returns_by_period = pd.DataFrame(data=np.column_stack(returns.to_numpy()), columns=[returns.index.month], index=[returns.index[-1]])
        elif 'W' in column_period:  # Weeklies
            year_returns_by_period = pd.DataFrame(data=np.column_stack(returns.to_numpy()), columns=[returns.index.week], index=[returns.index[-1]])
        else:
            raise TypeError(f"column_period={column_period} not implemented")
        returns_table = pd.concat([returns_table, year_returns_by_period], axis=0) if returns_table is not None else year_returns_by_period

    returns_table = returns_table.reindex(sorted(returns_table.columns), axis=1)

    #map months column: concat create multiindex columns
    if column_period == 'M':

        returns_table.columns = returns_table.columns.get_level_values(0).map(MONTH_MAP)

        if heatmap_freq == 'A-Mar':
            cols = returns_table.columns.tolist()
            cols = cols[3:] + cols[:3]
            returns_table = returns_table[cols]

    elif column_period == 'Q':
        returns_table.columns = returns_table.columns.get_level_values(0).map({1: 'Q1', 2: 'Q1', 3: 'Q1',
                                                                              4: 'Q2', 5: 'Q2', 6: 'Q2',
                                                                              7: 'Q3', 8: 'Q3', 9: 'Q3',
                                                                              10: 'Q4', 11: 'Q4', 12: 'Q4'})
    else:
        print(f"map for column_period={column_period} is not implemented")

    return returns_table


def get_periodic_returns_table(prices: Union[pd.Series, pd.DataFrame],
                               pivot: str,
                               heatmap_freq: str = 'A',
                               column_period: Optional[str] = 'M',  # colums for pivot
                               row_date_format: str = '%Y',
                               is_inverse_order: bool = False,
                               is_add_annual_column: bool = True,
                               ytd_name: str = 'YTD'
                               ) -> pd.DataFrame:

    if column_period is None:
        # insert returns returns table
        # compute annual returns
        row_periodic_returns = ret.to_returns(prices=prices,
                                              freq=heatmap_freq,
                                              include_start_date=True,
                                              include_end_date=True)
        
        row_periodic_returns = row_periodic_returns.set_index(
            row_periodic_returns.index.strftime(row_date_format).to_numpy())
        periodic_returns_table = row_periodic_returns
    else:

        if isinstance(prices, pd.Series):
            pivot_price_data = prices
        else:
            if pivot is None:
                pivot = prices.columns[0]
            pivot_price_data = prices[pivot]

        periodic_returns_table = compute_periodic_returns_by_row_table(prices=pivot_price_data,
                                                                       heatmap_freq=heatmap_freq,
                                                                       column_period=column_period)
        row_periodic_returns = ret.to_returns(prices=prices, freq=heatmap_freq,
                                              include_start_date=True, include_end_date=True, drop_first=True)
        # need to change to unique index
        if isinstance(prices, pd.Series):
            row_periodic_returns.index = row_periodic_returns.index.strftime(row_date_format)
        else:
            row_periodic_returns = row_periodic_returns.set_index(row_periodic_returns.index.strftime(row_date_format))
        # change index to year for merging
        periodic_returns_table = periodic_returns_table.set_index(periodic_returns_table.index.strftime(row_date_format))

        if is_add_annual_column:
            if isinstance(prices, pd.Series):
                row_periodic_returns = row_periodic_returns.rename(ytd_name)
            else:
                row_periodic_returns.columns = [ytd_name]
            periodic_returns_table = pd.concat([periodic_returns_table, row_periodic_returns], axis=1, join='inner')

    if is_inverse_order:
        periodic_returns_table = periodic_returns_table.reindex(index=periodic_returns_table.index[::-1])

    return periodic_returns_table


def plot_returns_heatmap(prices: Union[pd.Series, pd.DataFrame],
                         pivot: str = None,
                         heatmap_freq: str = 'A',
                         heatmap_column_freq: Optional[str] = 'M',  # colums for pivot
                         date_format: str = '%Y',
                         is_inverse_order: bool = False,
                         is_add_annual_column: bool = True,
                         cmap: Union[str, ListedColormap] = 'RdYlGn',
                         alpha: float = 1.0,
                         ytd_name: str = 'YTD',
                         fontsize: int = 8,
                         vline_columns: List[int] = None,
                         hline_rows: List[int] = None,
                         figsize: Tuple[float, float] = None,
                         ax: plt.Subplot = None,
                         **kwargs
                         ) -> plt.Figure:

    periodic_returns_table = get_periodic_returns_table(prices=prices,
                                                        pivot=pivot,
                                                        heatmap_freq=heatmap_freq,
                                                        column_period=heatmap_column_freq,
                                                        row_date_format=date_format,
                                                        is_inverse_order=is_inverse_order,
                                                        is_add_annual_column=is_add_annual_column,
                                                        ytd_name=ytd_name)
    if is_add_annual_column:
        shift = 4 if heatmap_column_freq == 'Q' else 12
        vline_columns_ = [0, shift]
        if vline_columns is not None:
            vline_columns_.append(vline_columns)
        else:
            vline_columns_ = vline_columns_
    else:
        vline_columns_ = vline_columns

    if ax is None:
        if figsize is not None:
            height = ptb.calc_table_height(num_rows=len(periodic_returns_table.index), scale=0.225)
            fig, ax = plt.subplots(1, 1, figsize=(figsize[0], height))
        else:
            fig, ax = plt.subplots()
    else:
        fig = None

    if periodic_returns_table.size == 0:
        return fig

    phe.plot_heatmap(df=periodic_returns_table,
                     cmap=cmap,
                     var_format="0.1%",
                     alpha=alpha,
                     fontsize=fontsize,
                     vline_columns=vline_columns_,
                     hline_rows=hline_rows,
                     ax=ax,
                     **kwargs)

    return fig


def plot_returns_table(prices: pd.DataFrame,
                       time_period_dict: Dict[str, da.TimePeriod],
                       vline_columns: List[int] = None,
                       hline_rows: List[int] = None,
                       is_transpose: bool = False,
                       var_format: str = '{:.1%}',
                       ax: plt.Subplot = None,
                       **kwargs
                       ) -> plt.Figure:
    """
    plot returns at specified dates dict
    """
    period_returns = []
    for period, time_period in time_period_dict.items():
        period_data = time_period.locate(prices)
        if len(period_data.index) > 1:
            period_return = period_data.iloc[-1, :] / period_data.iloc[0, :] - 1
            period_returns.append(period_return.rename(period))
    data = pd.concat(period_returns, axis=1)
    fig = plot_heatmap(df=data,
                       vline_columns=vline_columns,
                       hline_rows=hline_rows,
                       is_transpose=is_transpose,
                       var_format=var_format,
                       ax=ax,
                       **kwargs)
    return fig


def plot_periodic_returns_table(returns: pd.DataFrame,
                                freq: str = 'M',
                                is_transpose: bool = True,
                                var_format: str = '{:.0%}',
                                total_name: str = None,
                                ax: plt.Subplot = None,
                                **kwargs
                                ) -> plt.Figure:
    """
    plot returns at specified frequency
    """
    if freq == 'M':
        date_format = '%b'
        total_name = total_name or '1y'
    elif freq == 'A':
        date_format = '%Y'
        total_name = total_name or 'Total'
    else:
        raise NotImplementedError(f"{freq}")

    data = returns
    np_data = data.to_numpy()[:-2, :-2] # exclude last row from cmap
    fig = plot_heatmap(df=data,
                       vline_columns=[len(data.index)-1],
                       hline_rows=[len(data.columns)-2],
                       is_transpose=is_transpose,
                       var_format=var_format,
                       vmin=np.nanmin(np_data),
                       vmax=np.nanmax(np_data),
                       ax=ax,
                       **sop.update_kwargs(kwargs, dict(date_format=date_format)))
    return fig


def plot_periodic_returns_table_from_prices(prices: pd.DataFrame,
                                            freq: str = 'M',
                                            date_format: str = None,
                                            time_period: da.TimePeriod = None,
                                            is_transpose: bool = True,
                                            var_format: str = '{:.0%}',
                                            total_name: str = None,
                                            ax: plt.Subplot = None,
                                            **kwargs
                                            ) -> plt.Figure:
    """
    plot returns at specified frequency
    """
    if time_period is not None:
        prices = time_period.locate(prices)

    if freq == 'M':
        date_format = date_format or '%b'
        total_name = total_name or 'last 12m'
    elif freq == 'A':
        date_format = date_format or '%Y'
        total_name = total_name or 'Total'
    else:
        raise NotImplementedError(f"{freq}")

    data = ret.to_returns(prices=prices, freq=freq, include_start_date=True, include_end_date=True, drop_first=True)
    total_return = ret.to_total_returns(prices=prices).rename(total_name).to_frame().T
    data = pd.concat([data, total_return], axis=0)
    np_data = data.to_numpy()[:-1, :-1]  # exclude last row from cmap
    fig = plot_heatmap(df=data,
                       vline_columns=[len(data.index)-1],
                       is_transpose=is_transpose,
                       date_format=date_format,
                       var_format=var_format,
                       vmin=np.nanmin(np_data),
                       vmax=np.nanmax(np_data),
                       ax=ax,
                       **kwargs)
    return fig


def plot_sorted_periodic_returns(prices: pd.DataFrame,
                                 freq: str = 'M',
                                 date_format: str = '%d%b%Y',
                                 time_period: da.TimePeriod = None,
                                 is_transpose: bool = True,
                                 var_format: str = '{:.0%}',
                                 total_name: str = None,
                                 ax: plt.Subplot = None,
                                 **kwargs
                                 ) -> plt.Figure:
    """
    plot returns at specified frequency
    """
    if time_period is not None:
        prices = time_period.locate(prices)

    if freq == 'M':
        date_format = date_format or '%b'
        total_name = total_name or 'Total'
    elif freq == 'A':
        date_format = date_format or '%Y'
        total_name = total_name or 'Total'
    else:
        raise NotImplementedError(f"{freq}")

    data = ret.to_returns(prices=prices, freq=freq, include_start_date=True, drop_first=True)
    data.index = [pd.Timestamp(x).strftime(date_format) for x in data.index]
    total_return = ret.to_total_returns(prices=prices).rename(total_name).to_frame().T
    data = pd.concat([data, total_return], axis=0)

    fixed_colors = pd.Series(put.get_n_colors(n=len(data.columns), is_fixed_n_colors=False), index=data.columns)
    data_colors = pd.DataFrame(index=data.index, columns=data.columns)
    sorted_returns = []
    sorted_colors = []
    for idx, date in enumerate(data.index):
        current_period = data.loc[date, :].sort_values(ascending=False)
        # data_colors.loc[date, :] = fixed_colors[current_period.index].to_list()
        data_colors.loc[date, :] = [fixed_colors[x] for x in current_period.index]
        # data_colors.loc[date, :] = fixed_colors.to_list()
        entries = pd.Series([f"{key.split('_')[0]}\n{var_format.format(v)}" for key, v in current_period.to_dict().items()], name=date)
        sorted_returns.append(entries)
        entries_colors = pd.Series([fixed_colors[key] for key, v in current_period.to_dict().items()], name=date)
        sorted_colors.append(entries_colors)

    sorted_returns = pd.concat(sorted_returns, axis=1)
    sorted_colors = pd.concat(sorted_colors, axis=1)

    fig = ptb.plot_df_table(df=sorted_returns,
                            first_column_width=None,
                            add_index_as_column=False,
                            data_colors=sorted_colors.to_numpy(),
                            ax=ax,
                            **kwargs)
    return fig


class UnitTests(Enum):
    PERIODIC_RETURNS_BY_ROW = 1
    RETURNS_HEATMAP = 2
    RETURNS_TABLE = 3
    PERIODIC_RETURNS_TABLE = 4
    PERIODIC_RETURNS_TABLE_A = 5
    SORTED_PERIODIC_RETURNS_TABLE = 6


def run_unit_test(unit_test: UnitTests):

    from qis.data.yf_data import load_etf_data
    prices = load_etf_data().dropna()

    if unit_test == UnitTests.PERIODIC_RETURNS_BY_ROW:
        periodic_returns_table = compute_periodic_returns_by_row_table(prices=prices['SPY'],
                                                                       heatmap_freq='A',
                                                                       column_period='M')
        print(periodic_returns_table)

    elif unit_test == UnitTests.RETURNS_HEATMAP:
        periodic_returns_table = get_periodic_returns_table(prices=prices['SPY'],
                                                            pivot='SPY',
                                                            column_period='M',
                                                            is_add_annual_column=True,
                                                            is_inverse_order=True)
        print(periodic_returns_table)

        plot_returns_heatmap(prices=prices['SPY'],
                             heatmap_column_freq='M',
                             heatmap_freq='A',
                             #date_format='%b-%Y',
                             is_add_annual_column=True,
                             is_inverse_order=True)

    elif unit_test == UnitTests.RETURNS_TABLE:
        time_period_dict = {'Q1': da.TimePeriod(start='31Dec2019', end='31Mar2020'),
                            'Q2': da.TimePeriod(start='31Mar2020', end='30Jun2020'),
                            'YTD': da.TimePeriod(start='31Dec2019', end='30Jun2020')}
        plot_returns_table(prices=prices.iloc[:, :10],
                           time_period_dict=time_period_dict,
                           vline_columns=[2],
                           hline_rows=[1],
                           is_transpose=False,
                           is_inverse_order=True)

    elif unit_test == UnitTests.PERIODIC_RETURNS_TABLE:

        time_period = None

        plot_periodic_returns_table_from_prices(prices=prices,
                                                time_period=time_period,
                                                date_format='%b-%y',
                                                freq='A',
                                                x_rotation=90,
                                                df_out_name='heatmap1y')

    elif unit_test == UnitTests.PERIODIC_RETURNS_TABLE_A:

        time_period = da.TimePeriod(start='28Feb2010', end='31Jan2021')
        plot_periodic_returns_table_from_prices(prices=prices,
                                                time_period=time_period,
                                                date_format='%b-%y',
                                                freq='A',
                                                x_rotation=90,
                                                df_out_name='heatmap1y')

    elif unit_test == UnitTests.SORTED_PERIODIC_RETURNS_TABLE:
        time_period = da.TimePeriod(start='28Feb2010', end='31Jan2021')
        plot_sorted_periodic_returns(prices=prices.iloc[:, :20],
                                     time_period=time_period,
                                     date_format='%b-%y',
                                     freq='A',
                                     x_rotation=90)

    plt.show()


if __name__ == '__main__':

    unit_test = UnitTests.PERIODIC_RETURNS_TABLE

    is_run_all_tests = False
    if is_run_all_tests:
        for unit_test in UnitTests:
            run_unit_test(unit_test=unit_test)
    else:
        run_unit_test(unit_test=unit_test)
