.PHONY: gather check check-dynamics check-operators sync-dynamics-includes sync-operators-includes sync-includes

gather:
	./gather_targets_from_examples.sh

check-dynamics:
	./check_dynamics.sh

check-operators:
	./check_post_processors.sh

check-includes:
	./check_includes.sh

check: check-dynamics check-operators check-includes

sync-dynamics-includes:
	./sync_dynamics_includes.sh

sync-operators-includes:
	./sync_post_processors_includes.sh

sync-includes: sync-dynamics-includes sync-operators-includes
