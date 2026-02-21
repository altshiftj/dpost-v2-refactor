# Master Work Proposal (Condensed ~250 Words): Data Management and Automated Raw Data Capture in University Labs

University laboratories generate raw data from user-operated analytical devices. While measurement protocols are standardized, file handling is often inconsistent. Raw data is manually renamed, moved through ad hoc folders, and uploaded late to institutional systems. These practices increase the risk of data loss, weak traceability, and reduced reproducibility.

This master work will address that challenge as a combined data management and data engineering problem. The objective will be to design reliable edge data pipelines that automate raw file capture, preserve device-specific processing requirements, and improve operational transparency in university lab settings.

The work will build on the Python watchdog codebase, including PC/device plugin mechanisms, multi-situation deployment scripts, and observability interfaces. The approach will be evolutionary: improve and consolidate rather than replace.

Core focus areas will include:

- assessing the end-to-end pipeline for bottlenecks, fragilities, and integration gaps;
- reviewing internal and external solutions for reusable improvement patterns;
- using adaptive orchestration through one input-driven control model;
- defining PC profiles that unify access and device configuration;
- automating packaging and delivery of device processor code;
- adding behavior-aware monitoring with failure detection and response policies; and
- defining a central dashboard for deployment and runtime visibility.

The project will follow iterative validation in representative scenarios, with outcomes focused on a clearer architecture for automated raw data intake, stronger operational maintainability, and evidence-based recommendations for long-term university lab operation.


The work will build on an existing Python codebase designed within the Insitut für Partikeltechnik, including PC/device plugin mechanisms, multi-situation deployment scripts, and observability interfaces, and improve them 