.PHONY: build clean preview publish

build:
	python3 setup.py bdist_wheel

clean:
	rm -Rf build dist *.egg-info

preview:
	pip3 install .

publish:
	twine upload --identity F4DD3CEDB0E24417 --sign --username xeger dist/*
