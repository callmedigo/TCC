import re


NAMESPACE = 'http://schemas.microsoft.com/project'
NS = {'p': NAMESPACE}

DURATION_PATTERN = re.compile(
    r'^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$'
)

PROGRESS_STAGE_RANGES = {
    'early': (0.15, 0.30),
    'middle': (0.40, 0.65),
    'late': (0.75, 0.95),
}

FF, FS, SF, SS = 0, 1, 2, 3

PROB_SLIP_FINISH = 0.25
PROB_SLIP_START = 0.10
FRONTIER_DAYS = 14

TASK_TAG_ORDER = [
    'UID', 'ID', 'Name', 'Type', 'IsNull', 'CreateDate', 'WBS', 'OutlineNumber',
    'OutlineLevel', 'Priority', 'Start', 'Finish', 'Duration', 'DurationFormat',
    'Stop', 'Resume', 'ResumeValid', 'EffortDriven', 'Recurring', 'OverAllocated',
    'Estimated', 'Milestone', 'Summary', 'Critical', 'IsSubproject',
    'IsSubprojectReadOnly', 'ExternalTask', 'FixedCostAccrual', 'PercentComplete',
    'PercentWorkComplete', 'RemainingDuration', 'ConstraintType', 'CalendarUID',
    'ConstraintDate', 'LevelAssignments', 'LevelingCanSplit', 'LevelingDelay',
    'LevelingDelayFormat', 'IgnoreResourceCalendar', 'HideBar', 'Rollup',
    'EarnedValueMethod', 'PredecessorLink', 'ExtendedAttribute', 'Active', 'Manual',
]
