# Requirements Document

## Introduction

This feature adds distance-based statistics to the existing Sidebar component on the Dashboard. Currently the Sidebar displays swim counts for the current week, month, and year to date. This enhancement adds corresponding distance totals for the same time periods, giving swimmers a quick view of their training volume over time. The distance values use the existing `formatDistance` utility to display in kilometers or meters as appropriate.

## Glossary

- **Sidebar**: The React component (`Sidebar.tsx`) displayed on the Dashboard page that shows profile information and aggregate training statistics.
- **DashboardPage**: The parent page component that loads session data and computes aggregate stats passed to the Sidebar.
- **Session**: A single recorded swim workout containing metadata including `total_distance_meters` and `session_date`.
- **formatDistance**: A utility function that converts a distance in meters to a human-readable string — "X.X km" when the value is 1000 meters or greater, otherwise "X m".
- **Current_Week**: The ISO week period from Monday 00:00:00 to Sunday 23:59:59 containing the current date.
- **Current_Month**: The calendar month period from the 1st at 00:00:00 to the last day at 23:59:59 of the month containing the current date.
- **Year_To_Date**: The period from January 1st 00:00:00 of the current year up to and including the current date.

## Requirements

### Requirement 1: Compute Distance This Week

**User Story:** As a swimmer, I want to see the total distance I have swum this week, so that I can track my weekly training volume at a glance.

#### Acceptance Criteria

1. WHEN the DashboardPage computes sidebar statistics, THE DashboardPage SHALL sum the `total_distance_meters` field of all Sessions with a `session_date` on or after the start of the Current_Week.
2. THE DashboardPage SHALL pass the computed weekly distance value in meters to the Sidebar component as a prop.
3. IF no Sessions exist within the Current_Week, THEN THE DashboardPage SHALL pass a value of zero to the Sidebar component for weekly distance.

### Requirement 2: Compute Distance This Month

**User Story:** As a swimmer, I want to see the total distance I have swum this month, so that I can monitor my monthly training volume.

#### Acceptance Criteria

1. WHEN the DashboardPage computes sidebar statistics, THE DashboardPage SHALL sum the `total_distance_meters` field of all Sessions with a `session_date` on or after the start of the Current_Month.
2. THE DashboardPage SHALL pass the computed monthly distance value in meters to the Sidebar component as a prop.
3. IF no Sessions exist within the Current_Month, THEN THE DashboardPage SHALL pass a value of zero to the Sidebar component for monthly distance.

### Requirement 3: Compute Distance Year to Date

**User Story:** As a swimmer, I want to see the total distance I have swum since the start of the year, so that I can assess my cumulative annual training volume.

#### Acceptance Criteria

1. WHEN the DashboardPage computes sidebar statistics, THE DashboardPage SHALL sum the `total_distance_meters` field of all Sessions with a `session_date` on or after the start of the Year_To_Date period.
2. THE DashboardPage SHALL pass the computed year-to-date distance value in meters to the Sidebar component as a prop.
3. IF no Sessions exist within the Year_To_Date period, THEN THE DashboardPage SHALL pass a value of zero to the Sidebar component for year-to-date distance.

### Requirement 4: Display Distance Statistics in Sidebar

**User Story:** As a swimmer, I want distance statistics displayed in the Sidebar alongside existing swim counts, so that I can quickly compare sessions and volume.

#### Acceptance Criteria

1. THE Sidebar SHALL display the weekly distance value in the stats section using the formatDistance function for formatting.
2. THE Sidebar SHALL display the monthly distance value in the stats section using the formatDistance function for formatting.
3. THE Sidebar SHALL display the year-to-date distance value in the stats section using the formatDistance function for formatting.
4. THE Sidebar SHALL display each distance statistic with a descriptive label: "Distance / Week", "Distance / Month", and "Distance Year to Date".
5. THE Sidebar SHALL render each distance statistic as an accessible list item within the existing stats list, consistent with the current stat items.

### Requirement 5: Format Distance Values

**User Story:** As a swimmer, I want distance values formatted in a readable way, so that I can quickly understand whether values are in meters or kilometers.

#### Acceptance Criteria

1. WHEN a distance value is 1000 meters or greater, THE Sidebar SHALL display the value in kilometers with one decimal place (e.g., "2.5 km"), omitting the decimal when the value is a whole number of kilometers (e.g., "3 km").
2. WHEN a distance value is less than 1000 meters, THE Sidebar SHALL display the value in meters as a whole number (e.g., "750 m").
3. WHEN a distance value is zero, THE Sidebar SHALL display "0 m".

### Requirement 6: Prop Interface Extension

**User Story:** As a developer, I want the Sidebar component props interface to accept distance values, so that the component contract is explicit and type-safe.

#### Acceptance Criteria

1. THE Sidebar component props interface SHALL include a `distanceThisWeekMeters` property of type number.
2. THE Sidebar component props interface SHALL include a `distanceThisMonthMeters` property of type number.
3. THE Sidebar component props interface SHALL include a `distanceYTDMeters` property of type number.
