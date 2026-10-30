"""Compatibility entry point for generating synthetic Project XML schedules."""

import sys
from pathlib import Path

SOURCE_ROOT = str(Path(__file__).resolve().parents[1])
if SOURCE_ROOT not in sys.path:
    sys.path.insert(0, SOURCE_ROOT)

from generator.constants import (
    DURATION_PATTERN,
    FF,
    FRONTIER_DAYS,
    FS,
    NS,
    NAMESPACE,
    PROB_SLIP_FINISH,
    PROB_SLIP_START,
    PROGRESS_STAGE_RANGES,
    SF,
    SS,
    TASK_TAG_ORDER,
)
from generator.dataset import (
    DEFAULT_MASTER_LIST_PATH,
    create_synthetic_dataset,
    get_max_sequence,
)
from generator.generation import generate_synthetic_xml, shift_schedule_dates
from generator.progress import (
    apply_noise,
    assign_completion_percentages,
    compute_leaf_percentages,
    enforce_dependencies,
    planned_percentage,
    validate_cascade,
    write_progress,
)
from generator.schedule import (
    dependency_order,
    effective_links,
    leaves_of,
    load_schedule,
)
from generator.xml_utils import (
    back_to_weekday,
    duration_to_seconds,
    format_duration,
    parse_dt,
    remove_child,
    set_child,
)
from generator.project_metadata import generate_opening_date, generate_project_name
from generator.cli import main

__all__ = [
    'DURATION_PATTERN',
    'DEFAULT_MASTER_LIST_PATH',
    'FF',
    'FRONTIER_DAYS',
    'FS',
    'NS',
    'NAMESPACE',
    'PROB_SLIP_FINISH',
    'PROB_SLIP_START',
    'PROGRESS_STAGE_RANGES',
    'SF',
    'SS',
    'TASK_TAG_ORDER',
    'apply_noise',
    'assign_completion_percentages',
    'back_to_weekday',
    'compute_leaf_percentages',
    'create_synthetic_dataset',
    'dependency_order',
    'duration_to_seconds',
    'effective_links',
    'enforce_dependencies',
    'format_duration',
    'generate_synthetic_xml',
    'generate_opening_date',
    'generate_project_name',
    'get_max_sequence',
    'leaves_of',
    'load_schedule',
    'main',
    'parse_dt',
    'planned_percentage',
    'remove_child',
    'set_child',
    'shift_schedule_dates',
    'validate_cascade',
    'write_progress',
]


if __name__ == '__main__':
    main()
