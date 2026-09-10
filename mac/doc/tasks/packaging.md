# Packaging Module Tasks

Goal: support Python source execution now and macOS app packaging for current delivery.

Source design: `doc/detailed-design.md` section 5.11.

## Minimal Tasks

- [ ] Document Python source startup command.
- [ ] Confirm `python3 app.py` starts GUI from source.
- [ ] Confirm CLI command starts from source.
- [ ] Choose macOS packaging command or tool based on existing project approach.
- [ ] Add packaging notes under `packaging/` or `doc/`.
- [ ] Package macOS app.
- [ ] Verify packaged app starts.
- [ ] Verify packaged app can open `samples/phantom.edf`.
- [ ] Verify packaged app displays channel list.
- [ ] Verify packaged app computes one window.
- [ ] Verify packaged app exports current tab PNG.
- [ ] Document future Windows executable packaging as future scope.
- [ ] Document future Linux executable packaging as future scope.

## Acceptance Criteria

- [ ] Python source execution path is documented and tested.
- [ ] macOS app package can perform basic EDF workflow.
- [ ] Windows and Linux packaging remain future tasks.
