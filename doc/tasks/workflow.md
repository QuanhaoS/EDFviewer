# Application Workflow Tasks

Goal: provide the shared controller used by both GUI and CLI.

Source design: `doc/detailed-design.md` sections 5.7, 8.1, 8.2, 8.3, and 8.4.

## Minimal Tasks

- [ ] Create `core/workflow.py`.
- [ ] Implement `EDFViewerWorkflow`.
- [ ] Implement `load_file(file_path)`.
- [ ] Implement `get_channel_range(channel_name)`.
- [ ] Implement `compute_window(channel_name, parameters)`.
- [ ] Implement `export_result(result, export_request)`.
- [ ] Store active EDF metadata after file load.
- [ ] Validate that an EDF is loaded before compute.
- [ ] Validate selected channel before compute.
- [ ] Validate analysis parameters before compute.
- [ ] Build analysis cache key.
- [ ] Return cached result when key matches.
- [ ] Load selected channel window through data layer.
- [ ] Run preprocessing through preprocessing module.
- [ ] Run analysis through analysis module.
- [ ] Store result in cache.
- [ ] Dispatch PNG export requests.
- [ ] Dispatch CSV feature export requests.
- [ ] Dispatch parameter record export requests.
- [ ] Return `ExportResult` from export calls.
- [ ] Add workflow test for opening `samples/phantom.edf`.
- [ ] Add workflow test for computing a valid window.
- [ ] Add workflow test for cache hit.
- [ ] Add workflow test for cache invalidation when analysis parameter changes.
- [ ] Add workflow test for export to temporary directory.
- [ ] Confirm workflow imports no GUI widgets.

## Acceptance Criteria

- [ ] GUI and CLI can both call workflow.
- [ ] Workflow is the shared boundary for analysis.
- [ ] Workflow tests can run headlessly.

