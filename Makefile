.PHONY: all pipeline dashboard serve clean dev dashboard-only

all: pipeline dashboard

pipeline:
	python pipeline/run_pipeline.py --sectors 1,2,3 --presentation

dashboard:
	cd SPACE && npx next build

serve:
	cd SPACE && npx serve out -l 3000

clean:
	rm -rf outputs/
	rm -rf SPACE/out/
	rm -rf SPACE/public/plots/
	rm -rf SPACE/outputs/

dev:
	cd SPACE && npx next dev

dashboard-only:
	cd SPACE && npx next build
