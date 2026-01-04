.PHONY: build clean publish

build:
	pipenv run python3 setup.py bdist_wheel

clean:
	rm -Rf build dist *.egg-info

publish:
	pipenv run twine upload dist/*
