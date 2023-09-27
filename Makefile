.PHONY: build clean publish

build:
	python3 setup.py bdist_wheel

clean:
	rm -Rf build dist *.egg-info

publish:
	twine upload dist/*
