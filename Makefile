# AstroCare local commands.
# Комментарии в Makefile — русские, цели — английские.

PY := backend/.venv/bin/python

.PHONY: setup data test run demo clean

setup:
	scripts/setup.sh

data:
	PYTHONPATH=$$(pwd) $(PY) -m data_pipeline.build_offline_bundle

test:
	scripts/test.sh

run:
	scripts/run.sh

demo:
	scripts/demo.sh

clean:
	rm -rf backend/.venv frontend/node_modules frontend/.next simulation_exports simulation_checkpoints .pytest_cache
