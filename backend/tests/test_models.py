"""
Unit tests for backend/models.py

Tests cover the UserProfile, HRZonesData, and AbilityAssessment dataclass validation:
  - Valid profiles and HR zones data are accepted
  - Age validation (10-100 range)
  - Ability level validation (beginner, intermediate, advanced, elite)
  - Nationality and locality length validation
  - HR zones validation (non-negative times, percentages sum to ~100%, valid boundaries)
  - AbilityAssessment validation (string length constraints for all fields)
"""
import pytest

from backend.models import UserProfile, HRZonesData, AbilityAssessment, Session, TrainingPlan


class TestUserProfileValidation:
    """UserProfile dataclass validation tests."""

    def test_valid_profile(self):
        """Valid UserProfile with all fields populated should be accepted."""
        profile = UserProfile(
            age=25,
            nationality="United States",
            locality="California",
            ability_level="intermediate"
        )
        assert profile.age == 25
        assert profile.nationality == "United States"
        assert profile.locality == "California"
        assert profile.ability_level == "intermediate"

    def test_age_below_minimum_raises_error(self):
        """Age below 10 should raise ValueError."""
        with pytest.raises(ValueError, match="age must be between 10 and 100"):
            UserProfile(
                age=9,
                nationality="USA",
                locality="NYC",
                ability_level="beginner"
            )

    def test_age_above_maximum_raises_error(self):
        """Age above 100 should raise ValueError."""
        with pytest.raises(ValueError, match="age must be between 10 and 100"):
            UserProfile(
                age=101,
                nationality="USA",
                locality="NYC",
                ability_level="beginner"
            )

    def test_age_at_minimum_boundary(self):
        """Age exactly 10 should be accepted."""
        profile = UserProfile(
            age=10,
            nationality="USA",
            locality="NYC",
            ability_level="beginner"
        )
        assert profile.age == 10

    def test_age_at_maximum_boundary(self):
        """Age exactly 100 should be accepted."""
        profile = UserProfile(
            age=100,
            nationality="USA",
            locality="NYC",
            ability_level="elite"
        )
        assert profile.age == 100

    def test_invalid_ability_level_raises_error(self):
        """Invalid ability level should raise ValueError."""
        with pytest.raises(ValueError, match="ability_level must be one of"):
            UserProfile(
                age=25,
                nationality="USA",
                locality="NYC",
                ability_level="expert"
            )

    def test_ability_level_case_insensitive(self):
        """Ability level validation should be case-insensitive."""
        profile1 = UserProfile(
            age=25,
            nationality="USA",
            locality="NYC",
            ability_level="Beginner"
        )
        assert profile1.ability_level == "Beginner"

        profile2 = UserProfile(
            age=25,
            nationality="USA",
            locality="NYC",
            ability_level="INTERMEDIATE"
        )
        assert profile2.ability_level == "INTERMEDIATE"

    def test_empty_nationality_raises_error(self):
        """Empty nationality string should raise ValueError."""
        with pytest.raises(ValueError, match="nationality must be 1-100 characters if provided"):
            UserProfile(
                age=25,
                nationality="",
                locality="NYC",
                ability_level="beginner"
            )

    def test_nationality_exceeds_max_length_raises_error(self):
        """Nationality exceeding 100 characters should raise ValueError."""
        long_nationality = "a" * 101
        with pytest.raises(ValueError, match="nationality must be 1-100 characters if provided"):
            UserProfile(
                age=25,
                nationality=long_nationality,
                locality="NYC",
                ability_level="beginner"
            )

    def test_nationality_at_max_length(self):
        """Nationality exactly 100 characters should be accepted."""
        nationality = "a" * 100
        profile = UserProfile(
            age=25,
            nationality=nationality,
            locality="NYC",
            ability_level="beginner"
        )
        assert len(profile.nationality) == 100

    def test_empty_locality_raises_error(self):
        """Empty locality string should raise ValueError."""
        with pytest.raises(ValueError, match="locality must be 1-100 characters if provided"):
            UserProfile(
                age=25,
                nationality="USA",
                locality="",
                ability_level="beginner"
            )

    def test_locality_exceeds_max_length_raises_error(self):
        """Locality exceeding 100 characters should raise ValueError."""
        long_locality = "a" * 101
        with pytest.raises(ValueError, match="locality must be 1-100 characters if provided"):
            UserProfile(
                age=25,
                nationality="USA",
                locality=long_locality,
                ability_level="beginner"
            )

    def test_locality_at_max_length(self):
        """Locality exactly 100 characters should be accepted."""
        locality = "a" * 100
        profile = UserProfile(
            age=25,
            nationality="USA",
            locality=locality,
            ability_level="beginner"
        )
        assert len(profile.locality) == 100

    def test_all_ability_levels_accepted(self):
        """All valid ability levels should be accepted."""
        valid_levels = ["beginner", "intermediate", "advanced", "elite"]
        for level in valid_levels:
            profile = UserProfile(
                age=25,
                nationality="USA",
                locality="NYC",
                ability_level=level
            )
            assert profile.ability_level == level


class TestHRZonesDataValidation:
    """HRZonesData dataclass validation tests."""

    def test_valid_hr_zones_data(self):
        """Valid HRZonesData with all fields populated should be accepted."""
        hr_zones = HRZonesData(
            zone_1_seconds=300,
            zone_2_seconds=600,
            zone_3_seconds=900,
            zone_4_seconds=300,
            zone_5_seconds=100,
            zone_1_percent=13.6,
            zone_2_percent=27.3,
            zone_3_percent=40.9,
            zone_4_percent=13.6,
            zone_5_percent=4.5,
            max_hr=180,
            zone_boundaries={
                1: (90, 108),
                2: (108, 126),
                3: (126, 144),
                4: (144, 162),
                5: (162, 180)
            }
        )
        assert hr_zones.zone_1_seconds == 300
        assert hr_zones.max_hr == 180
        assert hr_zones.zone_boundaries[1] == (90, 108)

    def test_negative_zone_time_raises_error(self):
        """Negative zone time should raise ValueError."""
        with pytest.raises(ValueError, match="zone_1_seconds must be non-negative"):
            HRZonesData(
                zone_1_seconds=-10,
                zone_2_seconds=600,
                zone_3_seconds=900,
                zone_4_seconds=300,
                zone_5_seconds=100,
                zone_1_percent=0.0,
                zone_2_percent=30.0,
                zone_3_percent=45.0,
                zone_4_percent=15.0,
                zone_5_percent=10.0,
                max_hr=180,
                zone_boundaries={
                    1: (90, 108),
                    2: (108, 126),
                    3: (126, 144),
                    4: (144, 162),
                    5: (162, 180)
                }
            )

    def test_negative_zone_percentage_raises_error(self):
        """Negative zone percentage should raise ValueError."""
        with pytest.raises(ValueError, match="zone_2_percent must be non-negative"):
            HRZonesData(
                zone_1_seconds=300,
                zone_2_seconds=600,
                zone_3_seconds=900,
                zone_4_seconds=300,
                zone_5_seconds=100,
                zone_1_percent=15.0,
                zone_2_percent=-5.0,
                zone_3_percent=45.0,
                zone_4_percent=15.0,
                zone_5_percent=30.0,
                max_hr=180,
                zone_boundaries={
                    1: (90, 108),
                    2: (108, 126),
                    3: (126, 144),
                    4: (144, 162),
                    5: (162, 180)
                }
            )

    def test_percentages_sum_below_range_raises_error(self):
        """Individual percentages must be non-negative."""
        with pytest.raises(ValueError, match="must be non-negative"):
            HRZonesData(
                zone_1_seconds=300,
                zone_2_seconds=600,
                zone_3_seconds=900,
                zone_4_seconds=300,
                zone_5_seconds=100,
                zone_1_percent=-10.0,
                zone_2_percent=-20.0,
                zone_3_percent=-30.0,
                zone_4_percent=-15.0,
                zone_5_percent=-20.0,  # total = -95% (below 0%)
                max_hr=180,
                zone_boundaries={
                    1: (90, 108),
                    2: (108, 126),
                    3: (126, 144),
                    4: (144, 162),
                    5: (162, 180)
                }
            )

    def test_percentages_sum_above_range_raises_error(self):
        """Percentages summing to more than 101% should raise ValueError."""
        with pytest.raises(ValueError, match="zone percentages must sum to 0.0-101.0%"):
            HRZonesData(
                zone_1_seconds=300,
                zone_2_seconds=600,
                zone_3_seconds=900,
                zone_4_seconds=300,
                zone_5_seconds=100,
                zone_1_percent=20.0,
                zone_2_percent=25.0,
                zone_3_percent=30.0,
                zone_4_percent=20.0,
                zone_5_percent=10.0,  # total = 105%
                max_hr=180,
                zone_boundaries={
                    1: (90, 108),
                    2: (108, 126),
                    3: (126, 144),
                    4: (144, 162),
                    5: (162, 180)
                }
            )

    def test_percentages_sum_at_lower_boundary(self):
        """Percentages summing to exactly 99.0% should be accepted."""
        hr_zones = HRZonesData(
            zone_1_seconds=300,
            zone_2_seconds=600,
            zone_3_seconds=900,
            zone_4_seconds=300,
            zone_5_seconds=100,
            zone_1_percent=19.8,
            zone_2_percent=19.8,
            zone_3_percent=19.8,
            zone_4_percent=19.8,
            zone_5_percent=19.8,  # total = 99.0%
            max_hr=180,
            zone_boundaries={
                1: (90, 108),
                2: (108, 126),
                3: (126, 144),
                4: (144, 162),
                5: (162, 180)
            }
        )
        assert hr_zones.zone_1_percent == 19.8

    def test_percentages_sum_at_upper_boundary(self):
        """Percentages summing to exactly 101.0% should be accepted."""
        hr_zones = HRZonesData(
            zone_1_seconds=300,
            zone_2_seconds=600,
            zone_3_seconds=900,
            zone_4_seconds=300,
            zone_5_seconds=100,
            zone_1_percent=20.2,
            zone_2_percent=20.2,
            zone_3_percent=20.2,
            zone_4_percent=20.2,
            zone_5_percent=20.2,  # total = 101.0%
            max_hr=180,
            zone_boundaries={
                1: (90, 108),
                2: (108, 126),
                3: (126, 144),
                4: (144, 162),
                5: (162, 180)
            }
        )
        assert hr_zones.zone_2_percent == 20.2

    def test_zero_max_hr_raises_error(self):
        """Max HR of zero should raise ValueError."""
        with pytest.raises(ValueError, match="max_hr must be positive"):
            HRZonesData(
                zone_1_seconds=300,
                zone_2_seconds=600,
                zone_3_seconds=900,
                zone_4_seconds=300,
                zone_5_seconds=100,
                zone_1_percent=15.0,
                zone_2_percent=30.0,
                zone_3_percent=40.0,
                zone_4_percent=10.0,
                zone_5_percent=5.0,
                max_hr=0,
                zone_boundaries={
                    1: (90, 108),
                    2: (108, 126),
                    3: (126, 144),
                    4: (144, 162),
                    5: (162, 180)
                }
            )

    def test_negative_max_hr_raises_error(self):
        """Negative max HR should raise ValueError."""
        with pytest.raises(ValueError, match="max_hr must be positive"):
            HRZonesData(
                zone_1_seconds=300,
                zone_2_seconds=600,
                zone_3_seconds=900,
                zone_4_seconds=300,
                zone_5_seconds=100,
                zone_1_percent=15.0,
                zone_2_percent=30.0,
                zone_3_percent=40.0,
                zone_4_percent=10.0,
                zone_5_percent=5.0,
                max_hr=-180,
                zone_boundaries={
                    1: (90, 108),
                    2: (108, 126),
                    3: (126, 144),
                    4: (144, 162),
                    5: (162, 180)
                }
            )

    def test_missing_zone_boundary_raises_error(self):
        """Missing zone boundary should raise ValueError."""
        with pytest.raises(ValueError, match="zone_boundaries must contain exactly 5 zones"):
            HRZonesData(
                zone_1_seconds=300,
                zone_2_seconds=600,
                zone_3_seconds=900,
                zone_4_seconds=300,
                zone_5_seconds=100,
                zone_1_percent=15.0,
                zone_2_percent=30.0,
                zone_3_percent=40.0,
                zone_4_percent=10.0,
                zone_5_percent=5.0,
                max_hr=180,
                zone_boundaries={
                    1: (90, 108),
                    2: (108, 126),
                    # 3 missing
                    4: (144, 162),
                    5: (162, 180)
                }
            )

    def test_incorrect_number_of_zones_raises_error(self):
        """Incorrect number of zone boundaries should raise ValueError."""
        with pytest.raises(ValueError, match="zone_boundaries must contain exactly 5 zones"):
            HRZonesData(
                zone_1_seconds=300,
                zone_2_seconds=600,
                zone_3_seconds=900,
                zone_4_seconds=300,
                zone_5_seconds=100,
                zone_1_percent=15.0,
                zone_2_percent=30.0,
                zone_3_percent=40.0,
                zone_4_percent=10.0,
                zone_5_percent=5.0,
                max_hr=180,
                zone_boundaries={
                    1: (90, 108),
                    2: (108, 126),
                    3: (126, 144)
                }
            )

    def test_invalid_boundary_tuple_raises_error(self):
        """Invalid boundary tuple format should raise ValueError."""
        with pytest.raises(ValueError, match="zone_boundaries\\[2\\] must be a 2-tuple"):
            HRZonesData(
                zone_1_seconds=300,
                zone_2_seconds=600,
                zone_3_seconds=900,
                zone_4_seconds=300,
                zone_5_seconds=100,
                zone_1_percent=15.0,
                zone_2_percent=30.0,
                zone_3_percent=40.0,
                zone_4_percent=10.0,
                zone_5_percent=5.0,
                max_hr=180,
                zone_boundaries={
                    1: (90, 108),
                    2: (108, 126, 130),  # 3-tuple instead of 2-tuple
                    3: (126, 144),
                    4: (144, 162),
                    5: (162, 180)
                }
            )

    def test_lower_bound_greater_than_upper_bound_raises_error(self):
        """Lower bound greater than or equal to upper bound should raise ValueError."""
        with pytest.raises(ValueError, match="zone_boundaries\\[4\\] lower bound must be less than upper bound"):
            HRZonesData(
                zone_1_seconds=300,
                zone_2_seconds=600,
                zone_3_seconds=900,
                zone_4_seconds=300,
                zone_5_seconds=100,
                zone_1_percent=15.0,
                zone_2_percent=30.0,
                zone_3_percent=40.0,
                zone_4_percent=10.0,
                zone_5_percent=5.0,
                max_hr=180,
                zone_boundaries={
                    1: (90, 108),
                    2: (108, 126),
                    3: (126, 144),
                    4: (162, 144),  # lower > upper
                    5: (162, 180)
                }
            )

    def test_zero_time_zones_accepted(self):
        """Zero time in one or more zones should be accepted."""
        hr_zones = HRZonesData(
            zone_1_seconds=0,
            zone_2_seconds=0,
            zone_3_seconds=1800,
            zone_4_seconds=0,
            zone_5_seconds=0,
            zone_1_percent=0.0,
            zone_2_percent=0.0,
            zone_3_percent=100.0,
            zone_4_percent=0.0,
            zone_5_percent=0.0,
            max_hr=180,
            zone_boundaries={
                1: (90, 108),
                2: (108, 126),
                3: (126, 144),
                4: (144, 162),
                5: (162, 180)
            }
        )
        assert hr_zones.zone_1_seconds == 0
        assert hr_zones.zone_3_seconds == 1800


class TestAbilityAssessmentValidation:
    """AbilityAssessment dataclass validation tests."""

    def test_valid_ability_assessment(self):
        """Valid AbilityAssessment with all fields populated should be accepted."""
        assessment = AbilityAssessment(
            percentile_estimate="top 25%",
            local_ranking="estimated 5th out of 50 swimmers in your area",
            national_ranking="estimated top 15% nationally",
            competitive_analysis="Based on your current pace and metrics, you are competitive at the regional level."
        )
        assert assessment.percentile_estimate == "top 25%"
        assert assessment.local_ranking == "estimated 5th out of 50 swimmers in your area"
        assert assessment.national_ranking == "estimated top 15% nationally"
        assert "competitive at the regional level" in assessment.competitive_analysis

    def test_empty_percentile_estimate_raises_error(self):
        """Empty percentile_estimate should raise ValueError."""
        with pytest.raises(ValueError, match="percentile_estimate must be non-empty"):
            AbilityAssessment(
                percentile_estimate="",
                local_ranking="estimated 5th out of 50 swimmers",
                national_ranking="estimated top 15% nationally",
                competitive_analysis="Competitive at regional level."
            )

    def test_percentile_estimate_exceeds_max_length_raises_error(self):
        """percentile_estimate exceeding 100 characters should raise ValueError."""
        long_percentile = "a" * 101
        with pytest.raises(ValueError, match="percentile_estimate must not exceed 100 characters"):
            AbilityAssessment(
                percentile_estimate=long_percentile,
                local_ranking="estimated 5th out of 50 swimmers",
                national_ranking="estimated top 15% nationally",
                competitive_analysis="Competitive at regional level."
            )

    def test_percentile_estimate_at_max_length(self):
        """percentile_estimate exactly 100 characters should be accepted."""
        percentile = "a" * 100
        assessment = AbilityAssessment(
            percentile_estimate=percentile,
            local_ranking="local",
            national_ranking="national",
            competitive_analysis="analysis"
        )
        assert len(assessment.percentile_estimate) == 100

    def test_empty_local_ranking_raises_error(self):
        """Empty local_ranking should raise ValueError."""
        with pytest.raises(ValueError, match="local_ranking must be non-empty"):
            AbilityAssessment(
                percentile_estimate="top 25%",
                local_ranking="",
                national_ranking="estimated top 15% nationally",
                competitive_analysis="Competitive at regional level."
            )

    def test_local_ranking_exceeds_max_length_raises_error(self):
        """local_ranking exceeding 200 characters should raise ValueError."""
        long_local = "a" * 201
        with pytest.raises(ValueError, match="local_ranking must not exceed 200 characters"):
            AbilityAssessment(
                percentile_estimate="top 25%",
                local_ranking=long_local,
                national_ranking="estimated top 15% nationally",
                competitive_analysis="Competitive at regional level."
            )

    def test_local_ranking_at_max_length(self):
        """local_ranking exactly 200 characters should be accepted."""
        local = "a" * 200
        assessment = AbilityAssessment(
            percentile_estimate="top 25%",
            local_ranking=local,
            national_ranking="national",
            competitive_analysis="analysis"
        )
        assert len(assessment.local_ranking) == 200

    def test_empty_national_ranking_raises_error(self):
        """Empty national_ranking should raise ValueError."""
        with pytest.raises(ValueError, match="national_ranking must be non-empty"):
            AbilityAssessment(
                percentile_estimate="top 25%",
                local_ranking="estimated 5th out of 50 swimmers",
                national_ranking="",
                competitive_analysis="Competitive at regional level."
            )

    def test_national_ranking_exceeds_max_length_raises_error(self):
        """national_ranking exceeding 200 characters should raise ValueError."""
        long_national = "a" * 201
        with pytest.raises(ValueError, match="national_ranking must not exceed 200 characters"):
            AbilityAssessment(
                percentile_estimate="top 25%",
                local_ranking="estimated 5th out of 50 swimmers",
                national_ranking=long_national,
                competitive_analysis="Competitive at regional level."
            )

    def test_national_ranking_at_max_length(self):
        """national_ranking exactly 200 characters should be accepted."""
        national = "a" * 200
        assessment = AbilityAssessment(
            percentile_estimate="top 25%",
            local_ranking="local",
            national_ranking=national,
            competitive_analysis="analysis"
        )
        assert len(assessment.national_ranking) == 200

    def test_empty_competitive_analysis_raises_error(self):
        """Empty competitive_analysis should raise ValueError."""
        with pytest.raises(ValueError, match="competitive_analysis must be non-empty"):
            AbilityAssessment(
                percentile_estimate="top 25%",
                local_ranking="estimated 5th out of 50 swimmers",
                national_ranking="estimated top 15% nationally",
                competitive_analysis=""
            )

    def test_competitive_analysis_exceeds_max_length_raises_error(self):
        """competitive_analysis exceeding 800 characters should raise ValueError."""
        long_analysis = "a" * 801
        with pytest.raises(ValueError, match="competitive_analysis must not exceed 800 characters"):
            AbilityAssessment(
                percentile_estimate="top 25%",
                local_ranking="estimated 5th out of 50 swimmers",
                national_ranking="estimated top 15% nationally",
                competitive_analysis=long_analysis
            )

    def test_competitive_analysis_at_max_length(self):
        """competitive_analysis exactly 800 characters should be accepted."""
        analysis = "a" * 800
        assessment = AbilityAssessment(
            percentile_estimate="top 25%",
            local_ranking="local",
            national_ranking="national",
            competitive_analysis=analysis
        )
        assert len(assessment.competitive_analysis) == 800


class TestSessionValidation:
    """Session dataclass validation tests."""

    def test_valid_session(self):
        """Valid Session with all required fields should be accepted."""
        session = Session(
            session_id="123e4567-e89b-12d3-a456-426614174000",
            user_id="user-123",
            session_date="2024-01-15T10:30:00Z",
            pool_length_meters=25,
            total_distance_meters=1500,
            total_time_seconds=1800,
            stroke_type="freestyle",
            average_pace_per_100m=120.5,
            swolf_score=45,
            stroke_rate=42.5,
            uploaded_at="2024-01-15T11:00:00Z",
            s3_key="fit-files/user-123/session-123.fit"
        )
        assert session.session_id == "123e4567-e89b-12d3-a456-426614174000"
        assert session.pool_length_meters == 25
        assert session.total_distance_meters == 1500
        assert session.hr_zones is None
        assert session.ability_assessment is None

    def test_session_with_optional_fields(self):
        """Session with optional hr_zones and ability_assessment should be accepted."""
        hr_zones = HRZonesData(
            zone_1_seconds=300,
            zone_2_seconds=600,
            zone_3_seconds=600,
            zone_4_seconds=300,
            zone_5_seconds=0,
            zone_1_percent=16.7,
            zone_2_percent=33.3,
            zone_3_percent=33.3,
            zone_4_percent=16.7,
            zone_5_percent=0.0,
            max_hr=180,
            zone_boundaries={1: (90, 108), 2: (108, 126), 3: (126, 144), 4: (144, 162), 5: (162, 180)}
        )
        ability = AbilityAssessment(
            percentile_estimate="top 25%",
            local_ranking="competitive",
            national_ranking="middle of the pack",
            competitive_analysis="Strong swimmer for age group"
        )
        session = Session(
            session_id="123e4567-e89b-12d3-a456-426614174000",
            user_id="user-123",
            session_date="2024-01-15T10:30:00Z",
            pool_length_meters=25,
            total_distance_meters=1500,
            total_time_seconds=1800,
            stroke_type="freestyle",
            average_pace_per_100m=120.5,
            swolf_score=45,
            stroke_rate=42.5,
            uploaded_at="2024-01-15T11:00:00Z",
            s3_key="fit-files/user-123/session-123.fit",
            hr_zones=hr_zones,
            ability_assessment=ability
        )
        assert session.hr_zones == hr_zones
        assert session.ability_assessment == ability

    def test_empty_session_id_raises_error(self):
        """Empty session_id should raise ValueError."""
        with pytest.raises(ValueError, match="session_id must be a non-empty string"):
            Session(
                session_id="",
                user_id="user-123",
                session_date="2024-01-15T10:30:00Z",
                pool_length_meters=25,
                total_distance_meters=1500,
                total_time_seconds=1800,
                stroke_type="freestyle",
                average_pace_per_100m=120.5,
                swolf_score=45,
                stroke_rate=42.5,
                uploaded_at="2024-01-15T11:00:00Z",
                s3_key="fit-files/user-123/session-123.fit"
            )

    def test_negative_pool_length_raises_error(self):
        """Negative pool_length_meters should raise ValueError."""
        with pytest.raises(ValueError, match="pool_length_meters must be positive"):
            Session(
                session_id="123",
                user_id="user-123",
                session_date="2024-01-15T10:30:00Z",
                pool_length_meters=-25,
                total_distance_meters=1500,
                total_time_seconds=1800,
                stroke_type="freestyle",
                average_pace_per_100m=120.5,
                swolf_score=45,
                stroke_rate=42.5,
                uploaded_at="2024-01-15T11:00:00Z",
                s3_key="fit-files/user-123/session-123.fit"
            )

    def test_stroke_type_exceeds_max_length_raises_error(self):
        """Stroke type exceeding 50 characters should raise ValueError."""
        with pytest.raises(ValueError, match="stroke_type must not exceed 50 characters"):
            Session(
                session_id="123",
                user_id="user-123",
                session_date="2024-01-15T10:30:00Z",
                pool_length_meters=25,
                total_distance_meters=1500,
                total_time_seconds=1800,
                stroke_type="a" * 51,
                average_pace_per_100m=120.5,
                swolf_score=45,
                stroke_rate=42.5,
                uploaded_at="2024-01-15T11:00:00Z",
                s3_key="fit-files/user-123/session-123.fit"
            )

    def test_non_finite_pace_raises_error(self):
        """Non-finite average_pace_per_100m should raise ValueError."""
        with pytest.raises(ValueError, match="average_pace_per_100m must be a finite number"):
            Session(
                session_id="123",
                user_id="user-123",
                session_date="2024-01-15T10:30:00Z",
                pool_length_meters=25,
                total_distance_meters=1500,
                total_time_seconds=1800,
                stroke_type="freestyle",
                average_pace_per_100m=float('inf'),
                swolf_score=45,
                stroke_rate=42.5,
                uploaded_at="2024-01-15T11:00:00Z",
                s3_key="fit-files/user-123/session-123.fit"
            )


class TestTrainingPlanValidation:
    """TrainingPlan dataclass validation tests."""

    def test_valid_training_plan(self):
        """Valid TrainingPlan with all fields should be accepted."""
        plan = TrainingPlan(
            session_title="Speed Workout",
            warm_up=["400m easy freestyle"],
            main_set=["8x100m on 1:30", "4x50m sprint on 1:00"],
            cool_down=["200m easy"],
            total_distance=2000,
            focus_notes="Focus on maintaining stroke rate",
            goal_likelihood="Your goal is challenging but achievable with consistent training"
        )
        assert plan.session_title == "Speed Workout"
        assert plan.goal_likelihood == "Your goal is challenging but achievable with consistent training"

    def test_empty_goal_likelihood_raises_error(self):
        """Empty goal_likelihood should raise ValueError."""
        with pytest.raises(ValueError, match="goal_likelihood must be non-empty"):
            TrainingPlan(
                session_title="Speed Workout",
                warm_up=["400m easy freestyle"],
                main_set=["8x100m on 1:30"],
                cool_down=["200m easy"],
                total_distance=2000,
                focus_notes="Focus on maintaining stroke rate",
                goal_likelihood=""
            )

    def test_goal_likelihood_exceeds_max_length_raises_error(self):
        """goal_likelihood exceeding 300 characters should raise ValueError."""
        with pytest.raises(ValueError, match="goal_likelihood must not exceed 300 characters"):
            TrainingPlan(
                session_title="Speed Workout",
                warm_up=["400m easy freestyle"],
                main_set=["8x100m on 1:30"],
                cool_down=["200m easy"],
                total_distance=2000,
                focus_notes="Focus on maintaining stroke rate",
                goal_likelihood="a" * 301
            )

    def test_goal_likelihood_at_max_length(self):
        """goal_likelihood at exactly 300 characters should be accepted."""
        likelihood_text = "a" * 300
        plan = TrainingPlan(
            session_title="Speed Workout",
            warm_up=["400m easy freestyle"],
            main_set=["8x100m on 1:30"],
            cool_down=["200m easy"],
            total_distance=2000,
            focus_notes="Focus on maintaining stroke rate",
            goal_likelihood=likelihood_text
        )
        assert len(plan.goal_likelihood) == 300


class TestFullResponseStructure:
    """FullResponse dataclass structure tests."""

    def test_full_response_with_all_optional_fields(self):
        """FullResponse with all optional fields should be accepted."""
        from backend.models import FullResponse, SessionInfo, LengthSplit, Metrics, CoachingResponse

        session_info = SessionInfo(
            start_time="2024-01-15T10:30:00Z",
            pool_length_m=25.0,
            stroke="freestyle",
            total_distance_m=1500.0,
            total_time_seconds=1800.0,
            num_lengths=60
        )
        splits = [
            LengthSplit(length_number=1, time_seconds=30.5, stroke="freestyle", strokes=20)
        ]
        metrics = Metrics(pace=120.5, swolf=45.0, stroke_rate=42.5)
        coaching = CoachingResponse(
            tips=["Focus on hip rotation", "Maintain streamline position", "Increase kick frequency"],
            drill="6x50m single-arm freestyle with 10s rest"
        )
        hr_zones = HRZonesData(
            zone_1_seconds=300,
            zone_2_seconds=600,
            zone_3_seconds=600,
            zone_4_seconds=300,
            zone_5_seconds=0,
            zone_1_percent=16.7,
            zone_2_percent=33.3,
            zone_3_percent=33.3,
            zone_4_percent=16.7,
            zone_5_percent=0.0,
            max_hr=180,
            zone_boundaries={1: (90, 108), 2: (108, 126), 3: (126, 144), 4: (144, 162), 5: (162, 180)}
        )
        ability = AbilityAssessment(
            percentile_estimate="top 25%",
            local_ranking="competitive",
            national_ranking="middle of the pack",
            competitive_analysis="Strong swimmer for age group"
        )

        response = FullResponse(
            session=session_info,
            splits=splits,
            metrics=metrics,
            coaching=coaching,
            hr_zones=hr_zones,
            ability_assessment=ability,
            session_id="session-123"
        )
        assert response.hr_zones == hr_zones
        assert response.ability_assessment == ability
        assert response.session_id == "session-123"

    def test_full_response_without_optional_fields(self):
        """FullResponse without optional fields should default to None."""
        from backend.models import FullResponse, SessionInfo, LengthSplit, Metrics, CoachingResponse

        session_info = SessionInfo(
            start_time="2024-01-15T10:30:00Z",
            pool_length_m=25.0,
            stroke="freestyle",
            total_distance_m=1500.0,
            total_time_seconds=1800.0,
            num_lengths=60
        )
        splits = [
            LengthSplit(length_number=1, time_seconds=30.5, stroke="freestyle", strokes=20)
        ]
        metrics = Metrics(pace=120.5, swolf=45.0, stroke_rate=42.5)
        coaching = CoachingResponse(
            tips=["Focus on hip rotation", "Maintain streamline position", "Increase kick frequency"],
            drill="6x50m single-arm freestyle with 10s rest"
        )

        response = FullResponse(
            session=session_info,
            splits=splits,
            metrics=metrics,
            coaching=coaching
        )
        assert response.hr_zones is None
        assert response.ability_assessment is None
        assert response.session_id is None
