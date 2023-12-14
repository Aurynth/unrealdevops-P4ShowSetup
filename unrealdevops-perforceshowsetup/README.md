# Unreal Devops - Perforce Show Setup.

A collection of Perforce-targeting command line packages to help automate the
process of setting up a new DNEG show in Perforce.

## Getting Started

### Standard Setup

- Clone this repository to your local storage
- Set up a virtual environment at the root via `py -m venv .venv`
- Enter the python virtual environment via `.venv\Scripts\activate`
- Install the package in this repository via `pip install .`
    Note: Assuming at root level or repository, replace `.` to point to location
    of the `setup.py` found at the root of this repository.

### Development Setup

- Clone this repository to your local storage
- Set up a virtual environment at the root via `py -m venv .venv`
- Enter the python virtual environment via `.venv\Scripts\activate`
- Install the dev requirements for this repository via `pip install -r requirements.txt`
- Install an editable version of this repository via `pip install -e .`
    Note: Assuming at root level or repository, replace `.` to point to location
    of the `setup.py` found at the root of this repository.
- Run the unit tests to verify everything synced correctly via `pytest`
- Run the desired package invoking it by its name as logged in the Tools Index
   section disclosed below.

## Running the script

- From the root of the repository, the base command is `python src\p4_show_setup.py`
- arguments:
    - `-s` is required, used to specify the showcode for the new depot.
    - `-d` is optional, to specify which division the depot should follow.
        - options are "TS", "VFX", or "RE"
        - the division is used to determine the structure of the depot's streams, and permissions
        - if not specified, the division will be determined by the showcode (start with "TS", or ends with "RE"), otherwise it falls back on the "VFX division by default.
    - `-h` will print the manual for this command in the command line.

## Contributing

Contributions to the Unreal Engine DevOp tool repository are highly encouraged
and welcomed. Please ensure:
- The required [one-pagers][RealtimeOnePager] and/or [Technical Design Documents][RealtimeTDD]
    are approved prior to contribution in accordance with the change process workflow
    adopted by the Realtime Team.
- The code you are submitting *must pass ALL unit tests and must have a minumum test coverage
    threshold of 80%*. Refer to the Testing section disclosed below.

### Testing

This repository relies on `pytest` for all unit/integration tests and `pytest-cov` for
code coverage tracking. To run the tests:
- Open a command line terminal
- Navigate to the `src` directory of the repository
- Run `pytest tests\test_p4_show_setup.py` and verify the results are in line with the requirements of this
    repository.

### Code Style

- Code must conform to DNEG's coding standards and style guides whenever possible.
    - [Python][PythonStyleGuide]
    - [C++][CPPStyleGuide]
    - [C#][CSharpStyleGuide]

### Pull Request Process

To help get your pull request accepted please follow these steps:
- Ensure that your [one pager][RealtimeOnePager] / [TDD][RealTimeTDD] document has been approved prior to
    any work taking place.
- Create a new `feature/` or `bugfix/` branch applicable to your contribution.
- Author your contributions to the repo.
- Ensure that your code passes all tests and meets the minimum test coverage threshold.
- When creating the pull request, make sure you are merging into the correct
   staging branch. The staging branch for this repository is `develop`
- When creating the pull request, the maintainer will be added automatically
    to the PR. If this is not the case please email [rnd-realtime@dneg.com][RealtimeContact]
- Rely, whenever possible, on the auto-merging feature of stash. Rebase &
    re-test your changes if any conflicts arise.
- Unless there is an explicit reason to not, delete your branch following a
    successful merge.

## Versioning

We use [SemVer][SemVer] for versioning of the applicable packages.
For the versions available, see the tags on this repository.

## Maintainers

This repository is maintained by the RealTime Development Team.
You can contact them at [rnd-realtime@dneg.com][RealtimeContact]

## Further Reading

### [Unreal support matrix]

Outlines currently supported UE deployments at DNEG.

### [Packaging UE Plugins via command line][PluginCommandline]

Manual steps to replicate the underlying behavior automated by this tool.

### [Unreal Engine Automation Tool][UEAutomationTool]

The system used to build plugins by the engine itself.

[TechBrief]:https://docs.google.com/document/d/1M1IW_9-VBC6wo7hySljoi9qJp7Hgprz6GcWvVGtM1_g/edit?usp=sharing
[Unreal support matrix]: http://dnet.dneg.com/pages/viewpage.action?pageId=548086613
[PluginErrors]:http://dnet.dneg.com/display/VP/Resolve+Projects+being+unable+to+open+due+to+Plugin+missing+or+requiring+to+be+built?src=contextnavpagetreemode
[PluginCommandLine]:http://dnet.dneg.com/display/VP/How+To+Package+an+Unreal+Plugin+on+the+Command+Line
[UEAutomationTool]:https://docs.unrealengine.com/4.27/en-US/ProductionPipelines/BuildTools/AutomationTool
[RealtimeContact]:mailto:rnd-realtime@dneg.com
[RealtimeOnePager]:https://docs.google.com/document/d/1PNi8_Mm4_vtVPT6efRHiITJBCWa0ZREyc46t63_lZKQ/edit?usp=sharing
[RealtimeTDD]:https://docs.google.com/document/d/18XflNCz0MpbpWcXEGWCq9kIUHecJZW1bO8XVy9_VZp8/edit?usp=sharing
[SemVer]:http://semver.org
[PythonStyleGuide]:http://i/tools/SITE/doc/coding-standards/latest/standards/languages/python/python_style_guide.html
[CPPStyleGuide]:http://i/tools/SITE/doc/coding-standards/latest/standards/languages/cpp/cpp_style_guide.html
[CSharpStyleGuide]:mailto:lpla@dneg.com?subject=Why%20haven't%20you%20written%20the%20C%23%20coding%20styleguide%20yet.&body=I%20will%20use%20https%3A%2F%2Fgithub.com%2FDotNetAnalyzers%2FStyleCopAnalyzers%20while%20I%20wait.