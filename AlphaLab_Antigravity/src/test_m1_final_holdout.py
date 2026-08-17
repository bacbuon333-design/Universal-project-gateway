from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from m1_final_holdout.confirmation import (
    BOOTSTRAP_ITERATIONS, HOLDOUT_YEARS, REPRESENTATIONS,
    _holdout_control_matrix, day_block_bootstrap, evaluate_final_holdout_gates,
    fit_holdout_payload, joint_max_rho_day_block_bootstrap, validate_holdout_frame,
)


def bars(start="2015-01-01T00:00:00Z",n=20):
    dt=pd.date_range(start,periods=n,freq="min")
    return pd.DataFrame({"datetime":dt,"open":100.0,"high":100.2,"low":99.8,"close":100.0})


def payload(n=600,rho=.94):
    dt=pd.date_range("2015-01-01T00:00:00Z",periods=n,freq="12h"); x=np.linspace(.05,1.5,n)
    return pd.DataFrame({"datetime":dt,"_x":x,"_y":rho*x+.2,"_exc_control":.2+(np.arange(n)%7)*.03,
        "atr_percentile":20+(np.arange(n)%70),"path_efficiency":.1+(np.arange(n)%8)/10,
        "stretch_abs":.2+(np.arange(n)%9)/3,"location_count":np.arange(n)%3,
        "side":np.where(np.arange(n)%2==0,"LONG","SHORT"),"hour":dt.hour,
        "year":np.resize(np.array([2015,2016,2017]),n)})


def gate_frame(n=120000):
    return pd.DataFrame({"exact_5m_available":np.ones(n,dtype=bool),"breach_excursion_atr":np.full(n,.2),
        "atr14":np.ones(n),"pre_event_atr14":np.ones(n),"prior_extreme":np.full(n,100.),
        "in_candle_reversion_atr":np.full(n,.4),"total_reversion_atr_5m":np.full(n,.5),
        "atr_percentile":np.full(n,50.),"path_efficiency":np.full(n,.5),"stretch_abs":np.ones(n),
        "location_count":np.zeros(n),"side":np.where(np.arange(n)%2==0,"LONG","SHORT"),"hour":np.zeros(n),
        "year":np.resize(np.array([2015,2016,2017]),n),"datetime":pd.date_range("2015-01-01",periods=n,freq="min")})


def good_audit():
    return {"rows":900000,"years":[2015,2016,2017],"duplicate_timestamps":0,"non_whole_minute_timestamps":0,
            "invalid_or_nonfinite_ohlc":0,"per_year_row_sufficiency":True}


def test_holdout_validator_accepts_only_three_year_range():
    df=pd.concat([bars("2015-01-01"),bars("2016-01-01"),bars("2017-01-01")],ignore_index=True).sort_values("datetime")
    validate_holdout_frame(df,require_all_years=True)


def test_holdout_validator_blocks_2018():
    with pytest.raises(RuntimeError): validate_holdout_frame(bars("2018-01-01"),require_all_years=False)


def test_holdout_validator_blocks_pre2015():
    with pytest.raises(RuntimeError): validate_holdout_frame(bars("2014-12-31T23:00:00Z"),require_all_years=False)


def test_holdout_years_frozen(): assert HOLDOUT_YEARS==(2015,2016,2017)
def test_four_coordinates_frozen(): assert REPRESENTATIONS==("ATR_T","ATR_PRE","PRICE_BPS","EXCURSION_RATIO")


def test_controls_have_2016_2017_not_development_dummies():
    _,names=_holdout_control_matrix(payload(100),True)
    assert "year_2016" in names and "year_2017" in names
    assert "year_2018" not in names and "year_2025" not in names


def test_fwl_recovers_frozen_direction():
    f=fit_holdout_payload(payload(600,.93)); assert abs(f["rho"]-.93)<1e-10


def test_day_bootstrap_deterministic():
    f=fit_holdout_payload(payload(),return_residuals=True)
    assert day_block_bootstrap(f,iterations=100,seed=123)==day_block_bootstrap(f,iterations=100,seed=123)


def test_joint_bootstrap_uses_all_coordinates():
    fits={r:fit_holdout_payload(payload(600,.92+i*.01),return_residuals=True) for i,r in enumerate(REPRESENTATIONS)}
    out=joint_max_rho_day_block_bootstrap(fits,iterations=100,seed=321)
    assert out["valid_iterations"]==100 and set(out["observed_rho_by_representation"])==set(REPRESENTATIONS)


def test_final_pass_requires_individual_and_joint_confirmation():
    conf=pd.DataFrame([{"representation":r,"horizon_min":5,"rho":.95,"ci95_upper":.98} for r in REPRESENTATIONS])
    boots={r:{"valid_iterations":BOOTSTRAP_ITERATIONS} for r in REPRESENTATIONS}
    joint={"valid_iterations":BOOTSTRAP_ITERATIONS,"bootstrap_ci95_upper_max_rho":.99}
    g=evaluate_final_holdout_gates(good_audit(),gate_frame(),conf,boots,joint)
    assert g["verdict"]=="FINAL_HOLDOUT_CONFIRMED"


def test_valid_data_scientific_failure_closes_family_rejected():
    conf=pd.DataFrame([{"representation":r,"horizon_min":5,"rho":1.01 if r=="PRICE_BPS" else .95,"ci95_upper":1.03 if r=="PRICE_BPS" else .98} for r in REPRESENTATIONS])
    boots={r:{"valid_iterations":BOOTSTRAP_ITERATIONS} for r in REPRESENTATIONS}
    joint={"valid_iterations":BOOTSTRAP_ITERATIONS,"bootstrap_ci95_upper_max_rho":1.03}
    g=evaluate_final_holdout_gates(good_audit(),gate_frame(),conf,boots,joint)
    assert g["verdict"]=="FINAL_HOLDOUT_REJECTED"
    assert g["research_program_status"]=="CLOSE_REJECTED_MECHANISM_FAMILY"


def test_runner_has_no_development_dataset_or_execution_surface():
    text=Path(__file__).with_name("run_m1_final_holdout.py").read_text(encoding="utf-8").lower()
    forbidden=("gold_m1_pre2026","order_send","order_check","paper_trade","live_trade")
    assert not any(x in text for x in forbidden)


def test_runner_has_no_gradient_or_placebo_rescue():
    text=Path(__file__).with_name("run_m1_final_holdout.py").read_text(encoding="utf-8").lower()
    assert "qcut" not in text and "within_day_side_cyclic" not in text and "balanced_post_sign" not in text


def test_runner_blocks_inference_before_coverage_gate():
    text=Path(__file__).with_name("run_m1_final_holdout.py").read_text(encoding="utf-8")
    assert "pre_inference_coverage_ok" in text
    assert "NOT_RUN_PRE_INFERENCE_COVERAGE_BLOCK" in text
    assert text.index("pre_inference_coverage_ok") < text.index("build_confirmation_table(frame)")


def test_extractor_contains_one_shot_failure_marker_contract():
    text=Path(__file__).with_name("extract_m1_final_holdout.py").read_text(encoding="utf-8")
    assert "STOP_BLOCKED_HOLDOUT_ALREADY_OPENED_OR_EXTRACTED" in text
    assert "HOLDOUT_OPENED_FAILURE_DO_NOT_RERUN" in text
    assert "copy_rates_range" in text and '"interpolation":False' in text


def test_extractor_fails_canonical_quality_before_seal_replace():
    text=Path(__file__).with_name("extract_m1_final_holdout.py").read_text(encoding="utf-8")
    assert "STOP_BLOCKED_HOLDOUT_CANONICAL_QUALITY_FAILED" in text
    assert text.index("STOP_BLOCKED_HOLDOUT_CANONICAL_QUALITY_FAILED") < text.index("os.replace(td,DATA_PATH)")
