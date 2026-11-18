"""Reject the misapplied-cache failure class with synthetic metadata only."""
import copy
import unittest
from report16 import check_configuration, CACHES


class ConfigurationChecks(unittest.TestCase):
    def good(self,regime='fit'):
        return dict(cache_regime=regime,block_cache_capacity=CACHES[regime],block_cache_usage=1000000,method='Direct',
                    configuration_check=dict(effective_cache_capacity=CACHES[regime],explicit_default_column_family=True,
                                             cache_object_equals_db_usage=True,bloom_useful_of_2000_misses=1983,
                                             positive_probe_hit_rate=1. if regime=='fit' else .0005),
                    rocksdb_statistics_delta={'rocksdb.bloom.filter.useful':10000})

    def rejects(self,r):
        with self.assertRaises(AssertionError):check_configuration(r)

    def test_valid_both_regimes(self):
        for regime in CACHES:check_configuration(self.good(regime))

    def test_unused_supplied_cache(self):
        r=self.good();r['block_cache_usage']=0;self.rejects(r)

    def test_requested_capacity_without_effective_capacity(self):
        r=self.good();r['configuration_check']['effective_cache_capacity']=CACHES['pressure'];self.rejects(r)

    def test_bloom_disabled_in_precheck(self):
        r=self.good();r['configuration_check']['bloom_useful_of_2000_misses']=0;self.rejects(r)

    def test_bloom_unused_during_direct_measurement(self):
        r=self.good();r['rocksdb_statistics_delta']['rocksdb.bloom.filter.useful']=0;self.rejects(r)

    def test_fit_regime_did_not_fit(self):
        r=self.good();r['configuration_check']['positive_probe_hit_rate']=.1;self.rejects(r)

    def test_pressure_regime_was_resident(self):
        r=self.good('pressure');r['configuration_check']['positive_probe_hit_rate']=1.;self.rejects(r)

    def test_cache_object_not_database_cache(self):
        r=self.good();r['configuration_check']['cache_object_equals_db_usage']=False;self.rejects(r)


if __name__=='__main__':unittest.main()
