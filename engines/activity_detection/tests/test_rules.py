"""
Tests for ActivityRules and ACTIVITY_METADATA.
"""

import pytest

from engines.activity_detection.rules import (
    ActivityRules, ACTIVITY_METADATA, ACTIVITY_PRIORITY,
)


class TestActivityMetadata:
    def test_all_activities_have_metadata(self):
        expected = ['normal', 'running', 'fighting', 'falling', 'loitering']
        for activity in expected:
            assert activity in ACTIVITY_METADATA
            assert 'severity' in ACTIVITY_METADATA[activity]
            assert 'is_abnormal' in ACTIVITY_METADATA[activity]

    def test_normal_is_not_abnormal(self):
        assert ACTIVITY_METADATA['normal']['is_abnormal'] is False

    def test_fighting_is_high_severity(self):
        assert ACTIVITY_METADATA['fighting']['severity'] == 'high'

    def test_falling_is_high_severity(self):
        assert ACTIVITY_METADATA['falling']['severity'] == 'high'


class TestActivityPriority:
    def test_fighting_highest(self):
        assert ACTIVITY_PRIORITY['fighting'] > ACTIVITY_PRIORITY['falling']
        assert ACTIVITY_PRIORITY['fighting'] > ACTIVITY_PRIORITY['running']

    def test_normal_lowest(self):
        assert ACTIVITY_PRIORITY['normal'] == 0


class TestActivityRules:
    def test_default_values(self):
        rules = ActivityRules()
        assert rules.falling_angle == 65.0
        assert rules.falling_persistence == 3
        assert rules.falling_window == 5
        assert rules.falling_hip_offset == 80.0
        assert rules.falling_hip_angle_req == 50.0
        assert rules.running_velocity == 25.0
        assert rules.fighting_proximity == 80.0
        assert rules.loiter_duration == 60.0

    def test_custom_override(self):
        rules = ActivityRules(
            falling_angle=80.0,
            fighting_proximity=50.0,
            loiter_duration=120.0,
        )
        assert rules.falling_angle == 80.0
        assert rules.fighting_proximity == 50.0
        assert rules.loiter_duration == 120.0
        # Other defaults unchanged
        assert rules.running_velocity == 25.0
