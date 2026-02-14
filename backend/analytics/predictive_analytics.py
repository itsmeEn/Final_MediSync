import pandas as pd
import numpy as np
import json
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import mean_absolute_error, mean_squared_error
from scipy.stats import chi2_contingency
from django.db.models import QuerySet
import warnings
import base64
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
from .ai_insights_model import MediSyncAIInsights

# Consistent train/test split for predictive analytics
DEFAULT_TRAIN_RATIO = 0.7

def get_data_from_queryset(queryset: QuerySet):
    """
    Loads data from a Django QuerySet into a pandas DataFrame.
    """
    if not queryset.exists():
        return pd.DataFrame()
    
    # Efficiently load data into a DataFrame
    return pd.DataFrame.from_records(queryset.values())

def normalize_date_range(df: pd.DataFrame, date_col: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """
    Clip a DataFrame to a consistent date range for comparability across analyses.

    - Converts `date_col` to datetime
    - Applies inclusive filtering between `start` and `end` (if provided)
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col])
    if start is not None:
        df = df[df[date_col] >= pd.to_datetime(start)]
    if end is not None:
        df = df[df[date_col] <= pd.to_datetime(end)]
    return df

def strip_pii_columns(df: pd.DataFrame, pii_columns: list[str] | None = None) -> pd.DataFrame:
    """
    Remove personally identifiable information columns to support data privacy compliance.

    Default PII columns can be expanded based on the dataset.
    """
    if pii_columns is None:
        pii_columns = ['patient_name', 'full_name', 'address', 'phone', 'email']
    return df.drop(columns=[c for c in pii_columns if c in df.columns], errors='ignore')

def export_analysis_to_csv(outputs: dict, output_dir: str) -> dict:
    """
    Export analysis outputs to CSV files in `output_dir`.

    - Supports values that are: pandas DataFrame, list[dict], or simple dicts with 'records'
    - Returns a dict mapping keys to written file paths
    """
    os.makedirs(output_dir, exist_ok=True)
    written = {}
    for key, value in outputs.items():
        try:
            df = None
            if isinstance(value, pd.DataFrame):
                df = value
            elif isinstance(value, list):
                if len(value) > 0 and isinstance(value[0], dict):
                    df = pd.DataFrame(value)
                else:
                    df = pd.DataFrame({key: value})
            elif isinstance(value, dict) and 'records' in value and isinstance(value['records'], list):
                df = pd.DataFrame(value['records'])
            elif isinstance(value, dict):
                df = pd.DataFrame([value])

            if df is not None:
                file_path = os.path.join(output_dir, f"{key}.csv")
                df.to_csv(file_path, index=False)
                written[key] = file_path
        except Exception:
            # Skip values that cannot be serialized to CSV
            continue
    return written

def perform_patient_health_trends(df):
    """Analyzes and returns the top 5 medical conditions per week."""
    # Ensure 'Date of Admission' is in datetime format
    df['date_of_admission'] = pd.to_datetime(df['date_of_admission'], errors='coerce')
    df.dropna(subset=['date_of_admission'], inplace=True)
    
    if 'medical_condition' not in df.columns or 'date_of_admission' not in df.columns:
        return {"error": "Required columns not found for patient health trends."}
        
    weekly_illness_counts = df.groupby([pd.Grouper(key='date_of_admission', freq='W'), 'medical_condition']).size().reset_index(name='count')
    top_illnesses = weekly_illness_counts.sort_values(by='count', ascending=False).groupby('date_of_admission').head(5)
    
    # Prepare data for JSON serialization
    top_illnesses['date_of_admission'] = top_illnesses['date_of_admission'].astype(str)
    return {"top_illnesses_by_week": top_illnesses.to_dict('records')}

def analyze_patient_demographics(df):
    """Analyzes and returns patient age and gender distribution."""
    demographics_data = df[['age', 'gender']].copy()
    age_bins = [20, 40, 60, 80, 100]
    age_labels = ['20-39', '40-59', '60-79', '80+']
    demographics_data['age_group'] = pd.cut(demographics_data['age'], bins=age_bins, labels=age_labels, right=False)
    
    age_distribution = demographics_data['age_group'].value_counts().sort_index()
    gender_counts = demographics_data['gender'].value_counts()
    gender_proportions = (gender_counts / gender_counts.sum() * 100).round(2)
    
    return {
        "age_distribution": age_distribution.to_dict(),
        "gender_proportions": gender_proportions.to_dict()
    }

def analyze_illness_prediction_chi_square(df):
    """Performs Chi-Square test for illness prediction based on age and gender."""
    df['date_of_admission'] = pd.to_datetime(df['date_of_admission'], errors='coerce')
    df.dropna(subset=['date_of_admission'], inplace=True)
    
    age_bins = [20, 40, 60, 90]
    age_labels = ['20-39', '40-59', '60+']
    df['age_group'] = pd.cut(df['age'], bins=age_bins, labels=age_labels, right=False)
    
    contingency_table = pd.crosstab([df['age_group'], df['gender']], df['medical_condition'])
    
    chi2, p_value, _, _ = chi2_contingency(contingency_table)
    
    association_result = "Statistically significant association." if p_value < 0.05 else "No statistically significant association."
    
    contingency_data = contingency_table.reset_index().to_dict('records')
    
    return {
        "chi_square_statistic": round(chi2, 2),
        "p_value": round(p_value, 4),
        "association_result": association_result,
        "contingency_table": contingency_data
    }

def analyze_common_medications(df):
    """Analyzes and returns the frequency of prescribed medications."""
    medication_frequency = df['medication'].value_counts()
    medication_frequency_sorted = medication_frequency.sort_values(ascending=False)
    cumulative_frequency = medication_frequency_sorted.cumsum()
    cumulative_percentage = (cumulative_frequency / cumulative_frequency.iloc[-1] * 100).round(2)
    
    pareto_data = pd.DataFrame({
        'frequency': medication_frequency_sorted,
        'cumulative_percentage': cumulative_percentage
    })
    
    return {"medication_pareto_data": pareto_data.reset_index().rename(columns={'index': 'medication'}).to_dict('records')}

def predict_patient_volume(df):
    """Predicts future patient volume using SARIMA model."""
    df['date_of_admission'] = pd.to_datetime(df['date_of_admission'], errors='coerce')
    df.dropna(subset=['date_of_admission'], inplace=True)

    df['month_year'] = df['date_of_admission'].dt.to_period('M')
    monthly_volumes = df.groupby('month_year').size()
    monthly_volumes.index = monthly_volumes.index.to_timestamp()

    # Split the data (70-30)
    train_size = int(len(monthly_volumes) * DEFAULT_TRAIN_RATIO)
    train_data = monthly_volumes[:train_size]
    test_data = monthly_volumes[train_size:]
    
    try:
        model = SARIMAX(train_data, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        results = model.fit(disp=False)
        forecast = results.get_forecast(steps=len(test_data))
        forecasted_values = forecast.predicted_mean

        mae = mean_absolute_error(test_data, forecasted_values)
        mse = mean_squared_error(test_data, forecasted_values)
        rmse = np.sqrt(mse)
        
        comparison_df = pd.DataFrame({'Actual': test_data, 'Forecasted': forecasted_values})
        comparison_df['Actual'] = comparison_df['Actual'].round(2)
        comparison_df['Forecasted'] = comparison_df['Forecasted'].round(2)
        
        # Generate visualization
        plt.figure(figsize=(10, 6))
        plt.plot(comparison_df.index, comparison_df['Actual'], label='Actual', marker='o')
        plt.plot(comparison_df.index, comparison_df['Forecasted'], label='Forecasted', marker='x', linestyle='--')
        plt.title('Patient Volume Prediction: Actual vs Forecasted')
        plt.xlabel('Date')
        plt.ylabel('Patient Volume')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        plot_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        return {
        "evaluation_metrics": {
            "mae": round(mae, 2),
            "mse": round(mse, 2),
            "rmse": round(rmse, 2)
        },
        "comparison_data": comparison_df.reset_index().rename(columns={'index': 'date'}).to_dict('records'),
        "plot_image": plot_base64
    }
    except Exception as e:
        return {"error": f"Patient volume prediction failed: {str(e)}"}

def analyze_performance_factors(df):
    """
    Analyzes factors affecting performance including correlations and trends.
    Returns dictionary with correlation matrix image and trend analysis data.
    """
    results = {}
    
    # Preprocess dates
    df['date_of_admission'] = pd.to_datetime(df['date_of_admission'], errors='coerce')
    df['discharge_date'] = pd.to_datetime(df['discharge_date'], errors='coerce')
    
    # Derive Metrics
    # 1. Length of Stay (Days)
    df['length_of_stay'] = (df['discharge_date'] - df['date_of_admission']).dt.days
    df['length_of_stay'] = df['length_of_stay'].fillna(0).apply(lambda x: max(x, 1)) # Min 1 day
    
    # 2. Age
    if 'age' in df.columns:
        df['age'] = pd.to_numeric(df['age'], errors='coerce').fillna(0)
        
    # 3. Billing Amount (Simulated if not present)
    if 'billing_amount' not in df.columns:
        # Simulate based on LOS and Age
        df['billing_amount'] = df['length_of_stay'] * 1000 + df['age'] * 50
        
    # Select numerical columns for correlation
    numerical_cols = ['age', 'length_of_stay', 'billing_amount']
    corr_df = df[numerical_cols].dropna()
    
    if not corr_df.empty:
        # Correlation Matrix
        corr_matrix = corr_df.corr()
        
        # Generate Heatmap
        plt.figure(figsize=(8, 6))
        plt.imshow(corr_matrix, cmap='coolwarm', interpolation='nearest')
        plt.colorbar()
        tick_marks = [i for i in range(len(corr_matrix.columns))]
        plt.xticks(tick_marks, corr_matrix.columns, rotation=45)
        plt.yticks(tick_marks, corr_matrix.columns)
        plt.title('Performance Factor Correlations')
        
        # Add values to heatmap
        for i in range(len(corr_matrix.columns)):
            for j in range(len(corr_matrix.columns)):
                plt.text(j, i, f"{corr_matrix.iloc[i, j]:.2f}", 
                         ha="center", va="center", color="black")
                         
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        results['correlation_matrix'] = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        # Significant Factors (Correlation > 0.5 with LOS)
        los_corr = corr_matrix['length_of_stay'].drop('length_of_stay')
        significant = los_corr[abs(los_corr) > 0.3].to_dict()
        results['significant_factors'] = significant

    # Trend Analysis (Monthly Average Length of Stay)
    df['month_year'] = df['date_of_admission'].dt.to_period('M')
    monthly_trends = df.groupby('month_year')['length_of_stay'].mean()
    
    if not monthly_trends.empty:
        plt.figure(figsize=(10, 4))
        monthly_trends.plot(kind='line', marker='o')
        plt.title('Average Length of Stay Trend (Monthly)')
        plt.xlabel('Month')
        plt.ylabel('Days')
        plt.grid(True)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        results['trend_chart'] = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        # Raw Data for Table
        results['trend_data'] = monthly_trends.reset_index().astype(str).to_dict('records')
        
    return results


def _preprocess_daily_series(
    df: pd.DataFrame,
    date_col: str,
    count_col: str,
    fill_method: str = 'time'
) -> pd.Series:
    """
    Preprocess input DataFrame into a clean daily time series.

    - Ensures datetime index
    - Sorts chronologically
    - Resamples to daily frequency, summing if multiple entries per day
    - Fills missing days via interpolation or forward/backfill
    """
    ts = df[[date_col, count_col]].copy()
    ts[date_col] = pd.to_datetime(ts[date_col], errors='coerce')
    ts.dropna(subset=[date_col], inplace=True)
    ts = ts.sort_values(by=date_col)
    ts = ts.set_index(date_col)[count_col]

    # Resample to daily frequency
    ts_daily = ts.resample('D').sum()

    # Fill missing values
    try:
        if fill_method == 'time':
            ts_filled = ts_daily.interpolate(method='time')
        elif fill_method == 'ffill':
            ts_filled = ts_daily.ffill().bfill()
        else:
            ts_filled = ts_daily.fillna(0)
    except Exception:
        ts_filled = ts_daily.ffill().bfill()

    # Ensure non-negative and reasonable type
    ts_filled = ts_filled.clip(lower=0)
    return ts_filled.astype(float)


def _sarima_grid_search(
    ts: pd.Series,
    seasonal_period: int = 7,
    p_values = (0, 1, 2),
    d_values = (0, 1),
    q_values = (0, 1, 2),
    P_values = (0, 1),
    D_values = (0, 1),
    Q_values = (0, 1),
    max_models: int = 200
):
    """
    Simple SARIMA grid search selecting the configuration with lowest AIC.
    Returns (order, seasonal_order, best_aic).
    """
    best_cfg = None
    best_aic = np.inf
    tried = 0

    # Suppress common convergence warnings during search
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')

        for p in p_values:
            for d in d_values:
                for q in q_values:
                    for P in P_values:
                        for D in D_values:
                            for Q in Q_values:
                                if tried >= max_models:
                                    break
                                order = (p, d, q)
                                seasonal_order = (P, D, Q, seasonal_period)
                                try:
                                    model = SARIMAX(
                                        ts,
                                        order=order,
                                        seasonal_order=seasonal_order,
                                        enforce_stationarity=False,
                                        enforce_invertibility=False,
                                    )
                                    res = model.fit(disp=False)
                                    aic = res.aic
                                    if aic < best_aic:
                                        best_aic = aic
                                        best_cfg = (order, seasonal_order)
                                except Exception:
                                    pass
                                tried += 1

    # Fallback if search failed
    if best_cfg is None:
        best_cfg = ((1, 1, 1), (1, 1, 1, seasonal_period))
        best_aic = np.nan
    return best_cfg[0], best_cfg[1], best_aic


def _walk_forward_validate(ts: pd.Series, order, seasonal_order, test_size: int = 28):
    """
    Walk-forward validation (expanding window) performing 1-step ahead forecasts.
    Returns metrics and per-step predictions with confidence intervals.
    """
    n = len(ts)
    if n < (test_size + 14):
        # Ensure enough history for reasonable training
        test_size = max(7, min(test_size, n // 3))

    train_end = n - test_size
    predictions = []
    actuals = []
    lowers = []
    uppers = []

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        for i in range(train_end, n):
            train_series = ts.iloc[:i]
            try:
                model = SARIMAX(
                    train_series,
                    order=order,
                    seasonal_order=seasonal_order,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                res = model.fit(disp=False)
                fc = res.get_forecast(steps=1)
                mean = float(fc.predicted_mean.iloc[-1])
                ci = fc.conf_int().iloc[-1]
                lower = float(ci.min())
                upper = float(ci.max())
            except Exception:
                mean = train_series.iloc[-1]
                lower = max(0.0, mean - 1.0)
                upper = mean + 1.0

            predictions.append(mean)
            lowers.append(lower)
            uppers.append(upper)
            actuals.append(float(ts.iloc[i]))

    mae = mean_absolute_error(actuals, predictions)
    rmse = np.sqrt(mean_squared_error(actuals, predictions))

    index = ts.index[-test_size:]
    per_step = [
        {
            'date': idx.strftime('%Y-%m-%d'),
            'actual': round(act, 2),
            'predicted': round(pred, 2),
            'confidence_lower': round(lo, 2),
            'confidence_upper': round(up, 2),
        }
        for idx, act, pred, lo, up in zip(index, actuals, predictions, lowers, uppers)
    ]

    return {
        'mae': round(mae, 2),
        'rmse': round(rmse, 2),
        'per_step': per_step,
    }


def _plot_history_vs_forecast(ts: pd.Series, forecast_df: pd.DataFrame) -> str:
    """
    Plot historical series and forecast horizon; return base64 PNG.
    forecast_df expects columns: 'date', 'predicted', 'confidence_lower', 'confidence_upper'.
    """
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(ts.index, ts.values, label='Historical', color='#286660')

    # Forecast horizon
    dates = pd.to_datetime(forecast_df['date'])
    ax.plot(dates, forecast_df['predicted'], label='Forecast', color='#1976d2')
    ax.fill_between(
        dates,
        forecast_df['confidence_lower'],
        forecast_df['confidence_upper'],
        color='#1976d2', alpha=0.15, label='Confidence Interval'
    )

    ax.set_title('Daily Patient Volume: History vs Forecast')
    ax.set_xlabel('Date')
    ax.set_ylabel('Patients')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.25)

    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format='png')
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def forecast_patient_volumes_sarima(
    df: pd.DataFrame,
    date_col: str = 'date',
    count_col: str = 'patient_count',
    seasonal_period: int = 7,
    test_size_days: int = 28,
    weekly_horizon_weeks: int = 4,
):
    """
    End-to-end SARIMA forecasting pipeline for daily patient volumes.

    Input Requirements:
    - df must contain daily patient totals with columns [date_col, count_col]
    - Data is assumed to be chronological or will be sorted

    Output:
    - Next-day forecast with CI
    - Weekly forecasts (sum over upcoming 7-day periods) with CI (approximate)
    - Walk-forward validation metrics (MAE, RMSE) and per-step predictions
    - Visualization (base64 PNG) comparing history vs forecast horizon
    - Documentation of assumptions and limitations
    """
    if df is None or len(df) == 0:
        return {'error': 'No data provided'}

    ts = _preprocess_daily_series(df, date_col, count_col)
    if len(ts) < 14:
        return {'error': 'Insufficient data for SARIMA (need at least 14 days)'}

    # Parameter search (AIC-based)
    order, seasonal_order, best_aic = _sarima_grid_search(ts, seasonal_period=seasonal_period)

    # Walk-forward validation
    validation = _walk_forward_validate(ts, order, seasonal_order, test_size=test_size_days)

    # Fit on full series with best parameters
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        try:
            model = SARIMAX(
                ts,
                order=order,
                seasonal_order=seasonal_order,
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            res = model.fit(disp=False)
        except Exception as e:
            return {'error': f'Failed to fit final model: {str(e)}'}

    # Next-day forecast
    next_fc = res.get_forecast(steps=1)
    next_mean = float(next_fc.predicted_mean.iloc[-1])
    next_ci = next_fc.conf_int().iloc[-1]
    next_lower = float(next_ci.min())
    next_upper = float(next_ci.max())
    next_date = (ts.index[-1] + pd.Timedelta(days=1)).strftime('%Y-%m-%d')

    # Multi-day horizon for weekly aggregation
    horizon_days = weekly_horizon_weeks * 7
    multi_fc = res.get_forecast(steps=horizon_days)
    multi_mean = multi_fc.predicted_mean
    multi_ci = multi_fc.conf_int()

    # Build daily forecast dataframe for plotting
    daily_forecast_df = pd.DataFrame({
        'date': [ (ts.index[-1] + pd.Timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(horizon_days) ],
        'predicted': [ float(x) for x in multi_mean.values ],
        'confidence_lower': [ float(row.min()) for _, row in multi_ci.iterrows() ],
        'confidence_upper': [ float(row.max()) for _, row in multi_ci.iterrows() ],
    })

    # Aggregate upcoming days into weekly sums (approximate CI aggregation via summation)
    weekly_forecasts = []
    for w in range(weekly_horizon_weeks):
        start_idx = w * 7
        end_idx = start_idx + 7
        week_slice = daily_forecast_df.iloc[start_idx:end_idx]
        if week_slice.empty:
            break
        week_label_start = week_slice['date'].iloc[0]
        week_label_end = week_slice['date'].iloc[-1]
        weekly_forecasts.append({
            'week_range': f"{week_label_start} to {week_label_end}",
            'predicted_total_patients': round(float(week_slice['predicted'].sum()), 2),
            'confidence_lower_sum': round(float(week_slice['confidence_lower'].sum()), 2),
            'confidence_upper_sum': round(float(week_slice['confidence_upper'].sum()), 2),
        })

    # Visualization
    plot_png_b64 = _plot_history_vs_forecast(ts, daily_forecast_df)

    return {
        'model': {
            'order': order,
            'seasonal_order': seasonal_order,
            'seasonal_period': seasonal_period,
            'best_aic': None if np.isnan(best_aic) else round(float(best_aic), 2)
        },
        'validation': validation,
        'next_day_forecast': {
            'date': next_date,
            'predicted_patients': round(next_mean, 2),
            'confidence_lower': round(next_lower, 2),
            'confidence_upper': round(next_upper, 2),
        },
        'weekly_forecasts': weekly_forecasts,
        'daily_forecast_horizon': daily_forecast_df.to_dict('records'),
        'visualization_png_b64': plot_png_b64,
        'assumptions_and_limitations': [
            'Daily seasonality assumed with period s=7 (weekly pattern).',
            'Missing days are interpolated; extreme gaps may affect accuracy.',
            'Weekly confidence interval sums are approximate (sum of daily bounds).',
            'Grid search selects parameters by AIC; alternate criteria may yield different models.',
            'Walk-forward validation uses 1-step refits; computationally intensive for very long series.'
        ],
    }

def predict_illness_surge(df):
    """Predicts illness surge for each medical condition using SARIMA."""
    df['date_of_admission'] = pd.to_datetime(df['date_of_admission'], errors='coerce')
    df.dropna(subset=['date_of_admission'], inplace=True)
    
    df['month_year'] = df['date_of_admission'].dt.to_period('M')
    df_monthly = df.groupby(['month_year', 'medical_condition']).size().unstack(fill_value=0)
    df_monthly.index = df_monthly.index.to_timestamp()
    
    forecast_df = pd.DataFrame()
    evaluation_metrics = {}
    forecast_steps = 6

    for medical_condition in df_monthly.columns:
        ts = df_monthly[medical_condition]
        train_size = int(len(ts) * DEFAULT_TRAIN_RATIO)
        train = ts[:train_size]
        test = ts[train_size:]
        
        try:
            model = SARIMAX(train, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12),
                            enforce_stationarity=False, enforce_invertibility=False)
            results = model.fit(disp=False)
            forecast = results.get_forecast(steps=forecast_steps)
            forecast_values = forecast.predicted_mean
            
            forecast_df[medical_condition] = forecast_values
            
            if len(test) > 0:
                common_index = test.index.intersection(forecast_values.index)
                if len(common_index) > 0:
                    actual = test[common_index]
                    predicted = forecast_values[common_index]
                    
                    mae = mean_absolute_error(actual, predicted)
                    mse = mean_squared_error(actual, predicted)
                    rmse = np.sqrt(mse)
                    evaluation_metrics[medical_condition] = {
                        'mae': round(mae, 2), 'mse': round(mse, 2), 'rmse': round(rmse, 2)
                    }
        except Exception:
            evaluation_metrics[medical_condition] = {'error': 'Failed to fit model'}

    forecast_json = forecast_df.reset_index().rename(columns={'index': 'date'}).to_dict('records')
    
    return {
        "forecasted_monthly_cases": forecast_json,
        "evaluation_metrics": evaluation_metrics
    }

def predict_weekly_illness_forecast(df):
    """Predicts specific illnesses that will occur in the following weeks."""
    df['date_of_admission'] = pd.to_datetime(df['date_of_admission'], errors='coerce')
    df.dropna(subset=['date_of_admission'], inplace=True)
    
    # Group by week and medical condition
    df['week_year'] = df['date_of_admission'].dt.to_period('W')
    df_weekly = df.groupby(['week_year', 'medical_condition']).size().unstack(fill_value=0)
    df_weekly.index = df_weekly.index.to_timestamp()
    
    forecast_df = pd.DataFrame()
    evaluation_metrics = {}
    forecast_steps = 8  # Predict next 8 weeks
    
    illness_predictions = []
    
    for medical_condition in df_weekly.columns:
        ts = df_weekly[medical_condition]
        if len(ts) < 4:  # Need at least 4 weeks of data
            continue
            
        train_size = int(len(ts) * DEFAULT_TRAIN_RATIO)
        train = ts[:train_size]
        test = ts[train_size:]
        
        try:
            # Use simpler model for weekly data
            model = SARIMAX(train, order=(1, 1, 1), seasonal_order=(1, 1, 1, 4),
                            enforce_stationarity=False, enforce_invertibility=False)
            results = model.fit(disp=False)
            forecast = results.get_forecast(steps=forecast_steps)
            forecast_values = forecast.predicted_mean
            
            forecast_df[medical_condition] = forecast_values
            
            # Calculate confidence intervals
            confidence_intervals = forecast.conf_int()
            
            # Create weekly predictions with confidence
            for i, (date, predicted_cases) in enumerate(forecast_values.items()):
                if predicted_cases > 0:  # Only include predictions with expected cases
                    lower_bound = confidence_intervals.iloc[i, 0]
                    upper_bound = confidence_intervals.iloc[i, 1]
                    
                    illness_predictions.append({
                        'illness': medical_condition,
                        'week': date.strftime('%Y-%m-%d'),
                        'predicted_cases': round(predicted_cases, 1),
                        'confidence_lower': round(lower_bound, 1),
                        'confidence_upper': round(upper_bound, 1),
                        'risk_level': 'High' if predicted_cases > ts.mean() * 1.5 else 'Medium' if predicted_cases > ts.mean() else 'Low'
                    })
            
            if len(test) > 0:
                common_index = test.index.intersection(forecast_values.index)
                if len(common_index) > 0:
                    actual = test[common_index]
                    predicted = forecast_values[common_index]
                    
                    mae = mean_absolute_error(actual, predicted)
                    mse = mean_squared_error(actual, predicted)
                    rmse = np.sqrt(mse)
                    evaluation_metrics[medical_condition] = {
                        'mae': round(mae, 2), 'mse': round(mse, 2), 'rmse': round(rmse, 2)
                    }
        except Exception as e:
            evaluation_metrics[medical_condition] = {'error': f'Failed to fit model: {str(e)}'}

    # Sort predictions by predicted cases (highest risk first)
    illness_predictions.sort(key=lambda x: x['predicted_cases'], reverse=True)
    
    return {
        "weekly_illness_forecast": illness_predictions,
        "evaluation_metrics": evaluation_metrics,
        "summary": {
            "total_predictions": len(illness_predictions),
            "high_risk_illnesses": len([p for p in illness_predictions if p['risk_level'] == 'High']),
            "medium_risk_illnesses": len([p for p in illness_predictions if p['risk_level'] == 'Medium']),
            "low_risk_illnesses": len([p for p in illness_predictions if p['risk_level'] == 'Low'])
        }
    }

def predict_monthly_illness_forecast(df):
    """Predicts specific illnesses that will occur in the following months."""
    df['date_of_admission'] = pd.to_datetime(df['date_of_admission'], errors='coerce')
    df.dropna(subset=['date_of_admission'], inplace=True)
    
    # Group by month and medical condition
    df['month_year'] = df['date_of_admission'].dt.to_period('M')
    df_monthly = df.groupby(['month_year', 'medical_condition']).size().unstack(fill_value=0)
    df_monthly.index = df_monthly.index.to_timestamp()
    
    forecast_df = pd.DataFrame()
    evaluation_metrics = {}
    forecast_steps = 6  # Predict next 6 months
    
    illness_predictions = []
    
    for medical_condition in df_monthly.columns:
        ts = df_monthly[medical_condition]
        if len(ts) < 3:  # Need at least 3 months of data
            continue
            
        train_size = int(len(ts) * DEFAULT_TRAIN_RATIO)
        train = ts[:train_size]
        test = ts[train_size:]
        
        try:
            model = SARIMAX(train, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12),
                            enforce_stationarity=False, enforce_invertibility=False)
            results = model.fit(disp=False)
            forecast = results.get_forecast(steps=forecast_steps)
            forecast_values = forecast.predicted_mean
            
            forecast_df[medical_condition] = forecast_values
            
            # Calculate confidence intervals
            confidence_intervals = forecast.conf_int()
            
            # Create monthly predictions with confidence
            for i, (date, predicted_cases) in enumerate(forecast_values.items()):
                if predicted_cases > 0:  # Only include predictions with expected cases
                    lower_bound = confidence_intervals.iloc[i, 0]
                    upper_bound = confidence_intervals.iloc[i, 1]
                    
                    # Determine risk level based on historical average
                    historical_avg = ts.mean()
                    if predicted_cases > historical_avg * 2:
                        risk_level = 'Critical'
                    elif predicted_cases > historical_avg * 1.5:
                        risk_level = 'High'
                    elif predicted_cases > historical_avg:
                        risk_level = 'Medium'
                    else:
                        risk_level = 'Low'
                    
                    illness_predictions.append({
                        'illness': medical_condition,
                        'month': date.strftime('%Y-%m'),
                        'predicted_cases': round(predicted_cases, 1),
                        'confidence_lower': round(lower_bound, 1),
                        'confidence_upper': round(upper_bound, 1),
                        'risk_level': risk_level,
                        'trend': 'Increasing' if predicted_cases > historical_avg else 'Stable' if predicted_cases > historical_avg * 0.8 else 'Decreasing'
                    })
            
            if len(test) > 0:
                common_index = test.index.intersection(forecast_values.index)
                if len(common_index) > 0:
                    actual = test[common_index]
                    predicted = forecast_values[common_index]
                    
                    mae = mean_absolute_error(actual, predicted)
                    mse = mean_squared_error(actual, predicted)
                    rmse = np.sqrt(mse)
                    evaluation_metrics[medical_condition] = {
                        'mae': round(mae, 2), 'mse': round(mse, 2), 'rmse': round(rmse, 2)
                    }
        except Exception as e:
            evaluation_metrics[medical_condition] = {'error': f'Failed to fit model: {str(e)}'}

    # Sort predictions by predicted cases (highest risk first)
    illness_predictions.sort(key=lambda x: x['predicted_cases'], reverse=True)
    
    return {
        "monthly_illness_forecast": illness_predictions,
        "evaluation_metrics": evaluation_metrics,
        "summary": {
            "total_predictions": len(illness_predictions),
            "critical_risk_illnesses": len([p for p in illness_predictions if p['risk_level'] == 'Critical']),
            "high_risk_illnesses": len([p for p in illness_predictions if p['risk_level'] == 'High']),
            "medium_risk_illnesses": len([p for p in illness_predictions if p['risk_level'] == 'Medium']),
            "low_risk_illnesses": len([p for p in illness_predictions if p['risk_level'] == 'Low'])
        }
    }
    
def run_full_analysis():
    """Master function to run the full predictive analysis pipeline."""
    # Assuming this function is called from a Django view or Celery task.
    # We must access the model from a Django context.
    from .models import PatientRecord 
    queryset = PatientRecord.objects.all()
    df = get_data_from_queryset(queryset)
    
    if df.empty:
        return {"error": "No data available for analysis."}
    
    # Clean and rename columns to be consistent with the original notebook
    df.columns = df.columns.str.lower().str.replace(' ', '_')
    
    # Call all analytical functions
    results = {
        "patient_health_trends": perform_patient_health_trends(df),
        "patient_demographics": analyze_patient_demographics(df),
        "illness_prediction_chi_square": analyze_illness_prediction_chi_square(df),
        "common_medications": analyze_common_medications(df),
        "predictive_analytics": predict_patient_volume(df),
        "illness_surge_prediction": predict_illness_surge(df),
        "weekly_illness_forecast": predict_weekly_illness_forecast(df),
        "monthly_illness_forecast": predict_monthly_illness_forecast(df),
        "performance_factors": analyze_performance_factors(df)
    }
    return results

if __name__ == "__main__":
    try:
        # This block is for direct execution (e.g., via subprocess)
        # It's a placeholder for local testing and requires a way to mock a Django environment
        # to access the models. For a real setup, this would be run by the Django view/Celery task.
        print(json.dumps({"info": "This script is designed to be run within a Django context."}, indent=4))
        
    except Exception as e:
        print(json.dumps({"error": f"An error occurred: {str(e)}"}))