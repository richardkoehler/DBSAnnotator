Output Format
=============

This page describes the data files produced by the application and the
structure of the exported reports.

----

TSV Data File
-------------

All session data is stored as a **tab-separated values** (``.tsv``) file.
One file is created per session; rows are appended in real-time as entries
are recorded.

Filename Convention
^^^^^^^^^^^^^^^^^^^

The filename follows the `BIDS <https://bids.neuroimaging.io/>`_ specification::

   sub-<PatientID>_ses-<YYYYMMDD>_task-programming_run-<NN>_events.tsv

Examples::

   sub-01_ses-20250315_task-programming_run-01_events.tsv
   sub-01_ses-20250315_task-annotations_run-01_events.tsv

Columns
^^^^^^^

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Column
     - Type
     - Description
   * - ``date``
     - string
     - Date of the entry (``YYYY-MM-DD``).
   * - ``time``
     - string
     - Time of the entry (``HH:MM:SS``, Eastern Time).
   * - ``onset``
     - float
     - Time in seconds since session start (BIDS onset field).
   * - ``block_id``
     - integer
     - Index of the stimulation configuration block within the session.
   * - ``is_initial``
     - integer
     - ``1`` for baseline / initial entries recorded in Step 1;
       ``0`` for session entries recorded in Step 3.
   * - ``session_ID``
     - integer
     - Internal session counter.
   * - ``electrode_model``
     - string
     - Name of the electrode model selected (e.g. ``SenSight B33015``).
   * - ``group_ID``
     - string
     - Stimulation group label (e.g. ``A``, ``B``).
   * - ``scale_name``
     - string
     - Name of the clinical scale recorded in this row (may be empty if
       multiple scales are stored as newline-separated values).
   * - ``scale_value``
     - string / float
     - Numeric value of the clinical scale.  ``NaN`` if the scale was
       marked as "not assessed".
   * - ``left_anode``
     - string
     - Left hemisphere anode contact(s), comma-separated.
   * - ``left_cathode``
     - string
     - Left hemisphere cathode contact(s), comma-separated.
   * - ``left_amplitude``
     - float
     - Left hemisphere stimulation amplitude (mA).
   * - ``left_stim_freq``
     - float
     - Left hemisphere stimulation frequency (Hz).
   * - ``left_pulse_width``
     - float
     - Left hemisphere pulse width (µs).
   * - ``right_anode``
     - string
     - Right hemisphere anode contact(s).
   * - ``right_cathode``
     - string
     - Right hemisphere cathode contact(s).
   * - ``right_amplitude``
     - float
     - Right hemisphere stimulation amplitude (mA).
   * - ``right_stim_freq``
     - float
     - Right hemisphere stimulation frequency (Hz).
   * - ``right_pulse_width``
     - float
     - Right hemisphere pulse width (µs).
   * - ``notes``
     - string
     - Free-text note associated with this entry.

.. note::
   When multiple cathode contacts are active, the ``left_cathode`` /
   ``right_cathode`` field contains comma-separated contact names and the
   amplitude field stores the **total** delivered current.  The per-contact
   split (in mA) is shown in the report but not stored in a separate column.

Example rows
^^^^^^^^^^^^

.. code-block:: text

   date	time	block_id	is_initial	electrode_model	scale_name	scale_value	left_cathode	left_anode	left_amplitude	left_stim_freq	left_pulse_width	notes
   2025-03-15	10:02:31	0	1	SenSight B33015	UPDRS-III	42	1C	Case	0.0	130	60	Baseline pre-stim
   2025-03-15	10:15:44	1	0	SenSight B33015	UPDRS-III	38	1C	Case	2.5	130	60	Config 1
   2025-03-15	10:28:12	2	0	SenSight B33015	UPDRS-III	34	2A,2B	Case	3.0	130	90	Config 2 – wider contacts

----

Word / PDF Reports
------------------

Reports are generated in Microsoft Word (``.docx``) format and optionally
converted to PDF.  The document structure depends on the sections selected
at export time.

Single-Session Report
^^^^^^^^^^^^^^^^^^^^^^

Sections (in order):

1. **Title** — "Clinical DBS Session Report", generated date, patient ID,
   session number.
2. **Initial Clinical Notes** *(optional)* — baseline scale scores and any
   initial notes recorded in Step 1.
3. **Session Data** *(optional)* — lateral table (L/R rows per configuration)
   with all recorded stimulation parameters, scale values, and notes.  The
   best entry is highlighted in green.
4. **Electrode Configurations** *(optional)* — a borderless 4-column table:

   +-------------------+-------------------+-------------------+-------------------+
   | Initial — Left    | Initial — Right   | Final — Left      | Final — Right     |
   +===================+===================+===================+===================+
   | Diagram + text    | Diagram + text    | Diagram + text    | Diagram + text    |
   +-------------------+-------------------+-------------------+-------------------+

5. **Programming Summary** *(optional)* — session duration, number of
   configurations, and amplitude / frequency / pulse-width ranges per side.

Longitudinal Report
^^^^^^^^^^^^^^^^^^^^

Sections (in order, selected at export time):

1. **Title** — "Longitudinal DBS Report", generated date, patient ID,
   list of included files.
2. **Sessions Overview** *(optional)* — one-row-per-session summary table
   with date, number of entries, and final scale values.
3. **Session Data** *(optional)* — combined table across all sessions.
   First column is the entry **date**; the best entry per session is
   highlighted.
4. **Electrode Configuration** *(optional)* — per-file Initial/Final diagrams
   separated by page breaks.
5. **Programming Summary** *(optional)* — per-session parameter ranges.

----

Timestamp Alignment
--------------------

All timestamps are recorded in **Eastern Time (ET)** to align with the
Medtronic Percept PC neurostimulator's internal clock.  If you are working in
a different timezone, note this when interpreting combined Percept + annotator
datasets.
