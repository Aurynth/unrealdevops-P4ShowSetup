@Echo OFF
echo Running pytest with coverage enabled. Failure point if below 80%
call pytest -c .\pyproject-with-coverage.toml