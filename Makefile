.PHONY: validate validate-fen-assets

validate: validate-fen-assets

validate-fen-assets:
	python scripts/check_fen_assets.py
