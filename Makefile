.PHONY: figures paper clean

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip

.venv/bin/python:
	python3 -m venv .venv
	$(PIP) install -r requirements.txt

figures: .venv/bin/python
	$(PYTHON) scripts/make_figures.py

paper: figures
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

clean:
	rm -f paper/*.aux paper/*.blg paper/*.fdb_latexmk paper/*.fls paper/*.log paper/*.out paper/*.toc paper/*.synctex.gz
