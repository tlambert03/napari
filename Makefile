.PHONY: docs clean gui-spec gui-build bundle

CLEANFILES := dist build

docs:
	make -C docs clean
	make -C docs html

install-gui:
	pip install -e .
	pip install pyinstaller

gui-spec:
	pyi-makespec -D -w -n napari napari/main.py

gui-build: clean
	pyinstaller --clean napari.spec

bundle: 
	bash ./bundle/build.sh

clean:
	rm -rf $(CLEANFILES)
