import pytest

from core.cache import AnalysisCache, build_cache_key
from core.models import EDFMetadata
from core.parameters import AnalysisParameters, DisplayParameters, validate_analysis_parameters, validate_display_parameters
from core.errors import ParameterValidationError


def _metadata():
    return EDFMetadata(
        file_path="samples/phantom.edf",
        file_name="phantom.edf",
        channel_names=["sine"],
        sfreq_by_channel={"sine": 100.0},
        duration_s=300.0,
        n_samples_by_channel={"sine": 30000},
    )


def test_valid_default_parameters_pass():
    validate_analysis_parameters(AnalysisParameters(), _metadata(), channel_name="sine")


def test_invalid_window_fails():
    params = AnalysisParameters(window_start_s=290.0, window_length_s=20.0)
    with pytest.raises(ParameterValidationError):
        validate_analysis_parameters(params, _metadata(), channel_name="sine")


def test_invalid_filter_fails():
    params = AnalysisParameters(
        filter_enabled=True,
        filter_type="band_pass",
        low_cut_hz=5.0,
        high_cut_hz=4.0,
    )
    with pytest.raises(ParameterValidationError):
        validate_analysis_parameters(params, _metadata(), channel_name="sine")


def test_band_stop_filter_parameters_validate():
    params = AnalysisParameters(
        filter_enabled=True,
        filter_type="band_stop",
        low_cut_hz=4.0,
        high_cut_hz=8.0,
        filter_family="ellip",
        filter_ripple_db=1.0,
        filter_stop_atten_db=40.0,
    )

    validate_analysis_parameters(params, _metadata(), channel_name="sine")


def test_invalid_filter_family_fails():
    params = AnalysisParameters(
        filter_enabled=True,
        filter_type="low_pass",
        high_cut_hz=8.0,
        filter_family="not-a-family",
    )
    with pytest.raises(ParameterValidationError):
        validate_analysis_parameters(params, _metadata(), channel_name="sine")


def test_invalid_filter_ripple_and_attenuation_fail():
    ripple = AnalysisParameters(
        filter_enabled=True,
        filter_type="low_pass",
        high_cut_hz=8.0,
        filter_family="cheby1",
        filter_ripple_db=0.0,
    )
    attenuation = AnalysisParameters(
        filter_enabled=True,
        filter_type="low_pass",
        high_cut_hz=8.0,
        filter_family="cheby2",
        filter_stop_atten_db=0.0,
    )
    with pytest.raises(ParameterValidationError):
        validate_analysis_parameters(ripple, _metadata(), channel_name="sine")
    with pytest.raises(ParameterValidationError):
        validate_analysis_parameters(attenuation, _metadata(), channel_name="sine")


def test_display_manual_color_range_fails():
    with pytest.raises(ParameterValidationError):
        validate_display_parameters(
            DisplayParameters(color_range_mode="manual", color_min=1.0, color_max=1.0)
        )


def test_display_plot_specific_manual_color_ranges_validate():
    validate_display_parameters(
        DisplayParameters(
            scalogram_color_range_mode="manual",
            scalogram_color_min=0.1,
            scalogram_color_max=2.0,
            spectrogram_color_range_mode="manual",
            spectrogram_color_min=-80.0,
            spectrogram_color_max=-10.0,
        )
    )


def test_display_plot_specific_manual_color_range_fails_when_partial():
    with pytest.raises(ParameterValidationError):
        validate_display_parameters(
            DisplayParameters(
                scalogram_color_range_mode="manual",
                scalogram_color_min=0.1,
            )
        )


def test_analysis_plot_specific_manual_color_range_fails_when_inverted():
    params = AnalysisParameters(
        spectrogram_color_range_mode="manual",
        spectrogram_color_min=1.0,
        spectrogram_color_max=1.0,
    )
    with pytest.raises(ParameterValidationError):
        validate_analysis_parameters(params, _metadata(), channel_name="sine")


def test_analysis_cache_lru_and_parameter_key():
    cache = AnalysisCache(max_size=1)
    p1 = AnalysisParameters(window_start_s=0.0)
    p2 = AnalysisParameters(window_start_s=10.0)
    k1 = build_cache_key("x.edf", "sine", p1)
    k2 = build_cache_key("x.edf", "sine", p2)
    assert k1 != k2
    cache.put(k1, "first")
    cache.put(k2, "second")
    assert cache.get(k1) is None
    assert cache.get(k2) == "second"
    cache.clear()
    assert len(cache) == 0


def test_filter_family_parameters_change_cache_key():
    base = AnalysisParameters(
        filter_enabled=True,
        filter_type="low_pass",
        high_cut_hz=8.0,
        filter_family="butter",
    )
    family = AnalysisParameters(
        filter_enabled=True,
        filter_type="low_pass",
        high_cut_hz=8.0,
        filter_family="cheby1",
    )
    ripple = AnalysisParameters(
        filter_enabled=True,
        filter_type="low_pass",
        high_cut_hz=8.0,
        filter_family="cheby1",
        filter_ripple_db=2.0,
    )

    assert build_cache_key("x.edf", "sine", base) != build_cache_key("x.edf", "sine", family)
    assert build_cache_key("x.edf", "sine", family) != build_cache_key("x.edf", "sine", ripple)
