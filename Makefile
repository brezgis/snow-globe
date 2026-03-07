.PHONY: test test-quick test-full

test: test-quick

test-quick:
	npx vitest run

test-full:
	npx vitest run
	npx playwright test
