test:
	python -m pytest tests/unit_tests/cost_sim_test.py

coverage:
	python -m coverage run -m pytest tests
	python -m coverage report -m

coverage-html:
	python -m coverage run -m pytest tests
	python -m coverage html