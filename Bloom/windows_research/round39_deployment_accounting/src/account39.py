"""Exact incremental-call accounting and explicit, conditional time extrapolation."""
import math

SCENARIOS=(
    dict(name='calls_only',startup_s=0.,backend_us=10.,processing_delta_us=0.,member_share=0.),
    dict(name='startup_1s_backend_10us',startup_s=1.,backend_us=10.,processing_delta_us=0.,member_share=.1),
    dict(name='startup_1s_backend_40us',startup_s=1.,backend_us=40.,processing_delta_us=.1,member_share=.1),
    dict(name='startup_10s_backend_40us',startup_s=10.,backend_us=40.,processing_delta_us=.1,member_share=.1),
    dict(name='startup_1s_backend_100us',startup_s=1.,backend_us=100.,processing_delta_us=.1,member_share=.1),
    dict(name='positive_90pct',startup_s=1.,backend_us=40.,processing_delta_us=.1,member_share=.9),
)


def calls(learning_negatives,tail_negatives,baseline_learning_calls,baseline_tail_calls,ra_tail_calls,shared_learning=False):
    values=(learning_negatives,tail_negatives,baseline_learning_calls,baseline_tail_calls,ra_tail_calls)
    if any(not isinstance(x,int) for x in values) or min(learning_negatives,tail_negatives)<=0:
        raise ValueError('Integer counts and nonempty windows required')
    if not (0<=baseline_learning_calls<=learning_negatives and 0<=baseline_tail_calls<=tail_negatives and 0<=ra_tail_calls<=tail_negatives):
        raise ValueError('Backend-call counts outside query bounds')
    extra=0 if shared_learning else learning_negatives-baseline_learning_calls
    saving=baseline_tail_calls-ra_tail_calls
    return dict(extra_learning_backend_calls=extra,tail_backend_calls_saved=saving,
                net_backend_calls_saved_after_one_window=saving-extra,
                saving_per_negative_query=saving/tail_negatives,
                backend_only_break_even_negative_queries=extra/(saving/tail_negatives) if saving>0 else None,
                observed_window_negative_queries=tail_negatives,
                shared_learning=shared_learning)


def project(account,startup_s,backend_us,processing_delta_us,member_share):
    if not all(math.isfinite(x) for x in (startup_s,backend_us,processing_delta_us,member_share)):
        raise ValueError('Finite scenario parameters required')
    if startup_s<0 or backend_us<0 or not 0<=member_share<1:
        raise ValueError('Nonnegative startup/backend and member share in [0,1) required')
    startup=startup_s+account['extra_learning_backend_calls']*backend_us/1e6
    benefit=(1-member_share)*account['saving_per_negative_query']*backend_us-processing_delta_us
    window=account['observed_window_negative_queries']/(1-member_share)
    if benefit>0:
        break_even=math.ceil(startup*1e6/benefit)
        status='positive_slope'
    elif startup==0 and benefit==0:
        break_even=0;status='flat_equal'
    else:break_even=None;status='no_amortization_at_constant_rates'
    return dict(status=status,incremental_startup_and_learning_s=startup,benefit_us_per_total_query=benefit,
                break_even_total_queries=break_even,projected_total_queries_in_observed_negative_window=window,
                projected_RA_minus_baseline_s_at_window=startup-window*benefit/1e6)


def required_index_bytes(mode,cache_bytes,members,array_header_bytes):
    if mode not in ('index','fp64') or min(cache_bytes,members,array_header_bytes)<0:
        raise ValueError('Invalid resource inputs')
    return 8*members+array_header_bytes if mode=='index' and cache_bytes>0 else 0
